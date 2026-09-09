from __future__ import annotations

from dataclasses import FrozenInstanceError
import os
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch

from marketplace.application.auth_evidence_trust_ed25519 import (
    AuthenticationEvidenceTrustAnchor,
)
from marketplace.application.auth_startup_provisioning import (
    PROFILE_NAME,
    TRUST_ANCHOR_MANIFEST_FILENAME,
    VERIFICATION_METHOD_ATTESTATION_FILENAME,
    VERIFICATION_METHOD_CLAIMS_FILENAME,
    MarketplaceAuthenticationStartupProvisioning,
    MarketplaceAuthenticationStartupProvisioningError,
    _identity,
    _read_bounded,
    load_marketplace_authentication_startup_provisioning,
)
from marketplace.application.auth_trust_anchor_manifest import (
    AUTH_TRUST_ANCHOR_MANIFEST_MAX_BYTES,
    MarketplaceAuthenticationEvidenceTrustAnchorManifest,
    encode_marketplace_authentication_trust_anchor_manifest,
)
from marketplace.application.auth_verification_method_evidence import (
    AUTH_EVIDENCE_ATTESTATION_MAX_BYTES,
    AUTH_EVIDENCE_CLAIMS_MAX_BYTES,
    AuthenticationVerificationMethodEvidenceClaim,
    MarketplaceAuthenticationVerificationMethodEvidenceClaims,
    MarketplaceAuthenticationVerificationMethodEvidenceEnvelope,
    encode_marketplace_authentication_verification_method_evidence_claims,
)

AUTHORITY = "https://authority.example/auth"
PUBLIC_KEY = bytes(range(32))
ATTESTATION = b"opaque-public-attestation"


def _manifest() -> bytes:
    return encode_marketplace_authentication_trust_anchor_manifest(
        MarketplaceAuthenticationEvidenceTrustAnchorManifest(
            anchors=(
                AuthenticationEvidenceTrustAnchor(AUTHORITY, PUBLIC_KEY),
            )
        )
    )


def _claims() -> bytes:
    claim = AuthenticationVerificationMethodEvidenceClaim(
        verification_method="did:example:alice#key-1",
        controller_principal="did:example:alice",
        public_key=PUBLIC_KEY,
    )
    claims = MarketplaceAuthenticationVerificationMethodEvidenceClaims(
        authority=AUTHORITY,
        issued_at=100,
        expires_at=200,
        entries=(claim,),
    )
    return encode_marketplace_authentication_verification_method_evidence_claims(
        claims
    )


def _write_bundle(directory: Path) -> tuple[bytes, bytes, bytes]:
    manifest = _manifest()
    claims = _claims()
    attestation = ATTESTATION
    (directory / TRUST_ANCHOR_MANIFEST_FILENAME).write_bytes(manifest)
    (directory / VERIFICATION_METHOD_CLAIMS_FILENAME).write_bytes(claims)
    (directory / VERIFICATION_METHOD_ATTESTATION_FILENAME).write_bytes(
        attestation
    )
    return manifest, claims, attestation


def _stat_proxy(info: os.stat_result, **changes: int) -> SimpleNamespace:
    names = (
        "st_dev",
        "st_ino",
        "st_mode",
        "st_size",
        "st_mtime_ns",
        "st_ctime_ns",
        "st_nlink",
        "st_file_attributes",
    )
    values: dict[str, int] = {}
    for name in names:
        values[name] = int(getattr(info, name, 0))
    values.update(changes)
    return SimpleNamespace(**values)


