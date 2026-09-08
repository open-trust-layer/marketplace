from __future__ import annotations

import json
import unittest
from unittest.mock import patch

import marketplace.application.auth_proof_profile as profile
from marketplace.application.auth import AUTH_PROOF_DOMAIN, AUTH_PROOF_PURPOSE
from marketplace.application.auth_challenge import encode_marketplace_auth_challenge
from marketplace.application.auth_proof_profile import (
    AUTH_PROOF_CRYPTOSUITE,
    AUTH_PROOF_TYPE,
    AUTH_PROOF_VERSION,
    AUTH_SIGNATURE_BYTES,
    AUTH_SIGNATURE_PAYLOAD_CHARS,
    AUTH_SIGNATURE_PREFIX,
    AUTH_SIGNATURE_TEXT_CHARS,
    AuthenticationProofSigningRequest,
    MarketplaceAuthenticationProofProfileError,
    build_marketplace_auth_transcript,
    decode_marketplace_authentication_proof_json,
    encode_marketplace_auth_signature,
    encode_marketplace_authentication_proof_json,
    make_marketplace_authentication_proof,
    parse_marketplace_auth_signature,
    parse_marketplace_authentication_proof_document,
)


CHALLENGE = bytes(range(32))
SIGNATURE = bytes(range(64))
VERIFICATION_METHOD = "did:example:alice#key-1"
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


def signing_request() -> AuthenticationProofSigningRequest:
    return AuthenticationProofSigningRequest(
        verification_method=VERIFICATION_METHOD,
        challenge=CHALLENGE,
    )


def proof_document() -> dict[str, object]:
    proof = make_marketplace_authentication_proof(signing_request(), SIGNATURE)
    return proof.to_document()


