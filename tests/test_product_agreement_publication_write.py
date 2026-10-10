from __future__ import annotations

import unittest

from olp.encoding.record_identity import record_identity_text

from marketplace.application.agreement_candidate import AgreementCandidateBuildResult
from marketplace.application.agreement_publication import AgreementPublicationPreflightResult
from marketplace.application.agreement_publication_write import (
    AgreementPublicationWriteError,
    MarketplaceAgreementPublicationService,
)
from marketplace.application.listing import ExactDecimal, ProductListingDraft, UNIT_ITEM
from marketplace.application.proposal import BuyerRequestProposalDraft
from marketplace.application.state import MarketplaceApplicationStateService
from marketplace.reference.agreement_candidate_v1 import (
    ACTION_BUY,
    build_product_agreement_candidate,
)
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


def _state() -> MarketplaceApplicationStateService:
    store = MemoryApplicationStateStore()
    state = MarketplaceApplicationStateService(
        store=store,
        prepare_record=prepare_marketplace_application_record,
        decode_record=decode_marketplace_application_record,
    )
    state.initialize()
    return state


def _candidate() -> AgreementCandidateBuildResult:
    listing = build_product_listing_record(
        ProductListingDraft(
            seller_principal=SELLER,
            subject_uri=SUBJECT,
            title="Bicycle",
            description="Agreement publication write test item",
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
    agreement = build_product_agreement_candidate(listing, proposal, acceptance)
    return AgreementCandidateBuildResult(
        record=agreement,
        record_id=record_identity_text(agreement),
        listing_record_id=record_identity_text(listing),
        proposal_record_id=record_identity_text(proposal),
        acceptance_record_id=record_identity_text(acceptance),
    )


def _positive_preflight(candidate: AgreementCandidateBuildResult) -> AgreementPublicationPreflightResult:
    return AgreementPublicationPreflightResult(
        agreement_record_id=candidate.record_id,
        actor_principal=SELLER,
        formation_evidence="EVIDENCE_SUFFICIENT_FOR_PROFILE",
        required_principals=(BUYER, SELLER),
        preconditions_satisfied=True,
        reason="PRECONDITIONS_SATISFIED",
    )


class ProductAgreementPublicationWriteTests(unittest.TestCase):
    def test_positive_preflight_publishes_exact_candidate_once(self) -> None:
        state = _state()
        candidate = _candidate()
        service = MarketplaceAgreementPublicationService(
            state=state,
            record_identity=record_identity_text,
        )
        watermark_before = state.sync_watermark()

        result = service.publish(
            candidate=candidate,
            preflight=_positive_preflight(candidate),
        )

        self.assertEqual(result.record_id, candidate.record_id)
        self.assertEqual(record_identity_text(state.peek(candidate.record_id)), candidate.record_id)
        self.assertGreater(state.sync_watermark(), watermark_before)

    def test_negative_preflight_never_mutates_state(self) -> None:
        state = _state()
        candidate = _candidate()
        negative = AgreementPublicationPreflightResult(
            agreement_record_id=candidate.record_id,
            actor_principal=SELLER,
            formation_evidence="EVIDENCE_INCOMPLETE",
            required_principals=(BUYER, SELLER),
            preconditions_satisfied=False,
            reason="FORMATION_EVIDENCE_INCOMPLETE",
        )
        service = MarketplaceAgreementPublicationService(
            state=state,
            record_identity=record_identity_text,
        )
        watermark_before = state.sync_watermark()

        with self.assertRaises(AgreementPublicationWriteError) as caught:
            service.publish(candidate=candidate, preflight=negative)

        self.assertEqual(caught.exception.code, "AGREEMENT_PUBLICATION_PREFLIGHT_NOT_SATISFIED")
        self.assertEqual(state.sync_watermark(), watermark_before)
        self.assertIsNone(state.peek(candidate.record_id))

    def test_preflight_for_other_agreement_never_mutates_state(self) -> None:
        state = _state()
        candidate = _candidate()
        wrong = AgreementPublicationPreflightResult(
            agreement_record_id="r1_other-agreement",
            actor_principal=SELLER,
            formation_evidence="EVIDENCE_SUFFICIENT_FOR_PROFILE",
            required_principals=(BUYER, SELLER),
            preconditions_satisfied=True,
            reason="PRECONDITIONS_SATISFIED",
        )
        service = MarketplaceAgreementPublicationService(
            state=state,
            record_identity=record_identity_text,
        )
        watermark_before = state.sync_watermark()

        with self.assertRaises(AgreementPublicationWriteError) as caught:
            service.publish(candidate=candidate, preflight=wrong)

        self.assertEqual(caught.exception.code, "AGREEMENT_PUBLICATION_BINDING_MISMATCH")
        self.assertEqual(state.sync_watermark(), watermark_before)

    def test_candidate_identity_is_reverified_before_write(self) -> None:
        state = _state()
        candidate = _candidate()
        service = MarketplaceAgreementPublicationService(
            state=state,
            record_identity=lambda _record: "r1_different",
        )
        watermark_before = state.sync_watermark()

        with self.assertRaises(AgreementPublicationWriteError) as caught:
            service.publish(
                candidate=candidate,
                preflight=_positive_preflight(candidate),
            )

        self.assertEqual(caught.exception.code, "AGREEMENT_PUBLICATION_IDENTITY_MISMATCH")
        self.assertEqual(state.sync_watermark(), watermark_before)

    def test_positive_flag_with_noncanonical_reason_is_rejected(self) -> None:
        state = _state()
        candidate = _candidate()
        hostile = AgreementPublicationPreflightResult(
            agreement_record_id=candidate.record_id,
            actor_principal=SELLER,
            formation_evidence="EVIDENCE_SUFFICIENT_FOR_PROFILE",
            required_principals=(BUYER, SELLER),
            preconditions_satisfied=True,
            reason="SYNTHETIC_PROMOTION",
        )
        service = MarketplaceAgreementPublicationService(
            state=state,
            record_identity=record_identity_text,
        )
        watermark_before = state.sync_watermark()

        with self.assertRaises(AgreementPublicationWriteError) as caught:
            service.publish(candidate=candidate, preflight=hostile)

        self.assertEqual(caught.exception.code, "AGREEMENT_PUBLICATION_PREFLIGHT_NOT_SATISFIED")
        self.assertEqual(state.sync_watermark(), watermark_before)


if __name__ == "__main__":
    unittest.main()
