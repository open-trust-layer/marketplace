"""Inert loopback launch metadata for the Agreement-assent startup overlay."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from .agreement_assent_startup_composition import (
    MarketplaceAgreementAssentStartupComposition,
)
from .auth_session_asgi import MarketplaceSessionEstablishmentAsgiHttpAdapter
from .launch import LOOPBACK_LAUNCH_HOST, MAX_LAUNCH_PORT, MIN_LAUNCH_PORT


PROFILE_NAME: Final = "MARKETPLACE_AGREEMENT_ASSENT_LOOPBACK_LAUNCH_PLAN_V1"


class MarketplaceAgreementAssentLoopbackLaunchPlanError(ValueError):
    """Stable non-reflective Agreement-assent launch-plan failure."""

    def __init__(self) -> None:
        super().__init__("Agreement assent loopback launch plan failed")


def _fail() -> None:
    raise MarketplaceAgreementAssentLoopbackLaunchPlanError() from None


def _validate_host(host: str) -> None:
    if type(host) is not str or host != LOOPBACK_LAUNCH_HOST:
        _fail()


def _validate_port(port: int) -> None:
    if type(port) is not int or isinstance(port, bool):
        _fail()
    if port < MIN_LAUNCH_PORT or port > MAX_LAUNCH_PORT:
        _fail()


def _validate_startup(startup: MarketplaceAgreementAssentStartupComposition) -> None:
    if type(startup) is not MarketplaceAgreementAssentStartupComposition:
        _fail()
    try:
        if (
            startup.agreement_http.authenticated_http
            is not startup.authenticated_startup.http
        ):
            _fail()
        if (
            startup.agreement_asgi.authenticated_http
            is not startup.authenticated_startup.http
        ):
            _fail()
        if startup.agreement_asgi.agreement_http is not startup.agreement_http:
            _fail()
        if (
            type(startup.agreement_asgi.asgi)
            is not MarketplaceSessionEstablishmentAsgiHttpAdapter
        ):
            _fail()
        if (
            startup.agreement_asgi.asgi._marketplace_http
            is not startup.agreement_http.assent_http
        ):
            _fail()
        if (
            startup.agreement_asgi.asgi._auth_http
            is not startup.authenticated_startup.http.session_http
        ):
            _fail()
    except MarketplaceAgreementAssentLoopbackLaunchPlanError:
        raise
    except Exception:
        _fail()


@dataclass(frozen=True, slots=True)
class MarketplaceAgreementAssentLoopbackLaunchPlan:
    """Immutable loopback metadata for the reviewed Agreement-assent ASGI graph."""

    host: str
    port: int
    startup: MarketplaceAgreementAssentStartupComposition
    asgi: MarketplaceSessionEstablishmentAsgiHttpAdapter

    def __post_init__(self) -> None:
        _validate_host(self.host)
        _validate_port(self.port)
        _validate_startup(self.startup)
        if type(self.asgi) is not MarketplaceSessionEstablishmentAsgiHttpAdapter:
            _fail()
        if self.asgi is not self.startup.agreement_asgi.asgi:
            _fail()


def build_marketplace_agreement_assent_loopback_launch_plan(
    *,
    host: str,
    port: int,
    startup: MarketplaceAgreementAssentStartupComposition,
) -> MarketplaceAgreementAssentLoopbackLaunchPlan:
    """Bind exact loopback metadata to the inert Agreement-assent startup overlay."""

    try:
        _validate_host(host)
        _validate_port(port)
        _validate_startup(startup)
        return MarketplaceAgreementAssentLoopbackLaunchPlan(
            host=host,
            port=port,
            startup=startup,
            asgi=startup.agreement_asgi.asgi,
        )
    except MarketplaceAgreementAssentLoopbackLaunchPlanError:
        raise
    except Exception:
        _fail()


__all__ = [
    "MarketplaceAgreementAssentLoopbackLaunchPlan",
    "MarketplaceAgreementAssentLoopbackLaunchPlanError",
    "PROFILE_NAME",
    "build_marketplace_agreement_assent_loopback_launch_plan",
]
