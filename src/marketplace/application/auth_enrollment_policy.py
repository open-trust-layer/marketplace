"""M17.6F unselected authentication enrollment approval-policy gate.

This module validates one exact M17.6E enrollment request, obtains one explicit
purpose-specific policy decision, and only then delegates to the existing
M17.6E authority issuance boundary. It selects no concrete policy or attestor.
"""
from __future__ import annotations

from typing import Final, Protocol

from .auth_enrollment_authority import (
    AuthenticationEnrollmentAuthorityAttestor,
    AuthenticationEnrollmentAuthorityError,
    MarketplaceAuthenticationEnrollmentProposal,
    issue_marketplace_authentication_enrollment_evidence,
)
from .auth_verification_method_evidence import (
    AuthenticationVerificationMethodEvidenceClaim,
    AuthenticationVerificationMethodEvidenceError,
    MarketplaceAuthenticationVerificationMethodEvidenceClaims,
    MarketplaceAuthenticationVerificationMethodEvidenceEnvelope,
    parse_marketplace_auth_verification_public_key,
)


PROFILE_NAME: Final = "MARKETPLACE_APPLICATION_AUTH_ENROLLMENT_POLICY_V1"


class AuthenticationEnrollmentPolicyError(ValueError):
    """Stable fail-closed enrollment-policy error without input reflection."""

    def __init__(self) -> None:
        super().__init__("authentication enrollment policy operation failed")


def _fail() -> None:
    raise AuthenticationEnrollmentPolicyError() from None


class AuthenticationEnrollmentApprovalPolicy(Protocol):
    """Purpose-specific approval policy for one exact enrollment request."""

    def approve_authentication_enrollment(
        self,
        *,
        principal: str,
        verification_method: str,
        public_key: str,
        authority: str,
        issued_at: int,
        expires_at: int,
    ) -> bool: ...


def _validate_request(
    *,
    proposal: MarketplaceAuthenticationEnrollmentProposal,
    authority: str,
    issued_at: int,
    expires_at: int,
) -> None:
    if type(proposal) is not MarketplaceAuthenticationEnrollmentProposal:
        _fail()

    try:
        public_key = parse_marketplace_auth_verification_public_key(proposal.public_key)
        claim = AuthenticationVerificationMethodEvidenceClaim(
            verification_method=proposal.verification_method,
            controller_principal=proposal.principal,
            public_key=public_key,
        )
        MarketplaceAuthenticationVerificationMethodEvidenceClaims(
            authority=authority,
            issued_at=issued_at,
            expires_at=expires_at,
            entries=(claim,),
        )
    except AuthenticationVerificationMethodEvidenceError:
        _fail()


def issue_marketplace_authentication_enrollment_evidence_after_policy(
    *,
    proposal: MarketplaceAuthenticationEnrollmentProposal,
    authority: str,
    issued_at: int,
    expires_at: int,
    policy: AuthenticationEnrollmentApprovalPolicy,
    attestor: AuthenticationEnrollmentAuthorityAttestor,
) -> MarketplaceAuthenticationVerificationMethodEvidenceEnvelope:
    """Issue M17.6E evidence only after one exact explicit approval decision."""

    _validate_request(
        proposal=proposal,
        authority=authority,
        issued_at=issued_at,
        expires_at=expires_at,
    )

    try:
        operation = getattr(policy, "approve_authentication_enrollment", None)
    except Exception:
        _fail()
    if not callable(operation):
        _fail()

    try:
        approved = operation(
            principal=proposal.principal,
            verification_method=proposal.verification_method,
            public_key=proposal.public_key,
            authority=authority,
            issued_at=issued_at,
            expires_at=expires_at,
        )
    except Exception:
        _fail()

    if type(approved) is not bool or approved is not True:
        _fail()

    try:
        return issue_marketplace_authentication_enrollment_evidence(
            proposal=proposal,
            authority=authority,
            issued_at=issued_at,
            expires_at=expires_at,
            attestor=attestor,
        )
    except AuthenticationEnrollmentAuthorityError:
        _fail()


__all__ = [
    "AuthenticationEnrollmentApprovalPolicy",
    "AuthenticationEnrollmentPolicyError",
    "PROFILE_NAME",
    "issue_marketplace_authentication_enrollment_evidence_after_policy",
]
