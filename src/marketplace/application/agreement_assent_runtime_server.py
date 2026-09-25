"""Explicit foreground execution seam for one Agreement-assent loopback plan."""
from __future__ import annotations

from typing import Final

from .agreement_assent_launch import MarketplaceAgreementAssentLoopbackLaunchPlan
from .auth_session_asgi import MarketplaceSessionEstablishmentAsgiHttpAdapter
from .launch import LOOPBACK_LAUNCH_HOST, MAX_LAUNCH_PORT, MIN_LAUNCH_PORT
from .runtime_server import MarketplaceAsgiServerProvider


PROFILE_NAME: Final = "MARKETPLACE_AGREEMENT_ASSENT_FOREGROUND_RUNTIME_V1"
EXECUTE_ONE_AGREEMENT_ASSENT_MARKETPLACE_LOOPBACK_SERVER: Final = (
    "EXECUTE_ONE_AGREEMENT_ASSENT_MARKETPLACE_LOOPBACK_SERVER"
)


class MarketplaceAgreementAssentLocalRuntimeError(RuntimeError):
    """Stable Agreement-assent runtime failure without provider-detail reflection."""

    def __init__(self) -> None:
        super().__init__("Agreement assent loopback runtime failed")


def _fail() -> None:
    raise MarketplaceAgreementAssentLocalRuntimeError() from None


def _validate_execute_token(execute_token: str) -> None:
    if (
        type(execute_token) is not str
        or execute_token != EXECUTE_ONE_AGREEMENT_ASSENT_MARKETPLACE_LOOPBACK_SERVER
    ):
        _fail()


def _validate_plan(plan: MarketplaceAgreementAssentLoopbackLaunchPlan) -> None:
    if type(plan) is not MarketplaceAgreementAssentLoopbackLaunchPlan:
        _fail()
    try:
        if type(plan.host) is not str or plan.host != LOOPBACK_LAUNCH_HOST:
            _fail()
        if type(plan.port) is not int or isinstance(plan.port, bool):
            _fail()
        if plan.port < MIN_LAUNCH_PORT or plan.port > MAX_LAUNCH_PORT:
            _fail()
        startup = plan.startup
        if plan.asgi is not startup.agreement_asgi.asgi:
            _fail()
        if type(plan.asgi) is not MarketplaceSessionEstablishmentAsgiHttpAdapter:
            _fail()
        if plan.asgi._site is not startup.authenticated_startup.http.application.site:
            _fail()
        if plan.asgi._marketplace_http is not startup.agreement_http.assent_http:
            _fail()
        if plan.asgi._auth_http is not startup.authenticated_startup.http.session_http:
            _fail()
    except MarketplaceAgreementAssentLocalRuntimeError:
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


def run_marketplace_agreement_assent_foreground(
    *,
    plan: MarketplaceAgreementAssentLoopbackLaunchPlan,
    provider: MarketplaceAsgiServerProvider,
    execute_token: str,
) -> None:
    """Delegate exactly once after exact Agreement-assent authority checks."""

    _validate_execute_token(execute_token)
    _validate_plan(plan)
    run = _provider_run(provider)
    try:
        run(application=plan.asgi, host=plan.host, port=plan.port)
    except Exception:
        _fail()


__all__ = [
    "EXECUTE_ONE_AGREEMENT_ASSENT_MARKETPLACE_LOOPBACK_SERVER",
    "MarketplaceAgreementAssentLocalRuntimeError",
    "PROFILE_NAME",
    "run_marketplace_agreement_assent_foreground",
]
