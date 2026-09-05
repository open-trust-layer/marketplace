from __future__ import annotations

import json
import unittest

from marketplace.application.api import ApplicationApiError
from marketplace.application.http import (
    ApplicationHttpRequest,
    MAX_APPLICATION_HTTP_BODY_BYTES,
    MarketplaceApplicationHttpAdapter,
)
from marketplace.application.postgres_state import ApplicationStatePutResult, StoreDisposition
from marketplace.application.proposal import BuyerRequestProposalDraft
from marketplace.application.proposal_authoring import ProposalAuthoringError


class FakeApi:
    def __init__(self) -> None:
        self.calls: list[tuple[object, ...]] = []

    def respond_to_intent(self, parent_id, record):
        self.calls.append(("respond_to_intent", parent_id, record))
        return ApplicationStatePutResult(StoreDisposition.STORED, 4)


def decode_record(body: bytes):
    return json.loads(body.decode("utf-8"))


def encode_record(record: object) -> bytes:
    return json.dumps(record, sort_keys=True, separators=(",", ":")).encode("utf-8")


def proposal_document(**changes):
    document = {
        "buyer_principal": "did:example:buyer",
        "subject_uri": "urn:sku:moon-widget",
        "action_uri": "https://open-trust-layer.github.io/marketplace/action/request",
    }
    document.update(changes)
    return document


class M17StructuredProposalHttpTests(unittest.TestCase):
    def make_adapter(self, creator=None):
        api = FakeApi()
        calls: list[BuyerRequestProposalDraft] = []

        def default_creator(draft: BuyerRequestProposalDraft):
            calls.append(draft)
            return ApplicationStatePutResult(StoreDisposition.STORED, 12)

        adapter = MarketplaceApplicationHttpAdapter(
            api=api,
            decode_record_json=decode_record,
            encode_record_json=encode_record,
            create_product_listing=lambda fields: (_ for _ in ()).throw(AssertionError("listing creator called")),
            create_proposal=creator or default_creator,
        )
        return adapter, api, calls

    def request(self, method="POST", *, parent_id="parent-1", query=(), content_type="application/json", body=None):
        payload = proposal_document() if body is None else body
        encoded = payload if isinstance(payload, bytes) else json.dumps(payload).encode("utf-8")
        return ApplicationHttpRequest(
            method,
            f"/api/intents/{parent_id}/proposals",
            query,
            content_type,
            encoded,
        )

    @staticmethod
    def document(response):
        return json.loads(response.body.decode("utf-8"))

    def test_structured_proposal_delegates_exact_draft_once(self):
        adapter, api, calls = self.make_adapter()
        response = adapter.handle(self.request())
        self.assertEqual(response.status_code, 201)
        self.assertEqual(self.document(response), {"change_seq": 12, "disposition": "STORED"})
        self.assertEqual(calls, [BuyerRequestProposalDraft(
            buyer_principal="did:example:buyer",
            subject_uri="urn:sku:moon-widget",
            action_uri="https://open-trust-layer.github.io/marketplace/action/request",
            parent_record_id="parent-1",
        )])
        self.assertEqual(api.calls, [])

    def test_transport_shape_is_exact_before_creator(self):
        cases = (
            self.request(body={**proposal_document(), "extra": "x"}),
            self.request(body={"buyer_principal": "did:example:buyer", "subject_uri": "urn:sku:moon-widget"}),
            self.request(body=proposal_document(action_uri=7)),
            self.request(body=proposal_document(action_uri="not-an-absolute-uri")),
            self.request(body=b'{"action_uri":"urn:a","action_uri":"urn:b"}'),
            self.request(body=b"[]"),
            self.request(body=b"\xff"),
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

    def test_parent_is_path_only(self):
        adapter, _, calls = self.make_adapter()
        response = adapter.handle(self.request(body={**proposal_document(), "parent_record_id": "other"}))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.document(response)["error"]["code"], "PROPOSAL_REQUEST_INVALID")
        self.assertEqual(calls, [])

    def test_invalid_draft_error_is_non_reflective(self):
        hostile = "secret-draft-detail"

        def fail(draft):
            raise ProposalAuthoringError("PROPOSAL_DRAFT_INVALID", hostile)

        adapter, _, _ = self.make_adapter(fail)
        response = adapter.handle(self.request())
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.document(response)["error"]["code"], "PROPOSAL_DRAFT_INVALID")
        self.assertNotIn(hostile, response.body.decode("utf-8"))

    def test_build_failure_is_internal_and_non_reflective(self):
        hostile = "secret-builder-detail"

        def fail(draft):
            raise ProposalAuthoringError("PROPOSAL_BUILD_FAILED", hostile)

        adapter, _, _ = self.make_adapter(fail)
        response = adapter.handle(self.request())
        self.assertEqual(response.status_code, 500)
        self.assertEqual(self.document(response)["error"]["code"], "PROPOSAL_BUILD_FAILED")
        self.assertNotIn(hostile, response.body.decode("utf-8"))

    def test_oversized_body_is_rejected_before_creator(self):
        adapter, api, calls = self.make_adapter()
        response = adapter.handle(self.request(body=b"{" + b"x" * MAX_APPLICATION_HTTP_BODY_BYTES))
        self.assertEqual(response.status_code, 413)
        self.assertEqual(self.document(response)["error"]["code"], "PAYLOAD_TOO_LARGE")
        self.assertEqual(calls, [])
        self.assertEqual(api.calls, [])

    def test_application_failure_mapping_is_reused(self):
        def fail(draft):
            raise ApplicationApiError("PARENT_INTENT_NOT_FOUND", "hostile")

        adapter, _, _ = self.make_adapter(fail)
        response = adapter.handle(self.request())
        self.assertEqual(response.status_code, 404)
        self.assertEqual(self.document(response)["error"]["code"], "PARENT_INTENT_NOT_FOUND")

    def test_raw_response_post_route_remains_separate(self):
        adapter, api, calls = self.make_adapter()
        raw = {"kind": "intent", "response_to": ["parent-1"]}
        response = adapter.handle(ApplicationHttpRequest(
            "POST",
            "/api/intents/parent-1/responses",
            (),
            "application/json",
            json.dumps(raw).encode("utf-8"),
        ))
        self.assertEqual(response.status_code, 201)
        self.assertEqual(calls, [])
        self.assertEqual(api.calls, [("respond_to_intent", "parent-1", raw)])

    def test_malformed_proposal_path_does_not_dispatch(self):
        adapter, api, calls = self.make_adapter()
        response = adapter.handle(ApplicationHttpRequest(
            "POST", "/api/intents//proposals", (), "application/json", json.dumps(proposal_document()).encode("utf-8")
        ))
        self.assertEqual(response.status_code, 404)
        self.assertEqual(calls, [])
        self.assertEqual(api.calls, [])


if __name__ == "__main__":
    unittest.main()
