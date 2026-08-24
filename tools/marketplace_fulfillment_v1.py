"""Non-normative Marketplace fulfillment and performance v1 helpers.

The helpers evaluate method-relative evidence over immutable Agreements and
MarketEvents. They do not create universal fulfillment, completion, or truth.
"""
from __future__ import annotations

from dataclasses import dataclass
from itertools import islice
from typing import Any, Iterable, Mapping, Sequence

from olp import RecordV1
from olp.encoding.deterministic_cbor import encode as olp_encode
from olp.encoding.record_identity import record_identity_text
from olp.evidence import parse_relationship_record, record_ref as olp_record_ref
from olp.errors import ConformanceError, UnsupportedFeatureError
from olp.model.evidence import EvidenceKind, EvidenceRefV1
from olp.values import is_absolute_uri

from marketplace_record_v1 import (
    BASE,
    TYPE_AGREEMENT,
    TYPE_EVENT,
    validate_market_record,
)
EVENT_COMMITMENT_PERFORMANCE = f"{BASE}/event/commitment-performance"
EVENT_COMMITMENT_DELIVERY = f"{BASE}/event/commitment-delivery"
EVENT_COMMITMENT_INSPECTION = f"{BASE}/event/commitment-inspection"
EVENT_COMMITMENT_ACCEPTANCE = f"{BASE}/event/commitment-acceptance"
EVENT_COMMITMENT_REJECTION = f"{BASE}/event/commitment-rejection"
EVENT_COMMITMENT_COMPLETION = f"{BASE}/event/commitment-completion-assertion"
EVENT_COMMITMENT_FAILURE = f"{BASE}/event/commitment-failure-assertion"

OUTCOME_PERFORMANCE_PARTIAL = f"{BASE}/outcome/performance-partial"
OUTCOME_PERFORMANCE_CLAIMED_COMPLETE = f"{BASE}/outcome/performance-claimed-complete"
OUTCOME_CRITERION_OBSERVATION = f"{BASE}/outcome/acceptance-criterion-observation"

FULFILLMENT_METHOD_CORE = f"{BASE}/fulfillment/method/core-acceptance-v1"
CRITERION_STATUSES = {"SATISFIED", "UNSATISFIED", "UNKNOWN", "UNSUPPORTED"}
FULFILLMENT_EVENTS = {
    EVENT_COMMITMENT_PERFORMANCE,
    EVENT_COMMITMENT_DELIVERY,
    EVENT_COMMITMENT_INSPECTION,
    EVENT_COMMITMENT_ACCEPTANCE,
    EVENT_COMMITMENT_REJECTION,
    EVENT_COMMITMENT_COMPLETION,
    EVENT_COMMITMENT_FAILURE,
}
MAX_EVIDENCE_ITEMS = 4096
MAX_UNDERSTOOD_CRITICAL = 128


class MarketplaceFulfillmentError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def fail(code: str, message: str) -> None:
    raise MarketplaceFulfillmentError(code, message)


@dataclass(frozen=True)
class EventEvidence:
    record: RecordV1
    attribution_accepted: bool
    authority_accepted: bool

    @property
    def accepted_for_method(self) -> bool:
        return self.attribution_accepted and self.authority_accepted


@dataclass(frozen=True)
class RelationshipEvidence:
    record: RecordV1
    accepted_for_method: bool


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


def _bounded_tuple(values: Iterable[Any], limit: int, code: str) -> tuple[Any, ...]:
    if not isinstance(limit, int) or isinstance(limit, bool) or limit < 1:
        fail("INVALID_RESOURCE_LIMIT", "resource limit MUST be a positive integer")
    items = tuple(islice(values, limit + 1))
    if len(items) > limit:
        fail(code, f"evidence exceeds configured limit {limit}")
    return items


def _agreement_commitment(agreement: RecordV1, commitment_id: str) -> Mapping[str, Any]:
    validate_market_record(agreement)
    if agreement.type != TYPE_AGREEMENT:
        fail("AGREEMENT_REQUIRED", "fulfillment evaluation requires MarketAgreement")
    if not isinstance(commitment_id, str) or not commitment_id:
        fail("COMMITMENT_ID_REQUIRED", "commitment_id MUST be non-empty text")
    for commitment in agreement.content["commitments"]:
        if commitment["id"] == commitment_id:
            return commitment
    fail("COMMITMENT_NOT_FOUND", "commitment_id is not present in the Agreement")


