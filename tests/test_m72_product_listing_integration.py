from __future__ import annotations

import unittest

from olp import RecordV1

from marketplace.application import LocalMarketplaceApplication
from marketplace.application.listing import (
    ACTION_SELL,
    CORE_PROFILE,
    PRODUCT_LISTING_PROFILE,
    TERM_TITLE,
    UNIT_ITEM,
    ExactDecimal,
    ProductListingDraft,
    build_product_listing_mapping,
)
from marketplace.reference import (
    evaluate_discovery,
    evaluate_match,
    record_identity_text,
    validate_market_record,
)
from marketplace.reference.product_listing_v1 import (
    ProductListingProfileError,
    build_product_listing_record,
    extract_product_listing,
)
from marketplace.runtime import create_in_memory_runtime


class FakeExpiryHandle:
    def cancel(self) -> None:
        pass


class FakeExpiryScheduler:
    def schedule(self, _delay_seconds: float, _callback):
        return FakeExpiryHandle()


class M72ProductListingIntegrationTests(unittest.TestCase):
    def _draft(self) -> ProductListingDraft:
        return ProductListingDraft(
            seller_principal="did:example:alice",
            subject_uri="urn:example:product:bicycle-1",
            title="City bicycle",
            description="Reliable commuter bicycle",
            consideration=ExactDecimal.from_minor_units(12_500, scale=2),
            currency_code="EUR",
            quantity=ExactDecimal(1, 0),
            unit_uri=UNIT_ITEM,
            latitude_e6=52_520_000,
            longitude_e6=13_405_000,
        )

    def test_reference_builder_emits_genuine_valid_market_intent_and_extracts_listing(self):
        draft = self._draft()
        record = build_product_listing_record(draft)

        self.assertIs(type(record), RecordV1)
        validate_market_record(record)
        self.assertEqual(record.profiles, (CORE_PROFILE, PRODUCT_LISTING_PROFILE))
        extracted = extract_product_listing(record)
        self.assertEqual(extracted, draft)

    def test_listing_round_trips_through_m71_local_application(self):
        record = build_product_listing_record(self._draft())
        runtime = create_in_memory_runtime(
            validate_record=validate_market_record,
            record_identity_text=record_identity_text,
            evaluate_discovery=evaluate_discovery,
            evaluate_match=evaluate_match,
            scheduler=FakeExpiryScheduler(),
        )
        self.addCleanup(runtime.close)
        app = LocalMarketplaceApplication(
            node=runtime.node,
            discovery=runtime.discovery,
            source="urn:marketplace:local",
        )

        published = app.publish(record)
        self.assertIs(app.get(published.record_id), record)
        result = app.search(
            {"version": 1, "action_ids_any": [ACTION_SELL]},
            max_records=8,
        )
        self.assertEqual(result.record_ids, (published.record_id,))
        self.assertEqual(extract_product_listing(result.records[0]), self._draft())
        self.assertEqual(runtime.repository.retention_class, "EPHEMERAL")
        self.assertEqual(runtime.repository.retention_seconds, 10.0)

    def test_extractor_rejects_hostile_non_record_before_attribute_execution(self):
        touched: list[str] = []

        class Hostile:
            def __getattribute__(self, name: str):
                touched.append(name)
                raise AssertionError("hostile object MUST NOT be inspected")

        with self.assertRaises(ProductListingProfileError) as caught:
            extract_product_listing(Hostile())
        self.assertEqual(caught.exception.code, "PRODUCT_LISTING_RECORD_INVALID")
        self.assertEqual(touched, [])

    def test_extractor_requires_exact_listing_profile_set(self):
        mapping = build_product_listing_mapping(self._draft())
        mapping["profiles"] = [CORE_PROFILE]
        record = RecordV1.from_mapping(mapping)
        validate_market_record(record)
        with self.assertRaises(ProductListingProfileError) as caught:
            extract_product_listing(record)
        self.assertEqual(caught.exception.code, "PRODUCT_LISTING_PROFILE_REQUIRED")

    def test_extractor_rejects_core_valid_listing_term_drift(self):
        mapping = build_product_listing_mapping(self._draft())
        mapping["content"]["terms"][TERM_TITLE] = 7
        record = RecordV1.from_mapping(mapping)
        validate_market_record(record)
        with self.assertRaises(ProductListingProfileError) as caught:
            extract_product_listing(record)
        self.assertEqual(caught.exception.code, "PRODUCT_LISTING_SHAPE_INVALID")

    def test_extractor_accepts_equivalent_profile_ordering(self):
        mapping = build_product_listing_mapping(self._draft())
        mapping["profiles"] = [PRODUCT_LISTING_PROFILE, CORE_PROFILE]
        record = RecordV1.from_mapping(mapping)
        validate_market_record(record)
        self.assertEqual(extract_product_listing(record), self._draft())

    def test_extractor_rejects_hostile_rebound_content_before_mapping_execution(self):
        record = build_product_listing_record(self._draft())
        touched: list[str] = []

        class HostileMapping(dict):
            def items(self):
                touched.append("items")
                raise AssertionError("hostile mapping MUST NOT execute")

            def __iter__(self):
                touched.append("iter")
                raise AssertionError("hostile mapping MUST NOT execute")

        object.__setattr__(record, "content", HostileMapping())
        with self.assertRaises(ProductListingProfileError) as caught:
            extract_product_listing(record)
        self.assertEqual(caught.exception.code, "PRODUCT_LISTING_RECORD_INVALID")
        self.assertEqual(touched, [])

    def test_extractor_rejects_unreviewed_additional_profile(self):
        mapping = build_product_listing_mapping(self._draft())
        mapping["profiles"].append("https://example.test/profile/extra")
        record = RecordV1.from_mapping(mapping)
        validate_market_record(record)
        with self.assertRaises(ProductListingProfileError) as caught:
            extract_product_listing(record)
        self.assertEqual(caught.exception.code, "PRODUCT_LISTING_PROFILE_SET_INVALID")


if __name__ == "__main__":
    unittest.main()
