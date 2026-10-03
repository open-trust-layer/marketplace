"""M17.6Z compose reviewed keyfile intake X through Y into existing U."""
from __future__ import annotations

from typing import Final

from ..application.auth_launch import MarketplaceAuthenticatedLoopbackLaunchPlan
from .auth_enrollment_approval_policy_v1 import (
    MarketplaceReferenceAuthenticationEnrollmentApprovalBinding,
)
from .auth_enrollment_attestor_keyfile_v1 import (
    load_reference_authentication_enrollment_ed25519_attestor,
)
from .auth_enrollment_launch_policy_nonce_ed25519_attestor_v1 import (
    build_reference_authentication_enrollment_launch_policy_nonce_ed25519_attestor,
)
from .auth_enrollment_launch_policy_nonce_ed25519_v1 import (
    MarketplaceReferenceAuthenticationEnrollmentLaunchPolicyNonceEd25519,
)


PROFILE_NAME: Final = (
    "MARKETPLACE_REFERENCE_AUTHENTICATION_ENROLLMENT_"
    "LAUNCH_POLICY_NONCE_ED25519_KEYFILE_V1"
)
_ERROR_MESSAGE: Final = (
    "reference authentication enrollment Ed25519 keyfile composition failed"
)


class MarketplaceReferenceAuthenticationEnrollmentEd25519KeyfileCompositionError(
    RuntimeError
):
    """Stable fail-closed M17.6Z keyfile-to-U composition error."""

    def __init__(self) -> None:
        super().__init__(_ERROR_MESSAGE)


def _fail() -> None:
    raise MarketplaceReferenceAuthenticationEnrollmentEd25519KeyfileCompositionError(
    ) from None


def build_reference_authentication_enrollment_launch_policy_nonce_ed25519_keyfile(
    *,
    authenticated_plan: MarketplaceAuthenticatedLoopbackLaunchPlan,
    bindings: tuple[
        MarketplaceReferenceAuthenticationEnrollmentApprovalBinding,
        ...,
    ],
    directory: str,
    authority: str,
    evidence_lease_seconds: int,
) -> MarketplaceReferenceAuthenticationEnrollmentLaunchPolicyNonceEd25519:
    """Load one reviewed X attestor, delegate once to Y, and return exact U."""

    try:
        attestor = load_reference_authentication_enrollment_ed25519_attestor(
            directory=directory,
        )
        result = (
            build_reference_authentication_enrollment_launch_policy_nonce_ed25519_attestor(
                authenticated_plan=authenticated_plan,
                bindings=bindings,
                attestor=attestor,
                authority=authority,
                evidence_lease_seconds=evidence_lease_seconds,
            )
        )
        if (
            type(result)
            is not MarketplaceReferenceAuthenticationEnrollmentLaunchPolicyNonceEd25519
        ):
            _fail()
        return result
    except MarketplaceReferenceAuthenticationEnrollmentEd25519KeyfileCompositionError:
        raise
    except Exception:
        _fail()


__all__ = [
    "MarketplaceReferenceAuthenticationEnrollmentEd25519KeyfileCompositionError",
    "PROFILE_NAME",
    "build_reference_authentication_enrollment_launch_policy_nonce_ed25519_keyfile",
]