def _event_commitment_target(event: RecordV1) -> tuple[EvidenceRefV1, str]:
    refs = tuple(event.content.get("commitment_refs", ()))
    if len(refs) != 1:
        fail("FULFILLMENT_EVENT_TARGET", "fulfillment event MUST target exactly one CommitmentRef")
    item = refs[0]
    if not isinstance(item, Mapping) or set(item) != {"record", "id"}:
        fail("FULFILLMENT_EVENT_TARGET", "commitment target MUST use CommitmentRefV1")
    return _record_ref_from_value(item["record"], "commitment_ref.record"), item["id"]


def _criterion_observation(event: RecordV1, commitment: Mapping[str, Any]) -> tuple[bytes, str]:
    outcome = event.content.get("outcome")
    if not isinstance(outcome, Mapping) or outcome.get("type") != OUTCOME_CRITERION_OBSERVATION:
        fail("INSPECTION_OUTCOME_REQUIRED", "inspection event requires criterion-observation outcome")
    details = outcome.get("details")
    if not isinstance(details, Mapping):
        fail("INVALID_CRITERION_OBSERVATION", "criterion observation details MUST be a map")
    if set(details) - {"criterion", "status", "details"} or not {"criterion", "status"}.issubset(details):
        fail("INVALID_CRITERION_OBSERVATION", "criterion observation has invalid fields")
    criterion = details["criterion"]
    criteria = tuple(commitment.get("acceptance_criteria", ()))
    if criterion not in criteria:
        fail("CRITERION_NOT_FOUND", "inspection observation MUST reference an exact AcceptanceCriterionV1")
    status = details["status"]
    if status not in CRITERION_STATUSES:
        fail("INVALID_CRITERION_STATUS", "unsupported criterion observation status")
    return olp_encode(criterion), status


def validate_fulfillment_event(
    event: RecordV1,
    agreement: RecordV1,
    commitment_id: str,
) -> dict[str, Any]:
    commitment = _agreement_commitment(agreement, commitment_id)
    validate_market_record(event)
    if event.type != TYPE_EVENT:
        fail("MARKET_EVENT_REQUIRED", "fulfillment evidence MUST be a MarketEvent")
    event_type = event.content["event"]
    if event_type not in FULFILLMENT_EVENTS:
        fail("UNSUPPORTED_FULFILLMENT_EVENT", "event is not a core fulfillment event")
    ref, local_id = _event_commitment_target(event)
    if ref != olp_record_ref(agreement) or local_id != commitment_id:
        fail("FULFILLMENT_EVENT_TARGET", "event targets a different Agreement commitment")

    performer = commitment["party"]["principal"]
    if event_type in {EVENT_COMMITMENT_PERFORMANCE, EVENT_COMMITMENT_DELIVERY}:
        if event.content["issuer"]["principal"] != performer:
            fail("PERFORMER_MISMATCH", "performance/delivery assertion issuer MUST equal the commitment party")
        outcome = event.content.get("outcome")
        if not isinstance(outcome, Mapping) or outcome.get("type") not in {
            OUTCOME_PERFORMANCE_PARTIAL,
            OUTCOME_PERFORMANCE_CLAIMED_COMPLETE,
        }:
            fail("PERFORMANCE_EXTENT_REQUIRED", "performance/delivery assertion requires partial or claimed-complete outcome")

    criterion = None
    if event_type == EVENT_COMMITMENT_INSPECTION:
        criterion = _criterion_observation(event, commitment)
    return {
        "event": event_type,
        "record": record_identity_text(event),
        "commitment_id": commitment_id,
        "issuer": event.content["issuer"]["principal"],
        "criterion_observation": criterion,
    }


def _critical_uris(record: RecordV1) -> set[str]:
    values = record.content.get("critical", ())
    return set(values) if isinstance(values, (tuple, list)) else set()


