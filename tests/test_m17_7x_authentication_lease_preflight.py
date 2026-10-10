"""M17.7X/Y/Z: isolated signed-lease diagnostics, no runtime or PostgreSQL."""
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
import hashlib
import tempfile
import unittest
from unittest.mock import patch

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from marketplace.application.auth_evidence_trust_ed25519 import (
    AuthenticationEvidenceTrustAnchor,
    build_marketplace_authentication_evidence_trust_transcript,
)
from marketplace.application.auth_trust_anchor_manifest import (
    MarketplaceAuthenticationEvidenceTrustAnchorManifest,
    encode_marketplace_authentication_trust_anchor_manifest,
)
from marketplace.application.auth_verification_method_evidence import (
    AuthenticationVerificationMethodEvidenceClaim,
    MarketplaceAuthenticationVerificationMethodEvidenceClaims,
    encode_marketplace_authentication_verification_method_evidence_claims,
)
from marketplace.application.auth_startup_provisioning import (
    TRUST_ANCHOR_MANIFEST_FILENAME,
    VERIFICATION_METHOD_CLAIMS_FILENAME,
    VERIFICATION_METHOD_ATTESTATION_FILENAME,
)
from tools.marketplace_authentication_lease_preflight import (
    ProvisioningLeasePreflightError,
    check_provisioning_lease,
    main,
)

AT_TIME = 1_000


class M177XAuthenticationLeasePreflightTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.folder = Path(self.tmp.name) / "auth"
        self.folder.mkdir()
        self._write_bundle()

    def _write_bundle(self, *, issued=900, expires=1_100, second_window=None,
                      second_principal="did:example:buyer"):
        key = Ed25519PrivateKey.generate()
        pub = key.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
        manifest = encode_marketplace_authentication_trust_anchor_manifest(
            MarketplaceAuthenticationEvidenceTrustAnchorManifest(
                anchors=(AuthenticationEvidenceTrustAnchor(
                    authority="https://authority.example/auth",
                    public_key=pub,
                ),),
            ),
        )
        entries = (AuthenticationVerificationMethodEvidenceClaim(
            verification_method="did:example:seller#key-1",
            controller_principal="did:example:seller",
            public_key=pub,
            valid_from=issued,
            valid_until=expires,
        ),)
        if second_window is not None:
            entries += (AuthenticationVerificationMethodEvidenceClaim(
                verification_method="did:example:buyer#key-1",
                controller_principal=second_principal,
                public_key=pub,
                valid_from=second_window[0],
                valid_until=second_window[1],
            ),)
        claims = encode_marketplace_authentication_verification_method_evidence_claims(
            MarketplaceAuthenticationVerificationMethodEvidenceClaims(
                authority="https://authority.example/auth",
                issued_at=issued,
                expires_at=expires,
                entries=entries,
            ),
        )
        attestation = key.sign(build_marketplace_authentication_evidence_trust_transcript(
            authority="https://authority.example/auth",
            claims_sha256=hashlib.sha256(claims).digest(),
        ))
        (self.folder / TRUST_ANCHOR_MANIFEST_FILENAME).write_bytes(manifest)
        (self.folder / VERIFICATION_METHOD_CLAIMS_FILENAME).write_bytes(claims)
        (self.folder / VERIFICATION_METHOD_ATTESTATION_FILENAME).write_bytes(attestation)

    def _check(self, *, now=AT_TIME, minimum=30, principals=1):
        return check_provisioning_lease(
            str(self.folder), at_time=now, minimum_remaining_seconds=minimum,
            minimum_distinct_principals=principals,
        )

    def _expect(self, code, *, now=AT_TIME, minimum=30, principals=1):
        with self.assertRaises(ProvisioningLeasePreflightError) as ctx:
            self._check(now=now, minimum=minimum, principals=principals)
        self.assertEqual(ctx.exception.code, code)

    def test_valid_attestation_and_lease_pass(self):
        self.assertEqual(self._check(), (100, 1))

    def test_at_exact_expiry_fails_closed(self):
        self._expect("LEASE_EXPIRED", now=1_100)

    def test_not_yet_valid_fails_closed(self):
        self._expect("LEASE_NOT_YET_VALID", now=899)

    def test_insufficient_remaining_time_fails_closed(self):
        self._expect("LEASE_TOO_SHORT", minimum=101)
        self.assertEqual(self._check(minimum=100), (100, 1))

    def test_expired_valid_signed_evidence_yields_specific_code(self):
        self._write_bundle(issued=500, expires=950)
        self._expect("LEASE_EXPIRED")

    def test_invalid_signature_never_masquerades_as_expiry(self):
        self._write_bundle(issued=500, expires=950)
        path = self.folder / VERIFICATION_METHOD_ATTESTATION_FILENAME
        path.write_bytes(bytes(len(path.read_bytes())))
        self._expect("PROVISIONING_INVALID")

    def test_two_identities_report_the_shorter_effective_lease(self):
        self._write_bundle(second_window=(950, 1070))
        self.assertEqual(self._check(), (70, 2))

    def test_second_identity_expired_while_signed_bundle_valid(self):
        self._write_bundle(second_window=(900, 990))
        self._expect("IDENTITY_EXPIRED")

    def test_second_identity_not_yet_valid_while_bundle_valid(self):
        self._write_bundle(second_window=(1001, 1090))
        self._expect("IDENTITY_NOT_YET_VALID")

    def test_second_identity_has_insufficient_remaining_lease(self):
        self._write_bundle(second_window=(950, 1020))
        self._expect("IDENTITY_LEASE_TOO_SHORT", minimum=21)
        self.assertEqual(self._check(minimum=20), (20, 2))

    def test_invalid_attestation_is_not_misreported_as_identity_expiry(self):
        self._write_bundle(second_window=(900, 990))
        path = self.folder / VERIFICATION_METHOD_ATTESTATION_FILENAME
        path.write_bytes(bytes(len(path.read_bytes())))
        self._expect("PROVISIONING_INVALID")

    def test_distinct_two_party_controllers_pass(self):
        self._write_bundle(second_window=(950, 1070))
        self.assertEqual(self._check(principals=2), (70, 2))

    def test_two_methods_same_controller_fail_two_party_guard(self):
        self._write_bundle(
            second_window=(950, 1070),
            second_principal="did:example:seller",
        )
        self.assertEqual(self._check(principals=1), (70, 2))
        self._expect("DISTINCT_PRINCIPALS_INSUFFICIENT", principals=2)

    def test_only_one_method_fails_two_party_guard(self):
        self._expect("DISTINCT_PRINCIPALS_INSUFFICIENT", principals=2)

    def test_invalid_principal_guard_types_and_bounds(self):
        for count in (True, False, 0, -1, 1.5, "2", 999):
            with self.subTest(count=count):
                self._expect_invalid_guard(count)

    def _expect_invalid_guard(self, count):
        with self.assertRaises(ProvisioningLeasePreflightError) as ctx:
            self._check(principals=count)
        self.assertEqual(ctx.exception.code, "MINIMUM_PRINCIPALS_INVALID")

    def test_invalid_signature_does_not_masquerade_as_principal_gap(self):
        self._write_bundle(second_window=(950, 1070),
                           second_principal="did:example:seller")
        path = self.folder / VERIFICATION_METHOD_ATTESTATION_FILENAME
        path.write_bytes(bytes(len(path.read_bytes())))
        self._expect("PROVISIONING_INVALID", principals=2)

    def test_cli_two_party_rejects_one_controller_without_reflecting_identity(self):
        stdout, stderr = StringIO(), StringIO()
        with patch("tools.marketplace_authentication_lease_preflight.time.time",
                   return_value=AT_TIME):
            with redirect_stdout(stdout), redirect_stderr(stderr):
                exit_code = main([
                    "--authentication-provisioning-directory", str(self.folder),
                    "--minimum-remaining-seconds", "30",
                    "--minimum-distinct-principals", "2",
                ])
        self.assertEqual(exit_code, 1)
        self.assertEqual(stdout.getvalue(), "")
        self.assertEqual(stderr.getvalue().strip(),
                         "status=FAIL code=DISTINCT_PRINCIPALS_INSUFFICIENT")
        self.assertNotIn("did:example", stderr.getvalue())
        self.assertNotIn(str(self.folder), stderr.getvalue())

    def test_missing_canonical_evidence_fails_closed(self):
        (self.folder / VERIFICATION_METHOD_CLAIMS_FILENAME).unlink()
        self._expect("PROVISIONING_INVALID")

    def test_invalid_input_types_and_bounds(self):
        for directory in ("relative/path", "", None):
            with self.subTest(directory=directory):
                with self.assertRaises(ProvisioningLeasePreflightError) as ctx:
                    check_provisioning_lease(directory, at_time=AT_TIME)
                self.assertEqual(ctx.exception.code, "PROVISIONING_DIRECTORY_INVALID")
        for at_time in (True, -1, 1.5):
            with self.subTest(at_time=at_time):
                with self.assertRaises(ProvisioningLeasePreflightError) as ctx:
                    check_provisioning_lease(str(self.folder), at_time=at_time)
                self.assertEqual(ctx.exception.code, "TIME_INVALID")
        for threshold in (True, -1, 86401, 1.5):
            with self.subTest(threshold=threshold):
                with self.assertRaises(ProvisioningLeasePreflightError) as ctx:
                    check_provisioning_lease(
                        str(self.folder), at_time=AT_TIME,
                        minimum_remaining_seconds=threshold,
                    )
                self.assertEqual(ctx.exception.code, "MINIMUM_REMAINING_INVALID")

    def test_cli_succeeds_without_echoing_provisioning_path(self):
        stdout, stderr = StringIO(), StringIO()
        with patch("tools.marketplace_authentication_lease_preflight.time.time", return_value=AT_TIME):
            with redirect_stdout(stdout), redirect_stderr(stderr):
                exit_code = main([
                    "--authentication-provisioning-directory", str(self.folder),
                    "--minimum-remaining-seconds", "30",
                ])
        self.assertEqual(exit_code, 0)
        self.assertIn("status=PASS lease_remaining_seconds=100 identities=1", stdout.getvalue())
        self.assertNotIn(str(self.folder), stdout.getvalue())
        self.assertEqual(stderr.getvalue(), "")

    def test_cli_failure_shares_only_stable_code(self):
        stdout, stderr = StringIO(), StringIO()
        with patch("tools.marketplace_authentication_lease_preflight.time.time", return_value=1_100):
            with redirect_stdout(stdout), redirect_stderr(stderr):
                exit_code = main([
                    "--authentication-provisioning-directory", str(self.folder),
                    "--minimum-remaining-seconds", "30",
                ])
        self.assertEqual(exit_code, 1)
        self.assertEqual(stdout.getvalue(), "")
        self.assertEqual(stderr.getvalue().strip(), "status=FAIL code=LEASE_EXPIRED")
        self.assertNotIn(str(self.folder), stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
