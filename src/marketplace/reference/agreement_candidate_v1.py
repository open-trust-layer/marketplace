"""Reference authoring for one product Agreement candidate.

This module constructs deterministic MarketAgreement evidence from an exact
structured product listing, one buyer Proposal, and one seller Proposal-
acceptance event. It does not publish, sign, or evaluate formation.
"""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from olp import RecordV1
from olp.encoding.deterministic_cbor import encode as olp_encode
from olp.encoding.record_identity import record_identity_text
from olp.evidence import record_ref

from ..application.listing import ACTION_SELL
from .application_record_v1 import (
    marketplace_record_issuer_principal,
    marketplace_response_parent_ids,
)
from .product_listing_v1 import extract_product_listing
from .proposal_acceptance_v1 import (
    is_marketplace_proposal_record,
    proposal_acceptance_proposal_id,
)
from .record_v1 import BASE, CORE_PROFILE, TYPE_AGREEMENT, validate_market_record


ACTION_BUY = f"{BASE}/action/buy"
AGREEMENT_FORMATION_PROFILE = f"{BASE}/profile/agreement-formation-v1"
SELLER_DELIVERY_COMMITMENT_ID = "seller-delivery"


class AgreementCandidateProfileError(ValueError):
    """Stable product Agreement-candidate validation failure."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def _fail(code: str, message: str) -> None:
    raise AgreementCandidateProfileError(code, message) from None


def _plain(value: object) -> object:
    if isinstance(value, Mapping):
        return {str(key): _plain(item) for key, item in value.items()}
    if type(value) is tuple:
        return tuple(_plain(item) for item in value)
    return value


def _sort_set(values: tuple[object, ...]) -> tuple[object, ...]:
    return tuple(sorted(values, key=olp_encode))


def _proposal_product_binding(
    proposal: object,
    *,
    listing_record_id: str,
    listing_subject_uri: str,
) -> str:
    if not is_marketplace_proposal_record(proposal):
        _fail("AGREEMENT_CANDIDATE_PROPOSAL_INVALID", "Proposal is invalid")
    try:
        parents = marketplace_response_parent_ids(proposal)
    except Exception:
        _fail("AGREEMENT_CANDIDATE_PROPOSAL_INVALID", "Proposal parent binding is invalid")
    if parents != (listing_record_id,):
        _fail("AGREEMENT_CANDIDATE_PROPOSAL_PARENT_MISMATCH", "Proposal does not target the exact listing")

    content = proposal.content
    if not isinstance(content, Mapping):
        _fail("AGREEMENT_CANDIDATE_PROPOSAL_INVALID", "Proposal content is invalid")
    subjects = content.get("subjects")
    action = content.get("action")
    terms = content.get("terms")
    if type(subjects) is not tuple or len(subjects) != 1 or not isinstance(subjects[0], Mapping):
        _fail("AGREEMENT_CANDIDATE_PROPOSAL_INVALID", "Proposal subject shape changed")
    if set(subjects[0]) != {"uri"} or subjects[0].get("uri") != listing_subject_uri:
        _fail("AGREEMENT_CANDIDATE_PROPOSAL_SUBJECT_MISMATCH", "Proposal subject does not match listing")
    if not isinstance(action, Mapping) or set(action) != {"id"} or action.get("id") != ACTION_BUY:
        _fail("AGREEMENT_CANDIDATE_PROPOSAL_ACTION_MISMATCH", "Proposal is not the reviewed buy action")
    if not isinstance(terms, Mapping) or len(terms) != 0:
        _fail("AGREEMENT_CANDIDATE_PROPOSAL_TERMS_UNSUPPORTED", "Proposal terms are outside this product profile")
    try:
        return marketplace_record_issuer_principal(proposal)
    except Exception:
        _fail("AGREEMENT_CANDIDATE_BUYER_INVALID", "Proposal buyer principal is invalid")


def build_product_agreement_candidate(
    listing: object,
    proposal: object,
    acceptance: object,
) -> RecordV1:
    """Build one deterministic, unpublished Agreement candidate."""
    try:
        listing_draft = extract_product_listing(listing)
        listing_id = record_identity_text(listing)
        proposal_id = record_identity_text(proposal)
    except Exception:
        _fail("AGREEMENT_CANDIDATE_INPUT_INVALID", "listing or Proposal could not be reviewed")

    buyer = _proposal_product_binding(
        proposal,
        listing_record_id=listing_id,
        listing_subject_uri=listing_draft.subject_uri,
    )
    seller = listing_draft.seller_principal
    if buyer == seller:
        _fail("AGREEMENT_CANDIDATE_PARTICIPANTS_INVALID", "seller and buyer MUST be distinct")

    try:
        accepted_proposal_id = proposal_acceptance_proposal_id(acceptance)
        acceptance_seller = marketplace_record_issuer_principal(acceptance)
        acceptance_id = record_identity_text(acceptance)
    except Exception:
        _fail("AGREEMENT_CANDIDATE_ACCEPTANCE_INVALID", "Proposal acceptance is invalid")
    if accepted_proposal_id != proposal_id:
        _fail("AGREEMENT_CANDIDATE_ACCEPTANCE_MISMATCH", "acceptance does not target the exact Proposal")
    if acceptance_seller != seller:
        _fail("AGREEMENT_CANDIDATE_SELLER_MISMATCH", "acceptance issuer does not match listing seller")

    try:
        subjects = tuple(_plain(item) for item in listing.content["subjects"])
        terms = _plain(listing.content["terms"])
        seller_party = {"principal": seller}
        buyer_party = {"principal": buyer}
        commitment = {
            "id": SELLER_DELIVERY_COMMITMENT_ID,
            "party": seller_party,
            "action": {"id": ACTION_SELL},
            "subjects": subjects,
        }
        record = RecordV1(
            envelope_version=1,
            type=TYPE_AGREEMENT,
            content={
                "version": 1,
                "parties": _sort_set((seller_party, buyer_party)),
                "subjects": subjects,
                "actions": _sort_set(({"id": ACTION_SELL}, {"id": ACTION_BUY})),
                "terms": terms,
                "commitments": (commitment,),
                "source_records": _sort_set(
                    (
                        record_ref(listing).to_value(),
                        record_ref(proposal).to_value(),
                        record_ref(acceptance).to_value(),
                    )
                ),
            },
            profiles=(CORE_PROFILE, AGREEMENT_FORMATION_PROFILE),
        )
        validate_market_record(record)
        record_identity_text(record)
    except AgreementCandidateProfileError:
        raise
    except Exception:
        _fail("AGREEMENT_CANDIDATE_BUILD_FAILED", "Agreement candidate could not be built")
    return record


def agreement_candidate_record_id(record: object) -> str:
    """Return identity only for one valid Agreement-formation candidate."""
    if type(record) is not RecordV1:
        _fail("AGREEMENT_CANDIDATE_RECORD_INVALID", "candidate MUST be exact RecordV1")
    try:
        validate_market_record(record)
    except Exception:
        _fail("AGREEMENT_CANDIDATE_RECORD_INVALID", "candidate is not a valid Marketplace record")
    if record.type != TYPE_AGREEMENT or AGREEMENT_FORMATION_PROFILE not in record.profiles:
        _fail("AGREEMENT_CANDIDATE_RECORD_INVALID", "candidate Agreement profile changed")
    try:
        return record_identity_text(record)
    except Exception:
        _fail("AGREEMENT_CANDIDATE_IDENTITY_FAILED", "candidate identity could not be derived")


__all__ = [
    "ACTION_BUY",
    "AGREEMENT_FORMATION_PROFILE",
    "AgreementCandidateProfileError",
    "SELLER_DELIVERY_COMMITMENT_ID",
    "agreement_candidate_record_id",
    "build_product_agreement_candidate",
]
