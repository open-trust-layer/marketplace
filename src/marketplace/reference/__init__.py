"""Non-normative packaged Marketplace reference semantic adapters.

Importing this package requires the separately supplied Open Layer Protocol
reference implementation. The transport-neutral ``marketplace.runtime`` package
remains independent and does not import this package implicitly.
"""
from olp.encoding.record_identity import record_identity_text

from . import federation_v1
from .inbound_http_v1 import (
    decode_inbound_control_envelope_json,
    encode_prepared_inbound_response_json,
)
from .local_console_v1 import (
    LocalConsoleInteractionError,
    run_local_buy_sell_console,
)
from .local_demo_v1 import (
    LocalBuySellDemoError,
    LocalBuySellDemoResult,
    run_local_buy_sell_demo,
)
from .local_ui_http_v1 import (
    MAX_LOCAL_UI_HTTP_BODY_BYTES,
    LocalUiHttpError,
    LocalUiHttpRequest,
    LocalUiHttpResponse,
    handle_local_ui_http_request,
)
from .local_ui_loopback_client_v1 import (
    LOCAL_UI_LOOPBACK_CLIENT_EXECUTION_OPT_IN,
    LOCAL_UI_LOOPBACK_CLIENT_HOST,
    LocalUiLoopbackClientError,
    LocalUiLoopbackClientPlan,
    LocalUiLoopbackClientResult,
    plan_local_ui_loopback_client_once,
    run_local_ui_loopback_client_once,
)
from .local_ui_loopback_v1 import (
    LOCAL_UI_LOOPBACK_EXECUTION_OPT_IN,
    LOCAL_UI_LOOPBACK_HOST,
    LocalUiLoopbackError,
    LocalUiLoopbackPlan,
    LocalUiLoopbackResult,
    plan_local_ui_loopback_once,
    serve_local_ui_loopback_once,
)
from .local_visual_v1 import (
    LocalVisualInteractionError,
    LocalVisualSubmission,
    render_local_buy_sell_form,
    submit_local_buy_sell_form,
)
from .matching_v1 import (
    DEFAULT_MATCH_METHOD,
    DISCOVERY_SERVICE_TYPE,
    MAX_DISCOVERY_RECORDS,
    MarketplaceDiscoveryError,
    bind_cursor,
    evaluate_discovery,
    evaluate_match,
    merge_federated_views,
    query_fingerprint,
    validate_cursor_binding,
    validate_discovery_query,
    validate_ranked_view,
    verify_index_entry,
)
from .product_listing_v1 import (
    PRODUCT_LISTING_PROFILE,
    ProductListingProfileError,
    build_product_listing_record,
    extract_product_listing,
    validate_product_listing_record,
)
from .proposal_v1 import (
    ProposalProfileError,
    build_buyer_request_proposal_record,
)
from .record_retrieval_v1 import (
    RetrievedRecordVerificationError,
    VerifiedRetrievedRecord,
    verified_retrieved_market_record_value,
    verify_retrieved_market_record,
)
from .record_serving_v1 import (
    RecordServingReferenceError,
    make_record_transport_envelope,
    market_record_transport_payload,
    verify_prepared_record_transport_envelope,
)
from .record_v1 import (
    BASE,
    CORE_PROFILE,
    PROPOSAL_PROFILE,
    RECORD_TYPES,
    STRUCTURE_VALIDATORS,
    TYPE_AGREEMENT,
    TYPE_EVENT,
    TYPE_INTENT,
    MarketplaceConformanceError,
    validate_market_record,
)
from .web_map_v1 import render_product_listing_record_page
from .transport_json_v1 import (
    MarketplaceTransportJsonError,
    decode_transport_envelope_json,
    encode_transport_envelope_json,
)

__all__ = [
    "BASE",
    "CORE_PROFILE",
    "DEFAULT_MATCH_METHOD",
    "DISCOVERY_SERVICE_TYPE",
    "LOCAL_UI_LOOPBACK_CLIENT_EXECUTION_OPT_IN",
    "LOCAL_UI_LOOPBACK_CLIENT_HOST",
    "LOCAL_UI_LOOPBACK_EXECUTION_OPT_IN",
    "LOCAL_UI_LOOPBACK_HOST",
    "MAX_DISCOVERY_RECORDS",
    "MAX_LOCAL_UI_HTTP_BODY_BYTES",
    "LocalBuySellDemoError",
    "LocalBuySellDemoResult",
    "LocalConsoleInteractionError",
    "LocalUiHttpError",
    "LocalUiHttpRequest",
    "LocalUiHttpResponse",
    "LocalUiLoopbackClientError",
    "LocalUiLoopbackClientPlan",
    "LocalUiLoopbackClientResult",
    "LocalUiLoopbackError",
    "LocalUiLoopbackPlan",
    "LocalUiLoopbackResult",
    "LocalVisualInteractionError",
    "LocalVisualSubmission",
    "MarketplaceConformanceError",
    "MarketplaceDiscoveryError",
    "MarketplaceTransportJsonError",
    "PRODUCT_LISTING_PROFILE",
    "PROPOSAL_PROFILE",
    "ProductListingProfileError",
    "ProposalProfileError",
    "RECORD_TYPES",
    "RecordServingReferenceError",
    "RetrievedRecordVerificationError",
    "STRUCTURE_VALIDATORS",
    "TYPE_AGREEMENT",
    "TYPE_EVENT",
    "TYPE_INTENT",
    "VerifiedRetrievedRecord",
    "bind_cursor",
    "build_product_listing_record",
    "build_buyer_request_proposal_record",
    "decode_inbound_control_envelope_json",
    "decode_transport_envelope_json",
    "encode_prepared_inbound_response_json",
    "encode_transport_envelope_json",
    "evaluate_discovery",
    "evaluate_match",
    "extract_product_listing",
    "federation_v1",
    "handle_local_ui_http_request",
    "make_record_transport_envelope",
    "market_record_transport_payload",
    "merge_federated_views",
    "plan_local_ui_loopback_client_once",
    "plan_local_ui_loopback_once",
    "query_fingerprint",
    "record_identity_text",
    "render_local_buy_sell_form",
    "render_product_listing_record_page",
    "run_local_buy_sell_console",
    "run_local_buy_sell_demo",
    "run_local_ui_loopback_client_once",
    "serve_local_ui_loopback_once",
    "submit_local_buy_sell_form",
    "validate_cursor_binding",
    "validate_discovery_query",
    "validate_market_record",
    "validate_product_listing_record",
    "validate_ranked_view",
    "verified_retrieved_market_record_value",
    "verify_index_entry",
    "verify_prepared_record_transport_envelope",
    "verify_retrieved_market_record",
]
