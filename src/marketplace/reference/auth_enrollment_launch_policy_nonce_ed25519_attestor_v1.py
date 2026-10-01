"""M17.6Y compose an existing exact Ed25519 enrollment attestor into U."""
from __future__ import annotations

from typing import Final

from ..application.auth_launch import MarketplaceAuthenticatedLoopbackLaunchPlan
from .auth_enrollment_approval_policy_v1 import (
    MarketplaceReferenceAuthenticationEnrollmentApprovalBinding,
)
from .auth_enrollment_attestor_ed25519_v1 import (
    MarketplaceReferenceAuthenticationEnrollmentEd25519Attestor,
)
from .auth_enrollment_launch_policy_nonce_ed25519_v1 import (
    MarketplaceReferenceAuthenticationEnrollmentLaunchPolicyNonceEd25519,
)
from .auth_enrollment_launch_policy_nonce_v1 import (
    build_reference_authentication_enrollment_launch_policy_nonce,
)


PROFILE_NAME: Final = (
    "MARKETPLACE_REFERENCE_AUTHENTICATION_ENROLLMENT_"
    "LAUNCH_POLICY_NONCE_ED25519_ATTESTOR_V1"
)
_ERROR_MESSAGE: Final = (
    "reference authentication enrollment existing Ed25519 attestor composition failed"
)


class MarketplaceReferenceAuthenticationEnrollmentExistingEd25519AttestorError(
    RuntimeError
):
    """Stable fail-closed M17.6Y existing-attestor composition error."""

    def __init__(self) -> None:
        super().__init__(_ERROR_MESSAGE)


def _fail() -> None:
    raise MarketplaceReferenceAuthenticationEnrollmentExistingEd25519AttestorError(
    ) from None


def build_reference_authentication_enrollment_launch_policy_nonce_ed25519_attestor(
    *,
    authenticated_plan: MarketplaceAuthenticatedLoopbackLaunchPlan,
    bindings: tuple[
        MarketplaceReferenceAuthenticationEnrollmentApprovalBinding,
        ...,
    ],
    attestor: MarketplaceReferenceAuthenticationEnrollmentEd25519Attestor,
    authority: str,
    evidence_lease_seconds: int,
) -> MarketplaceReferenceAuthenticationEnrollmentLaunchPolicyNonceEd25519:
    """Supply one exact existing T attestor to S and return one exact U graph."""

    if type(attestor) is not MarketplaceReferenceAuthenticationEnrollmentEd25519Attestor:
        _fail()

    try:
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
    except MarketplaceReferenceAuthenticationEnrollmentExistingEd25519AttestorError:
        raise
    except Exception:
        _fail()


__all__ = [
    "MarketplaceReferenceAuthenticationEnrollmentExistingEd25519AttestorError",
    "PROFILE_NAME",
    "build_reference_authentication_enrollment_launch_policy_nonce_ed25519_attestor",
]
