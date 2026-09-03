"""Source-only Marketplace application composition without runtime ownership."""
from __future__ import annotations

from dataclasses import dataclass

from .api import (
    IntentQueryPort,
    IntentRecordPredicate,
    MarketplaceApplicationApiService,
    ResponseParentExtractor,
)
from .http import (
    MarketplaceApplicationHttpAdapter,
    RecordJsonDecoder,
    RecordJsonEncoder,
)
from .postgres_state import ExpiryResult
from .site_host import MarketplaceSiteHostAdapter
from .state import (
    ApplicationStateStore,
    MarketplaceApplicationStateService,
    RecordDecoder,
    RecordPreparer,
)


@dataclass(frozen=True, slots=True)
class MarketplaceApplicationComposition:
    """Inert object graph; initialization is explicit and runtime I/O is external."""

    state: MarketplaceApplicationStateService
    api: MarketplaceApplicationApiService
    http: MarketplaceApplicationHttpAdapter
    site: MarketplaceSiteHostAdapter

    def initialize(self) -> ExpiryResult:
        return self.api.initialize()


def compose_marketplace_application(
    *,
    store: ApplicationStateStore,
    intent_query: IntentQueryPort,
    prepare_record: RecordPreparer,
    decode_record: RecordDecoder,
    response_parent_ids: ResponseParentExtractor,
    is_intent_record: IntentRecordPredicate,
    decode_record_json: RecordJsonDecoder,
    encode_record_json: RecordJsonEncoder,
    index_html: bytes,
    app_js: bytes,
    styles_css: bytes,
) -> MarketplaceApplicationComposition:
    """Wire reviewed application layers from injected dependencies only."""

    state = MarketplaceApplicationStateService(
        store=store,
        prepare_record=prepare_record,
        decode_record=decode_record,
    )
    api = MarketplaceApplicationApiService(
        state=state,
        intent_query=intent_query,
        response_parent_ids=response_parent_ids,
        is_intent_record=is_intent_record,
    )
    http = MarketplaceApplicationHttpAdapter(
        api=api,
        decode_record_json=decode_record_json,
        encode_record_json=encode_record_json,
    )
    site = MarketplaceSiteHostAdapter(
        application_http=http,
        index_html=index_html,
        app_js=app_js,
        styles_css=styles_css,
    )
    return MarketplaceApplicationComposition(state=state, api=api, http=http, site=site)


__all__ = [
    "MarketplaceApplicationComposition",
    "compose_marketplace_application",
]
