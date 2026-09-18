from __future__ import annotations

import unittest

from olp.encoding.record_identity import record_identity_text

from marketplace.application.listing import ExactDecimal, ProductListingDraft, UNIT_ITEM
from marketplace.application.proposal import BuyerRequestProposalDraft
from marketplace.reference.product_listing_v1 import build_product_listing_record
from marketplace.reference.proposal_acceptance_v1 import (
    EVENT_PROPOSAL_ACCEPTANCE,
    ProposalAcceptanceProfileError,
    build_proposal_acceptance_record,
    is_marketplace_proposal_record,
    proposal_acceptance_proposal_id,
    proposal_acceptance_record_id,
)
from marketplace.reference.proposal_v1 import build_buyer_request_proposal_record
from marketplace.reference.record_v1 import BASE, CORE_PROFILE, TYPE_EVENT


SELLER = "did:example:seller"
BUYER = "did:example:buyer"


def listing_record():
    return build_product_listing_record(ProductListingDraft(
        seller_principal=SELLER,
        subject_uri="urn:sku:moon-widget",
        title="Moon widget",
        description="Reviewed product listing.",
        consideration=ExactDecimal(12500, 2),
        currency_code="EUR",
        quantity=ExactDecimal(1, 0),
        unit_uri=UNIT_ITEM,
        latitude_e6=52090700,
        longitude_e6=5121400,
    ))


class ProposalAcceptanceReferenceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.listing = listing_record()
        self.listing_id = record_identity_text(self.listing)
        self.proposal = build_buyer_request_proposal_record(BuyerRequestProposalDraft(
            buyer_principal=BUYER,
            subject_uri="urn:sku:moon-widget",
            action_uri=f"{BASE}/action/request",
            parent_record_id=self.listing_id,
        ))
        self.proposal_id = record_identity_text(self.proposal)

    def test_exact_proposal_and_acceptance_profile(self) -> None:
        self.assertTrue(is_marketplace_proposal_record(self.proposal))
        self.assertFalse(is_marketplace_proposal_record(self.listing))
        acceptance = build_proposal_acceptance_record(SELLER, self.proposal_id)
        self.assertEqual(acceptance.type, TYPE_EVENT)
        self.assertEqual(acceptance.profiles, (CORE_PROFILE,))
        self.assertEqual(acceptance.content["version"], 1)
        self.assertEqual(acceptance.content["issuer"]["principal"], SELLER)
        self.assertEqual(acceptance.content["event"], EVENT_PROPOSAL_ACCEPTANCE)
        self.assertEqual(proposal_acceptance_proposal_id(acceptance), self.proposal_id)
        acceptance_id = proposal_acceptance_record_id(acceptance)
        self.assertEqual(acceptance_id, record_identity_text(acceptance))

    def test_builder_rejects_noncanonical_proposal_identity(self) -> None:
        for value in ("", "not a record id", "/r1_x", "r1_x?query"):
            with self.subTest(value=value):
                with self.assertRaises(ProposalAcceptanceProfileError):
                    build_proposal_acceptance_record(SELLER, value)

    def test_acceptance_profile_rejects_wrong_event(self) -> None:
        good = build_proposal_acceptance_record(SELLER, self.proposal_id)
        wrong = type(good).from_mapping({
            "envelope_version": 1,
            "type": TYPE_EVENT,
            "content": {
                "version": 1,
                "issuer": {"principal": SELLER},
                "event": f"{BASE}/event/proposal-decline",
                "related_records": list(good.content["related_records"]),
            },
            "profiles": [CORE_PROFILE],
        })
        with self.assertRaises(ProposalAcceptanceProfileError):
            proposal_acceptance_proposal_id(wrong)


if __name__ == "__main__":
    unittest.main()