def _accepted_disputes(
    relationships: Iterable[RelationshipEvidence],
    event_ids: set[str],
    *,
    max_items: int,
) -> set[str]:
    disputed: set[str] = set()
    for item in _bounded_tuple(relationships, max_items, "RESOURCE_LIMIT_EXCEEDED"):
        if not isinstance(item.accepted_for_method, bool):
            fail("INVALID_EVIDENCE_ACCEPTANCE", "relationship acceptance MUST be boolean")
        try:
            statement = parse_relationship_record(item.record)
        except (ConformanceError, UnsupportedFeatureError) as exc:
            fail("INVALID_OLP_RELATIONSHIP", f"invalid OLP relationship: {exc}")
        if statement.relation_type != "disputes" or not item.accepted_for_method:
            continue
        for target in statement.objects:
            if target.kind == EvidenceKind.RECORD:
                identity = record_identity_text(target.identity_digest)
                if identity in event_ids:
                    disputed.add(identity)
    return disputed


def evaluate_commitment_fulfillment(
    agreement: RecordV1,
    commitment_id: str,
    evidence: Iterable[EventEvidence],
    *,
    method: str = FULFILLMENT_METHOD_CORE,
    require_acceptance: bool = True,
    understood_critical: Iterable[str] = (),
    disputes: Iterable[RelationshipEvidence] = (),
    max_evidence: int = MAX_EVIDENCE_ITEMS,
) -> dict[str, Any]:
    commitment = _agreement_commitment(agreement, commitment_id)
    method = _require_uri(method, "method")
    if method != FULFILLMENT_METHOD_CORE:
        fail("UNSUPPORTED_FULFILLMENT_METHOD", "reference evaluator implements only core-acceptance-v1")
    if not isinstance(require_acceptance, bool):
        fail("INVALID_METHOD_CONFIGURATION", "require_acceptance MUST be boolean")

    understood_values = _bounded_tuple(
        understood_critical,
        MAX_UNDERSTOOD_CRITICAL,
        "RESOURCE_LIMIT_EXCEEDED",
    )
    understood = {_require_uri(uri, "understood_critical[]") for uri in understood_values}
    required_critical = _critical_uris(agreement)

    accepted_events: list[RecordV1] = []
    accepted_event_ids: set[str] = set()
    ignored_nonfulfillment = 0
    rejected_by_method = 0
    criterion_statuses: dict[bytes, set[str]] = {}
    duplicate_event_count = 0
    seen_evidence_context: dict[str, tuple[bool, bool]] = {}

    for item in _bounded_tuple(evidence, max_evidence, "RESOURCE_LIMIT_EXCEEDED"):
        if not isinstance(item.attribution_accepted, bool) or not isinstance(item.authority_accepted, bool):
            fail("INVALID_EVIDENCE_ACCEPTANCE", "event attribution/authority acceptance MUST be boolean")
        validate_market_record(item.record)
        if item.record.type != TYPE_EVENT:
            fail("MARKET_EVENT_REQUIRED", "fulfillment evidence input MUST contain MarketEvent records")
        identity = record_identity_text(item.record)
        context = (item.attribution_accepted, item.authority_accepted)
        prior_context = seen_evidence_context.get(identity)
        if prior_context is not None:
            if prior_context != context:
                fail("DUPLICATE_EVIDENCE_CONTEXT_CONFLICT", "same event identity has conflicting evaluator acceptance context")
            duplicate_event_count += 1
            continue
        seen_evidence_context[identity] = context
        if item.record.content["event"] not in FULFILLMENT_EVENTS:
            ignored_nonfulfillment += 1
            continue
        metadata = validate_fulfillment_event(item.record, agreement, commitment_id)
        if not item.accepted_for_method:
            rejected_by_method += 1
            continue
        accepted_events.append(item.record)
        accepted_event_ids.add(identity)
        required_critical.update(_critical_uris(item.record))
        if metadata["criterion_observation"] is not None:
            key, status = metadata["criterion_observation"]
            criterion_statuses.setdefault(key, set()).add(status)

    unsupported_critical = sorted(required_critical - understood, key=lambda value: value.encode("utf-8"))
    disputed_event_ids = _accepted_disputes(
        disputes,
        accepted_event_ids,
        max_items=max_evidence,
    )

    partial_performance = 0
    complete_performance = 0
    acceptance_assertions = 0
    rejection_assertions = 0
    completion_assertions = 0
    failure_assertions = 0
    delivery_assertions = 0

    for event in accepted_events:
        event_type = event.content["event"]
        if event_type in {EVENT_COMMITMENT_PERFORMANCE, EVENT_COMMITMENT_DELIVERY}:
            if event_type == EVENT_COMMITMENT_DELIVERY:
                delivery_assertions += 1
            outcome_type = event.content["outcome"]["type"]
            if outcome_type == OUTCOME_PERFORMANCE_PARTIAL:
                partial_performance += 1
            elif outcome_type == OUTCOME_PERFORMANCE_CLAIMED_COMPLETE:
                complete_performance += 1
        elif event_type == EVENT_COMMITMENT_ACCEPTANCE:
            acceptance_assertions += 1
        elif event_type == EVENT_COMMITMENT_REJECTION:
            rejection_assertions += 1
        elif event_type == EVENT_COMMITMENT_COMPLETION:
            completion_assertions += 1
        elif event_type == EVENT_COMMITMENT_FAILURE:
            failure_assertions += 1

    required_criteria = {
        olp_encode(criterion): criterion
        for criterion in commitment.get("acceptance_criteria", ())
        if criterion["mode"] == "required"
    }
    criterion_satisfied = 0
    criterion_unsatisfied = 0
    criterion_unknown = 0
    criterion_conflicts = 0
    for key in required_criteria:
        statuses = criterion_statuses.get(key, set())
        if "SATISFIED" in statuses and "UNSATISFIED" in statuses:
            criterion_conflicts += 1
        elif "UNSATISFIED" in statuses:
            criterion_unsatisfied += 1
        elif statuses == {"SATISFIED"}:
            criterion_satisfied += 1
        else:
            criterion_unknown += 1

    if unsupported_critical:
        conclusion = "INDETERMINATE"
    elif disputed_event_ids:
        conclusion = "DISPUTED_EVIDENCE"
    elif criterion_conflicts or (acceptance_assertions and rejection_assertions):
        conclusion = "CONFLICTING_EVIDENCE"
    elif completion_assertions and failure_assertions:
        conclusion = "CONFLICTING_EVIDENCE"
    elif complete_performance and failure_assertions:
        conclusion = "CONFLICTING_EVIDENCE"
    elif rejection_assertions or failure_assertions or criterion_unsatisfied:
        conclusion = "NOT_FULFILLED_UNDER_METHOD"
    elif complete_performance:
        if criterion_unknown:
            conclusion = "INDETERMINATE"
        elif require_acceptance and not acceptance_assertions:
            conclusion = "INDETERMINATE"
        else:
            conclusion = "FULFILLED_UNDER_METHOD"
    elif partial_performance:
        conclusion = "PARTIALLY_PERFORMED_UNDER_METHOD"
    else:
        conclusion = "INDETERMINATE"

    return {
        "agreement": record_identity_text(agreement),
        "commitment_id": commitment_id,
        "method": method,
        "require_acceptance": require_acceptance,
        "accepted_event_count": len(accepted_events),
        "duplicate_event_count": duplicate_event_count,
        "ignored_nonfulfillment_event_count": ignored_nonfulfillment,
        "rejected_by_method_count": rejected_by_method,
        "partial_performance": partial_performance,
        "complete_performance": complete_performance,
        "acceptance_assertions": acceptance_assertions,
        "rejection_assertions": rejection_assertions,
        "completion_assertions": completion_assertions,
        "failure_assertions": failure_assertions,
        "delivery_assertions": delivery_assertions,
        "required_criteria": len(required_criteria),
        "criterion_satisfied": criterion_satisfied,
        "criterion_unsatisfied": criterion_unsatisfied,
        "criterion_unknown": criterion_unknown,
        "criterion_conflicts": criterion_conflicts,
        "unsupported_critical_semantics": unsupported_critical,
        "disputed_event_ids": sorted(disputed_event_ids),
        "conclusion": conclusion,
        "universal_truth": False,
        "payment_or_settlement_evaluated": False,
    }
