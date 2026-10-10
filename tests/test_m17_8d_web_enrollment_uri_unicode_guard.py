"""M17.8D: exact Web enrollment URI bytes require valid Unicode scalars."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "web" / "auth_ed25519_enrollment_proposal.js"
DOC = ROOT / "docs" / "m17-8d-web-enrollment-uri-unicode-guard.md"


class M178DWebEnrollmentUriUnicodeGuard(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source = SRC.read_text(encoding="utf-8")

    def test_strict_scalar_sequence_is_checked_before_utf8_encoding(self) -> None:
        src = self.source
        start = src.index("function reviewedUri(value)")
        end = src.index("function exactKeys(", start)
        body = src[start:end]
        self.assertIn("!validUnicodeScalarSequence(value)", body)
        self.assertIn("utf8(value).length > MAX_URI_BYTES", body)
        self.assertLess(
            body.index("!validUnicodeScalarSequence(value)"),
            body.index("utf8(value).length > MAX_URI_BYTES"),
        )
        self.assertIn(r"/^[A-Za-z][A-Za-z0-9+.-]*:\S+$/.test(value)", body)
        self.assertIn("throw stableEnrollmentProposalError();", body)
        self.assertIn("return value;", body)

    def test_surrogate_pair_fsm_is_bounded_and_rejects_unpaired(self) -> None:
        src = self.source
        start = src.index("function validUnicodeScalarSequence(")
        end = src.index("function reviewedUri(", start)
        body = src[start:end]
        for marker in (
            "index < value.length",
            "index += 1",
            "value.charCodeAt(index)",
            "unit >= 0xd800 && unit <= 0xdbff",
            "value.charCodeAt(index + 1)",
            "next >= 0xdc00 && next <= 0xdfff",
            "unit >= 0xdc00 && unit <= 0xdfff",
            "return false;",
            "return true;",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, body)
        self.assertIn("index += 1;\n    } else", body)
        for token in ("normalize(", "TextDecoder", "String.fromCharCode(", "replace(", "fetch("):
            with self.subTest(forbidden=token):
                self.assertNotIn(token, body)

    def test_result_and_public_key_authority_boundary_is_unchanged(self) -> None:
        src = self.source
        for marker in (
            'const PROFILE = "MARKETPLACE_WEB_AUTH_ED25519_ENROLLMENT_PROPOSAL_V1"',
            'const TYPE = "MarketplaceAuthenticationEnrollmentProposal"',
            '"AUTH_ENROLLMENT_PROPOSAL_UNAVAILABLE"',
            "reviewedUri(request.principal)",
            "reviewedUri(request.verificationMethod)",
            "publicKeyBytes: reviewedPublicKey(request.publicKeyValue)",
            "publicKey: EVIDENCE_PUBLIC_KEY_PREFIX + payload",
            "return Object.freeze({",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, src)
        for forbidden in (
            "fetch(", "XMLHttpRequest", "WebSocket", "localStorage", "sessionStorage",
            "privateKey", "crypto.subtle", "generateKey", "importKey", "exportKey",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, src)

    def test_document_preserves_non_authority_and_exact_release(self) -> None:
        text = DOC.read_text(encoding="utf-8")
        for phrase in (
            "MARKETPLACE_WEB_AUTH_ED25519_ENROLLMENT_PROPOSAL_V1",
            "unpaired surrogate",
            "valid surrogate pair",
            "non-authoritative",
            "no network",
            "source-only rollback",
        ):
            self.assertIn(phrase, text)


if __name__ == "__main__":
    unittest.main()
