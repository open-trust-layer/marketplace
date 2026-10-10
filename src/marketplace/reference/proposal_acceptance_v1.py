"""Reference profile for one seller Proposal-acceptance Marketplace event."""
from __future__ import annotations

from collections.abc import Mapping

from olp import RecordV1
from olp.encoding.record_identity import record_identity_text
from olp.model.evidence import EvidenceKind, EvidenceRefV1
from olp.transport import decode_identity_text, encode_identity_text

from .application_record_v1 import marketplace_response_parent_ids
from .record_v1 import (
    BASE,
    CORE_PROFILE,
    PROPOSAL_PROFILE,
    TYPE_EVENT,
    TYPE_INTENT,
    validate_market_record,
)


EVENT_PROPOSAL_ACCEPTANCE = f"{BASE}/event/proposal-acceptance"


class ProposalAcceptanceProfileError(ValueError):
    """Stable Proposal-acceptance profile failure."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def _fail(code: str, message: str) -> None:
    raise ProposalAcceptanceProfileError(code, message) from None


def _record_id(value: object) -> str:
    if type(value) is not str or not value or len(value) > 512:
        _fail("PROPOSAL_ACCEPTANCE_PROPOSAL_ID_INVALID", "Proposal Record Identity is invalid")
    if any(ord(char) < 33 or ord(char) > 126 or char in "/?#" for char in value):
        _fail("PROPOSAL_ACCEPTANCE_PROPOSAL_ID_INVALID", "Proposal Record Identity is invalid")
    return value


def is_marketplace_proposal_record(record: object) -> bool:
    """Classify one exact Marketplace Proposal with exactly one response parent."""
    if type(record) is not RecordV1:
        return False
    try:
        validate_market_record(record)
        if record.type != TYPE_INTENT:
            return False
        if type(record.profiles) is not tuple:
            return False
        if len(record.profiles) != 2 or set(record.profiles) != {CORE_PROFILE, PROPOSAL_PROFILE}:
            return False
        return len(marketplace_response_parent_ids(record)) == 1
    except Exception:
        return False


def proposal_acceptance_proposal_id(record: object) -> str:
    """Return the exact Proposal identity referenced by one exact acceptance event."""
    if type(record) is not RecordV1:
        _fail("PROPOSAL_ACCEPTANCE_RECORD_INVALID", "acceptance record MUST be exact RecordV1")
    try:
        validate_market_record(record)
    except Exception:
        _fail("PROPOSAL_ACCEPTANCE_RECORD_INVALID", "acceptance record is not a valid Marketplace record")
    if record.type != TYPE_EVENT:
        _fail("PROPOSAL_ACCEPTANCE_RECORD_INVALID", "acceptance record MUST be a MarketEvent")
    if type(record.profiles) is not tuple or record.profiles != (CORE_PROFILE,):
        _fail("PROPOSAL_ACCEPTANCE_RECORD_INVALID", "acceptance record profile set changed")
    content = record.content
    if not isinstance(content, Mapping) or set(content) != {"version", "issuer", "event", "related_records"}:
        _fail("PROPOSAL_ACCEPTANCE_RECORD_INVALID", "acceptance content shape changed")
    if content["version"] != 1 or isinstance(content["version"], bool):
        _fail("PROPOSAL_ACCEPTANCE_RECORD_INVALID", "acceptance content version changed")
    issuer = content["issuer"]
    if not isinstance(issuer, Mapping) or set(issuer) != {"principal"}:
        _fail("PROPOSAL_ACCEPTANCE_RECORD_INVALID", "acceptance issuer shape changed")
    if content["event"] != EVENT_PROPOSAL_ACCEPTANCE:
        _fail("PROPOSAL_ACCEPTANCE_RECORD_INVALID", "acceptance event identifier changed")
    related = content["related_records"]
    if not isinstance(related, tuple) or len(related) != 1:
        _fail("PROPOSAL_ACCEPTANCE_RECORD_INVALID", "acceptance MUST reference exactly one Proposal")
    try:
        ref = EvidenceRefV1.from_value(related[0])
        if ref.kind != EvidenceKind.RECORD:
            raise ValueError("related reference kind changed")
        return encode_identity_text("record", ref.identity_digest)
    except Exception:
        _fail("PROPOSAL_ACCEPTANCE_RECORD_INVALID", "acceptance Proposal reference is invalid")


def build_proposal_acceptance_record(
    seller_principal: str,
    proposal_record_id: str,
) -> RecordV1:
    """Build one exact seller acceptance event bound to one Proposal identity."""
    if type(seller_principal) is not str or not seller_principal:
        _fail("PROPOSAL_ACCEPTANCE_SELLER_INVALID", "seller principal is invalid")
    reviewed_proposal_id = _record_id(proposal_record_id)
    try:
        _, digest = decode_identity_text(reviewed_proposal_id, expected_kind="record")
        proposal_ref = EvidenceRefV1(EvidenceKind.RECORD, digest).to_value()
        record = RecordV1.from_mapping({
            "envelope_version": 1,
            "type": TYPE_EVENT,
            "content": {
                "version": 1,
                "issuer": {"principal": seller_principal},
                "event": EVENT_PROPOSAL_ACCEPTANCE,
                "related_records": [proposal_ref],
            },
            "profiles": [CORE_PROFILE],
        })
        validate_market_record(record)
        if proposal_acceptance_proposal_id(record) != reviewed_proposal_id:
            raise ValueError("acceptance relation changed")
    except ProposalAcceptanceProfileError:
        raise
    except Exception:
        _fail("PROPOSAL_ACCEPTANCE_BUILD_FAILED", "acceptance record could not be built")
    return record


def proposal_acceptance_record_id(record: object) -> str:
    """Return canonical identity only after exact acceptance-profile validation."""
    proposal_acceptance_proposal_id(record)
    try:
        return record_identity_text(record)
    except Exception:
        _fail("PROPOSAL_ACCEPTANCE_IDENTITY_FAILED", "acceptance identity could not be derived")


__all__ = [
    "EVENT_PROPOSAL_ACCEPTANCE",
    "ProposalAcceptanceProfileError",
    "build_proposal_acceptance_record",
    "is_marketplace_proposal_record",
    "proposal_acceptance_proposal_id",
    "proposal_acceptance_record_id",
]
