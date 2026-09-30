"""M17.6R unselected reference enrollment launch with reference nonce authority."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from ..application.auth_enrollment_authority import (
    AuthenticationEnrollmentAuthorityAttestor,
)
from ..application.auth_enrollment_policy import (
    AuthenticationEnrollmentApprovalPolicy,
)
from ..application.auth_launch import MarketplaceAuthenticatedLoopbackLaunchPlan
from .auth_enrollment_launch_v1 import (
    MarketplaceReferenceAuthenticationEnrollmentLaunch,
    build_reference_authentication_enrollment_launch,
)
from .auth_enrollment_nonce_authority_v1 import (
    MarketplaceReferenceAuthenticationEnrollmentNonceAuthority,
    build_reference_authentication_enrollment_nonce_authority,
)


PROFILE_NAME: Final = (
    "MARKETPLACE_REFERENCE_AUTHENTICATION_ENROLLMENT_LAUNCH_NONCE_V1"
)
_ERROR_MESSAGE: Final = (
    "reference authentication enrollment launch nonce composition failed"
)


class MarketplaceReferenceAuthenticationEnrollmentLaunchNonceError(RuntimeError):
    """Stable fail-closed reference launch/nonce composition error."""

    def __init__(self) -> None:
        super().__init__(_ERROR_MESSAGE)


def _fail() -> None:
    raise MarketplaceReferenceAuthenticationEnrollmentLaunchNonceError() from None


@dataclass(frozen=True, slots=True)
class MarketplaceReferenceAuthenticationEnrollmentLaunchNonce:
    """Exact inert Q-to-O graph with caller-supplied policy and attestor."""

    authenticated_plan: MarketplaceAuthenticatedLoopbackLaunchPlan
    policy: AuthenticationEnrollmentApprovalPolicy
    attestor: AuthenticationEnrollmentAuthorityAttestor
    authority: str
    evidence_lease_seconds: int
    nonce: MarketplaceReferenceAuthenticationEnrollmentNonceAuthority
    launch: MarketplaceReferenceAuthenticationEnrollmentLaunch

    def __post_init__(self) -> None:
        if type(self.authenticated_plan) is not MarketplaceAuthenticatedLoopbackLaunchPlan:
            _fail()
        if (
            type(self.nonce)
            is not MarketplaceReferenceAuthenticationEnrollmentNonceAuthority
        ):
            _fail()
        if (
            type(self.launch)
            is not MarketplaceReferenceAuthenticationEnrollmentLaunch
        ):
            _fail()

        try:
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
            if self.nonce.nonce_authority._nonce_bytes.__self__ is not self.nonce.material_source:
                _fail()
            if self.nonce.nonce_authority._outstanding != {}:
                _fail()
            if self.nonce.nonce_authority._spent != {}:
                _fail()
        except MarketplaceReferenceAuthenticationEnrollmentLaunchNonceError:
            raise
        except Exception:
            _fail()


def build_reference_authentication_enrollment_launch_nonce(
    *,
    authenticated_plan: MarketplaceAuthenticatedLoopbackLaunchPlan,
    policy: AuthenticationEnrollmentApprovalPolicy,
    attestor: AuthenticationEnrollmentAuthorityAttestor,
    authority: str,
    evidence_lease_seconds: int,
) -> MarketplaceReferenceAuthenticationEnrollmentLaunchNonce:
    """Compose exactly one Q graph into exactly one inert O launch graph."""

    if type(authenticated_plan) is not MarketplaceAuthenticatedLoopbackLaunchPlan:
        _fail()

    try:
        nonce = build_reference_authentication_enrollment_nonce_authority()
        launch = build_reference_authentication_enrollment_launch(
            authenticated_plan=authenticated_plan,
            nonce_authority=nonce.nonce_authority,
            policy=policy,
            attestor=attestor,
            authority=authority,
            evidence_lease_seconds=evidence_lease_seconds,
        )
        return MarketplaceReferenceAuthenticationEnrollmentLaunchNonce(
            authenticated_plan=authenticated_plan,
            policy=policy,
            attestor=attestor,
            authority=authority,
            evidence_lease_seconds=evidence_lease_seconds,
            nonce=nonce,
            launch=launch,
        )
    except MarketplaceReferenceAuthenticationEnrollmentLaunchNonceError:
        raise
    except Exception:
        _fail()


__all__ = [
    "MarketplaceReferenceAuthenticationEnrollmentLaunchNonce",
    "MarketplaceReferenceAuthenticationEnrollmentLaunchNonceError",
    "PROFILE_NAME",
    "build_reference_authentication_enrollment_launch_nonce",
]
