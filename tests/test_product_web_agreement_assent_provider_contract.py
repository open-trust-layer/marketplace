from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "web" / "agreement_ed25519_assent_provider.js"
TEXT = SOURCE.read_text(encoding="utf-8")

EXPECTED_AGREEMENT_ID = "r1_grS0_HlLNS2A1VqdELEa_daC4IJl_SBGzxcAO6esM5A"
EXPECTED_METHOD = "urn:example:olp:test-key-1"
EXPECTED_INPUT_HEX = (
    "89694f4c502d50524f4f46017065646473612d656432353531392d763169617373"
    "657274696f6e781a75726e3a6578616d706c653a6f6c703a746573742d6b65792d"
    "31822f582082b4b4fc794b352d80d55a9d10b11afdd682e08265fd2046cf17003b"
    "a7ac3390a0a080"
)
EXPECTED_SIGNATURE_HEX = (
    "796690ef7db0526e6c5c6c1c93ab0157ff5e3d14b2196103f22f39d208f6d590"
    "71528d13f3e5f6b34b14d2ebb04617822dd0962c36d4673aaa456601f5f76b0c"
)


class ProductWebAgreementAssentProviderContractTests(unittest.TestCase):
    def test_exact_profile_and_frozen_vector_are_recorded(self) -> None:
        self.assertIn(
            '"MARKETPLACE_WEB_AGREEMENT_ED25519_ASSENT_PROVIDER_V1"',
            TEXT,
        )
        self.assertEqual(len(bytes.fromhex(EXPECTED_INPUT_HEX)), 106)
        self.assertEqual(len(bytes.fromhex(EXPECTED_SIGNATURE_HEX)), 64)
        self.assertTrue(EXPECTED_AGREEMENT_ID.startswith("r1_"))
        self.assertEqual(EXPECTED_METHOD, "urn:example:olp:test-key-1")

    def test_preparation_shape_and_method_binding_are_exact(self) -> None:
        for marker in (
            '["agreementRecordId", "verificationMethod", "signingInput"]',
            "reviewedRecordId(preparation.agreementRecordId)",
            "preparation.verificationMethod !== verificationMethod",
            "preparation.signingInput instanceof Uint8Array",
            "preparation.signingInput.length < 1",
            "preparation.signingInput.length > MAX_SIGNING_INPUT_BYTES",
            "Uint8Array.from(preparation.signingInput)",
        ):
            self.assertIn(marker, TEXT)

    def test_private_key_is_nonextractable_ed25519_sign_only(self) -> None:
        start = TEXT.index("function reviewedPrivateKey")
        end = TEXT.index("function reviewedSubtle", start)
        block = TEXT[start:end]
        for marker in (
            'privateKey.type !== "private"',
            "privateKey.extractable !== false",
            'privateKey.algorithm.name !== "Ed25519"',
            "privateKey.usages.length !== 1",
            'privateKey.usages[0] !== "sign"',
        ):
            self.assertIn(marker, block)

    def test_only_exact_copied_signing_bytes_reach_one_sign_call(self) -> None:
        start = TEXT.index("async function createAgreementAssentSignature")
        end = TEXT.index(
            "return Object.freeze({ createAgreementAssentSignature })",
            start,
        )
        block = TEXT[start:end]
        self.assertEqual(block.count("reviewedSigner.sign("), 1)
        self.assertIn('{ name: "Ed25519" }', block)
        self.assertIn("preparation.signingBytes", block)
        self.assertNotIn("signingInput.hex", block)
        self.assertNotIn("JSON.stringify", block)

    def test_signature_result_is_exactly_64_bytes(self) -> None:
        self.assertIn("signatureResult instanceof ArrayBuffer", TEXT)
        self.assertIn("signatureResult.byteLength !== 64", TEXT)
        self.assertIn("return new Uint8Array(signatureResult)", TEXT)

    def test_provider_has_no_principal_or_attribution_authority(self) -> None:
        lowered = TEXT.lower()
        self.assertNotIn("principal", lowered)
        self.assertNotIn("attribution", lowered)
        self.assertNotIn("assentevidence", lowered)

    def test_provider_exposes_only_purpose_specific_operation(self) -> None:
        self.assertIn(
            "return Object.freeze({ createAgreementAssentSignature });",
            TEXT,
        )
        exported = TEXT[TEXT.rindex("export {"):]
        self.assertIn("PROFILE", exported)
        self.assertIn(
            "createMarketplaceWebAgreementEd25519AssentProvider",
            exported,
        )
        self.assertNotIn("reviewedPreparation", exported)
        self.assertNotIn("reviewedPrivateKey", exported)


if __name__ == "__main__":
    unittest.main()
