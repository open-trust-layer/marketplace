"""Structured Proposal authoring above the reviewed application API."""
from __future__ import annotations

from typing import Any, Callable

from .api import MarketplaceApplicationApiService
from .postgres_state import ApplicationStatePutResult
from .proposal import BuyerRequestProposalDraft, review_buyer_request_proposal_draft


ProposalRecordBuilder = Callable[[BuyerRequestProposalDraft], Any]


class ProposalAuthoringError(RuntimeError):
    """Stable structured Proposal authoring failure without reflected details."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


class MarketplaceProposalAuthoringService:
    """Build one reviewed Proposal response, then publish only through the application API."""

    def __init__(
        self,
        *,
        api: MarketplaceApplicationApiService,
        build_record: ProposalRecordBuilder,
    ) -> None:
        if type(api) is not MarketplaceApplicationApiService:
            raise TypeError("api MUST be exact MarketplaceApplicationApiService")
        if not callable(build_record):
            raise TypeError("build_record MUST be callable")
        self._api = api
        self._build_record = build_record

    def create_buyer_request_proposal(
        self,
        draft: BuyerRequestProposalDraft,
    ) -> ApplicationStatePutResult:
        if type(draft) is not BuyerRequestProposalDraft:
            raise TypeError("draft MUST be exact BuyerRequestProposalDraft")
        try:
            reviewed = review_buyer_request_proposal_draft(draft)
        except (TypeError, ValueError):
            raise ProposalAuthoringError(
                "PROPOSAL_DRAFT_INVALID",
                "structured Proposal draft is invalid",
            ) from None
        try:
            record = self._build_record(reviewed)
        except Exception:
            raise ProposalAuthoringError(
                "PROPOSAL_BUILD_FAILED",
                "Proposal record could not be built",
            ) from None
        return self._api.respond_to_intent(reviewed.parent_record_id, record)


__all__ = [
    "MarketplaceProposalAuthoringService",
    "ProposalAuthoringError",
    "ProposalRecordBuilder",
]
