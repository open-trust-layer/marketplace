"""Inert PostgreSQL composition root for the reviewed Marketplace application.

This module binds the existing PostgreSQL state/query adapters into the existing
reference application launch plan. Construction performs no database connection,
migration, environment loading, filesystem access, provider selection, socket
operation, or server execution.
"""
from __future__ import annotations

from ..application.launch import MarketplaceApplicationLaunchPlan
from ..application.postgres_query import PostgresIntentQuery
from ..application.postgres_state import (
    Clock,
    ConnectionFactory,
    PostgresApplicationStateStore,
)
from .application_v1 import build_reference_marketplace_application_launch_plan


def build_reference_postgres_marketplace_application_launch_plan(
    *,
    connection_factory: ConnectionFactory,
    clock: Clock,
    host: str,
    port: int,
    index_html: bytes,
    app_js: bytes,
    styles_css: bytes,
) -> MarketplaceApplicationLaunchPlan:
    """Compose the reviewed PostgreSQL-backed reference graph without activating it."""

    store = PostgresApplicationStateStore(
        connection_factory=connection_factory,
        clock=clock,
    )
    intent_query = PostgresIntentQuery(
        connection_factory=connection_factory,
        clock=clock,
    )
    return build_reference_marketplace_application_launch_plan(
        host=host,
        port=port,
        store=store,
        intent_query=intent_query,
        index_html=index_html,
        app_js=app_js,
        styles_css=styles_css,
    )


__all__ = ["build_reference_postgres_marketplace_application_launch_plan"]
