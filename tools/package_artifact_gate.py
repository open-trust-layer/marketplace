"""Reproducible Marketplace wheel and local provenance acceptance gate.

This tool creates only temporary build artifacts. It does not publish, sign, or
upload a distribution and it never enables package-index resolution.
"""
from __future__ import annotations

import argparse
import base64
import csv
import hashlib
import importlib.metadata
import io
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import tomllib
import zipfile
from dataclasses import dataclass
from email.parser import BytesParser
from email.policy import default as email_policy
from pathlib import Path, PurePosixPath
from typing import Mapping, Sequence

REVIEWED_BUILD_BACKEND_VERSION = "80.9.0"
SOURCE_DATE_EPOCH = 946684800  # 2000-01-01T00:00:00Z; stable archive timestamp.
DEFAULT_TIMEOUT_SECONDS = 90.0
EXPECTED_PACKAGE_NAME = "open-layer-marketplace"
_DEV_VERSION_RE = re.compile(r"^0\.0\.\d+\.dev\d+$")
_HEX_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_HEX_COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
_REQUIRED_PACKAGE_MEMBERS = {
    "marketplace/__init__.py",
    "marketplace/runtime/__init__.py",
    "marketplace/runtime/composition.py",
    "marketplace/runtime/federation.py",
    "marketplace/runtime/network_policy.py",
    "marketplace/runtime/https_transport.py",
    "marketplace/runtime/record_retrieval.py",
    "marketplace/runtime/page_hydration.py",
    "marketplace/runtime/continuation.py",
    "marketplace/runtime/inbound_http_accept.py",
    "marketplace/runtime/inbound_http_connection.py",
    "marketplace/runtime/inbound_http_single_session.py",
    "marketplace/runtime/inbound_http_response_preparer_factory.py",
    "marketplace/runtime/inbound_http_single_session_composition.py",
    "marketplace/runtime/inbound_http_end_to_end_composition.py",
    "marketplace/runtime/inbound_tcp_listener.py",
    "marketplace/runtime/inbound_tcp_socket_factory.py",
    "marketplace/reference/__init__.py",
    "marketplace/reference/record_v1.py",
    "marketplace/reference/matching_v1.py",
    "marketplace/reference/federation_v1.py",
    "marketplace/reference/transport_json_v1.py",
    "marketplace/reference/record_retrieval_v1.py",
}


