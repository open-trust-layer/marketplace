"""Read-only deterministic resolution of one published Proposal-acceptance identity."""
from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any, Callable

from .listing import ProductListingDraft
from .state import MarketplaceApplicationStateService


_URI_RE = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:[^\s]+$")
_MAX_URI_BYTES = 2048
_MAX_RECORD_ID_CHARS = 512

ProposalPredicate = Callable[[Any], bool]
ProposalParentExtractor = Callable[[Any], tuple[str, ...]]
ProductListingExtractor = Callable[[Any], ProductListingDraft]
RecordPrincipalExtractor = Callable[[Any], str]
ProposalAcceptanceRecordBuilder = Callable[[str, str], Any]
AcceptanceProposalExtractor = Callable[[Any], str]
RecordIdentityExtractor = Callable[[Any], str]


class ProposalAcceptanceResolutionError(RuntimeError):
    """Stable non-reflective acceptance-resolution failure."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def _fail(code: str, message: str) -> None:
    raise ProposalAcceptanceResolutionError(code, message) from None


def _record_id(value: object) -> str:
    if type(value) is not str or not value or len(value) > _MAX_RECORD_ID_CHARS:
        raise ValueError("record identity is invalid")
    if any(ord(char) < 33 or ord(char) > 126 or char in "/?#" for char in value):
        raise ValueError("record identity is invalid")
    return value


def _principal(value: object) -> str:
    if type(value) is not str or not value:
        raise ValueError("principal is invalid")
    try:
        encoded = value.encode("utf-8", "strict")
    except UnicodeEncodeError as exc:
        raise ValueError("principal is invalid") from exc
    if len(encoded) > _MAX_URI_BYTES or _URI_RE.fullmatch(value) is None:
        raise ValueError("principal is invalid")
    return value


@dataclass(frozen=True, slots=True)
class ProposalAcceptanceResolutionResult:
    record_id: str
    proposal_record_id: str

    def __post_init__(self) -> None:
        _record_id(self.record_id)
        _record_id(self.proposal_record_id)

    def to_document(self) -> dict[str, str]:
        return {
            "proposal_record_id": self.proposal_record_id,
            "record_id": self.record_id,
        }


class MarketplaceProposalAcceptanceResolutionService:
    """Resolve the one deterministic published acceptance for an exact Proposal party."""

    def __init__(
        self,
        *,
        state: MarketplaceApplicationStateService,
        is_proposal_record: ProposalPredicate,
        proposal_parent_ids: ProposalParentExtractor,
        extract_product_listing: ProductListingExtractor,
        record_principal: RecordPrincipalExtractor,
        build_acceptance_record: ProposalAcceptanceRecordBuilder,
        acceptance_proposal_id: AcceptanceProposalExtractor,
        record_identity: RecordIdentityExtractor,
    ) -> None:
        if type(state) is not MarketplaceApplicationStateService:
            raise TypeError("state MUST be exact MarketplaceApplicationStateService")
        for name, value in (
            ("is_proposal_record", is_proposal_record),
            ("proposal_parent_ids", proposal_parent_ids),
            ("extract_product_listing", extract_product_listing),
            ("record_principal", record_principal),
            ("build_acceptance_record", build_acceptance_record),
            ("acceptance_proposal_id", acceptance_proposal_id),
            ("record_identity", record_identity),
        ):
            if not callable(value):
                raise TypeError(f"{name} MUST be callable")
        self._state = state
        self._is_proposal_record = is_proposal_record
        self._proposal_parent_ids = proposal_parent_ids
        self._extract_product_listing = extract_product_listing
        self._record_principal = record_principal
        self._build_acceptance_record = build_acceptance_record
        self._acceptance_proposal_id = acceptance_proposal_id
        self._record_identity = record_identity

    def resolve(
        self,
        *,
        principal: str,
        proposal_record_id: str,
    ) -> ProposalAcceptanceResolutionResult:
        try:
            reviewed_principal = _principal(principal)
            proposal_id = _record_id(proposal_record_id)
        except ValueError:
            _fail(
                "PROPOSAL_ACCEPTANCE_RESOLUTION_REQUEST_INVALID",
                "acceptance resolution request is invalid",
            )

        try:
            proposal = self._state.peek(proposal_id)
        except Exception:
            _fail(
                "PROPOSAL_ACCEPTANCE_RESOLUTION_STATE_UNAVAILABLE",
                "required Marketplace state is unavailable",
            )
        if proposal is None:
            _fail(
                "PROPOSAL_ACCEPTANCE_RESOLUTION_PROPOSAL_NOT_FOUND",
                "Proposal was not found",
            )
        try:
            is_proposal = self._is_proposal_record(proposal)
            parents = self._proposal_parent_ids(proposal)
            buyer = _principal(self._record_principal(proposal))
        except Exception:
            _fail(
                "PROPOSAL_ACCEPTANCE_RESOLUTION_PROPOSAL_INVALID",
                "Proposal is invalid",
            )
        if type(is_proposal) is not bool or not is_proposal:
            _fail(
                "PROPOSAL_ACCEPTANCE_RESOLUTION_PROPOSAL_INVALID",
                "Proposal is invalid",
            )
        if type(parents) is not tuple or len(parents) != 1:
            _fail(
                "PROPOSAL_ACCEPTANCE_RESOLUTION_PARENT_INVALID",
                "Proposal parent binding is invalid",
            )
        try:
            listing_id = _record_id(parents[0])
            listing_record = self._state.peek(listing_id)
        except Exception:
            _fail(
                "PROPOSAL_ACCEPTANCE_RESOLUTION_STATE_UNAVAILABLE",
                "required Marketplace state is unavailable",
            )
        if listing_record is None:
            _fail(
                "PROPOSAL_ACCEPTANCE_RESOLUTION_LISTING_NOT_FOUND",
                "Proposal parent listing was not found",
            )
        try:
            listing = self._extract_product_listing(listing_record)
        except Exception:
            _fail(
                "PROPOSAL_ACCEPTANCE_RESOLUTION_LISTING_INVALID",
                "Proposal parent is not a valid product listing",
            )
        if type(listing) is not ProductListingDraft:
            _fail(
                "PROPOSAL_ACCEPTANCE_RESOLUTION_LISTING_INVALID",
                "Proposal parent is not a valid product listing",
            )
        seller = listing.seller_principal
        if reviewed_principal not in {buyer, seller}:
            _fail(
                "PROPOSAL_ACCEPTANCE_RESOLUTION_PARTY_REQUIRED",
                "authenticated principal is not a Proposal party",
            )

        try:
            expected = self._build_acceptance_record(seller, proposal_id)
            expected_id = _record_id(self._record_identity(expected))
        except Exception:
            _fail(
                "PROPOSAL_ACCEPTANCE_RESOLUTION_DERIVATION_FAILED",
                "canonical acceptance identity could not be derived",
            )

        try:
            stored = self._state.peek(expected_id)
        except Exception:
            _fail(
                "PROPOSAL_ACCEPTANCE_RESOLUTION_STATE_UNAVAILABLE",
                "required Marketplace state is unavailable",
            )
        if stored is None:
            _fail(
                "PROPOSAL_ACCEPTANCE_RESOLUTION_NOT_FOUND",
                "published Proposal acceptance was not found",
            )
        try:
            stored_id = _record_id(self._record_identity(stored))
            related_proposal = _record_id(self._acceptance_proposal_id(stored))
            issuer = _principal(self._record_principal(stored))
        except Exception:
            _fail(
                "PROPOSAL_ACCEPTANCE_RESOLUTION_ACCEPTANCE_INVALID",
                "published Proposal acceptance is invalid",
            )
        if (
            stored_id != expected_id
            or related_proposal != proposal_id
            or issuer != seller
        ):
            _fail(
                "PROPOSAL_ACCEPTANCE_RESOLUTION_ACCEPTANCE_INVALID",
                "published Proposal acceptance is invalid",
            )

        return ProposalAcceptanceResolutionResult(
            record_id=expected_id,
            proposal_record_id=proposal_id,
        )


__all__ = [
    "AcceptanceProposalExtractor",
    "MarketplaceProposalAcceptanceResolutionService",
    "ProductListingExtractor",
    "ProposalAcceptanceRecordBuilder",
    "ProposalAcceptanceResolutionError",
    "ProposalAcceptanceResolutionResult",
    "ProposalParentExtractor",
    "ProposalPredicate",
    "RecordIdentityExtractor",
    "RecordPrincipalExtractor",
]
