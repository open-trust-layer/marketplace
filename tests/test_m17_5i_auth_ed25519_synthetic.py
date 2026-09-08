from __future__ import annotations

import hashlib
import unittest

from olp.crypto.ed25519 import (
    public_key_bytes as olp_ed25519_public_key_bytes,
    sign as olp_ed25519_sign,
    verify as olp_ed25519_verify,
)

from marketplace.application.auth import (
    AUTH_PROOF_DOMAIN,
    AUTH_PROOF_PURPOSE,
    MarketplaceApplicationAuthService,
    VerifiedAuthenticationProof,
)
from marketplace.application.auth_challenge import parse_marketplace_auth_challenge
from marketplace.application.auth_proof_profile import (
    AuthenticationProofSigningRequest,
    build_marketplace_auth_transcript,
    encode_marketplace_auth_signature,
    make_marketplace_authentication_proof,
    parse_marketplace_auth_signature,
    parse_marketplace_authentication_proof_document,
)
from marketplace.application.auth_session_http import MarketplaceAuthenticationSessionHttpAdapter
from tests.test_m17_5d_session_establishment import (
    CHALLENGE,
    METHOD,
    PRINCIPAL,
    TOKEN,
    AllowBinding,
    MaterialSource,
    decode,
    request,
)


PROFILE_NAME = "MARKETPLACE_APPLICATION_AUTH_ED25519_SYNTHETIC_V1"

# RFC 8032 Ed25519 test vector 1. This fixture is deliberately public,
# deterministic, non-secret, and never suitable for production custody.
RFC8032_TEST_SEED_HEX = "9d61b19deffd5a60ba844af492ec2cc44449c5697b326919703bac031cae7f60"
RFC8032_TEST_PUBLIC_KEY_HEX = "d75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a"
TEST_SEED = bytes.fromhex(RFC8032_TEST_SEED_HEX)
TEST_PUBLIC_KEY = bytes.fromhex(RFC8032_TEST_PUBLIC_KEY_HEX)

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


class SyntheticEd25519AuthenticationProofSigner:
    """Test-only purpose-specific signer over the frozen M17.5H transcript."""

    __slots__ = ()

    def sign_authentication_proof(self, request_value: AuthenticationProofSigningRequest) -> bytes:
        if type(request_value) is not AuthenticationProofSigningRequest:
            raise TypeError("authentication proof signing request required")
        transcript = build_marketplace_auth_transcript(request_value)
        return olp_ed25519_sign(TEST_SEED, transcript)


class SyntheticEd25519AuthenticationProofVerifier:
    """Test-only verifier returning only the existing M17.5D proof facts."""

    __slots__ = ()

    def verify(self, proof_document: object) -> VerifiedAuthenticationProof:
        proof = parse_marketplace_authentication_proof_document(proof_document)
        transcript = build_marketplace_auth_transcript(proof.signing_request())
        cryptographically_valid = olp_ed25519_verify(
            TEST_PUBLIC_KEY,
            proof.proof_value,
            transcript,
        )
        return VerifiedAuthenticationProof(
            challenge_sha256=hashlib.sha256(proof.challenge).digest(),
            domain=proof.domain,
            proof_purpose=proof.proof_purpose,
            verification_method=proof.verification_method,
            cryptographically_valid=cryptographically_valid,
        )


def signing_request(challenge: bytes = CHALLENGE) -> AuthenticationProofSigningRequest:
    return AuthenticationProofSigningRequest(
        verification_method=METHOD,
        challenge=challenge,
    )


def signed_proof(challenge: bytes = CHALLENGE):
    signer = SyntheticEd25519AuthenticationProofSigner()
    signature = signer.sign_authentication_proof(signing_request(challenge))
    return make_marketplace_authentication_proof(signing_request(challenge), signature)