class ArtifactGateError(RuntimeError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class WheelAudit:
    filename: str
    sha256: str
    payload_sha256: str
    package_name: str
    package_version: str
    member_count: int
    dist_info: str


def _fail(code: str, message: str) -> None:
    raise ArtifactGateError(code, message)


def _sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _urlsafe_sha256(data: bytes) -> str:
    digest = hashlib.sha256(data).digest()
    return base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")


def _wheel_component(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9.]+", "_", value)


def _run(
    argv: Sequence[str],
    *,
    cwd: Path,
    env: Mapping[str, str],
    timeout: float,
    label: str,
) -> subprocess.CompletedProcess[str]:
    try:
        result = subprocess.run(
            list(argv),
            cwd=cwd,
            env=dict(env),
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        _fail("COMMAND_TIMEOUT", f"{label} exceeded {timeout:g}s timeout")
    except OSError as exc:
        _fail("COMMAND_START_FAILED", f"{label} could not start: {exc}")
    if result.returncode != 0:
        detail = "\n".join(part for part in (result.stdout.strip(), result.stderr.strip()) if part)
        suffix = f"\n{detail}" if detail else ""
        _fail("COMMAND_FAILED", f"{label} failed with exit code {result.returncode}{suffix}")
    return result


def _project_metadata(repo_root: Path) -> tuple[str, str, int]:
    path = repo_root / "pyproject.toml"
    try:
        document = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError) as exc:
        _fail("PYPROJECT_PARSE", f"could not parse {path}: {exc}")
    project = document.get("project")
    if not isinstance(project, dict):
        _fail("PYPROJECT_PROJECT", "pyproject project table is required")
    name = project.get("name")
    version = project.get("version")
    dependencies = project.get("dependencies")
    if name != EXPECTED_PACKAGE_NAME:
        _fail("PACKAGE_NAME", f"expected package name {EXPECTED_PACKAGE_NAME!r}, got {name!r}")
    if not isinstance(version, str) or not _DEV_VERSION_RE.fullmatch(version):
        _fail("PACKAGE_VERSION", "package version MUST remain experimental 0.0.N.devN")
    if dependencies != []:
        _fail("RUNTIME_DEPENDENCIES", "base runtime dependency list MUST remain empty")
    if project.get("optional-dependencies") not in (None, {}):
        _fail("OPTIONAL_DEPENDENCIES", "public-index optional dependencies are not permitted")
    return name, version, 0


def _read_olp_pin(repo_root: Path) -> str:
    path = repo_root / "conformance" / "olp-source-pin.txt"
    try:
        value = path.read_text(encoding="ascii").strip()
    except (OSError, UnicodeDecodeError) as exc:
        _fail("OLP_PIN_READ", f"could not read OLP source pin: {exc}")
    if not _HEX_COMMIT_RE.fullmatch(value):
        _fail("OLP_PIN_FORMAT", "OLP source pin MUST be a lowercase 40-hex Git commit")
    return value


def _source_commit(repo_root: Path, timeout: float) -> str:
    result = _run(
        ("git", "rev-parse", "HEAD"),
        cwd=repo_root,
        env=dict(os.environ),
        timeout=timeout,
        label="Marketplace source commit lookup",
    )
    value = result.stdout.strip()
    if not _HEX_COMMIT_RE.fullmatch(value):
        _fail("SOURCE_COMMIT_FORMAT", f"git returned invalid source commit {value!r}")
    return value


def _verify_clean_source(repo_root: Path, timeout: float) -> None:
    """Prevent provenance from attributing modified bytes to an unmodified HEAD."""
    result = _run(
        ("git", "status", "--porcelain=v1", "--untracked-files=all"),
        cwd=repo_root,
        env=dict(os.environ),
        timeout=timeout,
        label="Marketplace source cleanliness check",
    )
    if result.stdout.strip():
        _fail(
            "SOURCE_NOT_CLEAN",
            "artifact provenance requires a clean source checkout; commit or remove worktree changes first",
        )


def _verify_build_backend() -> None:
    try:
        actual = importlib.metadata.version("setuptools")
    except importlib.metadata.PackageNotFoundError:
        _fail("BUILD_BACKEND_MISSING", "reviewed setuptools build backend is not installed")
    if actual != REVIEWED_BUILD_BACKEND_VERSION:
        _fail(
            "BUILD_BACKEND_MISMATCH",
            f"expected setuptools {REVIEWED_BUILD_BACKEND_VERSION}, got {actual}",
        )


def _build_environment() -> dict[str, str]:
    env = dict(os.environ)
    env.pop("PYTHONPATH", None)
    env.update(
        {
            "PIP_NO_INDEX": "1",
            "PIP_NO_INPUT": "1",
            "PIP_DISABLE_PIP_VERSION_CHECK": "1",
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONNOUSERSITE": "1",
            "PYTHONHASHSEED": "0",
            "SOURCE_DATE_EPOCH": str(SOURCE_DATE_EPOCH),
            "TZ": "UTC",
            "LANG": "C.UTF-8",
            "LC_ALL": "C.UTF-8",
        }
    )
    return env


def _normalize_source_mtime(path: Path) -> None:
    """Normalize one copied path without weakening symlink safety on Windows."""
    timestamp = (SOURCE_DATE_EPOCH, SOURCE_DATE_EPOCH)
    try:
        os.utime(path, timestamp, follow_symlinks=False)
        return
    except NotImplementedError:
        # Windows does not implement follow_symlinks=False for os.utime.
        # Falling back is safe only after an explicit no-symlink check.
        if path.is_symlink():
            _fail("SOURCE_SYMLINK", f"copied source path MUST NOT be a symlink: {path}")
    except OSError as exc:
        _fail("SOURCE_MTIME_NORMALIZATION", f"could not normalize {path}: {exc}")

    try:
        os.utime(path, timestamp)
    except OSError as exc:
        _fail("SOURCE_MTIME_NORMALIZATION", f"could not normalize {path}: {exc}")


def _copy_source(repo_root: Path, destination: Path) -> None:
    shutil.copytree(
        repo_root,
        destination,
        ignore=shutil.ignore_patterns(
            ".git",
            "__pycache__",
            ".pytest_cache",
            ".mypy_cache",
            "build",
            "dist",
            "*.egg-info",
            "*.whl",
        ),
    )
    # Normalize copied-source mtimes as an additional defense against archive
    # metadata variance. The developer worktree is never mutated.
    for path in sorted(destination.rglob("*"), key=lambda item: len(item.parts), reverse=True):
        _normalize_source_mtime(path)
    _normalize_source_mtime(destination)


def _build_wheel(repo_root: Path, build_root: Path, timeout: float, label: str) -> Path:
    source_root = build_root / "source"
    wheel_dir = build_root / "wheel"
    wheel_dir.mkdir(parents=True)
    _copy_source(repo_root, source_root)
    _run(
        (
            sys.executable,
            "-m",
            "pip",
            "wheel",
            "--no-deps",
            "--no-build-isolation",
            "--wheel-dir",
            str(wheel_dir),
            str(source_root),
        ),
        cwd=build_root,
        env=_build_environment(),
        timeout=timeout,
        label=label,
    )
    wheels = sorted(wheel_dir.glob("*.whl"))
    if len(wheels) != 1:
        _fail("WHEEL_COUNT", f"{label} MUST produce exactly one wheel; found {len(wheels)}")
    return wheels[0]


def _validate_member_path(name: str) -> None:
    if not name or "\\" in name:
        _fail("UNSAFE_WHEEL_PATH", f"wheel member has non-canonical path {name!r}")
    path = PurePosixPath(name)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        _fail("UNSAFE_WHEEL_PATH", f"wheel member has unsafe path {name!r}")


def _metadata_message(data: bytes, label: str):
    try:
        return BytesParser(policy=email_policy).parsebytes(data)
    except Exception as exc:  # email parser errors vary by malformed input.
        _fail("WHEEL_METADATA_PARSE", f"could not parse {label}: {exc}")


def _verify_record(
    archive: zipfile.ZipFile,
    names: tuple[str, ...],
    dist_info: str,
) -> None:
    record_name = f"{dist_info}/RECORD"
    try:
        record_text = archive.read(record_name).decode("utf-8")
    except (KeyError, UnicodeDecodeError) as exc:
        _fail("WHEEL_RECORD_READ", f"could not read wheel RECORD: {exc}")
    try:
        rows = list(csv.reader(io.StringIO(record_text)))
    except csv.Error as exc:
        _fail("WHEEL_RECORD_PARSE", f"could not parse wheel RECORD: {exc}")

    expected_names = {name for name in names if not name.endswith("/")}
    seen: set[str] = set()
    for row in rows:
        if len(row) != 3:
            _fail("WHEEL_RECORD_SHAPE", "each RECORD row MUST contain path, hash, size")
        member, hash_field, size_field = row
        if member in seen:
            _fail("WHEEL_RECORD_DUPLICATE", f"RECORD repeats member {member!r}")
        seen.add(member)
        if member not in expected_names:
            _fail("WHEEL_RECORD_EXTRA", f"RECORD names absent member {member!r}")
        if member == record_name:
            if hash_field or size_field:
                _fail("WHEEL_RECORD_SELF_HASH", "RECORD self-entry MUST omit hash and size")
            continue
        if not hash_field.startswith("sha256=") or not size_field.isdigit():
            _fail("WHEEL_RECORD_HASH", f"invalid RECORD hash/size for {member!r}")
        data = archive.read(member)
        if hash_field != "sha256=" + _urlsafe_sha256(data):
            _fail("WHEEL_RECORD_HASH", f"RECORD SHA-256 mismatch for {member!r}")
        if int(size_field) != len(data):
            _fail("WHEEL_RECORD_SIZE", f"RECORD size mismatch for {member!r}")
    if seen != expected_names:
        missing = sorted(expected_names - seen)
        extra = sorted(seen - expected_names)
        _fail("WHEEL_RECORD_COVERAGE", f"RECORD coverage mismatch; missing={missing}, extra={extra}")


def _normalized_payload_digest(archive: zipfile.ZipFile, names: tuple[str, ...], dist_info: str) -> str:
    digest = hashlib.sha256()
    record_name = f"{dist_info}/RECORD"
    for name in sorted(name for name in names if not name.endswith("/") and name != record_name):
        data = archive.read(name)
        digest.update(name.encode("utf-8"))
        digest.update(b"\0")
        digest.update(hashlib.sha256(data).digest())
        digest.update(b"\0")
    return digest.hexdigest()


def audit_wheel(path: Path, *, expected_name: str, expected_version: str) -> WheelAudit:
    expected_filename = (
        f"{_wheel_component(expected_name)}-{_wheel_component(expected_version)}-py3-none-any.whl"
    )
    if path.name != expected_filename:
        _fail("WHEEL_FILENAME", f"expected wheel filename {expected_filename!r}, got {path.name!r}")
    wheel_sha = _sha256_path(path)
    if not _HEX_SHA256_RE.fullmatch(wheel_sha):
        _fail("WHEEL_HASH", "internal wheel SHA-256 formatting failure")
    try:
        archive = zipfile.ZipFile(path, "r")
    except (OSError, zipfile.BadZipFile) as exc:
        _fail("WHEEL_OPEN", f"could not open wheel: {exc}")
    with archive:
        infos = archive.infolist()
        names = tuple(info.filename for info in infos)
        if len(names) != len(set(names)):
            _fail("WHEEL_DUPLICATE_MEMBER", "wheel MUST NOT contain duplicate member names")
        for info in infos:
            _validate_member_path(info.filename)
            mode = (info.external_attr >> 16) & 0xFFFF
            if mode and stat.S_ISLNK(mode):
                _fail("WHEEL_SYMLINK", f"wheel member MUST NOT be a symlink: {info.filename}")

        top_levels = {PurePosixPath(name).parts[0] for name in names}
        dist_infos = sorted(root for root in top_levels if root.endswith(".dist-info"))
        if len(dist_infos) != 1:
            _fail("WHEEL_DIST_INFO", f"wheel MUST contain exactly one .dist-info root; found {dist_infos}")
        dist_info = dist_infos[0]
        expected_dist_info = f"{_wheel_component(expected_name)}-{_wheel_component(expected_version)}.dist-info"
        if dist_info != expected_dist_info:
            _fail("WHEEL_DIST_INFO", f"expected dist-info {expected_dist_info!r}, got {dist_info!r}")
        if top_levels != {"marketplace", dist_info}:
            _fail("WHEEL_PAYLOAD_ROOT", f"unexpected wheel top-level payload: {sorted(top_levels)}")

        missing_members = sorted(_REQUIRED_PACKAGE_MEMBERS - set(names))
        if missing_members:
            _fail("WHEEL_REQUIRED_MEMBER", f"wheel is missing required package members: {missing_members}")

        metadata_name = f"{dist_info}/METADATA"
        wheel_name = f"{dist_info}/WHEEL"
        record_name = f"{dist_info}/RECORD"
        for required in (metadata_name, wheel_name, record_name):
            if required not in names:
                _fail("WHEEL_REQUIRED_MEMBER", f"wheel is missing {required}")
        if f"{dist_info}/entry_points.txt" in names:
            _fail("WHEEL_ENTRY_POINTS", "wheel MUST NOT contain console/plugin entry points")

        metadata = _metadata_message(archive.read(metadata_name), "METADATA")
        if metadata.get("Name") != expected_name:
            _fail("WHEEL_METADATA_NAME", f"wheel Name mismatch: {metadata.get('Name')!r}")
        if metadata.get("Version") != expected_version:
            _fail("WHEEL_METADATA_VERSION", f"wheel Version mismatch: {metadata.get('Version')!r}")
        if metadata.get_all("Requires-Dist"):
            _fail("WHEEL_METADATA_DEPENDENCY", "wheel MUST NOT declare Requires-Dist")
        if metadata.get_all("Provides-Extra"):
            _fail("WHEEL_METADATA_EXTRA", "wheel MUST NOT declare package extras")

        wheel_metadata = _metadata_message(archive.read(wheel_name), "WHEEL")
        if wheel_metadata.get("Root-Is-Purelib", "").lower() != "true":
            _fail("WHEEL_PLATFORM", "wheel MUST be purelib")
        tags = wheel_metadata.get_all("Tag") or []
        if tags != ["py3-none-any"]:
            _fail("WHEEL_PLATFORM", f"wheel MUST have exactly Tag: py3-none-any; got {tags}")

        _verify_record(archive, names, dist_info)
        payload_sha = _normalized_payload_digest(archive, names, dist_info)

    return WheelAudit(
        filename=path.name,
        sha256=wheel_sha,
        payload_sha256=payload_sha,
        package_name=expected_name,
        package_version=expected_version,
        member_count=len(names),
        dist_info=dist_info,
    )


def provenance_report(
    audit: WheelAudit,
    *,
    source_commit: str,
    olp_source_commit: str,
    runtime_dependency_count: int,
) -> dict[str, object]:
    if not _HEX_COMMIT_RE.fullmatch(source_commit):
        _fail("SOURCE_COMMIT_FORMAT", "Marketplace source commit MUST be lowercase 40-hex")
    if not _HEX_COMMIT_RE.fullmatch(olp_source_commit):
        _fail("OLP_PIN_FORMAT", "OLP source commit MUST be lowercase 40-hex")
    if runtime_dependency_count != 0:
        _fail("RUNTIME_DEPENDENCIES", "provenance requires zero declared runtime dependencies")
    return {
        "artifact_sha256": audit.sha256,
        "build_backend": {
            "name": "setuptools",
            "version": REVIEWED_BUILD_BACKEND_VERSION,
        },
        "declared_runtime_dependency_count": runtime_dependency_count,
        "marketplace_source_commit": source_commit,
        "olp_source_commit": olp_source_commit,
        "package_name": audit.package_name,
        "package_version": audit.package_version,
        "payload_sha256": audit.payload_sha256,
        "provenance_schema": "marketplace-local-artifact-provenance",
        "provenance_version": 1,
        "reference_adapters_present": True,
        "signed": False,
        "source_date_epoch": SOURCE_DATE_EPOCH,
        "published": False,
        "verification_scope": "local-reproducible-wheel-build-and-content-audit",
        "wheel_filename": audit.filename,
    }


def canonical_report_json(report: Mapping[str, object]) -> str:
    return json.dumps(dict(report), sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def run_gate(repo_root: Path, *, timeout: float = DEFAULT_TIMEOUT_SECONDS) -> dict[str, object]:
    if timeout <= 0:
        _fail("INVALID_TIMEOUT", "timeout MUST be greater than zero")
    repo_root = repo_root.resolve()
    if not repo_root.is_dir():
        _fail("REPO_ROOT", f"repository root does not exist: {repo_root}")
    _verify_clean_source(repo_root, timeout)
    _verify_build_backend()
    package_name, package_version, dependency_count = _project_metadata(repo_root)
    source_commit = _source_commit(repo_root, timeout)
    olp_pin = _read_olp_pin(repo_root)

    with tempfile.TemporaryDirectory(prefix="marketplace-artifact-gate-") as temp_dir:
        temp_root = Path(temp_dir).resolve()
        wheel_a = _build_wheel(repo_root, temp_root / "build-a", timeout, "reproducible wheel build A")
        wheel_b = _build_wheel(repo_root, temp_root / "build-b", timeout, "reproducible wheel build B")
        audit_a = audit_wheel(wheel_a, expected_name=package_name, expected_version=package_version)
        audit_b = audit_wheel(wheel_b, expected_name=package_name, expected_version=package_version)

        if audit_a.filename != audit_b.filename:
            _fail("WHEEL_FILENAME_MISMATCH", f"wheel filenames differ: {audit_a.filename} vs {audit_b.filename}")
        if audit_a.sha256 != audit_b.sha256:
            _fail("WHEEL_REPRODUCIBILITY", f"wheel SHA-256 differs: {audit_a.sha256} vs {audit_b.sha256}")
        if wheel_a.read_bytes() != wheel_b.read_bytes():
            _fail("WHEEL_REPRODUCIBILITY", "wheel bytes differ despite equal filename/hash checks")
        if audit_a != audit_b:
            _fail("WHEEL_AUDIT_MISMATCH", "independent wheel audits differ")

        report = provenance_report(
            audit_a,
            source_commit=source_commit,
            olp_source_commit=olp_pin,
            runtime_dependency_count=dependency_count,
        )
        encoded = canonical_report_json(report)
        if encoded != canonical_report_json(report):
            _fail("PROVENANCE_NONDETERMINISTIC", "canonical provenance encoding is not stable")

        print(
            "Marketplace wheel reproducibility PASS: "
            f"{audit_a.filename} sha256={audit_a.sha256}"
        )
        print(
            "Marketplace wheel content audit PASS: "
            f"{audit_a.member_count} members payload_sha256={audit_a.payload_sha256}"
        )
        print("Marketplace artifact provenance: " + encoded)
        return report


def _parser() -> argparse.ArgumentParser:
    default_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description="Verify reproducible Marketplace wheel artifacts and local provenance.")
    parser.add_argument("--repo-root", type=Path, default=default_root)
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT_SECONDS)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        run_gate(args.repo_root, timeout=args.timeout)
    except ArtifactGateError as exc:
        print(f"Marketplace artifact gate FAIL [{exc.code}]: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())