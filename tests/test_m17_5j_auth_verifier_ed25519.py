from __future__ import annotations

import hashlib
import unittest

from marketplace.application.auth import (
    AUTH_PROOF_DOMAIN,
    AUTH_PROOF_PURPOSE,
    MarketplaceApplicationAuthService,
    VerifiedAuthenticationProof,
)
from marketplace.application.auth_challenge import parse_marketplace_auth_challenge
from marketplace.application.auth_proof_profile import (
    AuthenticationProofSigningRequest,
    make_marketplace_authentication_proof,
)
from marketplace.application.auth_session_http import MarketplaceAuthenticationSessionHttpAdapter
from marketplace.application.auth_verifier_ed25519 import (
    AuthenticationVerificationKeySource,
    MarketplaceEd25519AuthenticationProofVerifier,
    PROFILE_NAME,
)
from tests.test_m17_5d_session_establishment import (
    CHALLENGE,
    METHOD,
    PRINCIPAL,
    AllowBinding,
    MaterialSource,
    decode,
    request,
)


# Frozen M17.5I public qualification values. There is deliberately no private
# seed and no signing operation in this production-verifier milestone.
TEST_PUBLIC_KEY = bytes.fromhex(
    "d75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a"
)
EXPECTED_SIGNATURE = bytes.fromhex(
    "85fb0e24d5b1bf54ae397e1028a6e2db690e67d8eaa279fcd2e39cfe17240030"
    "206b3eda21574888fde8b0b6d331cba53438e660b3e17bb9d481ce06179ed505"
)


class FixedVerificationKeySource:
    def __init__(self, value: object = TEST_PUBLIC_KEY) -> None:
        self.value = value
        self.methods: list[str] = []

    def verification_key_bytes(self, verification_method: str) -> bytes:
        self.methods.append(verification_method)
        return self.value  # type: ignore[return-value]


class RaisingVerificationKeySource:
    def verification_key_bytes(self, verification_method: str) -> bytes:
        raise RuntimeError("provider detail MUST NOT be reflected")


def frozen_proof(
    *,
    challenge: bytes = CHALLENGE,
    method: str = METHOD,
    signature: bytes = EXPECTED_SIGNATURE,
):
    signing_request = AuthenticationProofSigningRequest(
        verification_method=method,
        challenge=challenge,
    )
    return make_marketplace_authentication_proof(signing_request, signature)


def make_adapter(key_source: AuthenticationVerificationKeySource):
    source = MaterialSource()
    auth = MarketplaceApplicationAuthService(principal_binding_verifier=AllowBinding())
    verifier = MarketplaceEd25519AuthenticationProofVerifier(key_source=key_source)
    adapter = MarketplaceAuthenticationSessionHttpAdapter(
        auth=auth,
        material_source=source,
        proof_verifier=verifier,
    )
    return adapter, source, verifier


class M17AuthEd25519VerifierTests(unittest.TestCase):
    def test_profile_and_frozen_public_vector_verify_without_private_material(self):
        key_source = FixedVerificationKeySource()
        verifier = MarketplaceEd25519AuthenticationProofVerifier(key_source=key_source)
        proof = frozen_proof()

        facts = verifier.verify(proof.to_document())

        self.assertEqual(PROFILE_NAME, "MARKETPLACE_APPLICATION_AUTH_ED25519_VERIFIER_V1")
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
        self.assertEqual(key_source.methods, [METHOD])

    def test_well_formed_corrupted_signature_returns_invalid_facts_and_existing_401(self):
        key_source = FixedVerificationKeySource()
        adapter, source, verifier = make_adapter(key_source)
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

        corrupted = bytearray(EXPECTED_SIGNATURE)
        corrupted[-1] ^= 0x01
        proof = frozen_proof(signature=bytes(corrupted))
        direct = verifier.verify(proof.to_document())
        self.assertFalse(direct.cryptographically_valid)

        response = adapter.handle(
            request(
                "POST",
                "/api/auth/sessions",
                {"challenge": challenge_text, "proof": proof.to_document()},
            ),
            session_token=None,
            session_invalid=False,
            now=101,
        )
        self.assertEqual(response.status_code, 401)
        self.assertEqual(decode(response)["error"]["code"], "AUTH_PROOF_INVALID")
        self.assertEqual(source.token_calls, 1)
        self.assertEqual(key_source.methods, [METHOD, METHOD])

    def test_changed_transcript_bound_challenge_cannot_verify_original_signature(self):
        key_source = FixedVerificationKeySource()
        verifier = MarketplaceEd25519AuthenticationProofVerifier(key_source=key_source)
        changed = bytearray(CHALLENGE)
        changed[0] ^= 0x01
        facts = verifier.verify(frozen_proof(challenge=bytes(changed)).to_document())
        self.assertFalse(facts.cryptographically_valid)
        self.assertEqual(key_source.methods, [METHOD])

    def test_key_source_exception_keeps_existing_verifier_unavailable_mapping(self):
        adapter, source, _ = make_adapter(RaisingVerificationKeySource())
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
                {"challenge": challenge_text, "proof": frozen_proof().to_document()},
            ),
            session_token=None,
            session_invalid=False,
            now=101,
        )
        self.assertEqual(response.status_code, 503)
        self.assertEqual(decode(response)["error"]["code"], "AUTH_PROOF_VERIFIER_UNAVAILABLE")
        self.assertNotIn(b"provider detail", response.body)
        self.assertEqual(source.token_calls, 0)

    def test_wrong_key_type_and_length_fail_closed_without_retry_or_fallback(self):
        for value in (bytearray(TEST_PUBLIC_KEY), TEST_PUBLIC_KEY[:-1], TEST_PUBLIC_KEY + b"\x00"):
            with self.subTest(value_type=type(value).__name__, value_length=len(value)):
                key_source = FixedVerificationKeySource(value)
                verifier = MarketplaceEd25519AuthenticationProofVerifier(key_source=key_source)
                with self.assertRaises(ValueError):
                    verifier.verify(frozen_proof().to_document())
                self.assertEqual(key_source.methods, [METHOD])

    def test_constructor_requires_purpose_specific_key_source_callable(self):
        with self.assertRaises(TypeError):
            MarketplaceEd25519AuthenticationProofVerifier(key_source=object())  # type: ignore[arg-type]


if __name__ == "__main__":
    unittest.main()
