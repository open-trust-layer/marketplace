from __future__ import annotations

import unittest

from olp.encoding.record_identity import record_identity_text

from marketplace.application.listing import ExactDecimal, ProductListingDraft, UNIT_ITEM
from marketplace.application.proposal import BuyerRequestProposalDraft
from marketplace.application.proposal_acceptance_resolution import (
    MarketplaceProposalAcceptanceResolutionService,
    ProposalAcceptanceResolutionError,
)
from marketplace.application.state import MarketplaceApplicationStateService
from marketplace.reference.agreement_candidate_v1 import ACTION_BUY
from marketplace.reference.application_record_v1 import (
    decode_marketplace_application_record,
    marketplace_record_issuer_principal,
    marketplace_response_parent_ids,
    prepare_marketplace_application_record,
)
from marketplace.reference.memory_application_v1 import MemoryApplicationStateStore
from marketplace.reference.product_listing_v1 import (
    build_product_listing_record,
    extract_product_listing,
)
from marketplace.reference.proposal_acceptance_v1 import (
    build_proposal_acceptance_record,
    is_marketplace_proposal_record,
    proposal_acceptance_proposal_id,
)
from marketplace.reference.proposal_v1 import build_buyer_request_proposal_record


SELLER = "urn:marketplace:test:seller"
BUYER = "urn:marketplace:test:buyer"
OTHER = "urn:marketplace:test:other"
SUBJECT = "urn:marketplace:test:item:acceptance-resolution"


def records():
    listing = build_product_listing_record(
        ProductListingDraft(
            seller_principal=SELLER,
            subject_uri=SUBJECT,
            title="Acceptance resolution item",
            description="Deterministic Proposal acceptance resolution fixture.",
            consideration=ExactDecimal(4200, 2),
            currency_code="EUR",
            quantity=ExactDecimal(1, 0),
            unit_uri=UNIT_ITEM,
            latitude_e6=50_110_900,
            longitude_e6=8_682_100,
        )
    )
    listing_id = record_identity_text(listing)
    proposal = build_buyer_request_proposal_record(
        BuyerRequestProposalDraft(
            buyer_principal=BUYER,
            subject_uri=SUBJECT,
            action_uri=ACTION_BUY,
            parent_record_id=listing_id,
        )
    )
    proposal_id = record_identity_text(proposal)
    acceptance = build_proposal_acceptance_record(SELLER, proposal_id)
    return listing, proposal, acceptance


def state_with(*values):
    store = MemoryApplicationStateStore()
    state = MarketplaceApplicationStateService(
        store=store,
        prepare_record=prepare_marketplace_application_record,
        decode_record=decode_marketplace_application_record,
    )
    state.initialize()
    for value in values:
        state.publish(value)
    return state


def service(state):
    return MarketplaceProposalAcceptanceResolutionService(
        state=state,
        is_proposal_record=is_marketplace_proposal_record,
        proposal_parent_ids=marketplace_response_parent_ids,
        extract_product_listing=extract_product_listing,
        record_principal=marketplace_record_issuer_principal,
        build_acceptance_record=build_proposal_acceptance_record,
        acceptance_proposal_id=proposal_acceptance_proposal_id,
        record_identity=record_identity_text,
    )


class ProductProposalAcceptanceResolutionTests(unittest.TestCase):
    def test_buyer_and_seller_resolve_same_published_canonical_acceptance(self) -> None:
        listing, proposal, acceptance = records()
        state = state_with(listing, proposal, acceptance)
        proposal_id = record_identity_text(proposal)
        acceptance_id = record_identity_text(acceptance)
        watermark = state.sync_watermark()
        resolver = service(state)

        buyer = resolver.resolve(principal=BUYER, proposal_record_id=proposal_id)
        seller = resolver.resolve(principal=SELLER, proposal_record_id=proposal_id)

        self.assertEqual(buyer, seller)
        self.assertEqual(
            buyer.to_document(),
            {
                "proposal_record_id": proposal_id,
                "record_id": acceptance_id,
            },
        )
        self.assertEqual(state.sync_watermark(), watermark)

    def test_non_party_is_rejected_before_acceptance_disclosure(self) -> None:
        listing, proposal, acceptance = records()
        state = state_with(listing, proposal, acceptance)
        with self.assertRaises(ProposalAcceptanceResolutionError) as caught:
            service(state).resolve(
                principal=OTHER,
                proposal_record_id=record_identity_text(proposal),
            )
        self.assertEqual(
            caught.exception.code,
            "PROPOSAL_ACCEPTANCE_RESOLUTION_PARTY_REQUIRED",
        )

    def test_unpublished_acceptance_is_not_inferred_as_present(self) -> None:
        listing, proposal, _ = records()
        state = state_with(listing, proposal)
        with self.assertRaises(ProposalAcceptanceResolutionError) as caught:
            service(state).resolve(
                principal=BUYER,
                proposal_record_id=record_identity_text(proposal),
            )
        self.assertEqual(
            caught.exception.code,
            "PROPOSAL_ACCEPTANCE_RESOLUTION_NOT_FOUND",
        )

    def test_resolution_uses_deterministic_identity_without_response_or_sync_scan(self) -> None:
        listing, proposal, acceptance = records()
        state = state_with(listing, proposal, acceptance)
        resolver = service(state)

        def forbidden(*_args, **_kwargs):
            raise AssertionError("ambient scan must not be used")

        state.response_ids = forbidden
        state.sync_since = forbidden
        result = resolver.resolve(
            principal=BUYER,
            proposal_record_id=record_identity_text(proposal),
        )
        self.assertEqual(result.record_id, record_identity_text(acceptance))

    def test_stored_acceptance_is_revalidated_against_exact_proposal_and_seller(self) -> None:
        listing, proposal, acceptance = records()
        state = state_with(listing, proposal, acceptance)
        calls = []

        def relation(record):
            calls.append(record)
            return proposal_acceptance_proposal_id(record)

        resolver = MarketplaceProposalAcceptanceResolutionService(
            state=state,
            is_proposal_record=is_marketplace_proposal_record,
            proposal_parent_ids=marketplace_response_parent_ids,
            extract_product_listing=extract_product_listing,
            record_principal=marketplace_record_issuer_principal,
            build_acceptance_record=build_proposal_acceptance_record,
            acceptance_proposal_id=relation,
            record_identity=record_identity_text,
        )
        result = resolver.resolve(
            principal=BUYER,
            proposal_record_id=record_identity_text(proposal),
        )
        self.assertEqual(result.record_id, record_identity_text(acceptance))
        self.assertEqual(len(calls), 1)


if __name__ == "__main__":
    unittest.main()
