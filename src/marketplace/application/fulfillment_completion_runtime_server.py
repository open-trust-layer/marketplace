"""Explicit foreground execution seam for one fulfillment-completion loopback plan."""
from __future__ import annotations

from typing import Final

from .auth_session_asgi import MarketplaceSessionEstablishmentAsgiHttpAdapter
from .fulfillment_completion_launch import (
    MarketplaceFulfillmentCompletionLoopbackLaunchPlan,
)
from .fulfillment_completion_startup_composition import (
    MarketplaceFulfillmentCompletionStartupComposition,
)
from .launch import LOOPBACK_LAUNCH_HOST, MAX_LAUNCH_PORT, MIN_LAUNCH_PORT
from .runtime_server import MarketplaceAsgiServerProvider


PROFILE_NAME: Final = "MARKETPLACE_FULFILLMENT_COMPLETION_FOREGROUND_RUNTIME_V1"
EXECUTE_ONE_FULFILLMENT_COMPLETION_MARKETPLACE_LOOPBACK_SERVER: Final = (
    "EXECUTE_ONE_FULFILLMENT_COMPLETION_MARKETPLACE_LOOPBACK_SERVER"
)
_ERROR_MESSAGE: Final = "Fulfillment completion loopback runtime failed"


class MarketplaceFulfillmentCompletionLocalRuntimeError(RuntimeError):
    """Stable fail-closed fulfillment runtime error without provider reflection."""

    def __init__(self) -> None:
        super().__init__(_ERROR_MESSAGE)


def _fail() -> None:
    raise MarketplaceFulfillmentCompletionLocalRuntimeError() from None


def _validate_execute_token(execute_token: str) -> None:
    if (
        type(execute_token) is not str
        or execute_token
        != EXECUTE_ONE_FULFILLMENT_COMPLETION_MARKETPLACE_LOOPBACK_SERVER
    ):
        _fail()


def _validate_plan(
    plan: MarketplaceFulfillmentCompletionLoopbackLaunchPlan,
) -> None:
    if type(plan) is not MarketplaceFulfillmentCompletionLoopbackLaunchPlan:
        _fail()
    try:
        if type(plan.host) is not str or plan.host != LOOPBACK_LAUNCH_HOST:
            _fail()
        if type(plan.port) is not int or isinstance(plan.port, bool):
            _fail()
        if plan.port < MIN_LAUNCH_PORT or plan.port > MAX_LAUNCH_PORT:
            _fail()
        startup = plan.startup
        if type(startup) is not MarketplaceFulfillmentCompletionStartupComposition:
            _fail()
        if type(plan.asgi) is not MarketplaceSessionEstablishmentAsgiHttpAdapter:
            _fail()
        if plan.asgi is not startup.fulfillment_asgi.asgi:
            _fail()
        authenticated_http = startup.agreement_startup.authenticated_startup.http
        if plan.asgi._site is not authenticated_http.application.site:
            _fail()
        if plan.asgi._marketplace_http is not startup.fulfillment_http.fulfillment_http:
            _fail()
        if plan.asgi._auth_http is not authenticated_http.session_http:
            _fail()
    except MarketplaceFulfillmentCompletionLocalRuntimeError:
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


def run_marketplace_fulfillment_completion_foreground(
    *,
    plan: MarketplaceFulfillmentCompletionLoopbackLaunchPlan,
    provider: MarketplaceAsgiServerProvider,
    execute_token: str,
) -> None:
    """Delegate once after exact fulfillment-completion authority checks."""

    _validate_execute_token(execute_token)
    _validate_plan(plan)
    run = _provider_run(provider)
    try:
        run(application=plan.asgi, host=plan.host, port=plan.port)
    except Exception:
        _fail()


__all__ = [
    "EXECUTE_ONE_FULFILLMENT_COMPLETION_MARKETPLACE_LOOPBACK_SERVER",
    "MarketplaceFulfillmentCompletionLocalRuntimeError",
    "PROFILE_NAME",
    "run_marketplace_fulfillment_completion_foreground",
]
