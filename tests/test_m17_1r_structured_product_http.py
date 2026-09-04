from __future__ import annotations

import json
import unittest

from marketplace.application.api import ApplicationApiError
from marketplace.application.authoring import (
    ProductListingAuthoringError,
    ProductListingAuthoringFields,
)
from marketplace.application.http import (
    ApplicationHttpRequest,
    MarketplaceApplicationHttpAdapter,
)
from marketplace.application.postgres_state import (
    ApplicationStatePutResult,
    StoreDisposition,
)


class FakeApi:
    def __init__(self) -> None:
        self.calls: list[tuple[object, ...]] = []

    def create_intent(self, record):
        self.calls.append(("create_intent", record))
        return ApplicationStatePutResult(StoreDisposition.STORED, 3)


def decode_record(body: bytes):
    return json.loads(body.decode("utf-8"))


def encode_record(record: object) -> bytes:
    return json.dumps(record, sort_keys=True, separators=(",", ":")).encode("utf-8")


def listing_document(**changes):
    document = {
        "seller_principal": "did:example:seller",
        "subject_uri": "urn:sku:moon-widget",
        "title": "Moon widget",
        "description": "Structured Marketplace listing.",
        "consideration_coefficient": 1299,
        "consideration_scale": 2,
        "currency_code": "USD",
        "quantity_coefficient": 1,
        "quantity_scale": 0,
        "unit_uri": "https://open-trust-layer.github.io/marketplace/unit/item",
        "latitude_e6": 52_520_000,
        "longitude_e6": 13_405_000,
    }
    document.update(changes)
    return document


class M17StructuredProductHttpTests(unittest.TestCase):
    def make_adapter(self, creator=None):
        api = FakeApi()
        calls: list[ProductListingAuthoringFields] = []

        def default_creator(fields: ProductListingAuthoringFields):
            calls.append(fields)
            return ApplicationStatePutResult(StoreDisposition.STORED, 11)

        adapter = MarketplaceApplicationHttpAdapter(
            api=api,
            decode_record_json=decode_record,
            encode_record_json=encode_record,
            create_product_listing=creator or default_creator,
        )
        return adapter, api, calls

    def request(self, method="POST", *, query=(), content_type="application/json", body=None):
        payload = listing_document() if body is None else body
        encoded = payload if isinstance(payload, bytes) else json.dumps(payload).encode("utf-8")
        return ApplicationHttpRequest(method, "/api/product-listings", query, content_type, encoded)

    def document(self, response):
        return json.loads(response.body.decode("utf-8"))

    def test_structured_listing_delegates_exact_fields_once(self):
        adapter, api, calls = self.make_adapter()
        response = adapter.handle(self.request())
        self.assertEqual(response.status_code, 201)
        self.assertEqual(self.document(response), {"change_seq": 11, "disposition": "STORED"})
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0], ProductListingAuthoringFields(**listing_document()))
        self.assertEqual(api.calls, [])

    def test_transport_shape_is_exact_and_bounded_before_creator(self):
        cases = (
            self.request(body={**listing_document(), "extra": "x"}),
            self.request(body={key: value for key, value in listing_document().items() if key != "title"}),
            self.request(body=listing_document(latitude_e6=True)),
            self.request(body=b'{"title":"x","title":"y"}'),
            self.request(query=(("x", "1"),)),
            self.request(content_type="text/plain"),
        )
        for request in cases:
            with self.subTest(request=request):
                adapter, api, calls = self.make_adapter()
                response = adapter.handle(request)
                self.assertIn(response.status_code, (400, 415))
                self.assertEqual(calls, [])
                self.assertEqual(api.calls, [])

    def test_only_post_is_allowed(self):
        adapter, _, calls = self.make_adapter()
        response = adapter.handle(self.request(method="GET", content_type=None, body=b""))
        self.assertEqual(response.status_code, 405)
        self.assertEqual(dict(response.headers)["Allow"], "POST")
        self.assertEqual(calls, [])

    def test_authoring_failures_are_stable_and_non_reflective(self):
        hostile = "secret-authoring-detail"

        def fail(fields):
            raise ProductListingAuthoringError("PRODUCT_LISTING_FIELDS_INVALID", hostile)

        adapter, _, _ = self.make_adapter(fail)
        response = adapter.handle(self.request())
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.document(response)["error"]["code"], "PRODUCT_LISTING_FIELDS_INVALID")
        self.assertNotIn(hostile, response.body.decode("utf-8"))

    def test_application_failure_mapping_is_reused(self):
        def fail(fields):
            raise ApplicationApiError("ROOT_INTENT_RESPONSE_FORBIDDEN", "hostile")

        adapter, _, _ = self.make_adapter(fail)
        response = adapter.handle(self.request())
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.document(response)["error"]["code"], "ROOT_INTENT_RESPONSE_FORBIDDEN")

    def test_raw_record_post_route_remains_separate(self):
        adapter, api, calls = self.make_adapter()
        body = b'{"kind":"intent","record_id":"r-raw"}'
        response = adapter.handle(ApplicationHttpRequest(
            "POST", "/api/intents", (), "application/json", body,
        ))
        self.assertEqual(response.status_code, 201)
        self.assertEqual(calls, [])
        self.assertEqual(api.calls, [("create_intent", {"kind": "intent", "record_id": "r-raw"})])


if __name__ == "__main__":
    unittest.main()
