"""M17.5X inert authenticated PostgreSQL reference application composition."""
from __future__ import annotations

from typing import Final

from ..application.auth_launch import MarketplaceAuthenticatedLoopbackLaunchPlan
from ..application.auth_runtime_inputs import MarketplaceAuthenticationRuntimeInputs
from ..application.auth_startup_provisioning import (
    MarketplaceAuthenticationStartupProvisioning,
)
from ..application.postgres_state import Clock, ConnectionFactory
from .auth_application_v1 import build_reference_authenticated_marketplace_launch_plan
from .postgres_application_v1 import (
    build_reference_postgres_marketplace_application_launch_plan,
)

PROFILE_NAME: Final = "MARKETPLACE_REFERENCE_AUTHENTICATED_POSTGRES_APPLICATION_V1"


def build_reference_authenticated_postgres_marketplace_launch_plan(
    *,
    connection_factory: ConnectionFactory,
    clock: Clock,
    host: str,
    port: int,
    index_html: bytes,
    app_js: bytes,
    styles_css: bytes,
    provisioning: MarketplaceAuthenticationStartupProvisioning,
    runtime_inputs: MarketplaceAuthenticationRuntimeInputs,
) -> MarketplaceAuthenticatedLoopbackLaunchPlan:
    """Compose reviewed PostgreSQL and authentication layers without activating them."""

    application_plan = build_reference_postgres_marketplace_application_launch_plan(
        connection_factory=connection_factory,
        clock=clock,
        host=host,
        port=port,
        index_html=index_html,
        app_js=app_js,
        styles_css=styles_css,
    )
    return build_reference_authenticated_marketplace_launch_plan(
        application_plan=application_plan,
        provisioning=provisioning,
        runtime_inputs=runtime_inputs,
    )


__all__ = [
    "PROFILE_NAME",
    "build_reference_authenticated_postgres_marketplace_launch_plan",
]
