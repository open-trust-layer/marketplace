"""M17.6S unselected reference enrollment launch with nonce authority and policy.

This module composes the reviewed M17.6Q process-local nonce authority and the
reviewed M17.6R exact-binding approval policy into the existing inert M17.6O
reference enrollment launch. Attestation remains caller-supplied and no runtime
is selected or executed.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from ..application.auth_enrollment_authority import (
    AuthenticationEnrollmentAuthorityAttestor,
)
from ..application.auth_launch import MarketplaceAuthenticatedLoopbackLaunchPlan
from .auth_enrollment_approval_policy_v1 import (
    MarketplaceReferenceAuthenticationEnrollmentApprovalBinding,
    MarketplaceReferenceAuthenticationEnrollmentApprovalPolicy,
)
from .auth_enrollment_launch_v1 import (
    MarketplaceReferenceAuthenticationEnrollmentLaunch,
    build_reference_authentication_enrollment_launch,
)
from .auth_enrollment_nonce_authority_v1 import (
    MarketplaceReferenceAuthenticationEnrollmentNonceAuthority,
    build_reference_authentication_enrollment_nonce_authority,
)


PROFILE_NAME: Final = (
    "MARKETPLACE_REFERENCE_AUTHENTICATION_ENROLLMENT_LAUNCH_POLICY_NONCE_V1"
)
_ERROR_MESSAGE: Final = (
    "reference authentication enrollment launch policy nonce composition failed"
)


class MarketplaceReferenceAuthenticationEnrollmentLaunchPolicyNonceError(
    RuntimeError
):
    """Stable fail-closed M17.6S composition error."""

    def __init__(self) -> None:
        super().__init__(_ERROR_MESSAGE)


def _fail() -> None:
    raise MarketplaceReferenceAuthenticationEnrollmentLaunchPolicyNonceError() from None


@dataclass(frozen=True, slots=True)
class MarketplaceReferenceAuthenticationEnrollmentLaunchPolicyNonce:
    """Exact inert Q + R -> O reference graph."""

    authenticated_plan: MarketplaceAuthenticatedLoopbackLaunchPlan
    bindings: tuple[
        MarketplaceReferenceAuthenticationEnrollmentApprovalBinding,
        ...,
    ]
    attestor: AuthenticationEnrollmentAuthorityAttestor
    authority: str
    evidence_lease_seconds: int
    nonce: MarketplaceReferenceAuthenticationEnrollmentNonceAuthority
    policy: MarketplaceReferenceAuthenticationEnrollmentApprovalPolicy
    launch: MarketplaceReferenceAuthenticationEnrollmentLaunch

    def __post_init__(self) -> None:
        if type(self.authenticated_plan) is not MarketplaceAuthenticatedLoopbackLaunchPlan:
            _fail()
        if type(self.bindings) is not tuple:
            _fail()
        if (
            type(self.nonce)
            is not MarketplaceReferenceAuthenticationEnrollmentNonceAuthority
        ):
            _fail()
        if (
            type(self.policy)
            is not MarketplaceReferenceAuthenticationEnrollmentApprovalPolicy
        ):
            _fail()
        if type(self.launch) is not MarketplaceReferenceAuthenticationEnrollmentLaunch:
            _fail()

        try:
            if self.policy.bindings is not self.bindings:
                _fail()
            if self.launch.authenticated_plan is not self.authenticated_plan:
                _fail()
            if self.launch.nonce_authority is not self.nonce.nonce_authority:
                _fail()
            if self.launch.policy is not self.policy:
                _fail()
            if self.launch.attestor is not self.attestor:
                _fail()
            if self.launch.authority != self.authority:
                _fail()
            if self.launch.evidence_lease_seconds != self.evidence_lease_seconds:
                _fail()
            if (
                getattr(self.nonce.nonce_authority._nonce_bytes, "__self__", None)
                is not self.nonce.material_source
            ):
                _fail()
            if self.nonce.nonce_authority._outstanding != {}:
                _fail()
            if self.nonce.nonce_authority._spent != {}:
                _fail()
        except MarketplaceReferenceAuthenticationEnrollmentLaunchPolicyNonceError:
            raise
        except Exception:
            _fail()


def build_reference_authentication_enrollment_launch_policy_nonce(
    *,
    authenticated_plan: MarketplaceAuthenticatedLoopbackLaunchPlan,
    bindings: tuple[
        MarketplaceReferenceAuthenticationEnrollmentApprovalBinding,
        ...,
    ],
    attestor: AuthenticationEnrollmentAuthorityAttestor,
    authority: str,
    evidence_lease_seconds: int,
) -> MarketplaceReferenceAuthenticationEnrollmentLaunchPolicyNonce:
    """Compose one exact Q authority and one exact R policy into one inert O launch."""

    try:
        nonce = build_reference_authentication_enrollment_nonce_authority()
        policy = MarketplaceReferenceAuthenticationEnrollmentApprovalPolicy(
            bindings=bindings,
        )
        launch = build_reference_authentication_enrollment_launch(
            authenticated_plan=authenticated_plan,
            nonce_authority=nonce.nonce_authority,
            policy=policy,
            attestor=attestor,
            authority=authority,
            evidence_lease_seconds=evidence_lease_seconds,
        )
        return MarketplaceReferenceAuthenticationEnrollmentLaunchPolicyNonce(
            authenticated_plan=authenticated_plan,
            bindings=bindings,
            attestor=attestor,
            authority=authority,
            evidence_lease_seconds=evidence_lease_seconds,
            nonce=nonce,
            policy=policy,
            launch=launch,
        )
    except MarketplaceReferenceAuthenticationEnrollmentLaunchPolicyNonceError:
        raise
    except Exception:
        _fail()


__all__ = [
    "MarketplaceReferenceAuthenticationEnrollmentLaunchPolicyNonce",
    "MarketplaceReferenceAuthenticationEnrollmentLaunchPolicyNonceError",
    "PROFILE_NAME",
    "build_reference_authentication_enrollment_launch_policy_nonce",
]
