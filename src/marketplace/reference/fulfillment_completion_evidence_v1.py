"""M17.7A reference authoring for the happy-path fulfillment evidence trio."""
from __future__ import annotations

from collections.abc import Mapping
import re
from typing import Final

from olp import RecordV1
from olp.encoding.record_identity import record_identity_text
from olp.evidence import record_ref
from olp.model.evidence import EvidenceKind, EvidenceRefV1
from olp.transport import encode_identity_text
from olp.values import is_absolute_uri

from .record_v1 import (
    BASE,
    CORE_PROFILE,
    TYPE_AGREEMENT,
    TYPE_EVENT,
    validate_market_record,
)


PROFILE_NAME: Final = "MARKETPLACE_REFERENCE_FULFILLMENT_COMPLETION_EVIDENCE_V1"

EVENT_COMMITMENT_PERFORMANCE: Final = f"{BASE}/event/commitment-performance"
EVENT_COMMITMENT_ACCEPTANCE: Final = f"{BASE}/event/commitment-acceptance"
EVENT_COMMITMENT_COMPLETION: Final = (
    f"{BASE}/event/commitment-completion-assertion"
)
OUTCOME_PERFORMANCE_CLAIMED_COMPLETE: Final = (
    f"{BASE}/outcome/performance-claimed-complete"
)

_MAX_URI_BYTES: Final = 2048
_LOCAL_ID_RE = re.compile(r"^[A-Za-z][A-Za-z0-9._-]{0,63}$")
_SUPPORTED_EVENTS = frozenset(
    {
        EVENT_COMMITMENT_PERFORMANCE,
        EVENT_COMMITMENT_ACCEPTANCE,
        EVENT_COMMITMENT_COMPLETION,
    }
)
_ERROR_MESSAGE: Final = "Marketplace fulfillment completion evidence operation failed"


class MarketplaceFulfillmentCompletionEvidenceError(ValueError):
    """Stable source-only fulfillment-evidence authoring failure."""

    def __init__(self, code: str) -> None:
        super().__init__(_ERROR_MESSAGE)
        self.code = code


def _fail(code: str) -> None:
    raise MarketplaceFulfillmentCompletionEvidenceError(code) from None


def _principal(value: object) -> str:
    if type(value) is not str or not value:
        _fail("FULFILLMENT_ISSUER_INVALID")
    try:
        encoded = value.encode("utf-8", "strict")
    except UnicodeEncodeError:
        _fail("FULFILLMENT_ISSUER_INVALID")
    if len(encoded) > _MAX_URI_BYTES or not is_absolute_uri(value):
        _fail("FULFILLMENT_ISSUER_INVALID")
    return value


def _commitment_id(value: object) -> str:
    if type(value) is not str or _LOCAL_ID_RE.fullmatch(value) is None:
        _fail("FULFILLMENT_COMMITMENT_ID_INVALID")
    return value


def _agreement_commitment(
    agreement: object,
    commitment_id: object,
) -> tuple[RecordV1, str, Mapping[str, object]]:
    if type(agreement) is not RecordV1:
        _fail("FULFILLMENT_AGREEMENT_REQUIRED")
    try:
        validate_market_record(agreement)
    except Exception:
        _fail("FULFILLMENT_AGREEMENT_INVALID")
    if agreement.type != TYPE_AGREEMENT:
        _fail("FULFILLMENT_AGREEMENT_REQUIRED")

    reviewed_id = _commitment_id(commitment_id)
    try:
        commitments = agreement.content["commitments"]
    except Exception:
        _fail("FULFILLMENT_AGREEMENT_INVALID")
    if not isinstance(commitments, tuple):
        _fail("FULFILLMENT_AGREEMENT_INVALID")

    match = None
    for commitment in commitments:
        if isinstance(commitment, Mapping) and commitment.get("id") == reviewed_id:
            if match is not None:
                _fail("FULFILLMENT_AGREEMENT_INVALID")
            match = commitment
    if match is None:
        _fail("FULFILLMENT_COMMITMENT_NOT_FOUND")
    return agreement, reviewed_id, match


