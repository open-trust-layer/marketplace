"""M17.6W unselected reference enrollment Uvicorn runtime selection."""
from __future__ import annotations

from typing import Final

from ..application.auth_enrollment_runtime_server import (
    EXECUTE_ONE_AUTHENTICATION_ENROLLMENT_MARKETPLACE_LOOPBACK_SERVER,
)
from ..application.uvicorn_provider import UvicornLoopbackServerProvider
from .auth_enrollment_launch_policy_nonce_ed25519_v1 import (
    MarketplaceReferenceAuthenticationEnrollmentLaunchPolicyNonceEd25519,
)
from .auth_enrollment_runtime_v1 import (
    run_reference_authentication_enrollment_foreground,
)


PROFILE_NAME: Final = (
    "MARKETPLACE_REFERENCE_AUTHENTICATION_ENROLLMENT_UVICORN_RUNTIME_V1"
)
_ERROR_MESSAGE: Final = (
    "reference authentication enrollment Uvicorn runtime failed"
)


class MarketplaceReferenceAuthenticationEnrollmentUvicornRuntimeError(
    RuntimeError
):
    """Stable fail-closed M17.6W concrete-provider selection error."""

    def __init__(self) -> None:
        super().__init__(_ERROR_MESSAGE)


def _fail() -> None:
    raise MarketplaceReferenceAuthenticationEnrollmentUvicornRuntimeError() from None


def _validate_execute_token(execute_token: str) -> None:
    if (
        type(execute_token) is not str
        or execute_token
        != EXECUTE_ONE_AUTHENTICATION_ENROLLMENT_MARKETPLACE_LOOPBACK_SERVER
    ):
        _fail()


def _validate_reference_type(
    reference: MarketplaceReferenceAuthenticationEnrollmentLaunchPolicyNonceEd25519,
) -> None:
    if (
        type(reference)
        is not MarketplaceReferenceAuthenticationEnrollmentLaunchPolicyNonceEd25519
    ):
        _fail()


def run_reference_authentication_enrollment_uvicorn_foreground(
    *,
    reference: MarketplaceReferenceAuthenticationEnrollmentLaunchPolicyNonceEd25519,
    execute_token: str,
) -> None:
    """Select one reviewed lazy Uvicorn provider and delegate exactly once to V."""

    _validate_execute_token(execute_token)
    _validate_reference_type(reference)
    try:
        provider = UvicornLoopbackServerProvider()
        run_reference_authentication_enrollment_foreground(
            reference=reference,
            provider=provider,
            execute_token=execute_token,
        )
    except MarketplaceReferenceAuthenticationEnrollmentUvicornRuntimeError:
        raise
    except Exception:
        _fail()


__all__ = [
    "MarketplaceReferenceAuthenticationEnrollmentUvicornRuntimeError",
    "PROFILE_NAME",
    "run_reference_authentication_enrollment_uvicorn_foreground",
]
