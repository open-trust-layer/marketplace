"""Explicit foreground execution seam for one injected Marketplace ASGI server provider."""
from __future__ import annotations

from typing import Final, Protocol

from .asgi import MarketplaceAsgiHttpAdapter
from .composition import MarketplaceApplicationComposition
from .launch import (
    LOOPBACK_LAUNCH_HOST,
    MAX_LAUNCH_PORT,
    MIN_LAUNCH_PORT,
    MarketplaceApplicationLaunchPlan,
)


EXECUTE_ONE_MARKETPLACE_LOOPBACK_SERVER: Final = "EXECUTE_ONE_MARKETPLACE_LOOPBACK_SERVER"


class MarketplaceLocalRuntimeError(RuntimeError):
    """Stable local runtime boundary error with no provider-detail reflection."""


class MarketplaceAsgiServerProvider(Protocol):
    """Injected foreground provider; concrete server selection lives outside this module."""

    def run(self, *, application: object, host: str, port: int) -> None:
        """Run the supplied ASGI application in the caller-selected provider."""


def _validate_execute_token(execute_token: str) -> None:
    if type(execute_token) is not str or execute_token != EXECUTE_ONE_MARKETPLACE_LOOPBACK_SERVER:
        raise PermissionError("MARKETPLACE_LOOPBACK_SERVER_EXECUTION_NOT_AUTHORIZED")


def _validate_plan(plan: MarketplaceApplicationLaunchPlan) -> None:
    if type(plan) is not MarketplaceApplicationLaunchPlan:
        raise TypeError("plan MUST be exact MarketplaceApplicationLaunchPlan")
    if type(plan.host) is not str:
        raise TypeError("launch host must be an exact string")
    if plan.host != LOOPBACK_LAUNCH_HOST:
        raise ValueError("launch host must be exact IPv4 loopback")
    if type(plan.port) is not int:
        raise TypeError("launch port must be an exact integer")
    if plan.port < MIN_LAUNCH_PORT or plan.port > MAX_LAUNCH_PORT:
        raise ValueError("launch port is outside the reviewed TCP range")
    if type(plan.composition) is not MarketplaceApplicationComposition:
        raise TypeError("launch composition must be exact MarketplaceApplicationComposition")
    if type(plan.asgi) is not MarketplaceAsgiHttpAdapter:
        raise TypeError("launch ASGI adapter must be exact MarketplaceAsgiHttpAdapter")
    if plan.asgi._site is not plan.composition.site:
        raise ValueError("launch ASGI adapter is not bound to launch composition")


def _provider_run(provider: MarketplaceAsgiServerProvider):
    try:
        run = provider.run
    except Exception:
        raise TypeError("provider MUST expose a callable run method") from None
    if not callable(run):
        raise TypeError("provider MUST expose a callable run method")
    return run


def run_marketplace_application_foreground(
    *,
    plan: MarketplaceApplicationLaunchPlan,
    provider: MarketplaceAsgiServerProvider,
    execute_token: str,
) -> None:
    """Delegate once to an injected foreground provider after exact authority validation."""

    _validate_execute_token(execute_token)
    _validate_plan(plan)
    run = _provider_run(provider)
    try:
        run(application=plan.asgi, host=plan.host, port=plan.port)
    except Exception:
        raise MarketplaceLocalRuntimeError("MARKETPLACE_LOOPBACK_SERVER_PROVIDER_FAILED") from None


__all__ = [
    "EXECUTE_ONE_MARKETPLACE_LOOPBACK_SERVER",
    "MarketplaceAsgiServerProvider",
    "MarketplaceLocalRuntimeError",
    "run_marketplace_application_foreground",
]
