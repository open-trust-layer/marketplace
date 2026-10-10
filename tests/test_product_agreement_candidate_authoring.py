from __future__ import annotations

import unittest

from olp.encoding.record_identity import record_identity_text

from marketplace.application.agreement_candidate import (
    AgreementCandidateAuthoringError,
    MarketplaceAgreementCandidateAuthoringService,
)
from marketplace.application.listing import ExactDecimal, ProductListingDraft, UNIT_ITEM
from marketplace.application.proposal import BuyerRequestProposalDraft
from marketplace.application.state import MarketplaceApplicationStateService
from marketplace.reference.agreement_candidate_v1 import ACTION_BUY, build_product_agreement_candidate
from marketplace.reference.application_record_v1 import (
    decode_marketplace_application_record,
    prepare_marketplace_application_record,
)
from marketplace.reference.memory_application_v1 import MemoryApplicationStateStore
from marketplace.reference.product_listing_v1 import build_product_listing_record
from marketplace.reference.proposal_acceptance_v1 import build_proposal_acceptance_record
from marketplace.reference.proposal_v1 import build_buyer_request_proposal_record


SELLER = "urn:marketplace:test:seller"
BUYER = "urn:marketplace:test:buyer"
SUBJECT = "urn:marketplace:test:item:bicycle"


def _records():
    listing = build_product_listing_record(
        ProductListingDraft(
            seller_principal=SELLER,
            subject_uri=SUBJECT,
            title="Bicycle",
            description="Agreement candidate authoring test item",
            consideration=ExactDecimal(12500, 2),
            currency_code="EUR",
            quantity=ExactDecimal(1, 0),
            unit_uri=UNIT_ITEM,
            latitude_e6=52_090_700,
            longitude_e6=5_121_400,
        )
    )
    proposal = build_buyer_request_proposal_record(
        BuyerRequestProposalDraft(
            parent_record_id=record_identity_text(listing),
            buyer_principal=BUYER,
            subject_uri=SUBJECT,
            action_uri=ACTION_BUY,
        )
    )
    acceptance = build_proposal_acceptance_record(SELLER, record_identity_text(proposal))
    return listing, proposal, acceptance


def _state():
    store = MemoryApplicationStateStore()
    state = MarketplaceApplicationStateService(
        store=store,
        prepare_record=prepare_marketplace_application_record,
        decode_record=decode_marketplace_application_record,
    )
    state.initialize()
    return state


class ProductAgreementCandidateAuthoringTests(unittest.TestCase):
    def test_build_candidate_is_read_only_and_explicitly_unformed(self) -> None:
        state = _state()
        listing, proposal, acceptance = _records()
        state.publish(listing)
        state.publish(proposal)
        state.publish(acceptance)
        listing_id = record_identity_text(listing)
        proposal_id = record_identity_text(proposal)
        acceptance_id = record_identity_text(acceptance)
        watermark_before = state.sync_watermark()

        service = MarketplaceAgreementCandidateAuthoringService(
            state=state,
            build_record=build_product_agreement_candidate,
            record_identity=record_identity_text,
        )
        result = service.build_candidate(
            listing_record_id=listing_id,
            proposal_record_id=proposal_id,
            acceptance_record_id=acceptance_id,
        )

        self.assertEqual(result.record_id, record_identity_text(result.record))
        self.assertFalse(result.published)
        self.assertEqual(result.formation_evidence, "NOT_EVALUATED")
        self.assertEqual(state.sync_watermark(), watermark_before)
        self.assertEqual(result.to_document()["published"], False)

    def test_missing_source_fails_closed(self) -> None:
        state = _state()
        listing, proposal, acceptance = _records()
        state.publish(listing)
        state.publish(proposal)
        listing_id = record_identity_text(listing)
        proposal_id = record_identity_text(proposal)
        service = MarketplaceAgreementCandidateAuthoringService(
            state=state,
            build_record=build_product_agreement_candidate,
            record_identity=record_identity_text,
        )
        with self.assertRaises(AgreementCandidateAuthoringError) as caught:
            service.build_candidate(
                listing_record_id=listing_id,
                proposal_record_id=proposal_id,
                acceptance_record_id=record_identity_text(acceptance),
            )
        self.assertEqual(caught.exception.code, "AGREEMENT_CANDIDATE_SOURCE_NOT_FOUND")

    def test_builder_failure_is_stable_and_does_not_publish(self) -> None:
        state = _state()
        listing, proposal, acceptance = _records()
        for record in (listing, proposal, acceptance):
            state.publish(record)
        ids = [record_identity_text(record) for record in (listing, proposal, acceptance)]
        watermark_before = state.sync_watermark()

        def fail_builder(_listing, _proposal, _acceptance):
            raise RuntimeError("synthetic detail")

        service = MarketplaceAgreementCandidateAuthoringService(
            state=state,
            build_record=fail_builder,
            record_identity=record_identity_text,
        )
        with self.assertRaises(AgreementCandidateAuthoringError) as caught:
            service.build_candidate(
                listing_record_id=ids[0],
                proposal_record_id=ids[1],
                acceptance_record_id=ids[2],
            )
        self.assertEqual(caught.exception.code, "AGREEMENT_CANDIDATE_BUILD_FAILED")
        self.assertNotIn("synthetic detail", str(caught.exception))
        self.assertEqual(state.sync_watermark(), watermark_before)


if __name__ == "__main__":
    unittest.main()