def make_session_adapter(*, verifier=None):
    source = MaterialSource()
    auth = MarketplaceApplicationAuthService(principal_binding_verifier=AllowBinding())
    proof_verifier = verifier or SyntheticEd25519AuthenticationProofVerifier()
    adapter = MarketplaceAuthenticationSessionHttpAdapter(
        auth=auth,
        material_source=source,
        proof_verifier=proof_verifier,
    )
    return adapter, source, proof_verifier


class M17AuthEd25519SyntheticTests(unittest.TestCase):
    def test_frozen_transcript_has_exact_real_ed25519_vector(self):
        transcript = build_marketplace_auth_transcript(signing_request())
        self.assertEqual(PROFILE_NAME, "MARKETPLACE_APPLICATION_AUTH_ED25519_SYNTHETIC_V1")
        self.assertEqual(len(transcript), 236)
        self.assertEqual(transcript.hex(), EXPECTED_TRANSCRIPT_HEX)
        self.assertEqual(olp_ed25519_public_key_bytes(TEST_SEED), TEST_PUBLIC_KEY)

        signature = SyntheticEd25519AuthenticationProofSigner().sign_authentication_proof(
            signing_request()
        )
        self.assertEqual(len(signature), 64)
        self.assertEqual(signature.hex(), EXPECTED_SIGNATURE_HEX)
        self.assertTrue(olp_ed25519_verify(TEST_PUBLIC_KEY, signature, transcript))

        carrier = encode_marketplace_auth_signature(signature)
        self.assertTrue(carrier.startswith("mks1_"))
        self.assertEqual(parse_marketplace_auth_signature(carrier), signature)

    def test_synthetic_signer_and_verifier_return_exact_frozen_facts(self):
        proof = signed_proof()
        facts = SyntheticEd25519AuthenticationProofVerifier().verify(proof.to_document())
        self.assertEqual(
            facts,
            VerifiedAuthenticationProof(
                challenge_sha256=hashlib.sha256(CHALLENGE).digest(),
                domain=AUTH_PROOF_DOMAIN,
                proof_purpose=AUTH_PROOF_PURPOSE,
                verification_method=METHOD,
                cryptographically_valid=True,
            ),
        )
        self.assertEqual(
            parse_marketplace_authentication_proof_document(proof.to_document()),
            proof,
        )

    def test_well_formed_corrupted_signature_maps_to_auth_proof_invalid(self):
        adapter, source, verifier = make_session_adapter()
        challenge_response = adapter.handle(
            request(
                "POST",
                "/api/auth/challenges",
                {"principal": PRINCIPAL, "verification_method": METHOD},
            ),
            session_token=None,
            session_invalid=False,
            now=100,
        )
        challenge_text = decode(challenge_response)["challenge"]
        self.assertEqual(parse_marketplace_auth_challenge(challenge_text), CHALLENGE)

        proof = signed_proof()
        corrupted = bytearray(proof.proof_value)
        corrupted[0] ^= 0x01
        corrupted_proof = make_marketplace_authentication_proof(
            proof.signing_request(),
            bytes(corrupted),
        )
        direct_facts = verifier.verify(corrupted_proof.to_document())
        self.assertFalse(direct_facts.cryptographically_valid)

        response = adapter.handle(
            request(
                "POST",
                "/api/auth/sessions",
                {"challenge": challenge_text, "proof": corrupted_proof.to_document()},
            ),
            session_token=None,
            session_invalid=False,
            now=101,
        )
        self.assertEqual(response.status_code, 401)
        self.assertEqual(decode(response)["error"]["code"], "AUTH_PROOF_INVALID")
        self.assertEqual(source.token_calls, 1)

    def test_changed_transcript_bound_challenge_cannot_authenticate_registered_attempt(self):
        adapter, _, verifier = make_session_adapter()
        challenge_response = adapter.handle(
            request(
                "POST",
                "/api/auth/challenges",
                {"principal": PRINCIPAL, "verification_method": METHOD},
            ),
            session_token=None,
            session_invalid=False,
            now=100,
        )
        challenge_text = decode(challenge_response)["challenge"]

        changed = bytearray(CHALLENGE)
        changed[0] ^= 0x01
        changed_proof = signed_proof(bytes(changed))
        self.assertTrue(verifier.verify(changed_proof.to_document()).cryptographically_valid)

        response = adapter.handle(
            request(
                "POST",
                "/api/auth/sessions",
                {"challenge": challenge_text, "proof": changed_proof.to_document()},
            ),
            session_token=None,
            session_invalid=False,
            now=101,
        )
        self.assertEqual(response.status_code, 401)
        self.assertEqual(decode(response)["error"]["code"], "AUTH_PROOF_INVALID")

    def test_full_in_process_challenge_signed_proof_session_flow_succeeds(self):
        adapter, source, verifier = make_session_adapter()
        challenge_response = adapter.handle(
            request(
                "POST",
                "/api/auth/challenges",
                {"principal": PRINCIPAL, "verification_method": METHOD},
            ),
            session_token=None,
            session_invalid=False,
            now=100,
        )
        self.assertEqual(challenge_response.status_code, 201)
        challenge_text = decode(challenge_response)["challenge"]
        challenge = parse_marketplace_auth_challenge(challenge_text)

        signer = SyntheticEd25519AuthenticationProofSigner()
        signing = AuthenticationProofSigningRequest(
            verification_method=METHOD,
            challenge=challenge,
        )
        signature = signer.sign_authentication_proof(signing)
        proof = make_marketplace_authentication_proof(signing, signature)

        session_response = adapter.handle(
            request(
                "POST",
                "/api/auth/sessions",
                {"challenge": challenge_text, "proof": proof.to_document()},
            ),
            session_token=None,
            session_invalid=False,
            now=101,
        )
        document = decode(session_response)
        self.assertEqual(session_response.status_code, 201)
        self.assertEqual(document["principal"], PRINCIPAL)
        self.assertEqual(document["verification_method"], METHOD)
        self.assertTrue(document["session_token"].startswith("mkt1_"))
        self.assertEqual(source.challenge_calls, 1)
        self.assertEqual(source.token_calls, 1)
        self.assertIsInstance(verifier, SyntheticEd25519AuthenticationProofVerifier)

    def test_verifier_infrastructure_exception_keeps_existing_unavailable_mapping(self):
        class RaisingVerifier:
            def verify(self, proof_document: object):
                raise RuntimeError("synthetic verifier infrastructure detail")

        adapter, source, _ = make_session_adapter(verifier=RaisingVerifier())
        challenge_response = adapter.handle(
            request(
                "POST",
                "/api/auth/challenges",
                {"principal": PRINCIPAL, "verification_method": METHOD},
            ),
            session_token=None,
            session_invalid=False,
            now=100,
        )
        challenge_text = decode(challenge_response)["challenge"]
        response = adapter.handle(
            request(
                "POST",
                "/api/auth/sessions",
                {"challenge": challenge_text, "proof": signed_proof().to_document()},
            ),
            session_token=None,
            session_invalid=False,
            now=101,
        )
        self.assertEqual(response.status_code, 503)
        self.assertEqual(
            decode(response)["error"]["code"],
            "AUTH_PROOF_VERIFIER_UNAVAILABLE",
        )
        self.assertNotIn(b"synthetic verifier infrastructure detail", response.body)
        self.assertEqual(source.token_calls, 0)

    def test_fixture_exposes_only_purpose_specific_signing_surface(self):
        signer = SyntheticEd25519AuthenticationProofSigner()
        self.assertTrue(callable(signer.sign_authentication_proof))
        self.assertFalse(hasattr(signer, "sign"))
        self.assertFalse(hasattr(signer, "__dict__"))
        self.assertEqual(SyntheticEd25519AuthenticationProofSigner.__slots__, ())


if __name__ == "__main__":
    unittest.main()
