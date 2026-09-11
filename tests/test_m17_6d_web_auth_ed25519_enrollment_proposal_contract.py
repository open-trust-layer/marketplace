from __future__ import annotations

import base64
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "web" / "auth_ed25519_enrollment_proposal.js"
TEXT = SOURCE.read_text(encoding="utf-8")

PROFILE = "MARKETPLACE_WEB_AUTH_ED25519_ENROLLMENT_PROPOSAL_V1"
PROPOSAL_TYPE = "MarketplaceAuthenticationEd25519EnrollmentProposal"
WEB_PREFIX = "mkpk1_"
EVIDENCE_PREFIX = "mkp1_"
PUBLIC_KEY_BYTES = bytes(range(32))
PUBLIC_KEY_PAYLOAD = "AAECAwQFBgcICQoLDA0ODxAREhMUFRYXGBkaGxwdHh8"
WEB_PUBLIC_KEY = WEB_PREFIX + PUBLIC_KEY_PAYLOAD
EVIDENCE_PUBLIC_KEY = EVIDENCE_PREFIX + PUBLIC_KEY_PAYLOAD


class M176DWebAuthEd25519EnrollmentProposalContractTests(unittest.TestCase):
    def test_profile_type_and_carriers_are_frozen(self) -> None:
        self.assertIn(f'"{PROFILE}"', TEXT)
        self.assertIn(f'"{PROPOSAL_TYPE}"', TEXT)
        self.assertIn('const WEB_PUBLIC_KEY_PREFIX = "mkpk1_"', TEXT)
        self.assertIn('const EVIDENCE_PUBLIC_KEY_PREFIX = "mkp1_"', TEXT)
        self.assertIn("const PUBLIC_KEY_BYTES = 32", TEXT)
        self.assertIn("const PUBLIC_KEY_PAYLOAD_CHARS = 43", TEXT)
        payload = base64.urlsafe_b64encode(PUBLIC_KEY_BYTES).rstrip(b"=").decode("ascii")
        self.assertEqual(payload, PUBLIC_KEY_PAYLOAD)
        self.assertEqual(WEB_PREFIX + payload, WEB_PUBLIC_KEY)
        self.assertEqual(EVIDENCE_PREFIX + payload, EVIDENCE_PUBLIC_KEY)

    def test_request_shape_is_exact_and_caller_provisioned(self) -> None:
        start = TEXT.index("function createMarketplaceWebAuthEd25519EnrollmentProposal")
        end = TEXT.index("const principal", start)
        block = TEXT[start:end]
        self.assertIn(
            'exactKeys(requestValue, ["profile", "principal", "verificationMethod", "publicKeyValue"])',
            block,
        )
        self.assertIn("requestValue.profile !== PROFILE", block)

    def test_principal_and_verification_method_use_exact_bounded_uri_validation(self) -> None:
        start = TEXT.index("function reviewedUri")
        end = TEXT.index("function base64UrlIndex", start)
        block = TEXT[start:end]
        self.assertIn('typeof value !== "string"', block)
        self.assertIn("value.length === 0", block)
        self.assertIn("utf8(value).length > MAX_URI_BYTES", block)
        self.assertIn("^[A-Za-z][A-Za-z0-9+.-]*", block)

        create_start = TEXT.index("function createMarketplaceWebAuthEd25519EnrollmentProposal")
        create_end = TEXT.index("return Object.freeze({", create_start)
        create_block = TEXT[create_start:create_end]
        self.assertIn("reviewedUri(requestValue.principal)", create_block)
        self.assertIn("reviewedUri(requestValue.verificationMethod)", create_block)
        self.assertNotIn("principal === verificationMethod", create_block)
        self.assertNotIn("principal !== verificationMethod", create_block)

    def test_mkpk1_input_is_canonical_and_decodes_to_exactly_32_bytes(self) -> None:
        start = TEXT.index("function reviewedPublicKeyValue")
        end = TEXT.index("function createMarketplaceWebAuthEd25519EnrollmentProposal", start)
        block = TEXT[start:end]
        self.assertIn("value.startsWith(WEB_PUBLIC_KEY_PREFIX)", block)
        self.assertIn("payload.length !== PUBLIC_KEY_PAYLOAD_CHARS", block)
        self.assertIn("decodeBase64Url(payload, PUBLIC_KEY_BYTES)", block)

        decode_start = TEXT.index("function decodeBase64Url")
        decode_end = TEXT.index("function reviewedPublicKeyValue", decode_start)
        decode_block = TEXT[decode_start:decode_end]
        self.assertIn("bytes.length !== expectedBytes", decode_block)
        self.assertIn("encodeBase64Url(bytes) !== payload", decode_block)

    def test_bridge_reencodes_the_same_public_bytes_only(self) -> None:
        start = TEXT.index("function createMarketplaceWebAuthEd25519EnrollmentProposal")
        end = TEXT.index("return Object.freeze({", start)
        block = TEXT[start:end]
        self.assertIn("const publicKeyBytes = reviewedPublicKeyValue(requestValue.publicKeyValue)", block)
        self.assertIn("const publicKey = EVIDENCE_PUBLIC_KEY_PREFIX + encodeBase64Url(publicKeyBytes)", block)
        self.assertEqual(WEB_PUBLIC_KEY.removeprefix(WEB_PREFIX), EVIDENCE_PUBLIC_KEY.removeprefix(EVIDENCE_PREFIX))

    def test_result_is_exactly_non_authoritative_proposal_metadata(self) -> None:
        start = TEXT.index("return Object.freeze({", TEXT.index("const publicKey ="))
        end = TEXT.index("});", start)
        returned = TEXT[start:end]
        for marker in (
            "profile: PROFILE",
            "type: PROPOSAL_TYPE",
            "principal,",
            "verificationMethod,",
            "publicKey,",
        ):
            self.assertIn(marker, returned)
        for forbidden in (
            "authority", "issuedAt", "expiresAt", "validFrom", "validUntil",
            "attestation", "accepted", "session", "privateKey",
        ):
            self.assertNotIn(forbidden, returned)

    def test_error_and_export_surface_are_stable_and_narrow(self) -> None:
        self.assertIn('new Error("Marketplace Web authentication enrollment proposal failed")', TEXT)
        self.assertIn('error.code = "AUTH_ENROLLMENT_PROPOSAL_UNAVAILABLE"', TEXT)
        exported = TEXT[TEXT.rindex("export {"):]
        self.assertIn("PROFILE", exported)
        self.assertIn("PROPOSAL_TYPE", exported)
        self.assertIn("createMarketplaceWebAuthEd25519EnrollmentProposal", exported)
        self.assertNotIn("reviewedPublicKeyValue", exported)
        self.assertNotIn("decodeBase64Url", exported)


if __name__ == "__main__":
    unittest.main()
