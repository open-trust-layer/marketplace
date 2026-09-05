"""Transport-neutral structured draft for one core buyer/request Proposal response."""
from __future__ import annotations

from dataclasses import dataclass
import re


MAX_PROPOSAL_PARENT_RECORD_ID_CHARS = 512
_MAX_PROPOSAL_URI_BYTES = 2048
_URI_RE = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:[^\s]+$")


def _absolute_uri(value: object, *, name: str) -> str:
    if type(value) is not str or not value:
        raise ValueError(f"{name} MUST be non-empty exact text")
    try:
        encoded = value.encode("utf-8", "strict")
    except UnicodeEncodeError as exc:
        raise ValueError(f"{name} MUST be valid UTF-8 text") from exc
    if len(encoded) > _MAX_PROPOSAL_URI_BYTES:
        raise ValueError(f"{name} exceeds its UTF-8 byte bound")
    if _URI_RE.fullmatch(value) is None:
        raise ValueError(f"{name} MUST be an absolute URI")
    return value


def _parent_record_id(value: object) -> str:
    if type(value) is not str or not value:
        raise ValueError("parent_record_id MUST be non-empty exact text")
    try:
        value.encode("utf-8", "strict")
    except UnicodeEncodeError as exc:
        raise ValueError("parent_record_id MUST be valid UTF-8 text") from exc
    if len(value) > MAX_PROPOSAL_PARENT_RECORD_ID_CHARS:
        raise ValueError("parent_record_id exceeds the application path bound")
    return value


@dataclass(frozen=True, slots=True)
class BuyerRequestProposalDraft:
    """Primitive buyer/request fields before OLP Proposal materialization."""

    buyer_principal: str
    subject_uri: str
    action_uri: str
    parent_record_id: str

    def __post_init__(self) -> None:
        _absolute_uri(self.buyer_principal, name="buyer_principal")
        _absolute_uri(self.subject_uri, name="subject_uri")
        _absolute_uri(self.action_uri, name="action_uri")
        _parent_record_id(self.parent_record_id)


def review_buyer_request_proposal_draft(value: object) -> BuyerRequestProposalDraft:
    """Return a fresh exact draft so frozen-object rebinding cannot bypass validation."""
    if type(value) is not BuyerRequestProposalDraft:
        raise TypeError("value MUST be exact BuyerRequestProposalDraft")
    return BuyerRequestProposalDraft(
        buyer_principal=value.buyer_principal,
        subject_uri=value.subject_uri,
        action_uri=value.action_uri,
        parent_record_id=value.parent_record_id,
    )


__all__ = [
    "BuyerRequestProposalDraft",
    "MAX_PROPOSAL_PARENT_RECORD_ID_CHARS",
    "review_buyer_request_proposal_draft",
]
