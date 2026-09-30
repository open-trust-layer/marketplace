"""M17.6R unselected exact-binding authentication-enrollment approval policy."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from ..application.auth_enrollment_authority import (
    AuthenticationEnrollmentAuthorityError,
    MarketplaceAuthenticationEnrollmentProposal,
)
from ..application.auth_verification_method_evidence import (
    AUTH_EVIDENCE_MAX_ENTRIES,
    AuthenticationVerificationMethodEvidenceClaim,
    AuthenticationVerificationMethodEvidenceError,
    MarketplaceAuthenticationVerificationMethodEvidenceClaims,
    parse_marketplace_auth_verification_public_key,
)


PROFILE_NAME: Final = (
    "MARKETPLACE_REFERENCE_AUTHENTICATION_ENROLLMENT_APPROVAL_POLICY_V1"
)
REFERENCE_AUTH_ENROLLMENT_APPROVAL_MAX_BINDINGS: Final = AUTH_EVIDENCE_MAX_ENTRIES
_ERROR_MESSAGE: Final = "reference authentication enrollment approval policy failed"


class MarketplaceReferenceAuthenticationEnrollmentApprovalPolicyError(ValueError):
    """Stable fail-closed reference enrollment-policy error."""

    def __init__(self) -> None:
        super().__init__(_ERROR_MESSAGE)


def _fail() -> None:
    raise MarketplaceReferenceAuthenticationEnrollmentApprovalPolicyError() from None


def _validate_exact_binding(
    *,
    principal: object,
    verification_method: object,
    public_key: object,
    authority: object,
    issued_at: object,
    expires_at: object,
) -> None:
    try:
        proposal = MarketplaceAuthenticationEnrollmentProposal(
            principal=principal,  # type: ignore[arg-type]
            verification_method=verification_method,  # type: ignore[arg-type]
            public_key=public_key,  # type: ignore[arg-type]
        )
        key_bytes = parse_marketplace_auth_verification_public_key(
            proposal.public_key
        )
        claim = AuthenticationVerificationMethodEvidenceClaim(
            verification_method=proposal.verification_method,
            controller_principal=proposal.principal,
            public_key=key_bytes,
        )
        MarketplaceAuthenticationVerificationMethodEvidenceClaims(
            authority=authority,  # type: ignore[arg-type]
            issued_at=issued_at,  # type: ignore[arg-type]
            expires_at=expires_at,  # type: ignore[arg-type]
            entries=(claim,),
        )
    except (
        AuthenticationEnrollmentAuthorityError,
        AuthenticationVerificationMethodEvidenceError,
    ):
        _fail()
    except Exception:
        _fail()


@dataclass(frozen=True, slots=True)
class MarketplaceReferenceAuthenticationEnrollmentApprovalBinding:
    """One exact pre-approved enrollment identity binding."""

    principal: str
    verification_method: str
    public_key: str
    authority: str

    def __post_init__(self) -> None:
        _validate_exact_binding(
            principal=self.principal,
            verification_method=self.verification_method,
            public_key=self.public_key,
            authority=self.authority,
            issued_at=0,
            expires_at=1,
        )


@dataclass(frozen=True, slots=True)
class MarketplaceReferenceAuthenticationEnrollmentApprovalPolicy:
    """Immutable bounded exact-match enrollment approval policy."""

    bindings: tuple[MarketplaceReferenceAuthenticationEnrollmentApprovalBinding, ...]

    def __post_init__(self) -> None:
        if type(self.bindings) is not tuple:
            _fail()
        if not (
            1
            <= len(self.bindings)
            <= REFERENCE_AUTH_ENROLLMENT_APPROVAL_MAX_BINDINGS
        ):
            _fail()

        seen: set[MarketplaceReferenceAuthenticationEnrollmentApprovalBinding] = set()
        for binding in self.bindings:
            if (
                type(binding)
                is not MarketplaceReferenceAuthenticationEnrollmentApprovalBinding
            ):
                _fail()
            if binding in seen:
                _fail()
            seen.add(binding)

    def approve_authentication_enrollment(
        self,
        *,
        principal: str,
        verification_method: str,
        public_key: str,
        authority: str,
        issued_at: int,
        expires_at: int,
    ) -> bool:
        """Approve iff one retained binding exactly equals the well-formed request."""

        _validate_exact_binding(
            principal=principal,
            verification_method=verification_method,
            public_key=public_key,
            authority=authority,
            issued_at=issued_at,
            expires_at=expires_at,
        )

        for binding in self.bindings:
            if (
                binding.principal == principal
                and binding.verification_method == verification_method
                and binding.public_key == public_key
                and binding.authority == authority
            ):
                return True
        return False


__all__ = [
    "MarketplaceReferenceAuthenticationEnrollmentApprovalBinding",
    "MarketplaceReferenceAuthenticationEnrollmentApprovalPolicy",
    "MarketplaceReferenceAuthenticationEnrollmentApprovalPolicyError",
    "PROFILE_NAME",
    "REFERENCE_AUTH_ENROLLMENT_APPROVAL_MAX_BINDINGS",
]
