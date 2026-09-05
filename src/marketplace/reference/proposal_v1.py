"""Reference OLP adapter for one structured core buyer/request Proposal response."""
from __future__ import annotations

from olp import RecordV1
from olp.model.evidence import EvidenceKind, EvidenceRefV1
from olp.transport import decode_identity_text

from ..application.proposal import (
    BuyerRequestProposalDraft,
    review_buyer_request_proposal_draft,
)
from .record_v1 import (
    CORE_PROFILE,
    PROPOSAL_PROFILE,
    TYPE_INTENT,
    validate_market_record,
)


class ProposalProfileError(ValueError):
    """Stable structured Proposal materialization failure."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def build_buyer_request_proposal_record(draft: BuyerRequestProposalDraft) -> RecordV1:
    """Build one genuine Proposal MarketIntent bound to the exact supplied parent."""
    if type(draft) is not BuyerRequestProposalDraft:
        raise TypeError("draft MUST be exact BuyerRequestProposalDraft")
    try:
        reviewed = review_buyer_request_proposal_draft(draft)
    except (TypeError, ValueError):
        raise ProposalProfileError(
            "PROPOSAL_DRAFT_INVALID",
            "structured Proposal draft is invalid",
        ) from None

    try:
        _, parent_digest = decode_identity_text(
            reviewed.parent_record_id,
            expected_kind="record",
        )
        parent_ref = EvidenceRefV1(EvidenceKind.RECORD, parent_digest).to_value()
    except Exception:
        raise ProposalProfileError(
            "PROPOSAL_PARENT_ID_INVALID",
            "Proposal parent Record Identity is invalid",
        ) from None

    try:
        record = RecordV1.from_mapping(
            {
                "envelope_version": 1,
                "type": TYPE_INTENT,
                "content": {
                    "version": 1,
                    "issuer": {"principal": reviewed.buyer_principal},
                    "subjects": [{"uri": reviewed.subject_uri}],
                    "action": {"id": reviewed.action_uri},
                    "terms": {},
                    "response_to": [parent_ref],
                },
                "profiles": [CORE_PROFILE, PROPOSAL_PROFILE],
            }
        )
        validate_market_record(record)
    except Exception:
        raise ProposalProfileError(
            "PROPOSAL_RECORD_INVALID",
            "structured Proposal could not be materialized as a valid Marketplace record",
        ) from None
    return record


__all__ = [
    "ProposalProfileError",
    "build_buyer_request_proposal_record",
]
