"""M17.5V authenticated foreground loopback execution seam without activation."""
from __future__ import annotations

from typing import Final

from .auth_asgi_composition import MarketplaceAuthenticatedAsgiComposition
from .auth_http_composition import MarketplaceAuthenticatedHttpComposition
from .auth_launch import MarketplaceAuthenticatedLoopbackLaunchPlan
from .auth_session_asgi import MarketplaceSessionEstablishmentAsgiHttpAdapter
from .auth_startup_composition import MarketplaceAuthenticatedStartupComposition
from .auth_static_composition import MarketplaceStaticAuthenticationComposition
from .launch import LOOPBACK_LAUNCH_HOST, MAX_LAUNCH_PORT, MIN_LAUNCH_PORT
from .runtime_server import MarketplaceAsgiServerProvider


PROFILE_NAME: Final = "MARKETPLACE_APPLICATION_AUTH_FOREGROUND_RUNTIME_V1"
EXECUTE_ONE_AUTHENTICATED_MARKETPLACE_LOOPBACK_SERVER: Final = (
    "EXECUTE_ONE_AUTHENTICATED_MARKETPLACE_LOOPBACK_SERVER"
)
_ERROR_MESSAGE: Final = "authenticated Marketplace loopback runtime failed"


class MarketplaceAuthenticatedLocalRuntimeError(RuntimeError):
    """Stable fail-closed authenticated runtime error without detail reflection."""

    def __init__(self) -> None:
        super().__init__(_ERROR_MESSAGE)


def _fail() -> None:
    raise MarketplaceAuthenticatedLocalRuntimeError() from None


def _validate_execute_token(execute_token: str) -> None:
    if (
        type(execute_token) is not str
        or execute_token != EXECUTE_ONE_AUTHENTICATED_MARKETPLACE_LOOPBACK_SERVER
    ):
        _fail()


def _validate_plan(plan: MarketplaceAuthenticatedLoopbackLaunchPlan) -> None:
    if type(plan) is not MarketplaceAuthenticatedLoopbackLaunchPlan:
        _fail()
    try:
        if type(plan.host) is not str or plan.host != LOOPBACK_LAUNCH_HOST:
            _fail()
        if type(plan.port) is not int:
            _fail()
        if plan.port < MIN_LAUNCH_PORT or plan.port > MAX_LAUNCH_PORT:
            _fail()

        startup = plan.startup
        if type(startup) is not MarketplaceAuthenticatedStartupComposition:
            _fail()
        if (
            type(startup.authentication)
            is not MarketplaceStaticAuthenticationComposition
        ):
            _fail()
        if type(startup.http) is not MarketplaceAuthenticatedHttpComposition:
            _fail()
        if type(startup.asgi) is not MarketplaceAuthenticatedAsgiComposition:
            _fail()
        if startup.http.authentication is not startup.authentication:
            _fail()
        if startup.asgi.http is not startup.http:
            _fail()

        if type(plan.asgi) is not MarketplaceSessionEstablishmentAsgiHttpAdapter:
            _fail()
        if plan.asgi is not startup.asgi.asgi:
            _fail()
        if plan.asgi._site is not startup.http.application.site:
            _fail()
        if plan.asgi._marketplace_http is not startup.http.application_http:
            _fail()
        if plan.asgi._auth_http is not startup.http.session_http:
            _fail()
    except MarketplaceAuthenticatedLocalRuntimeError:
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


def run_marketplace_authenticated_application_foreground(
    *,
    plan: MarketplaceAuthenticatedLoopbackLaunchPlan,
    provider: MarketplaceAsgiServerProvider,
    execute_token: str,
) -> None:
    """Delegate once to an injected provider after exact authenticated checks."""

    _validate_execute_token(execute_token)
    _validate_plan(plan)
    run = _provider_run(provider)
    try:
        run(application=plan.asgi, host=plan.host, port=plan.port)
    except Exception:
        _fail()


__all__ = [
    "EXECUTE_ONE_AUTHENTICATED_MARKETPLACE_LOOPBACK_SERVER",
    "MarketplaceAuthenticatedLocalRuntimeError",
    "PROFILE_NAME",
    "run_marketplace_authenticated_application_foreground",
]