"""Offline tests for signed Marketplace browser-to-bundle key binding."""
from __future__ import annotations

import base64
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from marketplace.application.auth_startup_provisioning import (
    VERIFICATION_METHOD_CLAIMS_FILENAME,
)
from tools.marketplace_browser_bundle_binding_preflight import (
    BrowserBundleBindingError,
    check_browser_bundle_binding,
    main,
)
from tools.marketplace_local_two_party_provisioning import (
    create_local_two_party_provisioning,
)

SAMPLE_TIME = 100000


def public_carrier() -> str:
    private = Ed25519PrivateKey.generate()
    raw = private.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    return "mkpk1_" + base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


class BrowserBundleBindingPreflightTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.directory = str(Path(temporary.name) / "signed-test-bundle")
        self.seller = public_carrier()
        self.buyer = public_carrier()
        self.other = public_carrier()
        create_local_two_party_provisioning(
            directory=self.directory,
            seller_public_key=self.seller,
            buyer_public_key=self.buyer,
            lease_seconds=7200,
            now=SAMPLE_TIME,
        )

    def check(self, **replacements):
        values = {
            "directory": self.directory,
            "seller_browser_public_key": self.seller,
            "buyer_browser_public_key": self.buyer,
            "at_time": SAMPLE_TIME + 10,
            "minimum_remaining_seconds": 1800,
        }
        values.update(replacements)
        return check_browser_bundle_binding(**values)

    def rejected(self, code, **replacements):
        with self.assertRaises(BrowserBundleBindingError) as caught:
            self.check(**replacements)
        self.assertEqual(caught.exception.code, code)

    def test_signature_valid_and_exact_two_live_browser_keys_pass(self):
        self.assertEqual(self.check(), 7190)

    def test_swapped_seller_buyer_keys_fail_closed(self):
        self.rejected(
            "BROWSER_KEY_BINDING_MISMATCH",
            seller_browser_public_key=self.buyer,
            buyer_browser_public_key=self.seller,
        )

    def test_stale_browser_key_fails_even_with_valid_signed_lease(self):
        self.rejected(
            "BROWSER_KEY_BINDING_MISMATCH",
            buyer_browser_public_key=self.other,
        )

    def test_duplicate_and_noncanonical_carriers_rejected(self):
        self.rejected(
            "BROWSER_KEYS_NOT_DISTINCT",
            buyer_browser_public_key=self.seller,
        )
        for invalid in ("mkp1_" + self.seller[6:], "mkpk1_bad", 123, self.seller + "!"):
            self.rejected(
                "BROWSER_PUBLIC_KEY_INVALID",
                buyer_browser_public_key=invalid,
            )

    def test_minimum_lease_and_expiry_not_weakened(self):
        self.rejected("LEASE_TOO_SHORT", at_time=SAMPLE_TIME + 5500)
        self.rejected("LEASE_EXPIRED", at_time=SAMPLE_TIME + 7200)
        self.rejected("LEASE_NOT_YET_VALID", at_time=SAMPLE_TIME - 1)

    def test_mandatory_acceptance_minimum_cannot_be_lowered(self):
        self.rejected("MINIMUM_REMAINING_INVALID", minimum_remaining_seconds=0)
        self.rejected("MINIMUM_REMAINING_INVALID", minimum_remaining_seconds=1799)
        self.rejected("MINIMUM_REMAINING_INVALID", minimum_remaining_seconds=86401)
        self.rejected("MINIMUM_REMAINING_INVALID", minimum_remaining_seconds=True)

    def test_tampered_signed_claims_rejected_before_binding(self):
        claims_path = Path(self.directory) / VERIFICATION_METHOD_CLAIMS_FILENAME
        text = claims_path.read_text(encoding="utf-8")
        self.assertIn("marketplace-local-evaluator-seller", text)
        claims_path.write_text(
            text.replace("marketplace-local-evaluator-seller", "marketplace-local-evaluator-other"),
            encoding="utf-8",
        )
        self.rejected("PROVISIONING_INVALID")

    def test_redacted_cli_receipts_and_argument_errors(self):
        argv = [
            "--authentication-provisioning-directory", self.directory,
            "--seller-browser-public-key", self.seller,
            "--buyer-browser-public-key", self.buyer,
        ]
        with patch("tools.marketplace_browser_bundle_binding_preflight.time.time", return_value=SAMPLE_TIME + 10):
            out, err = StringIO(), StringIO()
            with redirect_stdout(out), redirect_stderr(err):
                result = main(argv)
            self.assertEqual(result, 0)
            self.assertIn("status=BROWSER_BINDING_VERIFIED", out.getvalue())
            self.assertIn("private_keys_opened=false", out.getvalue())
            self.assertEqual(err.getvalue(), "")

            out, err = StringIO(), StringIO()
            with redirect_stdout(out), redirect_stderr(err):
                result = main(argv[:-1] + [self.other])
            self.assertEqual(result, 1)
            self.assertIn("status=BLOCKED code=BROWSER_KEY_BINDING_MISMATCH", err.getvalue())
            for key in (self.seller, self.buyer, self.other, self.directory):
                self.assertNotIn(key, out.getvalue() + err.getvalue())

            out, err = StringIO(), StringIO()
            with redirect_stdout(out), redirect_stderr(err):
                with self.assertRaises(SystemExit) as caught:
                    main(argv + ["--unexpected-private-value", self.other])
            self.assertEqual(caught.exception.code, 2)
            self.assertEqual(err.getvalue(), "status=BLOCKED code=ARGUMENT_INVALID\n")
            self.assertNotIn(self.other, err.getvalue())


if __name__ == "__main__":
    unittest.main()
