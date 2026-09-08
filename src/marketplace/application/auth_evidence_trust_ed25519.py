"""M17.5M static Ed25519 authentication-evidence trust verification.

Trust anchors are immutable, constructor-injected public material. This module
performs no acquisition, refresh, persistence, signing, or runtime selection.
"""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
import hashlib
import re
from types import MappingProxyType
from typing import Final, Mapping

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from .auth_verification_method_evidence import (
    AuthenticationVerificationMethodEvidenceError,
    MarketplaceAuthenticationVerificationMethodEvidenceEnvelope,
    VerifiedAuthenticationVerificationMethodEvidence,
    decode_marketplace_authentication_verification_method_evidence_claims,
)


PROFILE_NAME: Final = "MARKETPLACE_APPLICATION_AUTH_EVIDENCE_ED25519_TRUST_V1"
AUTH_EVIDENCE_TRUST_MAX_ANCHORS: Final = 64
AUTH_EVIDENCE_TRUST_PUBLIC_KEY_BYTES: Final = 32
AUTH_EVIDENCE_TRUST_SIGNATURE_BYTES: Final = 64
AUTH_EVIDENCE_TRUST_URI_MAX_BYTES: Final = 2048
AUTH_EVIDENCE_TRUST_TRANSCRIPT_PREFIX: Final = b"MARKETPLACE-AUTH-EVIDENCE"
AUTH_EVIDENCE_TRUST_TRANSCRIPT_VERSION: Final = 1
_AUTHORITY_RE = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:[^\s]+$")


class AuthenticationEvidenceTrustError(ValueError):
    """Stable fail-closed trust error without evidence reflection."""

    def __init__(self) -> None:
        super().__init__("authentication evidence trust verification failed")


def _fail() -> None:
    raise AuthenticationEvidenceTrustError() from None


def _authority_uri(value: object) -> str:
    if type(value) is not str or not value:
        _fail()
    try:
        encoded = value.encode("utf-8", "strict")
    except UnicodeEncodeError:
        _fail()
    if len(encoded) > AUTH_EVIDENCE_TRUST_URI_MAX_BYTES:
        _fail()
    if _AUTHORITY_RE.fullmatch(value) is None:
        _fail()
    return value


@dataclass(frozen=True, slots=True)
class AuthenticationEvidenceTrustAnchor:
    """One exact authority-to-public-key trust statement."""

    authority: str
    public_key: bytes

    def __post_init__(self) -> None:
        _authority_uri(self.authority)
        if type(self.public_key) is not bytes:
            _fail()
        if len(self.public_key) != AUTH_EVIDENCE_TRUST_PUBLIC_KEY_BYTES:
            _fail()


@dataclass(frozen=True, slots=True, init=False)
class MarketplaceAuthenticationEvidenceTrustAnchorSnapshot:
    """Immutable authority-key snapshot for authentication evidence only."""

    _anchors: Mapping[str, bytes]

    def __init__(self, anchors: Sequence[AuthenticationEvidenceTrustAnchor]) -> None:
        if type(anchors) not in (list, tuple):
            _fail()
        if not (1 <= len(anchors) <= AUTH_EVIDENCE_TRUST_MAX_ANCHORS):
            _fail()

        copied: dict[str, bytes] = {}
        for anchor in anchors:
            if type(anchor) is not AuthenticationEvidenceTrustAnchor:
                _fail()
            if anchor.authority in copied:
                _fail()
            copied[anchor.authority] = anchor.public_key
        object.__setattr__(self, "_anchors", MappingProxyType(copied))

    def authentication_evidence_trust_key_bytes(self, authority: str) -> bytes:
        """Return one exact public anchor key; never search or fall back."""

        reviewed_authority = _authority_uri(authority)
        key = self._anchors.get(reviewed_authority)
        if type(key) is not bytes:
            _fail()
        if len(key) != AUTH_EVIDENCE_TRUST_PUBLIC_KEY_BYTES:
            _fail()
        return key


