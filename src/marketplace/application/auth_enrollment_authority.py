"""M17.6E unselected authentication enrollment authority evidence issuance.

This module turns one exact caller-reviewed enrollment proposal into one canonical
M17.5L evidence envelope through one injected purpose-specific attestor. It
performs no attestor acquisition, key custody, persistence, network, or runtime
selection.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
from typing import Final, Protocol

from .auth_evidence_trust_ed25519 import (
    AUTH_EVIDENCE_TRUST_SIGNATURE_BYTES,
    AuthenticationEvidenceTrustError,
    build_marketplace_authentication_evidence_trust_transcript,
)
from .auth_verification_method_evidence import (
    AuthenticationVerificationMethodEvidenceClaim,
    AuthenticationVerificationMethodEvidenceError,
    MarketplaceAuthenticationVerificationMethodEvidenceClaims,
    MarketplaceAuthenticationVerificationMethodEvidenceEnvelope,
    encode_marketplace_authentication_verification_method_evidence_claims,
    parse_marketplace_auth_verification_public_key,
)


PROFILE_NAME: Final = "MARKETPLACE_APPLICATION_AUTH_ENROLLMENT_AUTHORITY_V1"


class AuthenticationEnrollmentAuthorityError(ValueError):
    """Stable fail-closed enrollment-authority error without input reflection."""

    def __init__(self) -> None:
        super().__init__("authentication enrollment authority operation failed")


def _fail() -> None:
    raise AuthenticationEnrollmentAuthorityError() from None


@dataclass(frozen=True, slots=True)
class MarketplaceAuthenticationEnrollmentProposal:
    """One exact non-authoritative enrollment proposal."""

    principal: str
    verification_method: str
    public_key: str

    def __post_init__(self) -> None:
        try:
            public_key = parse_marketplace_auth_verification_public_key(self.public_key)
            AuthenticationVerificationMethodEvidenceClaim(
                verification_method=self.verification_method,
                controller_principal=self.principal,
                public_key=public_key,
            )
        except AuthenticationVerificationMethodEvidenceError:
            _fail()


class AuthenticationEnrollmentAuthorityAttestor(Protocol):
    """Purpose-specific authority attestor; not a generic signing interface."""

    def attest_authentication_enrollment(self, transcript: bytes) -> bytes: ...


def issue_marketplace_authentication_enrollment_evidence(
    *,
    proposal: MarketplaceAuthenticationEnrollmentProposal,
    authority: str,
    issued_at: int,
    expires_at: int,
    attestor: AuthenticationEnrollmentAuthorityAttestor,
) -> MarketplaceAuthenticationVerificationMethodEvidenceEnvelope:
    """Issue one finite canonical evidence envelope for one exact proposal."""

    if type(proposal) is not MarketplaceAuthenticationEnrollmentProposal:
        _fail()

    try:
        public_key = parse_marketplace_auth_verification_public_key(proposal.public_key)
        claim = AuthenticationVerificationMethodEvidenceClaim(
            verification_method=proposal.verification_method,
            controller_principal=proposal.principal,
            public_key=public_key,
        )
        claims = MarketplaceAuthenticationVerificationMethodEvidenceClaims(
            authority=authority,
            issued_at=issued_at,
            expires_at=expires_at,
            entries=(claim,),
        )
        claims_json = encode_marketplace_authentication_verification_method_evidence_claims(claims)
    except AuthenticationVerificationMethodEvidenceError:
        _fail()

    claims_sha256 = hashlib.sha256(claims_json).digest()
    try:
        transcript = build_marketplace_authentication_evidence_trust_transcript(
            authority=claims.authority,
            claims_sha256=claims_sha256,
        )
    except AuthenticationEvidenceTrustError:
        _fail()

    operation = getattr(attestor, "attest_authentication_enrollment", None)
    if not callable(operation):
        _fail()
    try:
        signature = operation(transcript)
    except Exception:
        _fail()
    if type(signature) is not bytes or len(signature) != AUTH_EVIDENCE_TRUST_SIGNATURE_BYTES:
        _fail()

    try:
        return MarketplaceAuthenticationVerificationMethodEvidenceEnvelope(
            claims_json=claims_json,
            attestation=signature,
        )
    except AuthenticationVerificationMethodEvidenceError:
        _fail()


__all__ = [
    "AuthenticationEnrollmentAuthorityAttestor",
    "AuthenticationEnrollmentAuthorityError",
    "MarketplaceAuthenticationEnrollmentProposal",
    "PROFILE_NAME",
    "issue_marketplace_authentication_enrollment_evidence",
]
