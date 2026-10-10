"""Inert loopback launch metadata for fulfillment-completion startup."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from .auth_session_asgi import MarketplaceSessionEstablishmentAsgiHttpAdapter
from .fulfillment_completion_startup_composition import (
    MarketplaceFulfillmentCompletionStartupComposition,
)
from .launch import LOOPBACK_LAUNCH_HOST, MAX_LAUNCH_PORT, MIN_LAUNCH_PORT


PROFILE_NAME: Final = "MARKETPLACE_FULFILLMENT_COMPLETION_LOOPBACK_LAUNCH_PLAN_V1"
_ERROR_MESSAGE: Final = "Fulfillment completion loopback launch plan failed"


class MarketplaceFulfillmentCompletionLoopbackLaunchPlanError(ValueError):
    """Stable non-reflective M17.7F launch-plan failure."""

    def __init__(self) -> None:
        super().__init__(_ERROR_MESSAGE)


def _fail() -> None:
    raise MarketplaceFulfillmentCompletionLoopbackLaunchPlanError() from None


def _validate_host(host: str) -> None:
    if type(host) is not str or host != LOOPBACK_LAUNCH_HOST:
        _fail()


def _validate_port(port: int) -> None:
    if type(port) is not int or isinstance(port, bool):
        _fail()
    if port < MIN_LAUNCH_PORT or port > MAX_LAUNCH_PORT:
        _fail()


def _validate_startup(
    startup: MarketplaceFulfillmentCompletionStartupComposition,
) -> None:
    if type(startup) is not MarketplaceFulfillmentCompletionStartupComposition:
        _fail()
    try:
        if (
            startup.fulfillment_asgi.fulfillment_http
            is not startup.fulfillment_http
        ):
            _fail()
        if (
            startup.fulfillment_asgi.runtime_inputs
            is not startup.runtime_inputs
        ):
            _fail()
        if (
            type(startup.fulfillment_asgi.asgi)
            is not MarketplaceSessionEstablishmentAsgiHttpAdapter
        ):
            _fail()
        if (
            startup.fulfillment_asgi.asgi._marketplace_http
            is not startup.fulfillment_http.fulfillment_http
        ):
            _fail()
        if (
            startup.fulfillment_asgi.asgi._auth_http
            is not startup.agreement_startup.authenticated_startup.http.session_http
        ):
            _fail()
    except MarketplaceFulfillmentCompletionLoopbackLaunchPlanError:
        raise
    except Exception:
        _fail()


@dataclass(frozen=True, slots=True)
class MarketplaceFulfillmentCompletionLoopbackLaunchPlan:
    """Immutable loopback metadata for the reviewed fulfillment ASGI graph."""

    host: str
    port: int
    startup: MarketplaceFulfillmentCompletionStartupComposition
    asgi: MarketplaceSessionEstablishmentAsgiHttpAdapter

    def __post_init__(self) -> None:
        _validate_host(self.host)
        _validate_port(self.port)
        _validate_startup(self.startup)
        if type(self.asgi) is not MarketplaceSessionEstablishmentAsgiHttpAdapter:
            _fail()
        if self.asgi is not self.startup.fulfillment_asgi.asgi:
            _fail()


def build_marketplace_fulfillment_completion_loopback_launch_plan(
    *,
    host: str,
    port: int,
    startup: MarketplaceFulfillmentCompletionStartupComposition,
) -> MarketplaceFulfillmentCompletionLoopbackLaunchPlan:
    """Bind exact loopback metadata to the inert fulfillment startup overlay."""

    try:
        _validate_host(host)
        _validate_port(port)
        _validate_startup(startup)
        return MarketplaceFulfillmentCompletionLoopbackLaunchPlan(
            host=host,
            port=port,
            startup=startup,
            asgi=startup.fulfillment_asgi.asgi,
        )
    except MarketplaceFulfillmentCompletionLoopbackLaunchPlanError:
        raise
    except Exception:
        _fail()


__all__ = [
    "MarketplaceFulfillmentCompletionLoopbackLaunchPlan",
    "MarketplaceFulfillmentCompletionLoopbackLaunchPlanError",
    "PROFILE_NAME",
    "build_marketplace_fulfillment_completion_loopback_launch_plan",
]
