from __future__ import annotations

import base64
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "web" / "auth_ed25519_enrollment_proposal.js"
TEXT = SOURCE.read_text(encoding="utf-8")

PROFILE = "MARKETPLACE_WEB_AUTH_ED25519_ENROLLMENT_PROPOSAL_V1"
TYPE = "MarketplaceAuthenticationEnrollmentProposal"
ENROLLMENT_PREFIX = "mkpk1_"
EVIDENCE_PREFIX = "mkp1_"
KEY_BYTES = bytes(range(32))
PAYLOAD = "AAECAwQFBgcICQoLDA0ODxAREhMUFRYXGBkaGxwdHh8"
ENROLLMENT_VALUE = ENROLLMENT_PREFIX + PAYLOAD
EVIDENCE_VALUE = EVIDENCE_PREFIX + PAYLOAD


class M176DWebAuthEd25519EnrollmentProposalContractTests(unittest.TestCase):
    def test_exact_profile_type_and_carriers_are_frozen(self) -> None:
        self.assertIn(f'"{PROFILE}"', TEXT)
        self.assertIn(f'"{TYPE}"', TEXT)
        self.assertIn('const ENROLLMENT_PUBLIC_KEY_PREFIX = "mkpk1_"', TEXT)
        self.assertIn('const EVIDENCE_PUBLIC_KEY_PREFIX = "mkp1_"', TEXT)
        self.assertIn("const PUBLIC_KEY_BYTES = 32", TEXT)
        self.assertIn("const PUBLIC_KEY_PAYLOAD_CHARS = 43", TEXT)
        self.assertIn("const MAX_URI_BYTES = 2048", TEXT)

    def test_frozen_bridge_vector_preserves_exact_public_key_bytes(self) -> None:
        payload = base64.urlsafe_b64encode(KEY_BYTES).rstrip(b"=").decode("ascii")
        self.assertEqual(payload, PAYLOAD)
        self.assertEqual(ENROLLMENT_VALUE, "mkpk1_" + PAYLOAD)
        self.assertEqual(EVIDENCE_VALUE, "mkp1_" + PAYLOAD)
        self.assertEqual(ENROLLMENT_VALUE.removeprefix(ENROLLMENT_PREFIX), EVIDENCE_VALUE.removeprefix(EVIDENCE_PREFIX))

    def test_request_shape_is_exact_and_has_no_authority_fields(self) -> None:
        start = TEXT.index("function reviewedRequest")
        end = TEXT.index("function createMarketplaceWebAuthEd25519EnrollmentProposal", start)
        block = TEXT[start:end]
        self.assertIn(
            'exactKeys(request, ["profile", "principal", "verificationMethod", "publicKeyValue"])',
            block,
        )
        self.assertIn("request.profile !== PROFILE", block)
        for marker in (
            "authority", "issuedAt", "expiresAt", "validFrom", "validUntil",
            "attestation", "accepted", "trustStatus", "session",
        ):
            self.assertNotIn(marker, block)

    def test_uri_validation_matches_existing_web_absolute_uri_boundary(self) -> None:
        start = TEXT.index("function reviewedUri")
        end = TEXT.index("function exactKeys", start)
        block = TEXT[start:end]
        self.assertIn("utf8(value).length > MAX_URI_BYTES", block)
        self.assertIn(r"/^[A-Za-z][A-Za-z0-9+.-]*:\S+$/.test(value)", block)
        self.assertNotIn("toLowerCase", block)
        self.assertNotIn("normalize(", block)
        self.assertNotIn("URL(", block)

    def test_enrollment_carrier_must_be_canonical_32_byte_base64url(self) -> None:
        start = TEXT.index("function reviewedPublicKey")
        end = TEXT.index("function reviewedRequest", start)
        block = TEXT[start:end]
        self.assertIn("value.startsWith(ENROLLMENT_PUBLIC_KEY_PREFIX)", block)
        self.assertIn("payload.length !== PUBLIC_KEY_PAYLOAD_CHARS", block)
        self.assertIn("decodeBase64Url(payload, PUBLIC_KEY_BYTES)", block)
        self.assertIn("ENROLLMENT_PUBLIC_KEY_PREFIX + encodeBase64Url(bytes) !== value", block)

    def test_result_shape_is_exact_non_authoritative_proposal_metadata(self) -> None:
        start = TEXT.index("return Object.freeze({", TEXT.index("function createMarketplaceWebAuthEd25519EnrollmentProposal"))
        end = TEXT.index("});", start)
        returned = TEXT[start:end]
        for marker in (
            "profile: PROFILE",
            "type: TYPE",
            "principal: request.principal",
            "verificationMethod: request.verificationMethod",
            "publicKey: EVIDENCE_PUBLIC_KEY_PREFIX + payload",
        ):
            self.assertIn(marker, returned)
        for marker in (
            "authority", "issuedAt", "expiresAt", "validFrom", "validUntil",
            "attestation", "accepted", "trustStatus", "session",
        ):
            self.assertNotIn(marker, returned)

    def test_principal_and_verification_method_are_preserved_without_inference(self) -> None:
        start = TEXT.index("function createMarketplaceWebAuthEd25519EnrollmentProposal")
        end = TEXT.index("export {", start)
        block = TEXT[start:end]
        self.assertIn("principal: request.principal", block)
        self.assertIn("verificationMethod: request.verificationMethod", block)
        self.assertNotIn("split(", block)
        self.assertNotIn("replace(", block)
        self.assertNotIn("startsWith(request.principal", block)

    def test_factory_exports_only_profile_and_purpose_specific_handoff(self) -> None:
        exported = TEXT[TEXT.rindex("export {"):]
        self.assertIn("PROFILE", exported)
        self.assertIn("createMarketplaceWebAuthEd25519EnrollmentProposal", exported)
        self.assertNotIn("reviewedPublicKey", exported)
        self.assertNotIn("decodeBase64Url", exported)
        self.assertNotIn("reviewedUri", exported)


if __name__ == "__main__":
    unittest.main()
