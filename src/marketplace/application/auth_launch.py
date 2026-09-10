"""M17.5U inert authenticated loopback launch plan without runtime activation."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from .auth_asgi_composition import MarketplaceAuthenticatedAsgiComposition
from .auth_http_composition import MarketplaceAuthenticatedHttpComposition
from .auth_session_asgi import MarketplaceSessionEstablishmentAsgiHttpAdapter
from .auth_startup_composition import MarketplaceAuthenticatedStartupComposition
from .auth_static_composition import MarketplaceStaticAuthenticationComposition
from .launch import LOOPBACK_LAUNCH_HOST, MAX_LAUNCH_PORT, MIN_LAUNCH_PORT


PROFILE_NAME: Final = "MARKETPLACE_APPLICATION_AUTH_LOOPBACK_LAUNCH_PLAN_V1"
_ERROR_MESSAGE: Final = "authenticated Marketplace loopback launch plan failed"


class MarketplaceAuthenticatedLoopbackLaunchPlanError(ValueError):
    """Stable fail-closed launch-plan error without sensitive reflection."""

    def __init__(self) -> None:
        super().__init__(_ERROR_MESSAGE)


def _fail() -> None:
    raise MarketplaceAuthenticatedLoopbackLaunchPlanError() from None


def _validate_host(host: str) -> None:
    if type(host) is not str or host != LOOPBACK_LAUNCH_HOST:
        _fail()


def _validate_port(port: int) -> None:
    if type(port) is not int:
        _fail()
    if port < MIN_LAUNCH_PORT or port > MAX_LAUNCH_PORT:
        _fail()


def _validate_startup(startup: MarketplaceAuthenticatedStartupComposition) -> None:
    if type(startup) is not MarketplaceAuthenticatedStartupComposition:
        _fail()
    try:
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
        if (
            type(startup.asgi.asgi)
            is not MarketplaceSessionEstablishmentAsgiHttpAdapter
        ):
            _fail()
    except MarketplaceAuthenticatedLoopbackLaunchPlanError:
        raise
    except Exception:
        _fail()


@dataclass(frozen=True, slots=True)
class MarketplaceAuthenticatedLoopbackLaunchPlan:
    """Immutable authenticated ASGI launch metadata; never executes a runtime."""

    host: str
    port: int
    startup: MarketplaceAuthenticatedStartupComposition
    asgi: MarketplaceSessionEstablishmentAsgiHttpAdapter

    def __post_init__(self) -> None:
        _validate_host(self.host)
        _validate_port(self.port)
        _validate_startup(self.startup)
        if type(self.asgi) is not MarketplaceSessionEstablishmentAsgiHttpAdapter:
            _fail()
        if self.asgi is not self.startup.asgi.asgi:
            _fail()


def build_marketplace_authenticated_loopback_launch_plan(
    *,
    host: str,
    port: int,
    startup: MarketplaceAuthenticatedStartupComposition,
) -> MarketplaceAuthenticatedLoopbackLaunchPlan:
    """Bind exact loopback metadata to the existing authenticated ASGI graph."""

    try:
        _validate_host(host)
        _validate_port(port)
        _validate_startup(startup)
        asgi = startup.asgi.asgi
        return MarketplaceAuthenticatedLoopbackLaunchPlan(
            host=host,
            port=port,
            startup=startup,
            asgi=asgi,
        )
    except MarketplaceAuthenticatedLoopbackLaunchPlanError:
        raise
    except Exception:
        _fail()


__all__ = [
    "MarketplaceAuthenticatedLoopbackLaunchPlan",
    "MarketplaceAuthenticatedLoopbackLaunchPlanError",
    "PROFILE_NAME",
    "build_marketplace_authenticated_loopback_launch_plan",
]
