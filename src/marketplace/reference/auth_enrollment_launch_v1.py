"""M17.6O inert reference authentication-enrollment launch selection.

This module selects caller-supplied enrollment collaborators into the already
reviewed M17.6L/M startup and launch graph over one exact authenticated launch
plan. It does not choose concrete enrollment authority, invoke collaborators,
select runtime execution, inspect providers, or open sockets.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from ..application.auth_enrollment_authority import (
    AuthenticationEnrollmentAuthorityAttestor,
)
from ..application.auth_enrollment_launch import (
    MarketplaceAuthenticationEnrollmentLoopbackLaunchPlan,
    build_marketplace_authentication_enrollment_loopback_launch_plan,
)
from ..application.auth_enrollment_nonce import (
    MarketplaceAuthenticationEnrollmentNonceAuthority,
)
from ..application.auth_enrollment_policy import (
    AuthenticationEnrollmentApprovalPolicy,
)
from ..application.auth_enrollment_startup_composition import (
    MarketplaceAuthenticationEnrollmentStartupComposition,
    compose_marketplace_authentication_enrollment_startup,
)
from ..application.auth_launch import MarketplaceAuthenticatedLoopbackLaunchPlan
from ..application.auth_session_asgi import (
    MarketplaceSessionEstablishmentAsgiHttpAdapter,
)
from ..application.auth_startup_composition import (
    MarketplaceAuthenticatedStartupComposition,
)
from ..application.launch import (
    LOOPBACK_LAUNCH_HOST,
    MAX_LAUNCH_PORT,
    MIN_LAUNCH_PORT,
)


PROFILE_NAME: Final = (
    "MARKETPLACE_REFERENCE_AUTHENTICATION_ENROLLMENT_LAUNCH_V1"
)
_ERROR_MESSAGE: Final = (
    "reference authentication enrollment launch composition failed"
)


class MarketplaceReferenceAuthenticationEnrollmentLaunchError(ValueError):
    """Stable fail-closed reference enrollment-selection error."""

    def __init__(self) -> None:
        super().__init__(_ERROR_MESSAGE)


def _fail() -> None:
    raise MarketplaceReferenceAuthenticationEnrollmentLaunchError() from None


def _validate_authenticated_plan(
    authenticated_plan: MarketplaceAuthenticatedLoopbackLaunchPlan,
) -> None:
    if type(authenticated_plan) is not MarketplaceAuthenticatedLoopbackLaunchPlan:
        _fail()

    try:
        if (
            type(authenticated_plan.host) is not str
            or authenticated_plan.host != LOOPBACK_LAUNCH_HOST
        ):
            _fail()
        if type(authenticated_plan.port) is not int:
            _fail()
        if (
            authenticated_plan.port < MIN_LAUNCH_PORT
            or authenticated_plan.port > MAX_LAUNCH_PORT
        ):
            _fail()

        startup = authenticated_plan.startup
        if type(startup) is not MarketplaceAuthenticatedStartupComposition:
            _fail()
        if startup.http.authentication is not startup.authentication:
            _fail()
        if startup.asgi.http is not startup.http:
            _fail()
        if (
            type(authenticated_plan.asgi)
            is not MarketplaceSessionEstablishmentAsgiHttpAdapter
        ):
            _fail()
        if authenticated_plan.asgi is not startup.asgi.asgi:
            _fail()
        if authenticated_plan.asgi._site is not startup.http.application.site:
            _fail()
        if authenticated_plan.asgi._marketplace_http is not startup.http.application_http:
            _fail()
        if authenticated_plan.asgi._auth_http is not startup.http.session_http:
            _fail()
        if authenticated_plan.asgi._enrollment_http is not None:
            _fail()
    except MarketplaceReferenceAuthenticationEnrollmentLaunchError:
        raise
    except Exception:
        _fail()


@dataclass(frozen=True, slots=True)
class MarketplaceReferenceAuthenticationEnrollmentLaunch:
    """Exact inert enrollment launch graph over one authenticated launch plan."""

    authenticated_plan: MarketplaceAuthenticatedLoopbackLaunchPlan
    nonce_authority: MarketplaceAuthenticationEnrollmentNonceAuthority
    policy: AuthenticationEnrollmentApprovalPolicy
    attestor: AuthenticationEnrollmentAuthorityAttestor
    authority: str
    evidence_lease_seconds: int
    startup: MarketplaceAuthenticationEnrollmentStartupComposition
    plan: MarketplaceAuthenticationEnrollmentLoopbackLaunchPlan

    def __post_init__(self) -> None:
        _validate_authenticated_plan(self.authenticated_plan)
        if (
            type(self.nonce_authority)
            is not MarketplaceAuthenticationEnrollmentNonceAuthority
        ):
            _fail()
        if (
            type(self.startup)
            is not MarketplaceAuthenticationEnrollmentStartupComposition
        ):
            _fail()
        if (
            type(self.plan)
            is not MarketplaceAuthenticationEnrollmentLoopbackLaunchPlan
        ):
            _fail()

        authenticated_startup = self.authenticated_plan.startup
        if self.startup.authenticated_startup is not authenticated_startup:
            _fail()
        if self.startup.runtime_inputs is not authenticated_startup.asgi.runtime_inputs:
            _fail()
        if self.startup.enrollment_http.nonce_authority is not self.nonce_authority:
            _fail()
        if self.startup.enrollment_http.policy is not self.policy:
            _fail()
        if self.startup.enrollment_http.attestor is not self.attestor:
            _fail()
        if self.startup.enrollment_http.authority != self.authority:
            _fail()
        if (
            self.startup.enrollment_http.evidence_lease_seconds
            != self.evidence_lease_seconds
        ):
            _fail()
        if self.plan.startup is not self.startup:
            _fail()
        if self.plan.host != self.authenticated_plan.host:
            _fail()
        if self.plan.port != self.authenticated_plan.port:
            _fail()
        if self.plan.asgi is not self.startup.enrollment_asgi.asgi:
            _fail()
        if self.authenticated_plan.asgi._enrollment_http is not None:
            _fail()


def build_reference_authentication_enrollment_launch(
    *,
    authenticated_plan: MarketplaceAuthenticatedLoopbackLaunchPlan,
    nonce_authority: MarketplaceAuthenticationEnrollmentNonceAuthority,
    policy: AuthenticationEnrollmentApprovalPolicy,
    attestor: AuthenticationEnrollmentAuthorityAttestor,
    authority: str,
    evidence_lease_seconds: int,
) -> MarketplaceReferenceAuthenticationEnrollmentLaunch:
    """Select exact caller collaborators into inert L then M composition."""

    _validate_authenticated_plan(authenticated_plan)
    if (
        type(nonce_authority)
        is not MarketplaceAuthenticationEnrollmentNonceAuthority
    ):
        _fail()

    try:
        authenticated_startup = authenticated_plan.startup
        runtime_inputs = authenticated_startup.asgi.runtime_inputs
        startup = compose_marketplace_authentication_enrollment_startup(
            authenticated_startup=authenticated_startup,
            runtime_inputs=runtime_inputs,
            nonce_authority=nonce_authority,
            policy=policy,
            attestor=attestor,
            authority=authority,
            evidence_lease_seconds=evidence_lease_seconds,
        )
        plan = build_marketplace_authentication_enrollment_loopback_launch_plan(
            host=authenticated_plan.host,
            port=authenticated_plan.port,
            startup=startup,
        )
        return MarketplaceReferenceAuthenticationEnrollmentLaunch(
            authenticated_plan=authenticated_plan,
            nonce_authority=nonce_authority,
            policy=policy,
            attestor=attestor,
            authority=authority,
            evidence_lease_seconds=evidence_lease_seconds,
            startup=startup,
            plan=plan,
        )
    except MarketplaceReferenceAuthenticationEnrollmentLaunchError:
        raise
    except Exception:
        _fail()


__all__ = [
    "MarketplaceReferenceAuthenticationEnrollmentLaunch",
    "MarketplaceReferenceAuthenticationEnrollmentLaunchError",
    "PROFILE_NAME",
    "build_reference_authentication_enrollment_launch",
]
