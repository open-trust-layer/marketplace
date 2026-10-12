"""Bounded signed two-party LOCAL evaluator provisioning only; no runtime or SQL."""
from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
import os
from pathlib import Path
import tempfile
import unittest

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from marketplace.application.auth_startup_provisioning import (
    TRUST_ANCHOR_MANIFEST_FILENAME,
    VERIFICATION_METHOD_CLAIMS_FILENAME,
    VERIFICATION_METHOD_ATTESTATION_FILENAME,
    load_marketplace_authentication_startup_provisioning,
)
from tools.marketplace_authentication_lease_preflight import (
    ProvisioningLeasePreflightError,
    check_provisioning_lease,
)
from tools.marketplace_local_two_party_provisioning import (
    BUYER_METHOD,
    BUYER_PRINCIPAL,
    EXECUTION_OPT_IN,
    LocalProvisioningError,
    SELLER_METHOD,
    SELLER_PRINCIPAL,
    create_local_two_party_provisioning,
    main,
)


def browser_public_key() -> str:
    signing_key = Ed25519PrivateKey.generate()
    raw = signing_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw
    )
    import base64
    return "mkpk1_" + base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


class MarketplaceLocalTwoPartyProvisioningTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.folder = Path(self.tmp.name) / "test-auth"
        self.seller_key = browser_public_key()
        self.buyer_key = browser_public_key()

    def create(self, **kwargs):
        args = dict(
            directory=str(self.folder),
            seller_public_key=self.seller_key,
            buyer_public_key=self.buyer_key,
            lease_seconds=7200,
            now=100_000,
        )
        args.update(kwargs)
        return create_local_two_party_provisioning(**args)

    def assert_rejected(self, code, **kwargs):
        with self.assertRaises(LocalProvisioningError) as raised:
            self.create(**kwargs)
        self.assertEqual(raised.exception.code, code)
        self.assertFalse(self.folder.exists())

    def test_real_signature_two_distinct_controllers_and_expiry(self):
        self.create()
        names = {p.name for p in self.folder.iterdir()}
        self.assertEqual(names, {
            TRUST_ANCHOR_MANIFEST_FILENAME,
            VERIFICATION_METHOD_CLAIMS_FILENAME,
            VERIFICATION_METHOD_ATTESTATION_FILENAME,
        })
        self.assertEqual(check_provisioning_lease(
            str(self.folder), at_time=100_000,
            minimum_remaining_seconds=1800, minimum_distinct_principals=2,
        ), (7200, 2))
        loaded = load_marketplace_authentication_startup_provisioning(
            directory=str(self.folder)
        )
        entries = loaded.verification_method_evidence
        self.assertIsNotNone(entries)
        with self.assertRaises(ProvisioningLeasePreflightError) as result:
            check_provisioning_lease(
                str(self.folder), at_time=107_200,
                minimum_remaining_seconds=1800, minimum_distinct_principals=2,
            )
        self.assertEqual(result.exception.code, "LEASE_EXPIRED")
        if os.name != "nt":
            self.assertEqual(self.folder.stat().st_mode & 0o777, 0o700)
            self.assertTrue(all(p.stat().st_mode & 0o077 == 0 for p in self.folder.iterdir()))

    def test_distinct_browser_public_key_required(self):
        self.assert_rejected("PARTY_KEYS_NOT_DISTINCT", buyer_public_key=self.seller_key)

    def test_bad_prefix_and_noncanonical_carrier_fail_before_mkdir(self):
        self.assert_rejected("PUBLIC_KEY_INVALID", buyer_public_key="mkp1_" + self.buyer_key[6:])
        self.assert_rejected("PUBLIC_KEY_INVALID", buyer_public_key="mkpk1_bad")
        self.assert_rejected("PUBLIC_KEY_INVALID", seller_public_key="mkpk1_" + "_" * 43)

    def test_excessive_and_too_short_lease_fail_closed(self):
        self.assert_rejected("LEASE_INVALID", lease_seconds=1799)
        self.assert_rejected("LEASE_INVALID", lease_seconds=86401)
        self.assert_rejected("LEASE_INVALID", lease_seconds=True)

    def test_no_overwrite_and_no_relative_destination(self):
        self.folder.mkdir()
        with self.assertRaises(LocalProvisioningError) as raised:
            self.create()
        self.assertEqual(raised.exception.code, "DESTINATION_INVALID")
        self.folder.rmdir()
        self.assert_rejected("DESTINATION_INVALID", directory="relative/auth")

    def test_cli_requires_explicit_exact_opt_in_and_reports_only_safe_receipt(self):
        flags = [
            "--output-directory", str(self.folder),
            "--seller-browser-public-key", self.seller_key,
            "--buyer-browser-public-key", self.buyer_key,
            "--execute-local-test-provisioning", "INVALID",
        ]
        out, err = StringIO(), StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = main(flags)
        self.assertEqual(code, 1)
        self.assertEqual(out.getvalue(), "")
        self.assertEqual(err.getvalue().strip(), "status=BLOCKED code=EXECUTION_OPT_IN_REQUIRED")
        self.assertFalse(self.folder.exists())
        out, err = StringIO(), StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = main(flags[:-1] + [EXECUTION_OPT_IN])
        self.assertEqual(code, 0, err.getvalue())
        self.assertIn("status=LOCAL_TWO_PARTY_TEST_PROVISIONING_CREATED", out.getvalue())
        self.assertIn("private_keys_written=false", out.getvalue())
        self.assertNotIn(str(self.folder), out.getvalue())
        self.assertNotIn(self.seller_key, out.getvalue())
        self.assertNotIn(self.buyer_key, out.getvalue())
        self.assertEqual(err.getvalue(), "")

    def test_client_methods_are_pinned_to_test_only_identities(self):
        self.assertEqual(SELLER_PRINCIPAL, "did:example:marketplace-local-evaluator-seller")
        self.assertEqual(BUYER_PRINCIPAL, "did:example:marketplace-local-evaluator-buyer")
        self.assertEqual(SELLER_METHOD, SELLER_PRINCIPAL + "#key-1")
        self.assertEqual(BUYER_METHOD, BUYER_PRINCIPAL + "#key-1")


if __name__ == "__main__":
    unittest.main()
