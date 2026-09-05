from __future__ import annotations

import unittest

from olp import RecordV1
from olp.encoding.record_identity import record_identity_text

from marketplace.application.listing import ExactDecimal, ProductListingDraft, UNIT_ITEM
from marketplace.application.proposal import BuyerRequestProposalDraft
from marketplace.reference.application_record_v1 import (
    MarketplaceApplicationRecordError,
    decode_marketplace_application_record,
    is_marketplace_intent_record,
    marketplace_response_parent_ids,
    prepare_marketplace_application_record,
)
from marketplace.reference.product_listing_v1 import build_product_listing_record
from marketplace.reference.proposal_v1 import build_buyer_request_proposal_record
from marketplace.reference.record_v1 import CORE_PROFILE, TYPE_INTENT


def listing_record() -> RecordV1:
    return build_product_listing_record(
        ProductListingDraft(
            seller_principal="did:example:seller",
            subject_uri="urn:example:item:bicycle",
            title="Berlin bicycle",
            description="Canonical state adapter test",
            consideration=ExactDecimal(125, 2),
            currency_code="EUR",
            quantity=ExactDecimal(1, 0),
            unit_uri=UNIT_ITEM,
            latitude_e6=52_520_000,
            longitude_e6=13_405_000,
        )
    )


class M17ReferenceRecordStateAdapterTests(unittest.TestCase):
    def test_listing_prepare_decode_round_trip_preserves_exact_identity(self):
        record = listing_record()
        prepared = prepare_marketplace_application_record(record)
        self.assertEqual(prepared.record_id, record_identity_text(record))
        self.assertEqual(prepared.response_to, ())
        self.assertTrue(prepared.canonical_record.startswith(b"{"))
        decoded = decode_marketplace_application_record(prepared.canonical_record)
        self.assertIs(type(decoded), RecordV1)
        self.assertEqual(record_identity_text(decoded), prepared.record_id)
        self.assertEqual(decoded, record)
        self.assertTrue(is_marketplace_intent_record(decoded))

    def test_proposal_parent_extraction_matches_exact_parent_identity(self):
        parent = listing_record()
        parent_id = record_identity_text(parent)
        proposal = build_buyer_request_proposal_record(
            BuyerRequestProposalDraft(
                buyer_principal="did:example:buyer",
                subject_uri="urn:example:item:bicycle",
                action_uri="https://example.test/actions/buy",
                parent_record_id=parent_id,
            )
        )
        self.assertEqual(marketplace_response_parent_ids(proposal), (parent_id,))
        prepared = prepare_marketplace_application_record(proposal)
        self.assertEqual(prepared.response_to, (parent_id,))
        decoded = decode_marketplace_application_record(prepared.canonical_record)
        self.assertEqual(marketplace_response_parent_ids(decoded), (parent_id,))

    def test_intent_predicate_rejects_non_record_and_invalid_market_record(self):
        self.assertFalse(is_marketplace_intent_record(object()))
        invalid = RecordV1.from_mapping(
            {
                "envelope_version": 1,
                "type": TYPE_INTENT,
                "content": {
                    "version": 1,
                    "issuer": {"principal": "did:example:invalid"},
                    "subjects": [{"uri": "urn:example:item:invalid"}],
                    "action": {"id": "https://example.test/actions/sell"},
                    "terms": {},
                },
                "profiles": [],
            }
        )
        self.assertFalse(is_marketplace_intent_record(invalid))
        with self.assertRaises(MarketplaceApplicationRecordError) as caught:
            prepare_marketplace_application_record(invalid)
        self.assertEqual(caught.exception.code, "APPLICATION_RECORD_INVALID")

    def test_decode_rejects_noncanonical_equivalent_json_bytes(self):
        canonical = prepare_marketplace_application_record(listing_record()).canonical_record
        with self.assertRaises(MarketplaceApplicationRecordError) as caught:
            decode_marketplace_application_record(b" " + canonical)
        self.assertEqual(caught.exception.code, "APPLICATION_RECORD_NON_CANONICAL")

    def test_decode_rejects_wrong_transport_message_type(self):
        canonical = prepare_marketplace_application_record(listing_record()).canonical_record
        tampered = canonical.replace(b'"type":"record"', b'"type":"proof"', 1)
        self.assertNotEqual(tampered, canonical)
        with self.assertRaises(MarketplaceApplicationRecordError) as caught:
            decode_marketplace_application_record(tampered)
        self.assertEqual(caught.exception.code, "APPLICATION_RECORD_DECODING_FAILED")

    def test_root_intent_parent_extractor_is_empty(self):
        record = listing_record()
        self.assertEqual(marketplace_response_parent_ids(record), ())
        self.assertIn(CORE_PROFILE, record.profiles)


if __name__ == "__main__":
    unittest.main()
