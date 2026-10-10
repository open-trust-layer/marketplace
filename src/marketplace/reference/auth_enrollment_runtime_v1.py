"""M17.6V unselected reference enrollment foreground execution seam."""
from __future__ import annotations

from typing import Final

from ..application.auth_enrollment_launch import (
    MarketplaceAuthenticationEnrollmentLoopbackLaunchPlan,
)
from ..application.auth_enrollment_runtime_server import (
    EXECUTE_ONE_AUTHENTICATION_ENROLLMENT_MARKETPLACE_LOOPBACK_SERVER,
    run_marketplace_authentication_enrollment_foreground,
)
from ..application.runtime_server import MarketplaceAsgiServerProvider
from .auth_enrollment_attestor_ed25519_v1 import (
    MarketplaceReferenceAuthenticationEnrollmentEd25519Attestor,
)
from .auth_enrollment_launch_policy_nonce_ed25519_v1 import (
    MarketplaceReferenceAuthenticationEnrollmentLaunchPolicyNonceEd25519,
)
from .auth_enrollment_launch_policy_nonce_v1 import (
    MarketplaceReferenceAuthenticationEnrollmentLaunchPolicyNonce,
)
from .auth_enrollment_launch_v1 import (
    MarketplaceReferenceAuthenticationEnrollmentLaunch,
)


PROFILE_NAME: Final = (
    "MARKETPLACE_REFERENCE_AUTHENTICATION_ENROLLMENT_FOREGROUND_RUNTIME_V1"
)
_ERROR_MESSAGE: Final = "reference authentication enrollment foreground runtime failed"


class MarketplaceReferenceAuthenticationEnrollmentForegroundRuntimeError(
    RuntimeError
):
    """Stable fail-closed M17.6V reference runtime error."""

    def __init__(self) -> None:
        super().__init__(_ERROR_MESSAGE)


def _fail() -> None:
    raise MarketplaceReferenceAuthenticationEnrollmentForegroundRuntimeError() from None


def _validate_execute_token(execute_token: str) -> None:
    if (
        type(execute_token) is not str
        or execute_token
        != EXECUTE_ONE_AUTHENTICATION_ENROLLMENT_MARKETPLACE_LOOPBACK_SERVER
    ):
        _fail()


def _validate_reference(
    reference: MarketplaceReferenceAuthenticationEnrollmentLaunchPolicyNonceEd25519,
) -> MarketplaceAuthenticationEnrollmentLoopbackLaunchPlan:
    if (
        type(reference)
        is not MarketplaceReferenceAuthenticationEnrollmentLaunchPolicyNonceEd25519
    ):
        _fail()

    try:
        if (
            type(reference.attestor)
            is not MarketplaceReferenceAuthenticationEnrollmentEd25519Attestor
        ):
            _fail()
        if (
            type(reference.launch)
            is not MarketplaceReferenceAuthenticationEnrollmentLaunchPolicyNonce
        ):
            _fail()
        if reference.launch.authenticated_plan is not reference.authenticated_plan:
            _fail()
        if reference.launch.bindings is not reference.bindings:
            _fail()
        if reference.launch.policy.bindings is not reference.bindings:
            _fail()
        if reference.launch.attestor is not reference.attestor:
            _fail()
        if reference.launch.authority != reference.authority:
            _fail()
        if (
            reference.launch.evidence_lease_seconds
            != reference.evidence_lease_seconds
        ):
            _fail()

        selected = reference.launch.launch
        if type(selected) is not MarketplaceReferenceAuthenticationEnrollmentLaunch:
            _fail()
        if selected.authenticated_plan is not reference.authenticated_plan:
            _fail()
        if selected.policy is not reference.launch.policy:
            _fail()
        if selected.attestor is not reference.attestor:
            _fail()
        if selected.authority != reference.authority:
            _fail()
        if selected.evidence_lease_seconds != reference.evidence_lease_seconds:
            _fail()
        if selected.nonce_authority is not reference.launch.nonce.nonce_authority:
            _fail()

        if type(reference.launch.nonce.nonce_authority._outstanding) is not dict:
            _fail()
        if type(reference.launch.nonce.nonce_authority._spent) is not dict:
            _fail()

        plan = selected.plan
        if type(plan) is not MarketplaceAuthenticationEnrollmentLoopbackLaunchPlan:
            _fail()
        if plan.startup is not selected.startup:
            _fail()
        if plan.asgi is not selected.startup.enrollment_asgi.asgi:
            _fail()
        if plan.host != reference.authenticated_plan.host:
            _fail()
        if plan.port != reference.authenticated_plan.port:
            _fail()
        return plan
    except MarketplaceReferenceAuthenticationEnrollmentForegroundRuntimeError:
        raise
    except Exception:
        _fail()


def run_reference_authentication_enrollment_foreground(
    *,
    reference: MarketplaceReferenceAuthenticationEnrollmentLaunchPolicyNonceEd25519,
    provider: MarketplaceAsgiServerProvider,
    execute_token: str,
) -> None:
    """Execute one exact reviewed U graph through the existing N seam."""

    _validate_execute_token(execute_token)
    plan = _validate_reference(reference)
    try:
        run_marketplace_authentication_enrollment_foreground(
            plan=plan,
            provider=provider,
            execute_token=execute_token,
        )
    except MarketplaceReferenceAuthenticationEnrollmentForegroundRuntimeError:
        raise
    except Exception:
        _fail()


__all__ = [
    "MarketplaceReferenceAuthenticationEnrollmentForegroundRuntimeError",
    "PROFILE_NAME",
    "run_reference_authentication_enrollment_foreground",
]
