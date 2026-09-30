"""M17.6U unselected reference enrollment launch with exact Ed25519 attestor."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from ..application.auth_launch import MarketplaceAuthenticatedLoopbackLaunchPlan
from .auth_enrollment_approval_policy_v1 import (
    MarketplaceReferenceAuthenticationEnrollmentApprovalBinding,
)
from .auth_enrollment_attestor_ed25519_v1 import (
    MarketplaceReferenceAuthenticationEnrollmentEd25519Attestor,
)
from .auth_enrollment_launch_policy_nonce_v1 import (
    MarketplaceReferenceAuthenticationEnrollmentLaunchPolicyNonce,
    build_reference_authentication_enrollment_launch_policy_nonce,
)


PROFILE_NAME: Final = (
    "MARKETPLACE_REFERENCE_AUTHENTICATION_ENROLLMENT_LAUNCH_POLICY_NONCE_ED25519_V1"
)
_ERROR_MESSAGE: Final = (
    "reference authentication enrollment launch policy nonce Ed25519 composition failed"
)


class MarketplaceReferenceAuthenticationEnrollmentLaunchPolicyNonceEd25519Error(
    RuntimeError
):
    """Stable fail-closed M17.6U composition error."""

    def __init__(self) -> None:
        super().__init__(_ERROR_MESSAGE)


def _fail() -> None:
    raise MarketplaceReferenceAuthenticationEnrollmentLaunchPolicyNonceEd25519Error(
    ) from None


@dataclass(frozen=True, slots=True)
class MarketplaceReferenceAuthenticationEnrollmentLaunchPolicyNonceEd25519:
    """Exact inert T -> S reference enrollment graph."""

    authenticated_plan: MarketplaceAuthenticatedLoopbackLaunchPlan
    bindings: tuple[
        MarketplaceReferenceAuthenticationEnrollmentApprovalBinding,
        ...,
    ]
    attestor: MarketplaceReferenceAuthenticationEnrollmentEd25519Attestor
    authority: str
    evidence_lease_seconds: int
    launch: MarketplaceReferenceAuthenticationEnrollmentLaunchPolicyNonce

    def __post_init__(self) -> None:
        if type(self.authenticated_plan) is not MarketplaceAuthenticatedLoopbackLaunchPlan:
            _fail()
        if type(self.bindings) is not tuple:
            _fail()
        if (
            type(self.attestor)
            is not MarketplaceReferenceAuthenticationEnrollmentEd25519Attestor
        ):
            _fail()
        if (
            type(self.launch)
            is not MarketplaceReferenceAuthenticationEnrollmentLaunchPolicyNonce
        ):
            _fail()

        try:
            if self.launch.authenticated_plan is not self.authenticated_plan:
                _fail()
            if self.launch.bindings is not self.bindings:
                _fail()
            if self.launch.policy.bindings is not self.bindings:
                _fail()
            if self.launch.attestor is not self.attestor:
                _fail()
            if self.launch.launch.attestor is not self.attestor:
                _fail()
            if self.launch.authority != self.authority:
                _fail()
            if self.launch.launch.authority != self.authority:
                _fail()
            if self.launch.evidence_lease_seconds != self.evidence_lease_seconds:
                _fail()
            if (
                self.launch.launch.evidence_lease_seconds
                != self.evidence_lease_seconds
            ):
                _fail()
            if self.launch.nonce.nonce_authority._outstanding != {}:
                _fail()
            if self.launch.nonce.nonce_authority._spent != {}:
                _fail()
        except MarketplaceReferenceAuthenticationEnrollmentLaunchPolicyNonceEd25519Error:
            raise
        except Exception:
            _fail()


def build_reference_authentication_enrollment_launch_policy_nonce_ed25519(
    *,
    authenticated_plan: MarketplaceAuthenticatedLoopbackLaunchPlan,
    bindings: tuple[
        MarketplaceReferenceAuthenticationEnrollmentApprovalBinding,
        ...,
    ],
    private_key_bytes: bytes,
    authority: str,
    evidence_lease_seconds: int,
) -> MarketplaceReferenceAuthenticationEnrollmentLaunchPolicyNonceEd25519:
    """Construct one exact T attestor and supply it to one exact inert S graph."""

    try:
        attestor = MarketplaceReferenceAuthenticationEnrollmentEd25519Attestor(
            private_key_bytes=private_key_bytes,
        )
        launch = build_reference_authentication_enrollment_launch_policy_nonce(
            authenticated_plan=authenticated_plan,
            bindings=bindings,
            attestor=attestor,
            authority=authority,
            evidence_lease_seconds=evidence_lease_seconds,
        )
        return MarketplaceReferenceAuthenticationEnrollmentLaunchPolicyNonceEd25519(
            authenticated_plan=authenticated_plan,
            bindings=bindings,
            attestor=attestor,
            authority=authority,
            evidence_lease_seconds=evidence_lease_seconds,
            launch=launch,
        )
    except MarketplaceReferenceAuthenticationEnrollmentLaunchPolicyNonceEd25519Error:
        raise
    except Exception:
        _fail()


__all__ = [
    "MarketplaceReferenceAuthenticationEnrollmentLaunchPolicyNonceEd25519",
    "MarketplaceReferenceAuthenticationEnrollmentLaunchPolicyNonceEd25519Error",
    "PROFILE_NAME",
    "build_reference_authentication_enrollment_launch_policy_nonce_ed25519",
]
