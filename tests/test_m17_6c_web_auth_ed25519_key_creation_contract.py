from __future__ import annotations

import base64
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "web" / "auth_ed25519_key_creation.js"
TEXT = SOURCE.read_text(encoding="utf-8")

PROFILE = "MARKETPLACE_WEB_AUTH_ED25519_KEY_CREATION_V1"
PUBLIC_KEY_PREFIX = "mkpk1_"
PUBLIC_KEY_BYTES = bytes(range(32))
PUBLIC_KEY_PAYLOAD = "AAECAwQFBgcICQoLDA0ODxAREhMUFRYXGBkaGxwdHh8"
PUBLIC_KEY_VALUE = PUBLIC_KEY_PREFIX + PUBLIC_KEY_PAYLOAD


class M176CWebAuthEd25519KeyCreationContractTests(unittest.TestCase):
    def test_exact_profile_and_public_key_carrier_are_frozen(self) -> None:
        self.assertIn(f'"{PROFILE}"', TEXT)
        self.assertIn('const PUBLIC_KEY_PREFIX = "mkpk1_"', TEXT)
        self.assertIn("const PUBLIC_KEY_BYTES = 32", TEXT)
        self.assertIn("const PUBLIC_KEY_PAYLOAD_CHARS = 43", TEXT)
        payload = base64.urlsafe_b64encode(PUBLIC_KEY_BYTES).rstrip(b"=").decode("ascii")
        self.assertEqual(payload, PUBLIC_KEY_PAYLOAD)
        self.assertEqual(len(payload), 43)
        self.assertEqual(PUBLIC_KEY_PREFIX + payload, PUBLIC_KEY_VALUE)
        self.assertEqual(len(PUBLIC_KEY_VALUE), 49)

    def test_request_is_exactly_one_profile_member(self) -> None:
        start = TEXT.index("function reviewedRequest")
        end = TEXT.index("function reviewedPrivateKey", start)
        block = TEXT[start:end]
        self.assertIn('exactKeys(request, ["profile"])', block)
        self.assertIn("request.profile !== PROFILE", block)

    def test_valid_path_has_exactly_one_generation_and_one_public_export(self) -> None:
        start = TEXT.index("async function createAuthenticationKey")
        end = TEXT.index("return Object.freeze({ createAuthenticationKey })", start)
        block = TEXT[start:end]
        self.assertEqual(block.count("reviewedCrypto.generateKey("), 1)
        self.assertEqual(block.count("reviewedCrypto.exportKey("), 1)
        self.assertIn('{ name: "Ed25519" }', block)
        self.assertIn("false,", block)
        self.assertIn('["sign", "verify"]', block)
        self.assertIn('reviewedCrypto.exportKey("raw", publicKey)', block)
        request_at = block.index("reviewedRequest(requestValue)")
        generate_at = block.index("reviewedCrypto.generateKey(")
        private_at = block.index("reviewedPrivateKey(keyPair.privateKey)")
        public_at = block.index("reviewedPublicKey(keyPair.publicKey)")
        export_at = block.index('reviewedCrypto.exportKey("raw", publicKey)')
        self.assertLess(request_at, generate_at)
        self.assertLess(generate_at, private_at)
        self.assertLess(private_at, export_at)
        self.assertLess(public_at, export_at)

    def test_generated_keypair_shape_and_private_authority_are_exact(self) -> None:
        self.assertIn('exactKeys(keyPair, ["privateKey", "publicKey"])', TEXT)
        start = TEXT.index("function reviewedPrivateKey")
        end = TEXT.index("function reviewedPublicKey", start)
        block = TEXT[start:end]
        for marker in (
            'privateKey.type !== "private"',
            "privateKey.extractable !== false",
            'privateKey.algorithm.name !== "Ed25519"',
            "privateKey.usages.length !== 1",
            'privateKey.usages[0] !== "sign"',
        ):
            self.assertIn(marker, block)

    def test_public_key_is_ed25519_verification_only_and_exportable(self) -> None:
        start = TEXT.index("function reviewedPublicKey")
        end = TEXT.index("function encodeBase64Url", start)
        block = TEXT[start:end]
        for marker in (
            'publicKey.type !== "public"',
            "publicKey.extractable !== true",
            'publicKey.algorithm.name !== "Ed25519"',
            "publicKey.usages.length !== 1",
            'publicKey.usages[0] !== "verify"',
        ):
            self.assertIn(marker, block)

    def test_raw_public_export_must_be_exactly_32_bytes(self) -> None:
        start = TEXT.index("function encodePublicKey")
        end = TEXT.index("function createMarketplaceWebAuthEd25519KeyCreation", start)
        block = TEXT[start:end]
        self.assertIn("rawPublicKey instanceof ArrayBuffer", block)
        self.assertIn("rawPublicKey.byteLength !== PUBLIC_KEY_BYTES", block)
        self.assertIn("payload.length !== PUBLIC_KEY_PAYLOAD_CHARS", block)
        self.assertIn("return PUBLIC_KEY_PREFIX + payload", block)

    def test_result_exposes_only_profile_private_handle_and_public_carrier(self) -> None:
        start = TEXT.index("return Object.freeze({", TEXT.index("const publicKeyValue"))
        end = TEXT.index("});", start)
        returned = TEXT[start:end]
        self.assertIn("profile: PROFILE", returned)
        self.assertIn("privateKey,", returned)
        self.assertIn("publicKeyValue,", returned)
        self.assertNotIn("publicKey,", returned)
        self.assertNotIn("rawPublicKey", returned)

    def test_factory_exposes_only_purpose_specific_creation_operation(self) -> None:
        self.assertIn("return Object.freeze({ createAuthenticationKey });", TEXT)
        exported = TEXT[TEXT.rindex("export {"):]
        self.assertIn("PROFILE", exported)
        self.assertIn("createMarketplaceWebAuthEd25519KeyCreation", exported)
        self.assertNotIn("encodePublicKey", exported)
        self.assertNotIn("reviewedPrivateKey", exported)


if __name__ == "__main__":
    unittest.main()
