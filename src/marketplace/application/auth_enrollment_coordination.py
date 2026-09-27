"""M17.6G authenticated enrollment coordination with one-time replay consumption.

This module binds one exact active Marketplace session to one exact enrollment
proposal, consumes one injected purpose-specific replay nonce, and only then
delegates to the reviewed M17.6F policy gate. It selects no transport, nonce
store, policy implementation, attestor provider, or runtime.
"""
from __future__ import annotations

from typing import Final, Protocol

from .auth import (
    AUTH_SESSION_TOKEN_BYTES,
    ApplicationAuthError,
    MarketplaceApplicationAuthService,
)
from .auth_enrollment_authority import (
    AuthenticationEnrollmentAuthorityAttestor,
    MarketplaceAuthenticationEnrollmentProposal,
)
from .auth_enrollment_policy import (
    AuthenticationEnrollmentApprovalPolicy,
    AuthenticationEnrollmentPolicyError,
    issue_marketplace_authentication_enrollment_evidence_after_policy,
)
from .auth_verification_method_evidence import (
    AUTH_EVIDENCE_MAX_LEASE_SECONDS,
    AuthenticationVerificationMethodEvidenceClaim,
    AuthenticationVerificationMethodEvidenceError,
    MarketplaceAuthenticationVerificationMethodEvidenceClaims,
    MarketplaceAuthenticationVerificationMethodEvidenceEnvelope,
    parse_marketplace_auth_verification_public_key,
)


PROFILE_NAME: Final = "MARKETPLACE_APPLICATION_AUTH_ENROLLMENT_COORDINATION_V1"
AUTH_ENROLLMENT_NONCE_BYTES: Final = 32


class AuthenticationEnrollmentCoordinationError(ValueError):
    """Stable fail-closed coordination error without sensitive reflection."""

    def __init__(self) -> None:
        super().__init__("authentication enrollment coordination failed")


def _fail() -> None:
    raise AuthenticationEnrollmentCoordinationError() from None


class AuthenticationEnrollmentReplayGuard(Protocol):
    """Purpose-specific atomic one-time enrollment replay-consumption seam."""

    def consume_authentication_enrollment_nonce(
        self,
        *,
        nonce: bytes,
        principal: str,
        verification_method: str,
        public_key: str,
        authority: str,
        issued_at: int,
        expires_at: int,
    ) -> bool: ...


def _validate_static(
    *,
    auth: MarketplaceApplicationAuthService,
    session_token: bytes,
    proposal: MarketplaceAuthenticationEnrollmentProposal,
    nonce: bytes,
    now: int,
    authority: str,
    lease_seconds: int,
) -> int:
    if type(auth) is not MarketplaceApplicationAuthService:
        _fail()
    if type(session_token) is not bytes or len(session_token) != AUTH_SESSION_TOKEN_BYTES:
        _fail()
    if type(proposal) is not MarketplaceAuthenticationEnrollmentProposal:
        _fail()
    if type(nonce) is not bytes or len(nonce) != AUTH_ENROLLMENT_NONCE_BYTES:
        _fail()
    if type(now) is not int or now < 0:
        _fail()
    if (
        type(lease_seconds) is not int
        or lease_seconds <= 0
        or lease_seconds > AUTH_EVIDENCE_MAX_LEASE_SECONDS
    ):
        _fail()

    expires_at = now + lease_seconds
    try:
        public_key = parse_marketplace_auth_verification_public_key(proposal.public_key)
        claim = AuthenticationVerificationMethodEvidenceClaim(
            verification_method=proposal.verification_method,
            controller_principal=proposal.principal,
            public_key=public_key,
        )
        MarketplaceAuthenticationVerificationMethodEvidenceClaims(
            authority=authority,
            issued_at=now,
            expires_at=expires_at,
            entries=(claim,),
        )
    except AuthenticationVerificationMethodEvidenceError:
        _fail()
    return expires_at


def coordinate_marketplace_authentication_enrollment(
    *,
    auth: MarketplaceApplicationAuthService,
    session_token: bytes,
    proposal: MarketplaceAuthenticationEnrollmentProposal,
    nonce: bytes,
    now: int,
    authority: str,
    lease_seconds: int,
    replay_guard: AuthenticationEnrollmentReplayGuard,
    policy: AuthenticationEnrollmentApprovalPolicy,
    attestor: AuthenticationEnrollmentAuthorityAttestor,
) -> MarketplaceAuthenticationVerificationMethodEvidenceEnvelope:
    """Coordinate one authenticated, one-time enrollment attempt."""

    expires_at = _validate_static(
        auth=auth,
        session_token=session_token,
        proposal=proposal,
        nonce=nonce,
        now=now,
        authority=authority,
        lease_seconds=lease_seconds,
    )

    try:
        auth.authorize_principal(
            session_token=session_token,
            claimed_principal=proposal.principal,
            now=now,
        )
    except (ApplicationAuthError, Exception):
        _fail()

    try:
        consume = getattr(
            replay_guard,
            "consume_authentication_enrollment_nonce",
            None,
        )
    except Exception:
        _fail()
    if not callable(consume):
        _fail()

    try:
        consumed = consume(
            nonce=nonce,
            principal=proposal.principal,
            verification_method=proposal.verification_method,
            public_key=proposal.public_key,
            authority=authority,
            issued_at=now,
            expires_at=expires_at,
        )
    except Exception:
        _fail()
    if type(consumed) is not bool or consumed is not True:
        _fail()

    try:
        result = issue_marketplace_authentication_enrollment_evidence_after_policy(
            proposal=proposal,
            authority=authority,
            issued_at=now,
            expires_at=expires_at,
            policy=policy,
            attestor=attestor,
        )
    except AuthenticationEnrollmentPolicyError:
        _fail()

    if type(result) is not MarketplaceAuthenticationVerificationMethodEvidenceEnvelope:
        _fail()
    return result


__all__ = [
    "AUTH_ENROLLMENT_NONCE_BYTES",
    "AuthenticationEnrollmentCoordinationError",
    "AuthenticationEnrollmentReplayGuard",
    "PROFILE_NAME",
    "coordinate_marketplace_authentication_enrollment",
]
