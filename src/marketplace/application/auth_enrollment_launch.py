"""M17.6M inert enrollment-aware loopback launch metadata.

This module binds exact loopback metadata to one already-composed M17.6L
authenticated enrollment startup overlay. It never executes a server, opens a
socket, invokes a provider, handles a request, or consumes authentication or
enrollment material.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from .auth_enrollment_startup_composition import (
    MarketplaceAuthenticationEnrollmentStartupComposition,
)
from .auth_session_asgi import MarketplaceSessionEstablishmentAsgiHttpAdapter
from .launch import LOOPBACK_LAUNCH_HOST, MAX_LAUNCH_PORT, MIN_LAUNCH_PORT


PROFILE_NAME: Final = (
    "MARKETPLACE_APPLICATION_AUTH_ENROLLMENT_LOOPBACK_LAUNCH_PLAN_V1"
)
_ERROR_MESSAGE: Final = "authentication enrollment loopback launch plan failed"


class MarketplaceAuthenticationEnrollmentLoopbackLaunchPlanError(ValueError):
    """Stable fail-closed launch-plan error without sensitive reflection."""

    def __init__(self) -> None:
        super().__init__(_ERROR_MESSAGE)


def _fail() -> None:
    raise MarketplaceAuthenticationEnrollmentLoopbackLaunchPlanError() from None


def _validate_host(host: str) -> None:
    if type(host) is not str or host != LOOPBACK_LAUNCH_HOST:
        _fail()


def _validate_port(port: int) -> None:
    if type(port) is not int:
        _fail()
    if port < MIN_LAUNCH_PORT or port > MAX_LAUNCH_PORT:
        _fail()


def _bound_owner(value: object) -> object | None:
    try:
        if not callable(value):
            return None
        return getattr(value, "__self__", None)
    except Exception:
        _fail()


def _validate_startup(
    startup: MarketplaceAuthenticationEnrollmentStartupComposition,
) -> None:
    if type(startup) is not MarketplaceAuthenticationEnrollmentStartupComposition:
        _fail()
    try:
        if startup.enrollment_http.http is not startup.authenticated_startup.http:
            _fail()
        if startup.enrollment_asgi.enrollment is not startup.enrollment_http:
            _fail()
        if startup.enrollment_asgi.runtime_inputs is not startup.runtime_inputs:
            _fail()
        if startup.authenticated_startup.asgi.runtime_inputs is not startup.runtime_inputs:
            _fail()

        asgi = startup.enrollment_asgi.asgi
        if type(asgi) is not MarketplaceSessionEstablishmentAsgiHttpAdapter:
            _fail()
        if asgi._site is not startup.authenticated_startup.http.application.site:
            _fail()
        if asgi._marketplace_http is not startup.authenticated_startup.http.application_http:
            _fail()
        if asgi._auth_http is not startup.authenticated_startup.http.session_http:
            _fail()
        if asgi._enrollment_http is not startup.enrollment_http.enrollment_http:
            _fail()
        if _bound_owner(asgi._now) is not startup.runtime_inputs.clock:
            _fail()
    except MarketplaceAuthenticationEnrollmentLoopbackLaunchPlanError:
        raise
    except Exception:
        _fail()


@dataclass(frozen=True, slots=True)
class MarketplaceAuthenticationEnrollmentLoopbackLaunchPlan:
    """Immutable loopback metadata selecting the exact M17.6L/K ASGI object."""

    host: str
    port: int
    startup: MarketplaceAuthenticationEnrollmentStartupComposition
    asgi: MarketplaceSessionEstablishmentAsgiHttpAdapter

    def __post_init__(self) -> None:
        _validate_host(self.host)
        _validate_port(self.port)
        _validate_startup(self.startup)
        if type(self.asgi) is not MarketplaceSessionEstablishmentAsgiHttpAdapter:
            _fail()
        if self.asgi is not self.startup.enrollment_asgi.asgi:
            _fail()


def build_marketplace_authentication_enrollment_loopback_launch_plan(
    *,
    host: str,
    port: int,
    startup: MarketplaceAuthenticationEnrollmentStartupComposition,
) -> MarketplaceAuthenticationEnrollmentLoopbackLaunchPlan:
    """Bind exact loopback metadata without runtime or provider activation."""

    try:
        _validate_host(host)
        _validate_port(port)
        _validate_startup(startup)
        return MarketplaceAuthenticationEnrollmentLoopbackLaunchPlan(
            host=host,
            port=port,
            startup=startup,
            asgi=startup.enrollment_asgi.asgi,
        )
    except MarketplaceAuthenticationEnrollmentLoopbackLaunchPlanError:
        raise
    except Exception:
        _fail()


__all__ = [
    "MarketplaceAuthenticationEnrollmentLoopbackLaunchPlan",
    "MarketplaceAuthenticationEnrollmentLoopbackLaunchPlanError",
    "PROFILE_NAME",
    "build_marketplace_authentication_enrollment_loopback_launch_plan",
]
