"""M17.6R unselected reference enrollment launch with reference nonce authority.

This module composes the reviewed M17.6Q process-local nonce authority into the
existing inert M17.6O enrollment launch. Policy and attestor remain
caller-supplied. Construction consumes no nonce material and selects no runtime.
"""
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
    "MARKETPLACE_REFERENCE_AUTHENTICATION_ENROLLMENT_LAUNCH_NONCE_AUTHORITY_V1"
)
_ERROR_MESSAGE: Final = (
    "reference authentication enrollment launch nonce authority composition failed"
)


class MarketplaceReferenceAuthenticationEnrollmentLaunchNonceAuthorityError(
    RuntimeError
):
    """Stable fail-closed M17.6R composition error."""

    def __init__(self) -> None:
        super().__init__(_ERROR_MESSAGE)


def _fail() -> None:
    raise MarketplaceReferenceAuthenticationEnrollmentLaunchNonceAuthorityError() from None


@dataclass(frozen=True, slots=True)
class MarketplaceReferenceAuthenticationEnrollmentLaunchNonceAuthority:
    """Exact inert Q-to-O reference graph."""

    nonce: MarketplaceReferenceAuthenticationEnrollmentNonceAuthority
    launch: MarketplaceReferenceAuthenticationEnrollmentLaunch

    def __post_init__(self) -> None:
        if type(self.nonce) is not MarketplaceReferenceAuthenticationEnrollmentNonceAuthority:
            _fail()
        if type(self.launch) is not MarketplaceReferenceAuthenticationEnrollmentLaunch:
            _fail()
        try:
            if self.launch.nonce_authority is not self.nonce.nonce_authority:
                _fail()
            if (
                getattr(self.nonce.nonce_authority._nonce_bytes, "__self__", None)
                is not self.nonce.material_source
            ):
                _fail()
        except MarketplaceReferenceAuthenticationEnrollmentLaunchNonceAuthorityError:
            raise
        except Exception:
            _fail()


def build_reference_authentication_enrollment_launch_nonce_authority(
    *,
    authenticated_plan: MarketplaceAuthenticatedLoopbackLaunchPlan,
    policy: AuthenticationEnrollmentApprovalPolicy,
    attestor: AuthenticationEnrollmentAuthorityAttestor,
    authority: str,
    evidence_lease_seconds: int,
) -> MarketplaceReferenceAuthenticationEnrollmentLaunchNonceAuthority:
    """Compose exactly one Q nonce authority into exactly one inert O launch."""

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
        return MarketplaceReferenceAuthenticationEnrollmentLaunchNonceAuthority(
            nonce=nonce,
            launch=launch,
        )
    except MarketplaceReferenceAuthenticationEnrollmentLaunchNonceAuthorityError:
        raise
    except Exception:
        _fail()


__all__ = [
    "MarketplaceReferenceAuthenticationEnrollmentLaunchNonceAuthority",
    "MarketplaceReferenceAuthenticationEnrollmentLaunchNonceAuthorityError",
    "PROFILE_NAME",
    "build_reference_authentication_enrollment_launch_nonce_authority",
]
