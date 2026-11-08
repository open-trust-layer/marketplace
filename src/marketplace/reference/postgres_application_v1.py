"""Inert PostgreSQL composition root for the reviewed Marketplace application.

This module binds the existing PostgreSQL state/query adapters into the existing
reference application launch plan. Construction performs no database connection,
migration, environment loading, filesystem access, provider selection, socket
operation, or server execution.
"""
from __future__ import annotations

from ..application.http import MvpFlightRunner
from ..application.launch import MarketplaceApplicationLaunchPlan
from ..application.postgres_query import PostgresIntentQuery
from ..application.root_intent_filter import MarketplaceRootIntentQueryFilter
from ..application.postgres_state import (
    Clock,
    ConnectionFactory,
    PostgresApplicationStateStore,
)
from .application_record_v1 import (
    decode_marketplace_application_record,
    is_marketplace_intent_record,
)
from .application_v1 import build_reference_marketplace_application_launch_plan


def build_reference_postgres_marketplace_application_launch_plan(
    *,
    connection_factory: ConnectionFactory,
    clock: Clock,
    host: str,
    port: int,
    run_mvp_flight: MvpFlightRunner | None = None,
    index_html: bytes,
    app_js: bytes,
    styles_css: bytes,
    web_modules: tuple[tuple[str, bytes], ...] = (),
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
    # Type is intentionally absent from the original PostgreSQL record table.
    # The raw root index therefore contains acceptance events and Agreements as
    # well as genuine Intents. Inspect read-only canonical records before
    # exposing the root index to browsers, including historical persisted data.
    def is_root_intent(record_id: str) -> bool:
        prepared = store.peek(record_id)
        return prepared is not None and is_marketplace_intent_record(
            decode_marketplace_application_record(prepared.canonical_record)
        )

    filtered_query = MarketplaceRootIntentQueryFilter(
        root_query=intent_query,
        is_root_intent=is_root_intent,
    )
    return build_reference_marketplace_application_launch_plan(
        host=host,
        port=port,
        store=store,
        intent_query=filtered_query,
        run_mvp_flight=run_mvp_flight,
        index_html=index_html,
        app_js=app_js,
        styles_css=styles_css,
        web_modules=web_modules,
    )


__all__ = ["build_reference_postgres_marketplace_application_launch_plan"]
