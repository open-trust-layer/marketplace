from __future__ import annotations

import unittest

from marketplace.application.api import (
    ApplicationApiError,
    IntentIndexPage,
    MarketplaceApplicationApiService,
)
from marketplace.application.listing import ProductListingDraft, UNIT_ITEM
from marketplace.application.postgres_state import (
    ApplicationStatePutResult,
    ExpiryResult,
    StoreDisposition,
)
from marketplace.application.authoring import (
    MarketplaceProductListingAuthoringService,
    ProductListingAuthoringError,
    ProductListingAuthoringFields,
)


class FakeStateService:
    def __init__(self) -> None:
        self.publish_calls: list[object] = []

    def initialize(self):
        return ExpiryResult((), ())

    def publish(self, record):
        self.publish_calls.append(record)
        return ApplicationStatePutResult(StoreDisposition.STORED, 7)

    def peek(self, record_id):
        return None

    def get(self, record_id):
        return None

    def response_ids(self, record_id, *, limit=64):
        return ()

    def sync_since(self, cursor, *, limit=128):
        raise AssertionError("sync is outside M17.1Q")

    def sync_watermark(self):
        return 0


class FakeIntentQuery:
    def list_intent_ids(self, *, cursor, limit):
        return IntentIndexPage((), None)


class M17StructuredProductAuthoringTests(unittest.TestCase):
    def make_api(self):
        state = FakeStateService()
        parents: dict[int, tuple[str, ...]] = {}
        api = MarketplaceApplicationApiService(
            state=state,
            intent_query=FakeIntentQuery(),            response_parent_ids=lambda record: tuple(parents.get(id(record), ())),
            is_intent_record=lambda record: True,
        )
        return api, state, parents

    def fields(self, **changes):
        values = {
            "seller_principal": "did:example:seller",
            "subject_uri": "urn:sku:moon-widget",
            "title": "Moon widget",
            "description": "A bounded structured Marketplace listing.",
            "consideration_coefficient": 1299,
            "consideration_scale": 2,
            "currency_code": "USD",
            "quantity_coefficient": 1,
            "quantity_scale": 0,
            "unit_uri": UNIT_ITEM,
            "latitude_e6": 52_520_000,
            "longitude_e6": 13_405_000,
        }
        values.update(changes)
        return ProductListingAuthoringFields(**values)

    def test_structured_fields_reuse_m72_draft_and_publish_once(self):
        api, state, _ = self.make_api()
        api.initialize()
        built: list[ProductListingDraft] = []
        record = object()
        def build(draft: ProductListingDraft):
            built.append(draft)
            return record

        service = MarketplaceProductListingAuthoringService(
            api=api,
            build_record=build,
        )
        result = service.create_product_listing(self.fields())

        self.assertEqual(result.change_seq, 7)
        self.assertEqual(state.publish_calls, [record])
        self.assertEqual(len(built), 1)
        draft = built[0]
        self.assertEqual(draft.title, "Moon widget")
        self.assertEqual(draft.consideration.coefficient, 1299)
        self.assertEqual(draft.consideration.scale, 2)
        self.assertEqual(draft.quantity.coefficient, 1)
        self.assertEqual(draft.latitude_e6, 52_520_000)

    def test_invalid_structured_fields_fail_before_builder_or_publish(self):
        api, state, _ = self.make_api()
        api.initialize()
        build_calls: list[object] = []
        service = MarketplaceProductListingAuthoringService(
            api=api,
            build_record=lambda draft: build_calls.append(draft),
        )
        with self.assertRaises(ProductListingAuthoringError) as caught:
            service.create_product_listing(self.fields(title=""))

        self.assertEqual(caught.exception.code, "PRODUCT_LISTING_FIELDS_INVALID")
        self.assertEqual(build_calls, [])
        self.assertEqual(state.publish_calls, [])

    def test_builder_failure_is_stable_and_non_reflective(self):
        api, state, _ = self.make_api()
        api.initialize()

        def fail_builder(draft):
            raise RuntimeError("secret builder detail")

        service = MarketplaceProductListingAuthoringService(
            api=api,
            build_record=fail_builder,
        )
        with self.assertRaises(ProductListingAuthoringError) as caught:
            service.create_product_listing(self.fields())

        self.assertEqual(caught.exception.code, "PRODUCT_LISTING_BUILD_FAILED")
        self.assertNotIn("secret", str(caught.exception).lower())
        self.assertIsNone(caught.exception.__cause__)
        self.assertEqual(state.publish_calls, [])

    def test_response_bound_builder_output_is_rejected_by_existing_api(self):
        api, state, parents = self.make_api()
        api.initialize()
        record = object()
        parents[id(record)] = ("r-parent",)
        service = MarketplaceProductListingAuthoringService(
            api=api,
            build_record=lambda draft: record,
        )

        with self.assertRaises(ApplicationApiError) as caught:
            service.create_product_listing(self.fields())

        self.assertEqual(caught.exception.code, "ROOT_INTENT_RESPONSE_FORBIDDEN")
        self.assertEqual(state.publish_calls, [])

    def test_uninitialized_application_api_remains_authoritative(self):
        api, state, _ = self.make_api()
        service = MarketplaceProductListingAuthoringService(
            api=api,
            build_record=lambda draft: object(),
        )

        with self.assertRaises(ApplicationApiError) as caught:
            service.create_product_listing(self.fields())

        self.assertEqual(caught.exception.code, "APPLICATION_API_NOT_INITIALIZED")
        self.assertEqual(state.publish_calls, [])

    def test_requires_exact_fields_value(self):
        api, _, _ = self.make_api()
        service = MarketplaceProductListingAuthoringService(
            api=api,
            build_record=lambda draft: object(),
        )
        with self.assertRaises(TypeError):
            service.create_product_listing(object())  # type: ignore[arg-type]


if __name__ == "__main__":
    unittest.main()