def fulfillment_event_target(event: object) -> tuple[str, str]:
    """Return the exact Agreement identity and commitment id for one A event."""

    if type(event) is not RecordV1:
        _fail("FULFILLMENT_EVIDENCE_INVALID")
    try:
        validate_market_record(event)
    except Exception:
        _fail("FULFILLMENT_EVIDENCE_INVALID")
    if event.type != TYPE_EVENT or event.profiles != (CORE_PROFILE,):
        _fail("FULFILLMENT_EVIDENCE_INVALID")

    content = event.content
    if not isinstance(content, Mapping):
        _fail("FULFILLMENT_EVIDENCE_INVALID")
    event_type = content.get("event")
    if event_type not in _SUPPORTED_EVENTS:
        _fail("FULFILLMENT_EVIDENCE_EVENT_UNSUPPORTED")

    expected = {"version", "issuer", "event", "commitment_refs"}
    if event_type == EVENT_COMMITMENT_PERFORMANCE:
        expected.add("outcome")
    if set(content) != expected or len(content) != len(expected):
        _fail("FULFILLMENT_EVIDENCE_SHAPE_INVALID")
    if content.get("version") != 1 or isinstance(content.get("version"), bool):
        _fail("FULFILLMENT_EVIDENCE_SHAPE_INVALID")

    issuer = content.get("issuer")
    if not isinstance(issuer, Mapping) or set(issuer) != {"principal"}:
        _fail("FULFILLMENT_EVIDENCE_SHAPE_INVALID")
    _principal(issuer.get("principal"))

    refs = content.get("commitment_refs")
    if not isinstance(refs, tuple) or len(refs) != 1:
        _fail("FULFILLMENT_EVIDENCE_TARGET_INVALID")
    target = refs[0]
    if not isinstance(target, Mapping) or set(target) != {"record", "id"}:
        _fail("FULFILLMENT_EVIDENCE_TARGET_INVALID")
    target_id = _commitment_id(target.get("id"))
    try:
        ref = EvidenceRefV1.from_value(target.get("record"))
    except Exception:
        _fail("FULFILLMENT_EVIDENCE_TARGET_INVALID")
    if ref.kind != EvidenceKind.RECORD:
        _fail("FULFILLMENT_EVIDENCE_TARGET_INVALID")
    try:
        agreement_record_id = encode_identity_text("record", ref.identity_digest)
    except Exception:
        _fail("FULFILLMENT_EVIDENCE_TARGET_INVALID")

    if event_type == EVENT_COMMITMENT_PERFORMANCE:
        outcome = content.get("outcome")
        if (
            not isinstance(outcome, Mapping)
            or set(outcome) != {"type"}
            or outcome.get("type") != OUTCOME_PERFORMANCE_CLAIMED_COMPLETE
        ):
            _fail("FULFILLMENT_EVIDENCE_SHAPE_INVALID")
    return agreement_record_id, target_id


def _build_event(
    *,
    agreement: RecordV1,
    commitment_id: str,
    issuer: str,
    event_type: str,
    outcome_type: str | None,
) -> RecordV1:
    try:
        agreement_id = record_identity_text(agreement)
        target = {
            "record": record_ref(agreement).to_value(),
            "id": commitment_id,
        }
        content: dict[str, object] = {
            "version": 1,
            "issuer": {"principal": issuer},
            "event": event_type,
            "commitment_refs": [target],
        }
        if outcome_type is not None:
            content["outcome"] = {"type": outcome_type}
        event = RecordV1.from_mapping(
            {
                "envelope_version": 1,
                "type": TYPE_EVENT,
                "content": content,
                "profiles": [CORE_PROFILE],
            }
        )
        validate_market_record(event)
        if fulfillment_event_target(event) != (agreement_id, commitment_id):
            _fail("FULFILLMENT_EVIDENCE_TARGET_INVALID")
        return event
    except MarketplaceFulfillmentCompletionEvidenceError:
        raise
    except Exception:
        _fail("FULFILLMENT_EVIDENCE_BUILD_FAILED")


def build_claimed_complete_performance_event(
    *,
    agreement: RecordV1,
    commitment_id: str,
    issuer: str,
) -> RecordV1:
    """Build one claimed-complete performance assertion for one commitment."""

    reviewed_agreement, reviewed_id, commitment = _agreement_commitment(
        agreement,
        commitment_id,
    )
    reviewed_issuer = _principal(issuer)
    try:
        party = commitment["party"]
        party_principal = party["principal"]
    except Exception:
        _fail("FULFILLMENT_AGREEMENT_INVALID")
    if reviewed_issuer != party_principal:
        _fail("FULFILLMENT_PERFORMER_MISMATCH")
    return _build_event(
        agreement=reviewed_agreement,
        commitment_id=reviewed_id,
        issuer=reviewed_issuer,
        event_type=EVENT_COMMITMENT_PERFORMANCE,
        outcome_type=OUTCOME_PERFORMANCE_CLAIMED_COMPLETE,
    )


def build_commitment_acceptance_event(
    *,
    agreement: RecordV1,
    commitment_id: str,
    issuer: str,
) -> RecordV1:
    """Build one attributable acceptance assertion without authority inference."""

    reviewed_agreement, reviewed_id, _commitment = _agreement_commitment(
        agreement,
        commitment_id,
    )
    return _build_event(
        agreement=reviewed_agreement,
        commitment_id=reviewed_id,
        issuer=_principal(issuer),
        event_type=EVENT_COMMITMENT_ACCEPTANCE,
        outcome_type=None,
    )


def build_commitment_completion_event(
    *,
    agreement: RecordV1,
    commitment_id: str,
    issuer: str,
) -> RecordV1:
    """Build one attributable completion assertion without truth inference."""

    reviewed_agreement, reviewed_id, _commitment = _agreement_commitment(
        agreement,
        commitment_id,
    )
    return _build_event(
        agreement=reviewed_agreement,
        commitment_id=reviewed_id,
        issuer=_principal(issuer),
        event_type=EVENT_COMMITMENT_COMPLETION,
        outcome_type=None,
    )


__all__ = [
    "EVENT_COMMITMENT_ACCEPTANCE",
    "EVENT_COMMITMENT_COMPLETION",
    "EVENT_COMMITMENT_PERFORMANCE",
    "MarketplaceFulfillmentCompletionEvidenceError",
    "OUTCOME_PERFORMANCE_CLAIMED_COMPLETE",
    "PROFILE_NAME",
    "build_claimed_complete_performance_event",
    "build_commitment_acceptance_event",
    "build_commitment_completion_event",
    "fulfillment_event_target",
]
