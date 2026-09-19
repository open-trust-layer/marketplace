from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "web" / "agreement_ed25519_assent_provider.js"
TEXT = SOURCE.read_text(encoding="utf-8")

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
    def test_profiles_and_bounds_are_frozen(self) -> None:
        for marker in (
            '"MARKETPLACE_WEB_AGREEMENT_ED25519_ASSENT_PROVIDER_V1"',
            '"MARKETPLACE_AGREEMENT_ASSENT_SIGNING_PREPARATION_V1"',
            "const MAX_SIGNING_INPUT_BYTES = 4096",
            "const ED25519_SIGNATURE_BYTES = 64",
            "const MAX_URI_BYTES = 2048",
            "const RECORD_ID = /^r1_[A-Za-z0-9_-]{43}$/",
        ):
            self.assertIn(marker, TEXT)

    def test_frozen_cross_runtime_vector_shape_is_preserved(self) -> None:
        signing_input = bytes.fromhex(EXPECTED_INPUT_HEX)
        signature = bytes.fromhex(EXPECTED_SIGNATURE_HEX)
        self.assertEqual(len(signing_input), 106)
        self.assertEqual(len(signature), 64)

    def test_preparation_is_exact_and_method_bound(self) -> None:
        for marker in (
            '["profile", "agreementRecordId", "verificationMethod", "proofInput"]',
            "value.profile !== PREPARATION_PROFILE",
            "value.verificationMethod !== verificationMethod",
            "!RECORD_ID.test(value.agreementRecordId)",
            "reviewedSigningInput(value.proofInput)",
        ):
            self.assertIn(marker, TEXT)

    def test_signing_input_is_copied_and_bounded_before_signing(self) -> None:
        start = TEXT.index("function reviewedSigningInput")
        end = TEXT.index("function reviewedPreparation", start)
        block = TEXT[start:end]
        self.assertIn("value instanceof Uint8Array", block)
        self.assertIn("value.length < 1", block)
        self.assertIn("value.length > MAX_SIGNING_INPUT_BYTES", block)
        self.assertIn("return new Uint8Array(value)", block)

    def test_key_is_non_extractable_ed25519_sign_only(self) -> None:
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

    def test_exactly_one_purpose_specific_sign_call_exists(self) -> None:
        start = TEXT.index("async function createAgreementAssentSignature")
        end = TEXT.index(
            "return Object.freeze({ createAgreementAssentSignature })",
            start,
        )
        block = TEXT[start:end]
        self.assertEqual(block.count("reviewedSigner.sign("), 1)
        sign_at = block.index("reviewedSigner.sign(")
        for marker in (
            "reviewedPreparation(",
            "reviewedPrivateKey(privateKey)",
        ):
            self.assertLess(block.index(marker), sign_at)
        self.assertIn('{ name: "Ed25519" }', block)
        self.assertIn("preparation.proofInput", block)

    def test_result_carries_only_binding_metadata_and_signature(self) -> None:
        self.assertNotIn("principal", TEXT)
        start = TEXT.index("return Object.freeze({", TEXT.index("const signature ="))
        end = TEXT.index("});", start)
        returned = TEXT[start:end]
        for marker in (
            "profile: PROFILE",
            "agreementRecordId:",
            "verificationMethod:",
            "signature,",
        ):
            self.assertIn(marker, returned)

    def test_provider_exposes_only_assent_signature_operation(self) -> None:
        self.assertIn(
            "return Object.freeze({ createAgreementAssentSignature });",
            TEXT,
        )
        exported = TEXT[TEXT.rindex("export {"):]
        self.assertIn("PROFILE", exported)
        self.assertIn("PREPARATION_PROFILE", exported)
        self.assertIn("createMarketplaceWebAgreementEd25519AssentProvider", exported)
        self.assertNotIn("reviewedSigningInput", exported)


if __name__ == "__main__":
    unittest.main()
