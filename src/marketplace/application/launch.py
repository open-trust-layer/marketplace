"""Inert loopback-only launch plan for the reviewed Marketplace application graph."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from .api import IntentQueryPort, IntentRecordPredicate, ResponseParentExtractor
from .asgi import MarketplaceAsgiHttpAdapter
from .authoring import ProductListingRecordBuilder
from .composition import MarketplaceApplicationComposition, compose_marketplace_application
from .http import RecordJsonDecoder, RecordJsonEncoder
from .proposal_authoring import ProposalRecordBuilder
from .state import ApplicationStateStore, RecordDecoder, RecordPreparer


LOOPBACK_LAUNCH_HOST: Final = "127.0.0.1"
MIN_LAUNCH_PORT: Final = 1
MAX_LAUNCH_PORT: Final = 65535


@dataclass(frozen=True, slots=True)
class MarketplaceApplicationLaunchPlan:
    """Immutable source-only plan; host/port are metadata, not active authority."""

    host: str
    port: int
    composition: MarketplaceApplicationComposition
    asgi: MarketplaceAsgiHttpAdapter


def _validate_host(host: str) -> str:
    if type(host) is not str:
        raise TypeError("launch host must be an exact string")
    if host != LOOPBACK_LAUNCH_HOST:
        raise ValueError("launch host must be exact IPv4 loopback")
    return host


def _validate_port(port: int) -> int:
    if type(port) is not int:
        raise TypeError("launch port must be an exact integer")
    if port < MIN_LAUNCH_PORT or port > MAX_LAUNCH_PORT:
        raise ValueError("launch port is outside the reviewed TCP range")
    return port


def build_marketplace_application_launch_plan(
    *,
    host: str,
    port: int,
    store: ApplicationStateStore,
    intent_query: IntentQueryPort,
    prepare_record: RecordPreparer,
    decode_record: RecordDecoder,
    response_parent_ids: ResponseParentExtractor,
    is_intent_record: IntentRecordPredicate,
    decode_record_json: RecordJsonDecoder,
    encode_record_json: RecordJsonEncoder,
    build_product_listing_record: ProductListingRecordBuilder,
    build_proposal_record: ProposalRecordBuilder,
    index_html: bytes,
    app_js: bytes,
    styles_css: bytes,
) -> MarketplaceApplicationLaunchPlan:
    """Compose existing reviewed surfaces without initialization or external I/O."""

    validated_host = _validate_host(host)
    validated_port = _validate_port(port)
    composition = compose_marketplace_application(
        store=store,
        intent_query=intent_query,
        prepare_record=prepare_record,
        decode_record=decode_record,
        response_parent_ids=response_parent_ids,
        is_intent_record=is_intent_record,
        decode_record_json=decode_record_json,
        encode_record_json=encode_record_json,
        build_product_listing_record=build_product_listing_record,
        build_proposal_record=build_proposal_record,
        index_html=index_html,
        app_js=app_js,
        styles_css=styles_css,
    )
    asgi = MarketplaceAsgiHttpAdapter(site=composition.site)
    return MarketplaceApplicationLaunchPlan(
        host=validated_host,
        port=validated_port,
        composition=composition,
        asgi=asgi,
    )


__all__ = [
    "LOOPBACK_LAUNCH_HOST",
    "MAX_LAUNCH_PORT",
    "MIN_LAUNCH_PORT",
    "MarketplaceApplicationLaunchPlan",
    "build_marketplace_application_launch_plan",
]
