"""M17.6N explicit enrollment-aware foreground runtime seam.

This module introduces one source-level execution boundary for an already
reviewed M17.6M enrollment-aware loopback launch plan. It remains unselected by
startup, launch, reference, Web, Android, configuration, services, and concrete
server-provider paths.
"""
from __future__ import annotations

from typing import Final

from .auth_enrollment_launch import (
    MarketplaceAuthenticationEnrollmentLoopbackLaunchPlan,
)
from .auth_enrollment_startup_composition import (
    MarketplaceAuthenticationEnrollmentStartupComposition,
)
from .auth_session_asgi import MarketplaceSessionEstablishmentAsgiHttpAdapter
from .launch import LOOPBACK_LAUNCH_HOST, MAX_LAUNCH_PORT, MIN_LAUNCH_PORT
from .runtime_server import MarketplaceAsgiServerProvider


PROFILE_NAME: Final = (
    "MARKETPLACE_APPLICATION_AUTH_ENROLLMENT_FOREGROUND_RUNTIME_V1"
)
EXECUTE_ONE_AUTHENTICATION_ENROLLMENT_MARKETPLACE_LOOPBACK_SERVER: Final = (
    "EXECUTE_ONE_AUTHENTICATION_ENROLLMENT_MARKETPLACE_LOOPBACK_SERVER"
)
_ERROR_MESSAGE: Final = "authentication enrollment loopback runtime failed"


class MarketplaceAuthenticationEnrollmentLocalRuntimeError(RuntimeError):
    """Stable fail-closed runtime error without provider or credential reflection."""

    def __init__(self) -> None:
        super().__init__(_ERROR_MESSAGE)


def _fail() -> None:
    raise MarketplaceAuthenticationEnrollmentLocalRuntimeError() from None


def _validate_execute_token(execute_token: str) -> None:
    if (
        type(execute_token) is not str
        or execute_token
        != EXECUTE_ONE_AUTHENTICATION_ENROLLMENT_MARKETPLACE_LOOPBACK_SERVER
    ):
        _fail()


def _bound_owner(value: object) -> object | None:
    try:
        if not callable(value):
            return None
        return getattr(value, "__self__", None)
    except Exception:
        _fail()


def _validate_plan(
    plan: MarketplaceAuthenticationEnrollmentLoopbackLaunchPlan,
) -> None:
    if type(plan) is not MarketplaceAuthenticationEnrollmentLoopbackLaunchPlan:
        _fail()

    try:
        if type(plan.host) is not str or plan.host != LOOPBACK_LAUNCH_HOST:
            _fail()
        if type(plan.port) is not int:
            _fail()
        if plan.port < MIN_LAUNCH_PORT or plan.port > MAX_LAUNCH_PORT:
            _fail()

        startup = plan.startup
        if (
            type(startup)
            is not MarketplaceAuthenticationEnrollmentStartupComposition
        ):
            _fail()
        if startup.enrollment_http.http is not startup.authenticated_startup.http:
            _fail()
        if startup.enrollment_asgi.enrollment is not startup.enrollment_http:
            _fail()
        if startup.enrollment_asgi.runtime_inputs is not startup.runtime_inputs:
            _fail()
        if (
            startup.authenticated_startup.asgi.runtime_inputs
            is not startup.runtime_inputs
        ):
            _fail()

        if type(plan.asgi) is not MarketplaceSessionEstablishmentAsgiHttpAdapter:
            _fail()
        if plan.asgi is not startup.enrollment_asgi.asgi:
            _fail()
        if plan.asgi._site is not startup.authenticated_startup.http.application.site:
            _fail()
        if (
            plan.asgi._marketplace_http
            is not startup.authenticated_startup.http.application_http
        ):
            _fail()
        if plan.asgi._auth_http is not startup.authenticated_startup.http.session_http:
            _fail()
        if plan.asgi._enrollment_http is not startup.enrollment_http.enrollment_http:
            _fail()
        if _bound_owner(plan.asgi._now) is not startup.runtime_inputs.clock:
            _fail()
    except MarketplaceAuthenticationEnrollmentLocalRuntimeError:
        raise
    except Exception:
        _fail()


def _provider_run(provider: MarketplaceAsgiServerProvider):
    try:
        run = provider.run
    except Exception:
        _fail()
    if not callable(run):
        _fail()
    return run


def run_marketplace_authentication_enrollment_foreground(
    *,
    plan: MarketplaceAuthenticationEnrollmentLoopbackLaunchPlan,
    provider: MarketplaceAsgiServerProvider,
    execute_token: str,
) -> None:
    """Delegate exactly once after explicit token and exact graph validation."""

    _validate_execute_token(execute_token)
    _validate_plan(plan)
    run = _provider_run(provider)
    try:
        run(application=plan.asgi, host=plan.host, port=plan.port)
    except Exception:
        _fail()


__all__ = [
    "EXECUTE_ONE_AUTHENTICATION_ENROLLMENT_MARKETPLACE_LOOPBACK_SERVER",
    "MarketplaceAuthenticationEnrollmentLocalRuntimeError",
    "PROFILE_NAME",
    "run_marketplace_authentication_enrollment_foreground",
]
