"""Reference-layer binding for reviewed Marketplace application semantics.

This module only assembles an inert application launch plan. It performs no
initialization, filesystem discovery, environment loading, provider selection,
database connection, socket operation, or server execution.
"""
from __future__ import annotations

from ..application.api import IntentQueryPort
from ..application.launch import (
    MarketplaceApplicationLaunchPlan,
    build_marketplace_application_launch_plan,
)
from ..application.state import ApplicationStateStore
from .application_record_json_v1 import (
    decode_marketplace_application_record_json,
    encode_marketplace_application_record_json,
)
from .application_record_v1 import (
    decode_marketplace_application_record,
    is_marketplace_intent_record,
    marketplace_response_parent_ids,
    prepare_marketplace_application_record,
)
from .product_listing_v1 import build_product_listing_record
from .proposal_v1 import build_buyer_request_proposal_record


def build_reference_marketplace_application_launch_plan(
    *,
    host: str,
    port: int,
    store: ApplicationStateStore,
    intent_query: IntentQueryPort,
    index_html: bytes,
    app_js: bytes,
    styles_css: bytes,
) -> MarketplaceApplicationLaunchPlan:
    """Bind reviewed reference semantics without exercising runtime authority."""

    return build_marketplace_application_launch_plan(
        host=host,
        port=port,
        store=store,
        intent_query=intent_query,
        prepare_record=prepare_marketplace_application_record,
        decode_record=decode_marketplace_application_record,
        response_parent_ids=marketplace_response_parent_ids,
        is_intent_record=is_marketplace_intent_record,
        decode_record_json=decode_marketplace_application_record_json,
        encode_record_json=encode_marketplace_application_record_json,
        build_product_listing_record=build_product_listing_record,
        build_proposal_record=build_buyer_request_proposal_record,
        index_html=index_html,
        app_js=app_js,
        styles_css=styles_css,
    )


__all__ = ["build_reference_marketplace_application_launch_plan"]
