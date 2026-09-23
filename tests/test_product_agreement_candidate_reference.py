from __future__ import annotations

import unittest

from olp.encoding.record_identity import record_identity_text

from marketplace.application.listing import ExactDecimal, ProductListingDraft, UNIT_ITEM
from marketplace.application.proposal import BuyerRequestProposalDraft
from marketplace.reference.agreement_candidate_v1 import (
    ACTION_BUY,
    AGREEMENT_FORMATION_PROFILE,
    AgreementCandidateProfileError,
    SELLER_DELIVERY_COMMITMENT_ID,
    agreement_candidate_record_id,
    build_product_agreement_candidate,
)
from marketplace.reference.product_listing_v1 import build_product_listing_record
from marketplace.reference.proposal_acceptance_v1 import build_proposal_acceptance_record
from marketplace.reference.proposal_v1 import build_buyer_request_proposal_record
from marketplace.reference.record_v1 import TYPE_AGREEMENT, validate_market_record


SELLER = "urn:marketplace:test:seller"
BUYER = "urn:marketplace:test:buyer"
SUBJECT = "urn:marketplace:test:item:bicycle"


def _listing(*, seller: str = SELLER):
    return build_product_listing_record(
        ProductListingDraft(
            seller_principal=seller,
            subject_uri=SUBJECT,
            title="Bicycle",
            description="Agreement candidate test item",
            consideration=ExactDecimal(12500, 2),
            currency_code="EUR",
            quantity=ExactDecimal(1, 0),
            unit_uri=UNIT_ITEM,
            latitude_e6=52_090_700,
            longitude_e6=5_121_400,
        )
    )


def _proposal(listing, *, buyer: str = BUYER, subject: str = SUBJECT, action: str = ACTION_BUY):
    return build_buyer_request_proposal_record(
        BuyerRequestProposalDraft(
            parent_record_id=record_identity_text(listing),
            buyer_principal=buyer,
            subject_uri=subject,
            action_uri=action,
        )
    )


class ProductAgreementCandidateReferenceTests(unittest.TestCase):
    def test_builds_deterministic_unformed_market_agreement_candidate(self) -> None:
        listing = _listing()
        proposal = _proposal(listing)
        acceptance = build_proposal_acceptance_record(SELLER, record_identity_text(proposal))

        candidate = build_product_agreement_candidate(listing, proposal, acceptance)
        validate_market_record(candidate)

        self.assertEqual(candidate.type, TYPE_AGREEMENT)
        self.assertIn(AGREEMENT_FORMATION_PROFILE, candidate.profiles)
        self.assertEqual(
            {party["principal"] for party in candidate.content["parties"]},
            {SELLER, BUYER},
        )
        self.assertEqual(candidate.content["commitments"][0]["id"], SELLER_DELIVERY_COMMITMENT_ID)
        self.assertEqual(agreement_candidate_record_id(candidate), record_identity_text(candidate))
        self.assertEqual(
            record_identity_text(build_product_agreement_candidate(listing, proposal, acceptance)),
            record_identity_text(candidate),
        )
        self.assertNotIn("formation_evidence", candidate.content)

    def test_rejects_acceptance_for_different_proposal(self) -> None:
        listing = _listing()
        proposal = _proposal(listing)
        other = _proposal(listing, buyer="urn:marketplace:test:other-buyer")
        acceptance = build_proposal_acceptance_record(SELLER, record_identity_text(other))
        with self.assertRaises(AgreementCandidateProfileError) as caught:
            build_product_agreement_candidate(listing, proposal, acceptance)
        self.assertEqual(caught.exception.code, "AGREEMENT_CANDIDATE_ACCEPTANCE_MISMATCH")

    def test_rejects_acceptance_from_non_owner(self) -> None:
        listing = _listing()
        proposal = _proposal(listing)
        acceptance = build_proposal_acceptance_record(
            "urn:marketplace:test:not-seller",
            record_identity_text(proposal),
        )
        with self.assertRaises(AgreementCandidateProfileError) as caught:
            build_product_agreement_candidate(listing, proposal, acceptance)
        self.assertEqual(caught.exception.code, "AGREEMENT_CANDIDATE_SELLER_MISMATCH")

    def test_rejects_proposal_subject_mismatch(self) -> None:
        listing = _listing()
        proposal = _proposal(listing, subject="urn:marketplace:test:item:other")
        acceptance = build_proposal_acceptance_record(SELLER, record_identity_text(proposal))
        with self.assertRaises(AgreementCandidateProfileError) as caught:
            build_product_agreement_candidate(listing, proposal, acceptance)
        self.assertEqual(caught.exception.code, "AGREEMENT_CANDIDATE_PROPOSAL_SUBJECT_MISMATCH")


if __name__ == "__main__":
    unittest.main()