def build_marketplace_authentication_evidence_trust_transcript(
    *,
    authority: str,
    claims_sha256: bytes,
) -> bytes:
    """Build the frozen domain-separated evidence-attestation transcript."""

    reviewed_authority = _authority_uri(authority)
    if type(claims_sha256) is not bytes or len(claims_sha256) != 32:
        _fail()
    authority_bytes = reviewed_authority.encode("utf-8", "strict")
    if len(authority_bytes) > 0xFFFF:
        _fail()
    return (
        AUTH_EVIDENCE_TRUST_TRANSCRIPT_PREFIX
        + b"\x00"
        + bytes((AUTH_EVIDENCE_TRUST_TRANSCRIPT_VERSION,))
        + len(authority_bytes).to_bytes(2, "big")
        + authority_bytes
        + claims_sha256
    )


class MarketplaceEd25519AuthenticationEvidenceTrustVerifier:
    """Verify one L evidence attestation against one exact public anchor."""

    __slots__ = ("_trust_key_bytes",)

    def __init__(
        self,
        *,
        trust_anchors: MarketplaceAuthenticationEvidenceTrustAnchorSnapshot,
    ) -> None:
        if type(trust_anchors) is not MarketplaceAuthenticationEvidenceTrustAnchorSnapshot:
            _fail()
        trust_key_bytes = getattr(
            trust_anchors,
            "authentication_evidence_trust_key_bytes",
            None,
        )
        if not callable(trust_key_bytes):
            _fail()
        self._trust_key_bytes = trust_key_bytes

    def verify_authentication_verification_method_evidence(
        self,
        envelope: MarketplaceAuthenticationVerificationMethodEvidenceEnvelope,
    ) -> VerifiedAuthenticationVerificationMethodEvidence:
        if type(envelope) is not MarketplaceAuthenticationVerificationMethodEvidenceEnvelope:
            _fail()
        if len(envelope.attestation) != AUTH_EVIDENCE_TRUST_SIGNATURE_BYTES:
            _fail()

        try:
            claims = decode_marketplace_authentication_verification_method_evidence_claims(
                envelope.claims_json
            )
        except AuthenticationVerificationMethodEvidenceError:
            _fail()

        claims_sha256 = hashlib.sha256(envelope.claims_json).digest()
        key_material = self._trust_key_bytes(claims.authority)
        if type(key_material) is not bytes:
            _fail()
        if len(key_material) != AUTH_EVIDENCE_TRUST_PUBLIC_KEY_BYTES:
            _fail()

        transcript = build_marketplace_authentication_evidence_trust_transcript(
            authority=claims.authority,
            claims_sha256=claims_sha256,
        )
        try:
            public_key = Ed25519PublicKey.from_public_bytes(key_material)
        except (TypeError, ValueError):
            _fail()

        accepted = True
        try:
            public_key.verify(envelope.attestation, transcript)
        except InvalidSignature:
            accepted = False

        return VerifiedAuthenticationVerificationMethodEvidence(
            claims_sha256=claims_sha256,
            authority=claims.authority,
            accepted=accepted,
        )


__all__ = [
    "AUTH_EVIDENCE_TRUST_MAX_ANCHORS",
    "AUTH_EVIDENCE_TRUST_PUBLIC_KEY_BYTES",
    "AUTH_EVIDENCE_TRUST_SIGNATURE_BYTES",
    "AUTH_EVIDENCE_TRUST_TRANSCRIPT_PREFIX",
    "AUTH_EVIDENCE_TRUST_TRANSCRIPT_VERSION",
    "AUTH_EVIDENCE_TRUST_URI_MAX_BYTES",
    "AuthenticationEvidenceTrustAnchor",
    "AuthenticationEvidenceTrustError",
    "MarketplaceAuthenticationEvidenceTrustAnchorSnapshot",
    "MarketplaceEd25519AuthenticationEvidenceTrustVerifier",
    "PROFILE_NAME",
    "build_marketplace_authentication_evidence_trust_transcript",
]
