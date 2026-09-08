"""M17.5J production-source Ed25519 authentication proof verifier.

This module performs only public-key verification for the frozen Marketplace
application-authentication proof profile. Verification-key discovery remains an
injected capability; this module owns no private-key, signer, resolver, network,
persistence, runtime-selection, or principal-binding authority.
"""
from __future__ import annotations

import hashlib
from typing import Final, Protocol

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from .auth import VerifiedAuthenticationProof
from .auth_proof_profile import (
    build_marketplace_auth_transcript,
    parse_marketplace_authentication_proof_document,
)


PROFILE_NAME: Final = "MARKETPLACE_APPLICATION_AUTH_ED25519_VERIFIER_V1"
AUTH_VERIFICATION_KEY_BYTES: Final = 32


class AuthenticationVerificationKeySource(Protocol):
    """Injected authentication-only public verification-key lookup capability."""

    def verification_key_bytes(self, verification_method: str) -> bytes: ...


class MarketplaceEd25519AuthenticationProofVerifier:
    """Verify the exact frozen Marketplace authentication transcript with Ed25519."""

    __slots__ = ("_verification_key_bytes",)

    def __init__(self, *, key_source: AuthenticationVerificationKeySource) -> None:
        verification_key_bytes = getattr(key_source, "verification_key_bytes", None)
        if not callable(verification_key_bytes):
            raise TypeError("key_source MUST provide callable verification_key_bytes")
        self._verification_key_bytes = verification_key_bytes

    def verify(self, proof_document: object) -> VerifiedAuthenticationProof:
        proof = parse_marketplace_authentication_proof_document(proof_document)
        key_material = self._verification_key_bytes(proof.verification_method)
        if type(key_material) is not bytes or len(key_material) != AUTH_VERIFICATION_KEY_BYTES:
            raise ValueError("authentication verification key is unavailable")

        public_key = Ed25519PublicKey.from_public_bytes(key_material)
        transcript = build_marketplace_auth_transcript(proof.signing_request())
        cryptographically_valid = True
        try:
            public_key.verify(proof.proof_value, transcript)
        except InvalidSignature:
            cryptographically_valid = False

        return VerifiedAuthenticationProof(
            challenge_sha256=hashlib.sha256(proof.challenge).digest(),
            domain=proof.domain,
            proof_purpose=proof.proof_purpose,
            verification_method=proof.verification_method,
            cryptographically_valid=cryptographically_valid,
        )


__all__ = [
    "AUTH_VERIFICATION_KEY_BYTES",
    "AuthenticationVerificationKeySource",
    "MarketplaceEd25519AuthenticationProofVerifier",
    "PROFILE_NAME",
]
