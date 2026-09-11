from __future__ import annotations

import base64
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "web" / "auth_ed25519_proof_provider.js"
TEXT = SOURCE.read_text(encoding="utf-8")

CHALLENGE = bytes(range(32))
VERIFICATION_METHOD = "did:example:alice#key-1"
CRYPTOSUITE = "https://open-trust-layer.github.io/marketplace/application-auth/eddsa-ed25519-v1"
DOMAIN = "https://open-trust-layer.github.io/marketplace/application-auth/v1"
PURPOSE = "assertion"
EXPECTED_TRANSCRIPT_HEX = (
    "4d41524b4554504c4143452d415554480001"
    "005068747470733a2f2f6f70656e2d74727573742d6c617965722e6769746875622e696f2f"
    "6d61726b6574706c6163652f6170706c69636174696f6e2d617574682f65646473612d656432"
    "353531392d7631"
    "0009617373657274696f6e"
    "00176469643a6578616d706c653a616c696365236b65792d31"
    "004268747470733a2f2f6f70656e2d74727573742d6c617965722e6769746875622e696f2f"
    "6d61726b6574706c6163652f6170706c69636174696f6e2d617574682f7631"
    "000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f"
)
EXPECTED_SIGNATURE_HEX = (
    "85fb0e24d5b1bf54ae397e1028a6e2db690e67d8eaa279fcd2e39cfe17240030"
    "206b3eda21574888fde8b0b6d331cba53438e660b3e17bb9d481ce06179ed505"
)


def lp(value: str) -> bytes:
    encoded = value.encode("utf-8")
    return len(encoded).to_bytes(2, "big") + encoded


def frozen_transcript() -> bytes:
    return b"".join(
        (
            b"MARKETPLACE-AUTH",
            b"\x00\x01",
            lp(CRYPTOSUITE),
            lp(PURPOSE),
            lp(VERIFICATION_METHOD),
            lp(DOMAIN),
            CHALLENGE,
        )
    )


class M176BWebAuthEd25519ProofProviderContractTests(unittest.TestCase):
    def test_exact_profile_and_proof_constants_are_frozen(self) -> None:
        for marker in (
            '"MARKETPLACE_WEB_AUTH_ED25519_PROOF_PROVIDER_V1"',
            '"MARKETPLACE_WEB_AUTH_SESSION_ESTABLISHMENT_V1"',
            '"MarketplaceAuthenticationProof"',
            '"https://open-trust-layer.github.io/marketplace/application-auth/eddsa-ed25519-v1"',
            '"https://open-trust-layer.github.io/marketplace/application-auth/v1"',
            'const AUTH_PURPOSE = "assertion"',
            'const TRANSCRIPT_DOMAIN = "MARKETPLACE-AUTH"',
            'const CHALLENGE_PREFIX = "mkc1_"',
            'const SIGNATURE_PREFIX = "mks1_"',
        ):
            self.assertIn(marker, TEXT)

    def test_frozen_transcript_and_signature_carrier_match_m17_5_vectors(self) -> None:
        transcript = frozen_transcript()
        self.assertEqual(len(transcript), 236)
        self.assertEqual(transcript.hex(), EXPECTED_TRANSCRIPT_HEX)
        signature = bytes.fromhex(EXPECTED_SIGNATURE_HEX)
        payload = base64.urlsafe_b64encode(signature).rstrip(b"=").decode("ascii")
        self.assertEqual(len(signature), 64)
        self.assertEqual(len(payload), 86)
        self.assertEqual(len("mks1_" + payload), 91)

    def test_source_constructs_exact_transcript_components_in_order(self) -> None:
        start = TEXT.index("function buildTranscript")
        end = TEXT.index("function reviewedPrivateKey", start)
        block = TEXT[start:end]
        block = block[block.index("return concatenate(["):]
        expected = [
            "utf8(TRANSCRIPT_DOMAIN)",
            "Uint8Array.of(0x00, PROOF_VERSION)",
            "lengthPrefixed(PROOF_CRYPTOSUITE)",
            "lengthPrefixed(AUTH_PURPOSE)",
            "lengthPrefixed(verificationMethod)",
            "lengthPrefixed(AUTH_DOMAIN)",
            "challengeBytes",
        ]
        positions = [block.index(marker) for marker in expected]
        self.assertEqual(positions, sorted(positions))

    def test_key_and_request_guards_precede_the_only_signing_call(self) -> None:
        start = TEXT.index("async function createAuthenticationProof")
        end = TEXT.index("return Object.freeze({ createAuthenticationProof })", start)
        block = TEXT[start:end]
        self.assertEqual(block.count("reviewedSigner.sign("), 1)
        sign_at = block.index("reviewedSigner.sign(")
        for marker in (
            "reviewedRequest(requestValue, pinnedVerificationMethod)",
            "decodeChallenge(request.challenge)",
            "reviewedPrivateKey(privateKey)",
            "buildTranscript(pinnedVerificationMethod, challengeBytes)",
        ):
            self.assertLess(block.index(marker), sign_at)
        self.assertIn('{ name: "Ed25519" }', block)

    def test_private_key_shape_is_exact_and_signing_only(self) -> None:
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

    def test_request_binding_and_exact_proof_document_are_preserved(self) -> None:
        for marker in (
            "request.profile !== ESTABLISHMENT_PROFILE",
            "request.verificationMethod !== verificationMethod",
            "request.domain !== AUTH_DOMAIN",
            "request.proofPurpose !== AUTH_PURPOSE",
            "challenge: request.challenge",
            "proofValue,",
        ):
            self.assertIn(marker, TEXT)
        start = TEXT.index("return Object.freeze({", TEXT.index("const proofValue"))
        end = TEXT.index("});", start)
        returned = TEXT[start:end]
        for field in (
            "type:", "version:", "cryptosuite:", "proofPurpose:",
            "verificationMethod:", "domain:", "challenge:", "proofValue",
        ):
            self.assertIn(field, returned)

    def test_signature_result_is_exactly_64_bytes_before_transport(self) -> None:
        self.assertIn("signatureResult instanceof ArrayBuffer", TEXT)
        self.assertIn("bytes.length !== 64", TEXT)
        self.assertIn("payload.length !== SIGNATURE_PAYLOAD_CHARS", TEXT)

    def test_provider_exposes_only_purpose_specific_operation(self) -> None:
        self.assertIn("return Object.freeze({ createAuthenticationProof });", TEXT)
        self.assertNotIn("return Object.freeze({ sign", TEXT)
        self.assertNotIn("signAuthenticationProof", TEXT)


if __name__ == "__main__":
    unittest.main()
