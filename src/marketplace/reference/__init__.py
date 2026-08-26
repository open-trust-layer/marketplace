"""Non-normative packaged Marketplace reference semantic adapters.

Importing this package requires the separately supplied Open Layer Protocol
reference implementation. The transport-neutral ``marketplace.runtime`` package
remains independent and does not import this package implicitly.
"""
from olp.encoding.record_identity import record_identity_text

from . import federation_v1
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
from .record_retrieval_v1 import (
    RetrievedRecordVerificationError,
    VerifiedRetrievedRecord,
    verify_retrieved_market_record,
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
    "MAX_DISCOVERY_RECORDS",
    "MarketplaceConformanceError",
    "MarketplaceDiscoveryError",
    "MarketplaceTransportJsonError",
    "PROPOSAL_PROFILE",
    "RECORD_TYPES",
    "RetrievedRecordVerificationError",
    "STRUCTURE_VALIDATORS",
    "TYPE_AGREEMENT",
    "TYPE_EVENT",
    "TYPE_INTENT",
    "VerifiedRetrievedRecord",
    "bind_cursor",
    "decode_transport_envelope_json",
    "encode_transport_envelope_json",
    "evaluate_discovery",
    "evaluate_match",
    "federation_v1",
    "merge_federated_views",
    "query_fingerprint",
    "record_identity_text",
    "validate_cursor_binding",
    "validate_discovery_query",
    "validate_market_record",
    "validate_ranked_view",
    "verify_index_entry",
    "verify_retrieved_market_record",
]
