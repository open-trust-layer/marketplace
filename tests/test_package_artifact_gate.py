from __future__ import annotations

import base64
import csv
import hashlib
import io
import subprocess
import tempfile
import unittest
import warnings
import zipfile
from pathlib import Path
from unittest.mock import patch

from package_artifact_gate import (
    ArtifactGateError,
    SOURCE_DATE_EPOCH,
    _build_environment,
    _normalize_source_mtime,
    _verify_clean_source,
    audit_wheel,
    canonical_report_json,
    provenance_report,
)

PACKAGE = "open-layer-marketplace"
VERSION = "0.0.1.dev0"
WHEEL_FILENAME = "open_layer_marketplace-0.0.1.dev0-py3-none-any.whl"
DIST_INFO = "open_layer_marketplace-0.0.1.dev0.dist-info"
REQUIRED = {
    "marketplace/__init__.py": b"",
    "marketplace/runtime/__init__.py": b"",
    "marketplace/runtime/composition.py": b"# runtime\n",
    "marketplace/runtime/federation.py": b"# offline federation runtime\n",
    "marketplace/runtime/network_policy.py": b"# federation egress security policy\n",
    "marketplace/runtime/https_transport.py": b"# authorized HTTPS transport\n",
    "marketplace/runtime/record_retrieval.py": b"# authorized immutable Record retrieval\n",
    "marketplace/runtime/page_hydration.py": b"# bounded federation page hydration\n",
    "marketplace/runtime/continuation.py": b"# cursor-bound federation continuation planning\n",
    "marketplace/runtime/inbound_http_accept.py": b"# bounded inbound single-accept capability\n",
    "marketplace/runtime/inbound_http_connection.py": b"# bounded inbound single-connection transport\n",
    "marketplace/runtime/inbound_http_single_session.py": b"# bounded inbound single-session orchestrator\n",
    "marketplace/runtime/inbound_http_response_preparer_factory.py": b"# bounded inbound response-preparer composition factory\n",
    "marketplace/runtime/inbound_http_single_session_composition.py": b"# bounded inbound single-session composition root\n",
    "marketplace/runtime/inbound_tcp_listener.py": b"# bounded inbound listener construction\n",
    "marketplace/runtime/inbound_tcp_socket_factory.py": b"# bounded Python TCP socket factory\n",
    "marketplace/reference/__init__.py": b"",
    "marketplace/reference/record_v1.py": b"# record\n",
    "marketplace/reference/matching_v1.py": b"# matching\n",
    "marketplace/reference/federation_v1.py": b"# federation\n",
    "marketplace/reference/transport_json_v1.py": b"# strict OLP JSON transport codec\n",
    "marketplace/reference/record_retrieval_v1.py": b"# pinned OLP Record retrieval verifier\n",
}


def urlsafe_sha256(data: bytes) -> str:
    digest = hashlib.sha256(data).digest()
    return base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")


