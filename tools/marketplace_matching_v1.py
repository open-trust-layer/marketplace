"""Non-normative Marketplace matching and discovery v1 helpers.

The helpers standardize deterministic processing boundaries only. They do not
create a universal Match, ranking, recommendation, index, or market view.
"""
from __future__ import annotations

import base64
import hashlib
from collections import defaultdict
from itertools import islice
from typing import Any, Iterable, Mapping, Sequence

from olp import RecordV1
from olp.encoding.deterministic_cbor import encode as olp_encode
from olp.encoding.record_identity import record_identity_text
from olp.evidence import record_ref as olp_record_ref
from olp.errors import ConformanceError
from olp.model.evidence import EvidenceKind, EvidenceRefV1
from olp.transport import decode_identity_text
from olp.values import is_absolute_uri

from marketplace_record_v1 import (
    BASE,
    TYPE_INTENT,
    MarketplaceConformanceError,
    validate_market_record,
)

DISCOVERY_SERVICE_TYPE = f"{BASE}/service/market-discovery"
DEFAULT_MATCH_METHOD = f"{BASE}/matching/method/example-exact-v1"
MAX_QUERY_VALUES = 64
MAX_DISCOVERY_RECORDS = 10_000
QUERY_FIELDS = {
    "version",
    "profiles_all",
    "issuer_principals_any",
    "action_ids_any",
    "subject_uris_any",
}
COMPLETENESS_VALUES = {
    "COMPLETE_FOR_DECLARED_SOURCE",
    "PARTIAL_SOURCE",
    "UNKNOWN_SOURCE",
}
FRESHNESS_VALUES = {"FRESH", "STALE", "HISTORICAL", "UNKNOWN", "NOT_APPLICABLE"}
OBSERVATION_STATUSES = {"SATISFIED", "UNSATISFIED", "UNKNOWN", "UNSUPPORTED", "NOT_EVALUATED"}
BASE_MATCH_STATUSES = {"SATISFIED", "UNSATISFIED", "UNKNOWN", "UNSUPPORTED"}


class MarketplaceDiscoveryError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def fail(code: str, message: str) -> None:
    raise MarketplaceDiscoveryError(code, message)
def _require_uri(value: Any, path: str) -> str:
    if not isinstance(value, str) or not is_absolute_uri(value):
        fail("INVALID_URI", f"{path} MUST be an absolute URI")
    return value


def _record_ref_from_value(value: Any, path: str) -> EvidenceRefV1:
    try:
        ref = EvidenceRefV1.from_value(value)
    except ConformanceError as exc:
        fail("INVALID_RECORD_REF", f"{path}: {exc}")
    if ref.kind != EvidenceKind.RECORD:
        fail("WRONG_REFERENCE_KIND", f"{path} MUST reference an OLP Record")
    return ref


def _sorted_unique_uri_values(value: Any, path: str) -> tuple[str, ...]:
    if not isinstance(value, (tuple, list)) or not value:
        fail("INVALID_QUERY", f"{path} MUST be a non-empty array")
    if len(value) > MAX_QUERY_VALUES:
        fail("RESOURCE_LIMIT_EXCEEDED", f"{path} exceeds {MAX_QUERY_VALUES} values")
    items = tuple(_require_uri(item, f"{path}[]") for item in value)
    expected = tuple(sorted(set(items), key=lambda item: item.encode("utf-8")))
    if items != expected:
        fail("NONCANONICAL_QUERY_SET", f"{path} MUST be unique and UTF-8 sorted")
    return items