class M17AuthProofProfileTests(unittest.TestCase):
    def test_profile_constants_and_signature_carrier_are_exact(self):
        self.assertEqual(profile.PROFILE_NAME, "MARKETPLACE_APPLICATION_AUTH_PROOF_TRANSCRIPT_V1")
        self.assertEqual(AUTH_PROOF_TYPE, "MarketplaceAuthenticationProof")
        self.assertEqual(AUTH_PROOF_VERSION, 1)
        self.assertEqual(
            AUTH_PROOF_CRYPTOSUITE,
            "https://open-trust-layer.github.io/marketplace/application-auth/eddsa-ed25519-v1",
        )
        self.assertEqual(AUTH_PROOF_PURPOSE, "assertion")
        self.assertEqual(
            AUTH_PROOF_DOMAIN,
            "https://open-trust-layer.github.io/marketplace/application-auth/v1",
        )
        encoded = encode_marketplace_auth_signature(SIGNATURE)
        self.assertTrue(encoded.startswith(AUTH_SIGNATURE_PREFIX))
        self.assertEqual(len(encoded), AUTH_SIGNATURE_TEXT_CHARS)
        self.assertEqual(len(encoded.removeprefix(AUTH_SIGNATURE_PREFIX)), AUTH_SIGNATURE_PAYLOAD_CHARS)
        self.assertEqual(parse_marketplace_auth_signature(encoded), SIGNATURE)
        self.assertEqual(AUTH_SIGNATURE_BYTES, 64)

    def test_transcript_has_exact_frozen_vector(self):
        transcript = build_marketplace_auth_transcript(signing_request())
        self.assertEqual(len(transcript), 236)
        self.assertEqual(transcript.hex(), EXPECTED_TRANSCRIPT_HEX)
        self.assertNotIn(SIGNATURE, transcript)
        self.assertNotIn(b"mks1_", transcript)
        self.assertNotIn(b"mkc1_", transcript)

    def test_semantic_mutations_change_transcript_bytes(self):
        original = build_marketplace_auth_transcript(signing_request())

        changed_challenge = bytearray(CHALLENGE)
        changed_challenge[0] ^= 0x01
        self.assertNotEqual(
            build_marketplace_auth_transcript(
                AuthenticationProofSigningRequest(
                    verification_method=VERIFICATION_METHOD,
                    challenge=bytes(changed_challenge),
                )
            ),
            original,
        )
        self.assertNotEqual(
            build_marketplace_auth_transcript(
                AuthenticationProofSigningRequest(
                    verification_method="did:example:alice#key-2",
                    challenge=CHALLENGE,
                )
            ),
            original,
        )

        mutations = (
            ("AUTH_TRANSCRIPT_DOMAIN_SEPARATOR", b"MARKETPLACE-AUTI"),
            ("AUTH_PROOF_VERSION", 2),
            ("AUTH_PROOF_CRYPTOSUITE", AUTH_PROOF_CRYPTOSUITE[:-1] + "2"),
            ("AUTH_PROOF_PURPOSE", "assertiom"),
            ("AUTH_PROOF_DOMAIN", AUTH_PROOF_DOMAIN[:-1] + "2"),
        )
        for name, value in mutations:
            with self.subTest(name=name), patch.object(profile, name, value):
                self.assertNotEqual(build_marketplace_auth_transcript(signing_request()), original)

    def test_proof_document_and_json_round_trip_are_canonical(self):
        proof = make_marketplace_authentication_proof(signing_request(), SIGNATURE)
        document = proof.to_document()
        self.assertEqual(
            frozenset(document),
            frozenset(
                {
                    "type",
                    "version",
                    "cryptosuite",
                    "proofPurpose",
                    "verificationMethod",
                    "domain",
                    "challenge",
                    "proofValue",
                }
            ),
        )
        self.assertEqual(document["challenge"], encode_marketplace_auth_challenge(CHALLENGE))
        self.assertEqual(document["proofValue"], encode_marketplace_auth_signature(SIGNATURE))
        parsed = parse_marketplace_authentication_proof_document(document)
        self.assertEqual(parsed, proof)
        self.assertEqual(parsed.signing_request(), signing_request())

        wire = encode_marketplace_authentication_proof_json(proof)
        self.assertEqual(decode_marketplace_authentication_proof_json(wire), proof)
        self.assertEqual(wire, encode_marketplace_authentication_proof_json(parsed))
        self.assertNotIn(b" ", wire)
        self.assertNotIn(b"\n", wire)

    def test_signature_carrier_rejects_noncanonical_forms_without_reflection(self):
        valid = encode_marketplace_auth_signature(SIGNATURE)
        invalid_values = (
            None,
            b"not-text",
            "",
            "mks2_" + valid[5:],
            valid + "=",
            valid[:-1],
            valid[:-1] + "!",
            AUTH_SIGNATURE_PREFIX + "A" * (AUTH_SIGNATURE_PAYLOAD_CHARS - 1) + "B",
        )
        for value in invalid_values:
            with self.subTest(value=repr(value)[:30]):
                with self.assertRaises(MarketplaceAuthenticationProofProfileError) as raised:
                    parse_marketplace_auth_signature(value)
                self.assertEqual(str(raised.exception), "application authentication proof is invalid")
                self.assertNotIn(valid[:20], str(raised.exception))

    def test_document_rejects_unknown_missing_or_noncanonical_fields(self):
        base = proof_document()
        cases: list[dict[str, object]] = []

        unknown = dict(base)
        unknown["nonce"] = "forbidden"
        cases.append(unknown)

        missing = dict(base)
        del missing["domain"]
        cases.append(missing)

        for key, value in (
            ("type", "OLPProof"),
            ("version", True),
            ("version", 2),
            ("cryptosuite", "eddsa-ed25519-v1"),
            ("proofPurpose", "authorization"),
            ("verificationMethod", "not-an-absolute-uri"),
            ("verificationMethod", "did:example:" + "x" * 2048),
            ("domain", "https://example.invalid/other"),
            ("challenge", "mkc1_" + "A" * 42),
            ("proofValue", "mks1_" + "A" * 85),
        ):
            candidate = dict(base)
            candidate[key] = value
            cases.append(candidate)

        for candidate in cases:
            with self.subTest(candidate=repr(candidate)[:90]):
                with self.assertRaises(MarketplaceAuthenticationProofProfileError):
                    parse_marketplace_authentication_proof_document(candidate)

    def test_json_decoder_rejects_duplicates_bom_non_utf8_and_oversize(self):
        base = proof_document()
        canonical = json.dumps(base, separators=(",", ":"))
        duplicate = canonical[:-1] + ',"type":"MarketplaceAuthenticationProof"}'
        invalid_inputs = (
            duplicate.encode("utf-8"),
            b"\xef\xbb\xbf" + canonical.encode("utf-8"),
            b"\xff",
            b"[]",
            b"{}",
            b"{\"version\":NaN}",
            b"x" * (profile.AUTH_PROOF_JSON_MAX_BYTES + 1),
        )
        for raw in invalid_inputs:
            with self.subTest(size=len(raw)):
                with self.assertRaises(MarketplaceAuthenticationProofProfileError):
                    decode_marketplace_authentication_proof_json(raw)

    def test_signing_request_and_proof_values_never_admit_key_material(self):
        request = signing_request()
        self.assertEqual(request.verification_method, VERIFICATION_METHOD)
        self.assertEqual(request.challenge, CHALLENGE)
        self.assertEqual(request.__slots__, ("verification_method", "challenge"))
        proof = make_marketplace_authentication_proof(request, SIGNATURE)
        self.assertEqual(proof.proof_value, SIGNATURE)
        for forbidden_name in (
            "private_key",
            "seed",
            "mnemonic",
            "passphrase",
            "key_handle",
            "session_token",
            "principal",
        ):
            self.assertFalse(hasattr(request, forbidden_name))
            self.assertFalse(hasattr(proof, forbidden_name))

    def test_wrong_raw_shapes_fail_closed(self):
        with self.assertRaises(MarketplaceAuthenticationProofProfileError):
            AuthenticationProofSigningRequest(verification_method=VERIFICATION_METHOD, challenge=b"x" * 31)
        with self.assertRaises(MarketplaceAuthenticationProofProfileError):
            make_marketplace_authentication_proof(signing_request(), b"x" * 63)
        with self.assertRaises(MarketplaceAuthenticationProofProfileError):
            make_marketplace_authentication_proof(signing_request(), bytearray(SIGNATURE))
        with self.assertRaises(MarketplaceAuthenticationProofProfileError):
            build_marketplace_auth_transcript(object())  # type: ignore[arg-type]


if __name__ == "__main__":
    unittest.main()
