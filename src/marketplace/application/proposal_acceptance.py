"""Dedicated seller Proposal-acceptance authoring above application state."""
from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any, Callable

from .listing import ProductListingDraft
from .postgres_state import ApplicationStatePutResult, StoreDisposition
from .state import MarketplaceApplicationStateService


_URI_RE = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:[^\s]+$")
_MAX_URI_BYTES = 2048
_MAX_RECORD_ID_CHARS = 512

ProposalPredicate = Callable[[Any], bool]
ProposalParentExtractor = Callable[[Any], tuple[str, ...]]
ProductListingExtractor = Callable[[Any], ProductListingDraft]
ProposalAcceptanceRecordBuilder = Callable[[str, str], Any]
AcceptanceProposalExtractor = Callable[[Any], str]
RecordIdentityExtractor = Callable[[Any], str]


class ProposalAcceptanceAuthoringError(RuntimeError):
    """Stable seller-acceptance failure without record/payload reflection."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def _fail(code: str, message: str) -> None:
    raise ProposalAcceptanceAuthoringError(code, message) from None


def _record_id(value: object) -> str:
    if type(value) is not str or not value or len(value) > _MAX_RECORD_ID_CHARS:
        raise ValueError("proposal_record_id is invalid")
    if any(ord(char) < 33 or ord(char) > 126 or char in "/?#" for char in value):
        raise ValueError("proposal_record_id is invalid")
    return value


def _principal(value: object) -> str:
    if type(value) is not str or not value:
        raise ValueError("seller_principal is invalid")
    try:
        encoded = value.encode("utf-8", "strict")
    except UnicodeEncodeError as exc:
        raise ValueError("seller_principal is invalid") from exc
    if len(encoded) > _MAX_URI_BYTES or _URI_RE.fullmatch(value) is None:
        raise ValueError("seller_principal is invalid")
    return value


@dataclass(frozen=True, slots=True)
class ProposalAcceptancePublicationResult:
    record_id: str
    disposition: StoreDisposition
    change_seq: int | None

    def __post_init__(self) -> None:
        _record_id(self.record_id)
        if type(self.disposition) is not StoreDisposition:
            raise TypeError("disposition MUST be exact StoreDisposition")
        if self.change_seq is not None and (type(self.change_seq) is not int or self.change_seq < 1):
            raise ValueError("change_seq MUST be a positive exact integer when present")

    def to_document(self) -> dict[str, object]:
        return {
            "change_seq": self.change_seq,
            "disposition": self.disposition.value,
            "record_id": self.record_id,
        }


class MarketplaceProposalAcceptanceAuthoringService:
    """Resolve Proposal ownership, build one exact acceptance event, and publish it."""

    def __init__(
        self,
        *,
        state: MarketplaceApplicationStateService,
        is_proposal_record: ProposalPredicate,
        proposal_parent_ids: ProposalParentExtractor,
        extract_product_listing: ProductListingExtractor,
        build_record: ProposalAcceptanceRecordBuilder,
        acceptance_proposal_id: AcceptanceProposalExtractor,
        record_identity: RecordIdentityExtractor,
    ) -> None:
        if type(state) is not MarketplaceApplicationStateService:
            raise TypeError("state MUST be exact MarketplaceApplicationStateService")
        for name, value in (
            ("is_proposal_record", is_proposal_record),
            ("proposal_parent_ids", proposal_parent_ids),
            ("extract_product_listing", extract_product_listing),
            ("build_record", build_record),
            ("acceptance_proposal_id", acceptance_proposal_id),
            ("record_identity", record_identity),
        ):
            if not callable(value):
                raise TypeError(f"{name} MUST be callable")
        self._state = state
        self._is_proposal_record = is_proposal_record
        self._proposal_parent_ids = proposal_parent_ids
        self._extract_product_listing = extract_product_listing
        self._build_record = build_record
        self._acceptance_proposal_id = acceptance_proposal_id
        self._record_identity = record_identity

    def accept_proposal(
        self,
        *,
        seller_principal: str,
        proposal_record_id: str,
    ) -> ProposalAcceptancePublicationResult:
        try:
            seller = _principal(seller_principal)
            proposal_id = _record_id(proposal_record_id)
        except ValueError:
            _fail("PROPOSAL_ACCEPTANCE_REQUEST_INVALID", "acceptance request is invalid")

        try:
            proposal = self._state.peek(proposal_id)
        except Exception:
            _fail("PROPOSAL_ACCEPTANCE_PROPOSAL_UNAVAILABLE", "Proposal could not be resolved")
        if proposal is None:
            _fail("PROPOSAL_ACCEPTANCE_PROPOSAL_NOT_FOUND", "Proposal was not found")
        try:
            is_proposal = self._is_proposal_record(proposal)
        except Exception:
            _fail("PROPOSAL_ACCEPTANCE_PROPOSAL_INVALID", "target record is not a valid Proposal")
        if type(is_proposal) is not bool or not is_proposal:
            _fail("PROPOSAL_ACCEPTANCE_PROPOSAL_INVALID", "target record is not a valid Proposal")

        try:
            parents = self._proposal_parent_ids(proposal)
        except Exception:
            _fail("PROPOSAL_ACCEPTANCE_PARENT_INVALID", "Proposal parent binding is invalid")
        if (
            type(parents) is not tuple
            or len(parents) != 1
            or type(parents[0]) is not str
            or not parents[0]
        ):
            _fail("PROPOSAL_ACCEPTANCE_PARENT_INVALID", "Proposal MUST have exactly one parent listing")
        parent_id = parents[0]

        try:
            parent = self._state.peek(parent_id)
        except Exception:
            _fail("PROPOSAL_ACCEPTANCE_LISTING_UNAVAILABLE", "parent listing could not be resolved")
        if parent is None:
            _fail("PROPOSAL_ACCEPTANCE_LISTING_NOT_FOUND", "parent listing was not found")
        try:
            listing = self._extract_product_listing(parent)
        except Exception:
            _fail("PROPOSAL_ACCEPTANCE_LISTING_INVALID", "Proposal parent is not a valid product listing")
        if type(listing) is not ProductListingDraft:
            _fail("PROPOSAL_ACCEPTANCE_LISTING_INVALID", "Proposal parent is not a valid product listing")
        if listing.seller_principal != seller:
            _fail("PROPOSAL_ACCEPTANCE_SELLER_MISMATCH", "authenticated seller does not own the parent listing")

        try:
            record = self._build_record(seller, proposal_id)
        except Exception:
            _fail("PROPOSAL_ACCEPTANCE_BUILD_FAILED", "acceptance record could not be built")
        try:
            related_proposal_id = self._acceptance_proposal_id(record)
        except Exception:
            _fail("PROPOSAL_ACCEPTANCE_BINDING_MISMATCH", "acceptance Proposal binding could not be verified")
        if related_proposal_id != proposal_id:
            _fail("PROPOSAL_ACCEPTANCE_BINDING_MISMATCH", "acceptance record is not bound to the exact Proposal")
        try:
            acceptance_id = self._record_identity(record)
            acceptance_id = _record_id(acceptance_id)
        except Exception:
            _fail("PROPOSAL_ACCEPTANCE_IDENTITY_FAILED", "acceptance identity could not be derived")

        try:
            put = self._state.publish(record)
        except Exception:
            _fail("PROPOSAL_ACCEPTANCE_PUBLISH_FAILED", "acceptance record could not be published")
        if type(put) is not ApplicationStatePutResult:
            _fail("PROPOSAL_ACCEPTANCE_PUBLISH_FAILED", "acceptance publication returned an invalid result")
        try:
            return ProposalAcceptancePublicationResult(
                record_id=acceptance_id,
                disposition=put.disposition,
                change_seq=put.change_seq,
            )
        except Exception:
            _fail("PROPOSAL_ACCEPTANCE_PUBLISH_FAILED", "acceptance publication returned an invalid result")


__all__ = [
    "AcceptanceProposalExtractor",
    "MarketplaceProposalAcceptanceAuthoringService",
    "ProductListingExtractor",
    "ProposalAcceptanceAuthoringError",
    "ProposalAcceptancePublicationResult",
    "ProposalAcceptanceRecordBuilder",
    "ProposalParentExtractor",
    "ProposalPredicate",
    "RecordIdentityExtractor",
]