def validate_discovery_query(query: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(query, Mapping):
        fail("INVALID_QUERY", "DiscoveryQueryV1 MUST be a map")
    unknown = set(query) - QUERY_FIELDS
    if unknown:
        fail("UNKNOWN_QUERY_FIELD", "unknown DiscoveryQueryV1 field(s): " + ", ".join(sorted(unknown)))
    if query.get("version") != 1:
        fail("UNSUPPORTED_QUERY_VERSION", "DiscoveryQueryV1.version MUST equal 1")

    normalized: dict[str, Any] = {"version": 1}
    for field in ("profiles_all", "issuer_principals_any", "action_ids_any", "subject_uris_any"):
        if field in query:
            normalized[field] = _sorted_unique_uri_values(query[field], field)
    return normalized


def query_fingerprint(query: Mapping[str, Any]) -> str:
    normalized = validate_discovery_query(query)
    digest = hashlib.sha256(olp_encode(normalized)).digest()
    return base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")


def _subject_uris(record: RecordV1) -> set[str]:
    return {
        item["uri"]
        for item in record.content.get("subjects", ())
        if isinstance(item, Mapping) and isinstance(item.get("uri"), str)
    }
def _matches_query(record: RecordV1, query: Mapping[str, Any]) -> bool:
    if record.type != TYPE_INTENT:
        return False
    content = record.content
    profiles_all = query.get("profiles_all")
    if profiles_all and not set(profiles_all).issubset(set(record.profiles)):
        return False
    issuers = query.get("issuer_principals_any")
    if issuers and content["issuer"]["principal"] not in set(issuers):
        return False
    actions = query.get("action_ids_any")
    if actions and content["action"]["id"] not in set(actions):
        return False
    subjects = query.get("subject_uris_any")
    if subjects and not (_subject_uris(record) & set(subjects)):
        return False
    return True


def evaluate_discovery(
    records: Iterable[RecordV1],
    query: Mapping[str, Any],
    *,
    source: str,
    completeness: str,
    freshness: str,
    max_records: int = MAX_DISCOVERY_RECORDS,
) -> dict[str, Any]:
    source = _require_uri(source, "source")
    normalized = validate_discovery_query(query)
    if completeness not in COMPLETENESS_VALUES:
        fail("INVALID_COMPLETENESS", "invalid discovery completeness value")
    if freshness not in FRESHNESS_VALUES:
        fail("INVALID_FRESHNESS", "invalid discovery freshness value")
    if not isinstance(max_records, int) or isinstance(max_records, bool) or max_records < 1:
        fail("INVALID_RESOURCE_LIMIT", "max_records MUST be a positive integer")
    supplied = tuple(islice(records, max_records + 1))
    if len(supplied) > max_records:
        fail("RESOURCE_LIMIT_EXCEEDED", "discovery source exceeds configured record limit")

    matched: dict[str, RecordV1] = {}
    malformed = 0
    for record in supplied:
        try:
            validate_market_record(record)
        except (MarketplaceConformanceError, ConformanceError):
            malformed += 1
            continue
        if _matches_query(record, normalized):
            identity = record_identity_text(record)
            prior = matched.get(identity)
            if prior is not None and prior != record:
                fail("IDENTITY_COLLISION_OR_CONFLICT", "conflicting records share an OLP Record Identity")
            matched[identity] = record

    result_ids = sorted(matched)
    return {
        "service_type": DISCOVERY_SERVICE_TYPE,
        "source": source,
        "query_fingerprint": query_fingerprint(normalized),
        "result_refs": result_ids,
        "result_count": len(result_ids),
        "nonconforming_candidates_ignored": malformed,
        "completeness": completeness,
        "freshness": freshness,
        "global_completeness": "UNKNOWN",
        "absence_is_negative_evidence": False,
        "ordering": "REPRODUCIBLE_IDENTITY_ORDER_NOT_RANKING",
    }


def verify_index_entry(entry: Mapping[str, Any], record: RecordV1) -> dict[str, Any]:
    if not isinstance(entry, Mapping):
        fail("INVALID_INDEX_ENTRY", "index entry MUST be a map")
    allowed = {"record_ref", "issuer", "action", "profiles"}
    unknown = set(entry) - allowed
    if unknown:
        fail("UNKNOWN_INDEX_FIELD", "unknown verified index field(s): " + ", ".join(sorted(unknown)))
    validate_market_record(record)
    if record.type != TYPE_INTENT:
        fail("INTENT_REQUIRED", "verified discovery index entry currently targets MarketIntent")
    if "record_ref" not in entry:
        fail("INDEX_RECORD_REF_REQUIRED", "verified index entry requires record_ref")
    claimed = _record_ref_from_value(entry["record_ref"], "record_ref")
    actual = olp_record_ref(record)
    if claimed != actual:
        fail("INDEX_IDENTITY_MISMATCH", "index record_ref does not match supplied Record Identity")
    content = record.content
    if "issuer" in entry and entry["issuer"] != content["issuer"]["principal"]:
        fail("INDEX_PROJECTION_MISMATCH", "index issuer differs from authenticated record")
    if "action" in entry and entry["action"] != content["action"]["id"]:
        fail("INDEX_PROJECTION_MISMATCH", "index action differs from authenticated record")
    if "profiles" in entry and tuple(entry["profiles"]) != tuple(record.profiles):
        fail("INDEX_PROJECTION_MISMATCH", "index profiles differ from authenticated record")
    return {
        "record": record_identity_text(record),
        "status": "VERIFIED_AGAINST_RECORD",
        "index_metadata_is_authoritative": False,
    }


def _constraint_key(side: str, constraint: Mapping[str, Any]) -> tuple[str, bytes]:
    if side not in {"left", "right"}:
        fail("INVALID_MATCH_OBSERVATION", "constraint observation side MUST be left or right")
    return side, olp_encode(constraint)


def _constraint_inventory(record: RecordV1, side: str) -> dict[tuple[str, bytes], Mapping[str, Any]]:
    inventory: dict[tuple[str, bytes], Mapping[str, Any]] = {}
    for constraint in record.content.get("constraints", ()):
        inventory[_constraint_key(side, constraint)] = constraint
    return inventory


def evaluate_match(
    left: RecordV1,
    right: RecordV1,
    *,
    method: str,
    base_status: str,
    observations: Sequence[Mapping[str, Any]],
    evidence_completeness: str,
    understood_critical: Iterable[str] = (),
) -> dict[str, Any]:
    validate_market_record(left)
    validate_market_record(right)
    if left.type != TYPE_INTENT or right.type != TYPE_INTENT:
        fail("INTENT_REQUIRED", "matching evaluation requires two MarketIntent records")
    method = _require_uri(method, "method")
    if base_status not in BASE_MATCH_STATUSES:
        fail("INVALID_BASE_MATCH_STATUS", "unsupported base matching status")
    if evidence_completeness not in {"COMPLETE_FOR_METHOD_INPUTS", "INCOMPLETE", "UNKNOWN"}:
        fail("INVALID_EVIDENCE_COMPLETENESS", "invalid match evidence completeness")
    understood_values = tuple(islice(understood_critical, MAX_QUERY_VALUES + 1))
    if len(understood_values) > MAX_QUERY_VALUES:
        fail("RESOURCE_LIMIT_EXCEEDED", "understood_critical exceeds supported cardinality")
    understood = {_require_uri(uri, "understood_critical[]") for uri in understood_values}
    required_critical = set(left.content.get("critical", ())) | set(right.content.get("critical", ()))
    unsupported_critical = sorted(required_critical - understood, key=lambda item: item.encode("utf-8"))
    inventory = {}
    inventory.update(_constraint_inventory(left, "left"))
    inventory.update(_constraint_inventory(right, "right"))
    seen: set[tuple[str, bytes]] = set()
    statuses: dict[tuple[str, bytes], str] = {}
    preference_unknown = 0

    for item in observations:
        if not isinstance(item, Mapping) or set(item) != {"side", "constraint", "status"}:
            fail("INVALID_MATCH_OBSERVATION", "match observation MUST contain side, constraint, status")
        if not isinstance(item["constraint"], Mapping):
            fail("INVALID_MATCH_OBSERVATION", "observation constraint MUST be a map")
        key = _constraint_key(item["side"], item["constraint"])
        if key not in inventory:
            fail("OBSERVATION_CONSTRAINT_NOT_FOUND", "observation does not reference an exact constraint in the selected Intent")
        if key in seen:
            fail("DUPLICATE_MATCH_OBSERVATION", "duplicate constraint observation")
        status = item["status"]
        if status not in OBSERVATION_STATUSES:
            fail("INVALID_MATCH_OBSERVATION", "unsupported constraint observation status")
        seen.add(key)
        statuses[key] = status
    mandatory_unsatisfied = 0
    mandatory_unknown = 0
    preferred_unsatisfied = 0
    for key, constraint in inventory.items():
        mode = constraint["mode"]
        status = statuses.get(key, "NOT_EVALUATED")
        if mode == "mandatory":
            if status == "UNSATISFIED":
                mandatory_unsatisfied += 1
            elif status != "SATISFIED":
                mandatory_unknown += 1
        elif mode in {"preferred", "negotiable", "informational"}:
            if status == "UNSATISFIED":
                preferred_unsatisfied += 1
            elif status in {"UNKNOWN", "UNSUPPORTED", "NOT_EVALUATED"}:
                preference_unknown += 1

    if base_status == "UNSATISFIED" or mandatory_unsatisfied:
        conclusion = "INCOMPATIBLE_UNDER_METHOD"
    elif base_status in {"UNKNOWN", "UNSUPPORTED"} or unsupported_critical:
        conclusion = "INDETERMINATE"
    elif evidence_completeness != "COMPLETE_FOR_METHOD_INPUTS" or mandatory_unknown:
        conclusion = "INDETERMINATE"
    else:
        conclusion = "COMPATIBLE_UNDER_METHOD"
    return {
        "left": record_identity_text(left),
        "right": record_identity_text(right),
        "method": method,
        "base_status": base_status,
        "evidence_completeness": evidence_completeness,
        "mandatory_unsatisfied": mandatory_unsatisfied,
        "mandatory_unknown": mandatory_unknown,
        "preferred_unsatisfied": preferred_unsatisfied,
        "preference_unknown": preference_unknown,
        "unsupported_critical_semantics": unsupported_critical,
        "conclusion": conclusion,
        "protocol_truth": False,
        "creates_agreement": False,
    }


def validate_ranked_view(method: str, record_refs: Sequence[Any]) -> dict[str, Any]:
    method = _require_uri(method, "ranking method")
    refs = tuple(_record_ref_from_value(item, "record_refs[]") for item in record_refs)
    if not refs:
        fail("EMPTY_RANKING", "ranked view MUST contain at least one RecordRef")
    if len(set(refs)) != len(refs):
        fail("DUPLICATE_RANKED_RESULT", "ranked view MUST NOT repeat a RecordRef")
    return {
        "method": method,
        "ordered_refs": [record_identity_text(ref.identity_digest) for ref in refs],
        "canonical": False,
        "protocol_truth": False,
    }


def _validate_discovery_view(view: Mapping[str, Any]) -> tuple[str, str, tuple[str, ...]]:
    required = {
        "service_type", "source", "query_fingerprint", "result_refs", "result_count",
        "completeness", "freshness", "global_completeness", "absence_is_negative_evidence",
    }
    if not isinstance(view, Mapping) or not required.issubset(view):
        fail("INVALID_DISCOVERY_VIEW", "discovery view is missing required processing metadata")
    if view["service_type"] != DISCOVERY_SERVICE_TYPE:
        fail("INVALID_DISCOVERY_VIEW", "federated view has wrong service type")
    source = _require_uri(view["source"], "view.source")
    fingerprint = view["query_fingerprint"]
    if not isinstance(fingerprint, str) or not fingerprint:
        fail("INVALID_DISCOVERY_VIEW", "query_fingerprint MUST be non-empty text")
    if view["completeness"] not in COMPLETENESS_VALUES or view["freshness"] not in FRESHNESS_VALUES:
        fail("INVALID_DISCOVERY_VIEW", "discovery view has invalid completeness or freshness")
    if view["global_completeness"] != "UNKNOWN":
        fail("GLOBAL_COMPLETENESS_FORBIDDEN", "a discovery source MUST NOT claim global completeness")
    if view["absence_is_negative_evidence"] is not False:
        fail("NEGATIVE_ABSENCE_FORBIDDEN", "discovery absence MUST NOT become negative evidence")
    refs = tuple(view["result_refs"])
    if view["result_count"] != len(refs) or len(refs) != len(set(refs)):
        fail("INVALID_DISCOVERY_VIEW", "result_count and unique result_refs MUST agree")
    for identity in refs:
        try:
            decode_identity_text(identity, expected_kind="record")
        except ConformanceError as exc:
            fail("INVALID_DISCOVERY_VIEW", f"result identity MUST be canonical OLP r1_ presentation: {exc}")
    return source, fingerprint, refs


def merge_federated_views(views: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    if not views:
        fail("EMPTY_FEDERATION", "federation merge requires at least one discovery view")
    sources_by_ref: dict[str, set[str]] = defaultdict(set)
    query_fingerprints: set[str] = set()
    for view in views:
        source, fingerprint, refs = _validate_discovery_view(view)
        query_fingerprints.add(fingerprint)
        for identity in refs:
            sources_by_ref[identity].add(source)
    if len(query_fingerprints) != 1:
        fail("FEDERATION_QUERY_MISMATCH", "federated views MUST represent the same normalized query")
    ordered = sorted(sources_by_ref)
    return {
        "query_fingerprint": next(iter(query_fingerprints)),
        "result_refs": ordered,
        "result_count": len(ordered),
        "sources_by_ref": {identity: sorted(sources_by_ref[identity]) for identity in ordered},
        "global_completeness": "UNKNOWN",
        "canonical_ranking": False,
        "absence_is_negative_evidence": False,
    }


def bind_cursor(
    *,
    source: str,
    method: str,
    query: Mapping[str, Any],
    cursor: bytes,
) -> dict[str, Any]:
    source = _require_uri(source, "cursor source")
    method = _require_uri(method, "cursor method")
    if not isinstance(cursor, bytes) or not cursor or len(cursor) > 4096:
        fail("INVALID_CURSOR", "cursor MUST be 1..4096 opaque bytes")
    return {
        "source": source,
        "method": method,
        "query_fingerprint": query_fingerprint(query),
        "cursor": cursor,
    }


def validate_cursor_binding(
    binding: Mapping[str, Any],
    *,
    source: str,
    method: str,
    query: Mapping[str, Any],
) -> str:
    if not isinstance(binding, Mapping) or set(binding) != {"source", "method", "query_fingerprint", "cursor"}:
        fail("INVALID_CURSOR_BINDING", "cursor binding has an invalid shape")
    if binding["source"] != _require_uri(source, "cursor source"):
        fail("CURSOR_SOURCE_MISMATCH", "cursor is bound to another discovery source")
    if binding["method"] != _require_uri(method, "cursor method"):
        fail("CURSOR_METHOD_MISMATCH", "cursor is bound to another discovery method")
    if binding["query_fingerprint"] != query_fingerprint(query):
        fail("CURSOR_QUERY_MISMATCH", "cursor is bound to another discovery query")
    cursor = binding["cursor"]
    if not isinstance(cursor, bytes) or not cursor or len(cursor) > 4096:
        fail("INVALID_CURSOR", "cursor MUST be 1..4096 opaque bytes")
    return "CURSOR_BOUND_TO_SOURCE_METHOD_QUERY"
