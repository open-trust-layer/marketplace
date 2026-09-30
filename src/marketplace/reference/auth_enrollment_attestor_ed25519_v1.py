"""M17.6T unselected reference Ed25519 authentication-enrollment attestor."""
from __future__ import annotations

from typing import Final

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from ..application.auth_evidence_trust_ed25519 import (
    AUTH_EVIDENCE_TRUST_SIGNATURE_BYTES,
    AUTH_EVIDENCE_TRUST_TRANSCRIPT_PREFIX,
    AUTH_EVIDENCE_TRUST_TRANSCRIPT_VERSION,
    build_marketplace_authentication_evidence_trust_transcript,
)


PROFILE_NAME: Final = (
    "MARKETPLACE_REFERENCE_AUTHENTICATION_ENROLLMENT_ED25519_ATTESTOR_V1"
)
REFERENCE_AUTH_ENROLLMENT_ED25519_PRIVATE_KEY_BYTES: Final = 32
_CLAIMS_SHA256_BYTES: Final = 32
_ERROR_MESSAGE: Final = (
    "reference authentication enrollment Ed25519 attestor failed"
)


class MarketplaceReferenceAuthenticationEnrollmentEd25519AttestorError(
    RuntimeError
):
    """Stable fail-closed reference enrollment-attestor error."""

    def __init__(self) -> None:
        super().__init__(_ERROR_MESSAGE)


def _fail() -> None:
    raise MarketplaceReferenceAuthenticationEnrollmentEd25519AttestorError() from None


def _review_transcript(value: object) -> bytes:
    if type(value) is not bytes:
        _fail()

    prefix_length = len(AUTH_EVIDENCE_TRUST_TRANSCRIPT_PREFIX)
    authority_length_offset = prefix_length + 2
    header_length = prefix_length + 4
    minimum_length = header_length + 1 + _CLAIMS_SHA256_BYTES

    if len(value) < minimum_length:
        _fail()
    if value[:prefix_length] != AUTH_EVIDENCE_TRUST_TRANSCRIPT_PREFIX:
        _fail()
    if value[prefix_length] != 0:
        _fail()
    if value[prefix_length + 1] != AUTH_EVIDENCE_TRUST_TRANSCRIPT_VERSION:
        _fail()

    authority_length = int.from_bytes(
        value[authority_length_offset:header_length],
        "big",
    )
    if authority_length < 1:
        _fail()

    expected_length = header_length + authority_length + _CLAIMS_SHA256_BYTES
    if len(value) != expected_length:
        _fail()

    authority_bytes = value[header_length:header_length + authority_length]
    claims_sha256 = value[-_CLAIMS_SHA256_BYTES:]
    try:
        authority = authority_bytes.decode("utf-8", "strict")
        rebuilt = build_marketplace_authentication_evidence_trust_transcript(
            authority=authority,
            claims_sha256=claims_sha256,
        )
    except Exception:
        _fail()
    if rebuilt != value:
        _fail()
    return value


class MarketplaceReferenceAuthenticationEnrollmentEd25519Attestor:
    """Process-local purpose-specific Ed25519 enrollment attestor."""

    __slots__ = ("_private_key",)

    def __init__(self, *, private_key_bytes: bytes) -> None:
        if (
            type(private_key_bytes) is not bytes
            or len(private_key_bytes)
            != REFERENCE_AUTH_ENROLLMENT_ED25519_PRIVATE_KEY_BYTES
        ):
            _fail()
        try:
            private_key = Ed25519PrivateKey.from_private_bytes(private_key_bytes)
        except Exception:
            _fail()
        self._private_key = private_key

    def attest_authentication_enrollment(self, transcript: bytes) -> bytes:
        """Attest exactly one reviewed M17.5M authentication-evidence transcript."""

        reviewed = _review_transcript(transcript)
        try:
            signature = self._private_key.sign(reviewed)
        except Exception:
            _fail()
        if (
            type(signature) is not bytes
            or len(signature) != AUTH_EVIDENCE_TRUST_SIGNATURE_BYTES
        ):
            _fail()
        return signature


__all__ = [
    "MarketplaceReferenceAuthenticationEnrollmentEd25519Attestor",
    "MarketplaceReferenceAuthenticationEnrollmentEd25519AttestorError",
    "PROFILE_NAME",
    "REFERENCE_AUTH_ENROLLMENT_ED25519_PRIVATE_KEY_BYTES",
]
