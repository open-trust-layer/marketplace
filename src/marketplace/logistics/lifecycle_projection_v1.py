"""L2 source-only, method-relative delivery evidence lifecycle projection.

Accepts already-reviewed OLP MarketEvents. It never verifies proofs itself,
dispatches a carrier, determines factual delivery or authorizes payment.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from olp import RecordV1
from olp.encoding.record_identity import record_identity_text
from olp.evidence import record_ref

from marketplace.logistics.agreement_link_v1 import (
    PROFILE_DELIVERY_V1,
    inspect_delivery_agreement_link,
)
from marketplace.reference.record_v1 import (
    BASE,
    CORE_PROFILE,
    TYPE_EVENT,
    validate_market_record,
)

PROFILE_NAME: Final = "MARKETPLACE_LOGISTICS_DELIVERY_EVENT_PROJECTION_V1"
_STAGES: Final = (
    "REQUESTED", "QUOTED", "ASSIGNED", "PICKUP_READY", "PICKED_UP",
    "IN_TRANSIT", "OUT_FOR_DELIVERY", "DELIVERED", "CONFIRMED",
)
_EXCEPTIONS: Final = (
    "CANCELLED", "FAILED_PICKUP", "FAILED_DELIVERY", "RECIPIENT_UNAVAILABLE",
    "DAMAGED", "LOST", "RETURN_TO_SENDER", "DISPUTED",
    "PARTIAL_DELIVERY", "REFUND_REQUESTED",
)
_EVENT_TYPES: Final = {
    name: f"{BASE}/event/logistics-{name.lower().replace('_', '-')}"
    for name in _STAGES + _EXCEPTIONS
}
_REVERSE_EVENTS = {uri: name for name, uri in _EVENT_TYPES.items()}
_MAX_EVENTS: Final = 256
_ERROR: Final = "Marketplace delivery evidence projection failed"


class DeliveryProjectionError(ValueError):
    def __init__(self, code: str) -> None:
        super().__init__(_ERROR)
        self.code = code


@dataclass(frozen=True)
class ReviewedDeliveryEvent:
    """A local method assessment, not an OLP proof or universal permission."""

    event: RecordV1
    sequence: int
    attribution_accepted: bool
    authority_accepted: bool


@dataclass(frozen=True)
class DeliveryProjection:
    stage: str
    status: str
    exception_codes: tuple[str, ...]
    admitted_event_ids: tuple[str, ...]
    excluded_event_ids: tuple[str, ...]
    conflicting_event_ids: tuple[str, ...]


def _fail(code: str) -> None:
    raise DeliveryProjectionError(code) from None


def _reviewed_event(value: object, *, agreement: RecordV1, commitment_id: str):
    if type(value) is not RecordV1 or value.type != TYPE_EVENT:
        _fail("LOGISTICS_EVENT_REQUIRED")
    try:
        validate_market_record(value)
    except Exception:
        _fail("LOGISTICS_EVENT_INVALID")
    if set(value.profiles) != {CORE_PROFILE, PROFILE_DELIVERY_V1}:
        _fail("LOGISTICS_EVENT_PROFILE_INVALID")
    content = value.content
    if set(content) != {"version", "issuer", "event", "commitment_refs"}:
        _fail("LOGISTICS_EVENT_SHAPE_INVALID")
    step = _REVERSE_EVENTS.get(content["event"])
    if step is None:
        _fail("LOGISTICS_EVENT_KIND_UNSUPPORTED")
    target = content["commitment_refs"]
    expected = {"record": record_ref(agreement).to_value(), "id": commitment_id}
    if len(target) != 1 or target[0] != expected:
        _fail("LOGISTICS_EVENT_TARGET_MISMATCH")
    return step, content["issuer"]["principal"]


def _allowed_actor(stage: str, issuer: str, *, seller: str, carrier: str, buyer: str) -> bool:
    if stage in {"REQUESTED", "ASSIGNED", "PICKUP_READY"}:
        return issuer == seller
    if stage in {"QUOTED", "PICKED_UP", "IN_TRANSIT", "OUT_FOR_DELIVERY", "DELIVERED"}:
        return issuer == carrier
    if stage == "CONFIRMED":
        return issuer == buyer
    if stage in {"CANCELLED", "REFUND_REQUESTED"}:
        return issuer in {seller, buyer}
    if stage in {"FAILED_PICKUP", "DAMAGED", "LOST", "DISPUTED"}:
        return issuer in {seller, carrier, buyer} if stage == "DISPUTED" else issuer in {seller, carrier}
    if stage in {"FAILED_DELIVERY", "RECIPIENT_UNAVAILABLE", "RETURN_TO_SENDER"}:
        return issuer == carrier
    if stage == "PARTIAL_DELIVERY":
        return issuer in {buyer, carrier}
    return False


def _exception_allowed(stage: str, exception: str) -> bool:
    progress = _STAGES.index(stage) if stage in _STAGES else -1
    if exception == "CANCELLED":
        return progress < _STAGES.index("PICKED_UP")
    if exception == "FAILED_PICKUP":
        return stage == "PICKUP_READY"
    if exception in {"FAILED_DELIVERY", "RECIPIENT_UNAVAILABLE", "PARTIAL_DELIVERY"}:
        return stage == "OUT_FOR_DELIVERY"
    if exception in {"DAMAGED", "LOST", "RETURN_TO_SENDER"}:
        return _STAGES.index("PICKED_UP") <= progress <= _STAGES.index("DELIVERED")
    return progress >= _STAGES.index("ASSIGNED")


def project_delivery_events(
    *,
    purchase_agreement: object,
    delivery_agreement: object,
    buyer_principal: object,
    reviewed_events: object,
) -> DeliveryProjection:
    """Project local state from validated, exact-targeted, externally admitted events.

    Explicit integer sequence order is a *local reviewing method*, not a trusted
    timestamp or protocol truth. Unknown/missing or contradictory evidence never
    yields a confirmed result. Rejections and disputes are not silently discarded.
    """
    link = inspect_delivery_agreement_link(
        purchase_agreement=purchase_agreement,
        delivery_agreement=delivery_agreement,
    )
    purchase = purchase_agreement
    delivery = delivery_agreement
    seller = next(
        c["party"]["principal"] for c in purchase.content["commitments"]
        if c["id"] == link.purchase_commitment_id
    )
    others = {
        party["principal"] for party in purchase.content["parties"]
        if party["principal"] != seller
    }
    if type(buyer_principal) is not str or others != {buyer_principal}:
        _fail("LOGISTICS_BUYER_AMBIGUOUS")
    if type(reviewed_events) is not tuple or len(reviewed_events) > _MAX_EVENTS:
        _fail("LOGISTICS_REVIEW_SET_INVALID")

    reviewed = []
    for assessment in reviewed_events:
        if (type(assessment) is not ReviewedDeliveryEvent
            or type(assessment.sequence) is not int
            or not 1 <= assessment.sequence <= _MAX_EVENTS
            or type(assessment.attribution_accepted) is not bool
            or type(assessment.authority_accepted) is not bool):
            _fail("LOGISTICS_REVIEW_INVALID")
        reviewed.append(assessment)
    reviewed.sort(key=lambda x: x.sequence)
    if len({item.sequence for item in reviewed}) != len(reviewed):
        _fail("LOGISTICS_SEQUENCE_CONFLICT")

    stage = "UNKNOWN"
    exceptions: list[str] = []
    admitted: list[str] = []
    excluded: list[str] = []
    conflicts: list[str] = []
    visited: set[str] = set()
    for assessment in reviewed:
        step, issuer = _reviewed_event(
            assessment.event,
            agreement=delivery,
            commitment_id=link.carrier_commitment_id,
        )
        try:
            evidence_id = record_identity_text(assessment.event)
        except Exception:
            _fail("LOGISTICS_EVENT_ID_INVALID")
        if evidence_id in visited:
            _fail("LOGISTICS_EVIDENCE_DUPLICATE")
        visited.add(evidence_id)
        if not _allowed_actor(
            step, issuer, seller=seller, carrier=link.carrier_principal, buyer=buyer_principal
        ):
            _fail("LOGISTICS_EVENT_ACTOR_INVALID")
        if not (assessment.attribution_accepted and assessment.authority_accepted):
            excluded.append(evidence_id)
            continue
        admitted.append(evidence_id)
        if step in _EXCEPTIONS:
            if step not in exceptions:
                exceptions.append(step)
            if not _exception_allowed(stage, step):
                conflicts.append(evidence_id)
            continue
        next_index = 0 if stage == "UNKNOWN" else _STAGES.index(stage) + 1
        if next_index >= len(_STAGES) or _STAGES[next_index] != step:
            conflicts.append(evidence_id)
            continue
        if ("CANCELLED" in exceptions
            or ("LOST" in exceptions and step in {"DELIVERED", "CONFIRMED"})):
            conflicts.append(evidence_id)
            continue
        stage = step

    return DeliveryProjection(
        stage=stage,
        status="CONFLICT" if conflicts else ("INSUFFICIENT" if stage == "UNKNOWN" else "PROVISIONAL"),
        exception_codes=tuple(exceptions),
        admitted_event_ids=tuple(admitted),
        excluded_event_ids=tuple(excluded),
        conflicting_event_ids=tuple(conflicts),
    )


__all__ = [
    "PROFILE_NAME", "ReviewedDeliveryEvent", "DeliveryProjection",
    "DeliveryProjectionError", "project_delivery_events", "_EVENT_TYPES",
]