def write_wheel(
    path: Path,
    *,
    metadata_extra: str = "",
    wheel_extra: str = "",
    extra_members: dict[str, bytes] | None = None,
    tamper_record_for: str | None = None,
    symlink_member: str | None = None,
) -> None:
    members = dict(REQUIRED)
    members[f"{DIST_INFO}/METADATA"] = (
        "Metadata-Version: 2.4\n"
        f"Name: {PACKAGE}\n"
        f"Version: {VERSION}\n"
        f"{metadata_extra}"
        "\n"
    ).encode("utf-8")
    members[f"{DIST_INFO}/WHEEL"] = (
        "Wheel-Version: 1.0\n"
        "Generator: test\n"
        "Root-Is-Purelib: true\n"
        "Tag: py3-none-any\n"
        f"{wheel_extra}"
        "\n"
    ).encode("utf-8")
    if extra_members:
        members.update(extra_members)

    rows: list[list[str]] = []
    for name, data in sorted(members.items()):
        digest = urlsafe_sha256(data)
        if name == tamper_record_for:
            digest = "A" * 43
        rows.append([name, f"sha256={digest}", str(len(data))])
    record_name = f"{DIST_INFO}/RECORD"
    rows.append([record_name, "", ""])
    buffer = io.StringIO(newline="")
    csv.writer(buffer, lineterminator="\n").writerows(rows)
    members[record_name] = buffer.getvalue().encode("utf-8")

    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, data in sorted(members.items()):
            info = zipfile.ZipInfo(name, date_time=(2000, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, data)
        if symlink_member is not None:
            info = zipfile.ZipInfo(symlink_member, date_time=(2000, 1, 1, 0, 0, 0))
            info.external_attr = 0o120777 << 16
            archive.writestr(info, b"marketplace/__init__.py")


class PackageArtifactGateTests(unittest.TestCase):
    def wheel_path(self, temp_dir: str) -> Path:
        return Path(temp_dir) / WHEEL_FILENAME

    def test_valid_wheel_passes_content_metadata_and_record_audit(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = self.wheel_path(temp_dir)
            write_wheel(path)
            audit = audit_wheel(path, expected_name=PACKAGE, expected_version=VERSION)
            self.assertEqual(audit.package_name, PACKAGE)
            self.assertEqual(audit.package_version, VERSION)
            self.assertEqual(audit.dist_info, DIST_INFO)
            self.assertEqual(len(audit.sha256), 64)
            self.assertEqual(len(audit.payload_sha256), 64)

    def _assert_required_member_rejected_when_missing(self, member: str) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = self.wheel_path(temp_dir)
            missing = REQUIRED.pop(member)
            try:
                write_wheel(path)
            finally:
                REQUIRED[member] = missing
            with self.assertRaises(ArtifactGateError) as caught:
                audit_wheel(path, expected_name=PACKAGE, expected_version=VERSION)
            self.assertEqual(caught.exception.code, "WHEEL_REQUIRED_MEMBER")

    def test_missing_federation_runtime_member_is_rejected(self):
        self._assert_required_member_rejected_when_missing("marketplace/runtime/federation.py")

    def test_missing_network_policy_runtime_member_is_rejected(self):
        self._assert_required_member_rejected_when_missing("marketplace/runtime/network_policy.py")

    def test_missing_https_transport_runtime_member_is_rejected(self):
        self._assert_required_member_rejected_when_missing("marketplace/runtime/https_transport.py")

    def test_missing_record_retrieval_runtime_member_is_rejected(self):
        self._assert_required_member_rejected_when_missing("marketplace/runtime/record_retrieval.py")

    def test_missing_page_hydration_runtime_member_is_rejected(self):
        self._assert_required_member_rejected_when_missing("marketplace/runtime/page_hydration.py")

    def test_missing_continuation_runtime_member_is_rejected(self):
        self._assert_required_member_rejected_when_missing("marketplace/runtime/continuation.py")

    def test_missing_inbound_accept_runtime_member_is_rejected(self):
        self._assert_required_member_rejected_when_missing("marketplace/runtime/inbound_http_accept.py")

    def test_missing_inbound_connection_runtime_member_is_rejected(self):
        self._assert_required_member_rejected_when_missing("marketplace/runtime/inbound_http_connection.py")

    def test_missing_inbound_single_session_runtime_member_is_rejected(self):
        self._assert_required_member_rejected_when_missing("marketplace/runtime/inbound_http_single_session.py")

    def test_missing_inbound_response_preparer_factory_runtime_member_is_rejected(self):
        self._assert_required_member_rejected_when_missing("marketplace/runtime/inbound_http_response_preparer_factory.py")

    def test_missing_inbound_single_session_composition_runtime_member_is_rejected(self):
        self._assert_required_member_rejected_when_missing("marketplace/runtime/inbound_http_single_session_composition.py")

    def test_missing_inbound_tcp_listener_runtime_member_is_rejected(self):
        self._assert_required_member_rejected_when_missing("marketplace/runtime/inbound_tcp_listener.py")

    def test_missing_inbound_tcp_socket_factory_runtime_member_is_rejected(self):
        self._assert_required_member_rejected_when_missing("marketplace/runtime/inbound_tcp_socket_factory.py")

    def test_missing_federation_reference_member_is_rejected(self):
        self._assert_required_member_rejected_when_missing("marketplace/reference/federation_v1.py")

    def test_missing_transport_json_reference_member_is_rejected(self):
        self._assert_required_member_rejected_when_missing("marketplace/reference/transport_json_v1.py")

    def test_missing_record_retrieval_reference_member_is_rejected(self):
        self._assert_required_member_rejected_when_missing("marketplace/reference/record_retrieval_v1.py")

    def test_wrong_wheel_filename_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "bad.whl"
            write_wheel(path)
            with self.assertRaises(ArtifactGateError) as caught:
                audit_wheel(path, expected_name=PACKAGE, expected_version=VERSION)
            self.assertEqual(caught.exception.code, "WHEEL_FILENAME")

    def test_parent_traversal_member_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = self.wheel_path(temp_dir)
            write_wheel(path, extra_members={"../escape.txt": b"bad"})
            with self.assertRaises(ArtifactGateError) as caught:
                audit_wheel(path, expected_name=PACKAGE, expected_version=VERSION)
            self.assertEqual(caught.exception.code, "UNSAFE_WHEEL_PATH")

    def test_symlink_member_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = self.wheel_path(temp_dir)
            write_wheel(path, symlink_member="marketplace/link.py")
            with self.assertRaises(ArtifactGateError) as caught:
                audit_wheel(path, expected_name=PACKAGE, expected_version=VERSION)
            self.assertEqual(caught.exception.code, "WHEEL_SYMLINK")

    def test_duplicate_archive_member_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = self.wheel_path(temp_dir)
            write_wheel(path)
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", UserWarning)
                with zipfile.ZipFile(path, "a") as archive:
                    archive.writestr("marketplace/__init__.py", b"duplicate")
            with self.assertRaises(ArtifactGateError) as caught:
                audit_wheel(path, expected_name=PACKAGE, expected_version=VERSION)
            self.assertEqual(caught.exception.code, "WHEEL_DUPLICATE_MEMBER")

    def test_runtime_dependency_metadata_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = self.wheel_path(temp_dir)
            write_wheel(path, metadata_extra="Requires-Dist: requests>=2\n")
            with self.assertRaises(ArtifactGateError) as caught:
                audit_wheel(path, expected_name=PACKAGE, expected_version=VERSION)
            self.assertEqual(caught.exception.code, "WHEEL_METADATA_DEPENDENCY")

    def test_unexpected_repository_payload_root_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = self.wheel_path(temp_dir)
            write_wheel(path, extra_members={"tools/leak.py": b"secret = False\n"})
            with self.assertRaises(ArtifactGateError) as caught:
                audit_wheel(path, expected_name=PACKAGE, expected_version=VERSION)
            self.assertEqual(caught.exception.code, "WHEEL_PAYLOAD_ROOT")

    def test_tampered_record_hash_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = self.wheel_path(temp_dir)
            write_wheel(path, tamper_record_for="marketplace/reference/record_v1.py")
            with self.assertRaises(ArtifactGateError) as caught:
                audit_wheel(path, expected_name=PACKAGE, expected_version=VERSION)
            self.assertEqual(caught.exception.code, "WHEEL_RECORD_HASH")

    def test_entry_points_are_rejected(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = self.wheel_path(temp_dir)
            write_wheel(
                path,
                extra_members={f"{DIST_INFO}/entry_points.txt": b"[console_scripts]\nmarketplace=x:y\n"},
            )
            with self.assertRaises(ArtifactGateError) as caught:
                audit_wheel(path, expected_name=PACKAGE, expected_version=VERSION)
            self.assertEqual(caught.exception.code, "WHEEL_ENTRY_POINTS")

    def test_platform_specific_wheel_tag_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = self.wheel_path(temp_dir)
            write_wheel(path, wheel_extra="Tag: cp312-cp312-manylinux_x86_64\n")
            with self.assertRaises(ArtifactGateError) as caught:
                audit_wheel(path, expected_name=PACKAGE, expected_version=VERSION)
            self.assertEqual(caught.exception.code, "WHEEL_PLATFORM")

    def test_mtime_normalization_windows_fallback_requires_regular_path(self):
        path = Path("copied-source.py")
        with (
            patch("package_artifact_gate.os.utime", side_effect=[NotImplementedError, None]) as mocked_utime,
            patch.object(Path, "is_symlink", return_value=False),
        ):
            _normalize_source_mtime(path)
        self.assertEqual(mocked_utime.call_count, 2)
        self.assertEqual(mocked_utime.call_args_list[0].kwargs, {"follow_symlinks": False})
        self.assertEqual(mocked_utime.call_args_list[1].kwargs, {})

    def test_mtime_normalization_never_follows_symlink_on_windows_fallback(self):
        path = Path("copied-link")
        with (
            patch("package_artifact_gate.os.utime", side_effect=NotImplementedError) as mocked_utime,
            patch.object(Path, "is_symlink", return_value=True),
            self.assertRaises(ArtifactGateError) as caught,
        ):
            _normalize_source_mtime(path)
        self.assertEqual(caught.exception.code, "SOURCE_SYMLINK")
        self.assertEqual(mocked_utime.call_count, 1)

    def test_build_environment_fixes_reproducibility_controls_and_removes_pythonpath(self):
        env = _build_environment()
        self.assertEqual(env["SOURCE_DATE_EPOCH"], str(SOURCE_DATE_EPOCH))
        self.assertEqual(env["PYTHONHASHSEED"], "0")
        self.assertEqual(env["TZ"], "UTC")
        self.assertEqual(env["PIP_NO_INDEX"], "1")
        self.assertNotIn("PYTHONPATH", env)

    @patch("package_artifact_gate._run")
    def test_dirty_source_checkout_is_rejected_before_provenance(self, mocked_run):
        mocked_run.return_value = subprocess.CompletedProcess(
            ["git", "status"], 0, stdout=" M README.md\n?? local.txt\n", stderr=""
        )
        with self.assertRaises(ArtifactGateError) as caught:
            _verify_clean_source(Path("/example/repository"), 3.0)
        self.assertEqual(caught.exception.code, "SOURCE_NOT_CLEAN")

    def test_provenance_is_canonical_unsigned_unpublished_and_commit_bound(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = self.wheel_path(temp_dir)
            write_wheel(path)
            audit = audit_wheel(path, expected_name=PACKAGE, expected_version=VERSION)
            report = provenance_report(
                audit,
                source_commit="1" * 40,
                olp_source_commit="2" * 40,
                runtime_dependency_count=0,
            )
            self.assertFalse(report["signed"])
            self.assertFalse(report["published"])
            self.assertEqual(report["marketplace_source_commit"], "1" * 40)
            self.assertEqual(report["olp_source_commit"], "2" * 40)
            self.assertEqual(report["provenance_version"], 1)
            encoded = canonical_report_json(report)
            self.assertEqual(encoded, canonical_report_json(report))
            self.assertNotIn(" ", encoded)

    def test_provenance_rejects_invalid_source_commit(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = self.wheel_path(temp_dir)
            write_wheel(path)
            audit = audit_wheel(path, expected_name=PACKAGE, expected_version=VERSION)
            with self.assertRaises(ArtifactGateError) as caught:
                provenance_report(
                    audit,
                    source_commit="not-a-commit",
                    olp_source_commit="2" * 40,
                    runtime_dependency_count=0,
                )
            self.assertEqual(caught.exception.code, "SOURCE_COMMIT_FORMAT")


if __name__ == "__main__":
    unittest.main()