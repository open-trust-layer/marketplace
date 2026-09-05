"""Source-only Marketplace application composition without runtime ownership."""
from __future__ import annotations

from dataclasses import dataclass

from .api import (
    IntentQueryPort,
    IntentRecordPredicate,
    MarketplaceApplicationApiService,
    ResponseParentExtractor,
)
from .authoring import (
    MarketplaceProductListingAuthoringService,
    ProductListingRecordBuilder,
)
from .http import (
    MarketplaceApplicationHttpAdapter,
    RecordJsonDecoder,
    RecordJsonEncoder,
)
from .proposal_authoring import MarketplaceProposalAuthoringService, ProposalRecordBuilder
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
    authoring: MarketplaceProductListingAuthoringService
    proposal_authoring: MarketplaceProposalAuthoringService
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
    build_product_listing_record: ProductListingRecordBuilder,
    build_proposal_record: ProposalRecordBuilder,
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
    authoring = MarketplaceProductListingAuthoringService(
        api=api,
        build_record=build_product_listing_record,
    )
    proposal_authoring = MarketplaceProposalAuthoringService(
        api=api,
        build_record=build_proposal_record,
    )
    http = MarketplaceApplicationHttpAdapter(
        api=api,
        decode_record_json=decode_record_json,
        encode_record_json=encode_record_json,
        create_product_listing=authoring.create_product_listing,
        create_proposal=proposal_authoring.create_buyer_request_proposal,
    )
    site = MarketplaceSiteHostAdapter(
        application_http=http,
        index_html=index_html,
        app_js=app_js,
        styles_css=styles_css,
    )
    return MarketplaceApplicationComposition(
        state=state,
        api=api,
        authoring=authoring,
        proposal_authoring=proposal_authoring,
        http=http,
        site=site,
    )


__all__ = [
    "MarketplaceApplicationComposition",
    "compose_marketplace_application",
]