class MarketplaceAuthenticationStartupProvisioningTests(unittest.TestCase):
    def test_profile_exact_bundle_and_frozen_state(self) -> None:
        self.assertEqual(
            PROFILE_NAME,
            "MARKETPLACE_APPLICATION_AUTH_STARTUP_PROVISIONING_V1",
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            manifest, claims, attestation = _write_bundle(root)
            loaded = load_marketplace_authentication_startup_provisioning(
                directory=str(root)
            )
        self.assertIsInstance(
            loaded, MarketplaceAuthenticationStartupProvisioning
        )
        self.assertEqual(loaded.trust_anchor_manifest, manifest)
        self.assertEqual(loaded.verification_method_evidence.claims_json, claims)
        self.assertEqual(
            loaded.verification_method_evidence.attestation, attestation
        )
        with self.assertRaises((FrozenInstanceError, AttributeError)):
            loaded.trust_anchor_manifest = b"changed"  # type: ignore[misc]

    def test_success_uses_exact_three_read_only_opens(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _write_bundle(root)
            real_open = open
            calls: list[tuple[str, str]] = []

            def tracked_open(path, mode="r", *args, **kwargs):
                calls.append((os.fspath(path), mode))
                return real_open(path, mode, *args, **kwargs)

            with patch("builtins.open", side_effect=tracked_open):
                load_marketplace_authentication_startup_provisioning(
                    directory=str(root)
                )

        self.assertEqual(len(calls), 3)
        self.assertEqual([mode for _path, mode in calls], ["rb", "rb", "rb"])
        self.assertEqual(
            [Path(path).name for path, _mode in calls],
            [
                TRUST_ANCHOR_MANIFEST_FILENAME,
                VERIFICATION_METHOD_CLAIMS_FILENAME,
                VERIFICATION_METHOD_ATTESTATION_FILENAME,
            ],
        )

    def test_relative_noncanonical_and_redirected_directory_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _write_bundle(root)
            invalid = (
                root.name,
                str(root) + os.sep,
            )
            for directory in invalid:
                with self.subTest(directory=directory):
                    with self.assertRaises(
                        MarketplaceAuthenticationStartupProvisioningError
                    ):
                        load_marketplace_authentication_startup_provisioning(
                            directory=directory
                        )
            with (
                patch(
                    (
                        "marketplace.application.auth_startup_provisioning."
                        "os.path.realpath"
                    ),
                    return_value=str(root.parent),
                ),
                self.assertRaises(
                    MarketplaceAuthenticationStartupProvisioningError
                ),
            ):
                load_marketplace_authentication_startup_provisioning(
                    directory=str(root)
                )

    def test_child_path_escape_fails_before_open(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _write_bundle(root)
            real_realpath = os.path.realpath
            target = str(root / VERIFICATION_METHOD_CLAIMS_FILENAME)

            def escaped_realpath(path, *, strict=False):
                if os.fspath(path) == target:
                    return str(root.parent / "outside-claims.json")
                return real_realpath(path, strict=strict)

            with (
                patch(
                    "marketplace.application.auth_startup_provisioning."
                    "os.path.realpath",
                    side_effect=escaped_realpath,
                ),
                self.assertRaises(
                    MarketplaceAuthenticationStartupProvisioningError
                ),
            ):
                load_marketplace_authentication_startup_provisioning(
                    directory=str(root)
                )

    def test_missing_empty_oversized_and_nonregular_inputs_fail(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _write_bundle(root)
            missing = root / VERIFICATION_METHOD_ATTESTATION_FILENAME
            missing.unlink()
            with self.assertRaises(MarketplaceAuthenticationStartupProvisioningError):
                load_marketplace_authentication_startup_provisioning(
                    directory=str(root)
                )

        cases = (
            (TRUST_ANCHOR_MANIFEST_FILENAME, b""),
            (
                VERIFICATION_METHOD_ATTESTATION_FILENAME,
                b"x" * (AUTH_EVIDENCE_ATTESTATION_MAX_BYTES + 1),
            ),
        )
        for filename, replacement in cases:
            with self.subTest(filename=filename):
                with tempfile.TemporaryDirectory() as temp_dir:
                    root = Path(temp_dir)
                    _write_bundle(root)
                    (root / filename).write_bytes(replacement)
                    with self.assertRaises(
                        MarketplaceAuthenticationStartupProvisioningError
                    ):
                        load_marketplace_authentication_startup_provisioning(
                            directory=str(root)
                        )

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _write_bundle(root)
            target = root / VERIFICATION_METHOD_ATTESTATION_FILENAME
            target.unlink()
            target.mkdir()
            with self.assertRaises(MarketplaceAuthenticationStartupProvisioningError):
                load_marketplace_authentication_startup_provisioning(
                    directory=str(root)
                )

    def test_reparse_marker_fails_closed_before_read(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _write_bundle(root)
            target = str(root / VERIFICATION_METHOD_CLAIMS_FILENAME)
            real_lstat = os.lstat

            def marked_lstat(path):
                info = real_lstat(path)
                if os.fspath(path) == target:
                    return _stat_proxy(info, st_file_attributes=0x400)
                return info

            with (
                patch(
                    "marketplace.application.auth_startup_provisioning.os.lstat",
                    side_effect=marked_lstat,
                ),
                self.assertRaises(
                    MarketplaceAuthenticationStartupProvisioningError
                ),
            ):
                load_marketplace_authentication_startup_provisioning(
                    directory=str(root)
                )

    def test_symlink_mode_fails_closed_before_read(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _write_bundle(root)
            target = str(root / VERIFICATION_METHOD_CLAIMS_FILENAME)
            real_lstat = os.lstat

            def linked_lstat(path):
                info = real_lstat(path)
                if os.fspath(path) == target:
                    return _stat_proxy(info, st_mode=0o120777)
                return info

            with (
                patch(
                    "marketplace.application.auth_startup_provisioning.os.lstat",
                    side_effect=linked_lstat,
                ),
                self.assertRaises(
                    MarketplaceAuthenticationStartupProvisioningError
                ),
            ):
                load_marketplace_authentication_startup_provisioning(
                    directory=str(root)
                )

    def test_unstable_open_file_identity_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "input.bin"
            path.write_bytes(b"stable")
            expected = _identity(os.lstat(path))
            real_fstat = os.fstat
            calls = 0

            def changing_fstat(fd):
                nonlocal calls
                calls += 1
                info = real_fstat(fd)
                if calls == 2:
                    return _stat_proxy(info, st_mtime_ns=info.st_mtime_ns + 1)
                return info

            with (
                patch(
                    "marketplace.application.auth_startup_provisioning.os.fstat",
                    side_effect=changing_fstat,
                ),
                self.assertRaises(
                    MarketplaceAuthenticationStartupProvisioningError
                ),
            ):
                _read_bounded(str(path), expected, 16)

    def test_canonical_validation_and_public_error_are_nonreflective(self) -> None:
        marker = b"sensitive-filesystem-or-trust-details"
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _write_bundle(root)
            (root / TRUST_ANCHOR_MANIFEST_FILENAME).write_bytes(marker)
            with self.assertRaises(
                MarketplaceAuthenticationStartupProvisioningError
            ) as caught:
                load_marketplace_authentication_startup_provisioning(
                    directory=str(root)
                )
        self.assertEqual(
            str(caught.exception),
            "authentication startup provisioning is invalid or unavailable",
        )
        self.assertNotIn(marker.decode("ascii"), str(caught.exception))
        self.assertNotIn(temp_dir, str(caught.exception))

    def test_direct_bundle_constructor_cannot_bypass_canonicality(self) -> None:
        envelope = MarketplaceAuthenticationVerificationMethodEvidenceEnvelope(
            claims_json=_claims(),
            attestation=ATTESTATION,
        )
        with self.assertRaises(MarketplaceAuthenticationStartupProvisioningError):
            MarketplaceAuthenticationStartupProvisioning(
                trust_anchor_manifest=b"{}",
                verification_method_evidence=envelope,
            )


if __name__ == "__main__":
    unittest.main()
