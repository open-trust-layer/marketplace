"""M17.6L authenticated enrollment startup overlay composition.

This module overlays reviewed M17.6J/K enrollment HTTP/ASGI composition onto
one existing authenticated startup graph. It does not rebuild authentication,
resample time, consume material, select launch/runtime, or activate clients.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from .auth_enrollment_asgi_composition import (
    MarketplaceAuthenticationEnrollmentAsgiComposition,
    compose_marketplace_authentication_enrollment_asgi,
)
from .auth_enrollment_authority import AuthenticationEnrollmentAuthorityAttestor
from .auth_enrollment_http_composition import (
    MarketplaceAuthenticationEnrollmentHttpComposition,
    compose_marketplace_authentication_enrollment_http,
)
from .auth_enrollment_nonce import MarketplaceAuthenticationEnrollmentNonceAuthority
from .auth_enrollment_policy import AuthenticationEnrollmentApprovalPolicy
from .auth_runtime_inputs import MarketplaceAuthenticationRuntimeInputs
from .auth_startup_composition import MarketplaceAuthenticatedStartupComposition


PROFILE_NAME: Final = (
    "MARKETPLACE_APPLICATION_AUTH_ENROLLMENT_STARTUP_COMPOSITION_V1"
)
_ERROR_MESSAGE: Final = "authentication enrollment startup composition failed"


class MarketplaceAuthenticationEnrollmentStartupCompositionError(ValueError):
    """Stable fail-closed startup-overlay error without sensitive reflection."""

    def __init__(self) -> None:
        super().__init__(_ERROR_MESSAGE)


def _fail() -> None:
    raise MarketplaceAuthenticationEnrollmentStartupCompositionError() from None


def _validate_base(
    authenticated_startup: MarketplaceAuthenticatedStartupComposition,
    runtime_inputs: MarketplaceAuthenticationRuntimeInputs,
) -> None:
    if type(authenticated_startup) is not MarketplaceAuthenticatedStartupComposition:
        _fail()
    if type(runtime_inputs) is not MarketplaceAuthenticationRuntimeInputs:
        _fail()
    try:
        if authenticated_startup.asgi.http is not authenticated_startup.http:
            _fail()
        if authenticated_startup.http.authentication is not authenticated_startup.authentication:
            _fail()
        if authenticated_startup.asgi.runtime_inputs is not runtime_inputs:
            _fail()
    except MarketplaceAuthenticationEnrollmentStartupCompositionError:
        raise
    except Exception:
        _fail()


@dataclass(frozen=True, slots=True)
class MarketplaceAuthenticationEnrollmentStartupComposition:
    """Immutable enrollment overlay bound to one existing authenticated startup."""

    authenticated_startup: MarketplaceAuthenticatedStartupComposition
    runtime_inputs: MarketplaceAuthenticationRuntimeInputs
    enrollment_http: MarketplaceAuthenticationEnrollmentHttpComposition
    enrollment_asgi: MarketplaceAuthenticationEnrollmentAsgiComposition

    def __post_init__(self) -> None:
        _validate_base(self.authenticated_startup, self.runtime_inputs)
        if (
            type(self.enrollment_http)
            is not MarketplaceAuthenticationEnrollmentHttpComposition
        ):
            _fail()
        if (
            type(self.enrollment_asgi)
            is not MarketplaceAuthenticationEnrollmentAsgiComposition
        ):
            _fail()
        if self.enrollment_http.http is not self.authenticated_startup.http:
            _fail()
        if self.enrollment_asgi.enrollment is not self.enrollment_http:
            _fail()
        if self.enrollment_asgi.runtime_inputs is not self.runtime_inputs:
            _fail()
        if (
            self.enrollment_asgi.asgi._enrollment_http
            is not self.enrollment_http.enrollment_http
        ):
            _fail()


def compose_marketplace_authentication_enrollment_startup(
    *,
    authenticated_startup: MarketplaceAuthenticatedStartupComposition,
    runtime_inputs: MarketplaceAuthenticationRuntimeInputs,
    nonce_authority: MarketplaceAuthenticationEnrollmentNonceAuthority,
    policy: AuthenticationEnrollmentApprovalPolicy,
    attestor: AuthenticationEnrollmentAuthorityAttestor,
    authority: str,
    evidence_lease_seconds: int,
) -> MarketplaceAuthenticationEnrollmentStartupComposition:
    """Overlay J then K onto one exact authenticated startup without consumption."""

    _validate_base(authenticated_startup, runtime_inputs)
    if type(nonce_authority) is not MarketplaceAuthenticationEnrollmentNonceAuthority:
        _fail()

    try:
        enrollment_http = compose_marketplace_authentication_enrollment_http(
            http=authenticated_startup.http,
            nonce_authority=nonce_authority,
            policy=policy,
            attestor=attestor,
            authority=authority,
            evidence_lease_seconds=evidence_lease_seconds,
        )
        enrollment_asgi = compose_marketplace_authentication_enrollment_asgi(
            enrollment=enrollment_http,
            runtime_inputs=runtime_inputs,
        )
        return MarketplaceAuthenticationEnrollmentStartupComposition(
            authenticated_startup=authenticated_startup,
            runtime_inputs=runtime_inputs,
            enrollment_http=enrollment_http,
            enrollment_asgi=enrollment_asgi,
        )
    except MarketplaceAuthenticationEnrollmentStartupCompositionError:
        raise
    except Exception:
        _fail()


__all__ = [
    "MarketplaceAuthenticationEnrollmentStartupComposition",
    "MarketplaceAuthenticationEnrollmentStartupCompositionError",
    "PROFILE_NAME",
    "compose_marketplace_authentication_enrollment_startup",
]
