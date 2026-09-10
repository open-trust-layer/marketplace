"""M17.5W inert reference authenticated launch composition."""
from __future__ import annotations

from typing import Final

from ..application.asgi import MarketplaceAsgiHttpAdapter
from ..application.auth_launch import (
    MarketplaceAuthenticatedLoopbackLaunchPlan,
    build_marketplace_authenticated_loopback_launch_plan,
)
from ..application.auth_runtime_inputs import MarketplaceAuthenticationRuntimeInputs
from ..application.auth_startup_composition import (
    MarketplaceAuthenticatedStartupComposition,
    compose_marketplace_authenticated_startup,
)
from ..application.auth_startup_provisioning import (
    MarketplaceAuthenticationStartupProvisioning,
)
from ..application.composition import MarketplaceApplicationComposition
from ..application.launch import (
    LOOPBACK_LAUNCH_HOST,
    MAX_LAUNCH_PORT,
    MIN_LAUNCH_PORT,
    MarketplaceApplicationLaunchPlan,
)
from .application_record_json_v1 import decode_marketplace_application_record_json
from .application_record_v1 import marketplace_record_issuer_principal

PROFILE_NAME: Final = "MARKETPLACE_REFERENCE_AUTHENTICATED_LAUNCH_V1"
_ERROR_MESSAGE: Final = "reference authenticated Marketplace launch composition failed"


class MarketplaceReferenceAuthenticatedLaunchError(ValueError):
    """Stable fail-closed reference authentication composition error."""

    def __init__(self) -> None:
        super().__init__(_ERROR_MESSAGE)


def _fail() -> None:
    raise MarketplaceReferenceAuthenticatedLaunchError() from None


def _validate_application_plan(plan: MarketplaceApplicationLaunchPlan) -> None:
    if type(plan) is not MarketplaceApplicationLaunchPlan:
        _fail()
    try:
        if type(plan.host) is not str or plan.host != LOOPBACK_LAUNCH_HOST:
            _fail()
        if type(plan.port) is not int:
            _fail()
        if plan.port < MIN_LAUNCH_PORT or plan.port > MAX_LAUNCH_PORT:
            _fail()
        if type(plan.composition) is not MarketplaceApplicationComposition:
            _fail()
        if type(plan.asgi) is not MarketplaceAsgiHttpAdapter:
            _fail()
        if plan.asgi._site is not plan.composition.site:
            _fail()
    except MarketplaceReferenceAuthenticatedLaunchError:
        raise
    except Exception:
        _fail()


def build_reference_authenticated_marketplace_launch_plan(
    *,
    application_plan: MarketplaceApplicationLaunchPlan,
    provisioning: MarketplaceAuthenticationStartupProvisioning,
    runtime_inputs: MarketplaceAuthenticationRuntimeInputs,
) -> MarketplaceAuthenticatedLoopbackLaunchPlan:
    """Bind reviewed reference semantics into the existing authenticated T/U graph."""

    _validate_application_plan(application_plan)
    if type(provisioning) is not MarketplaceAuthenticationStartupProvisioning:
        _fail()
    if type(runtime_inputs) is not MarketplaceAuthenticationRuntimeInputs:
        _fail()

    try:
        startup = compose_marketplace_authenticated_startup(
            application=application_plan.composition,
            provisioning=provisioning,
            runtime_inputs=runtime_inputs,
            decode_record_json=decode_marketplace_application_record_json,
            record_principal=marketplace_record_issuer_principal,
        )
        if type(startup) is not MarketplaceAuthenticatedStartupComposition:
            _fail()
        authenticated_plan = build_marketplace_authenticated_loopback_launch_plan(
            host=application_plan.host,
            port=application_plan.port,
            startup=startup,
        )
        if type(authenticated_plan) is not MarketplaceAuthenticatedLoopbackLaunchPlan:
            _fail()
        if authenticated_plan.host != application_plan.host:
            _fail()
        if authenticated_plan.port != application_plan.port:
            _fail()
        if authenticated_plan.startup is not startup:
            _fail()
        if authenticated_plan.asgi is not startup.asgi.asgi:
            _fail()
        if startup.http.application is not application_plan.composition:
            _fail()
        return authenticated_plan
    except MarketplaceReferenceAuthenticatedLaunchError:
        raise
    except Exception:
        _fail()


__all__ = [
    "MarketplaceReferenceAuthenticatedLaunchError",
    "PROFILE_NAME",
    "build_reference_authenticated_marketplace_launch_plan",
]
