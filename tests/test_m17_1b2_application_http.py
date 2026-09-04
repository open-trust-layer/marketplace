from __future__ import annotations

import json
import unittest

from marketplace.application.api import ApplicationApiError, IntentIndexPage
from marketplace.application.postgres_state import (
    ApplicationStatePutResult,
    StoreDisposition,
    SyncChange,
    SyncPage,
)
from marketplace.application.http import (
    ApplicationHttpRequest,
    MarketplaceApplicationHttpAdapter,
)


class FakeApi:
    def __init__(self) -> None:
        self.calls: list[tuple[object, ...]] = []
        self.record = {"record_id": "r-root", "kind": "intent"}

    def list_intents(self, *, cursor=None, limit=64):
        self.calls.append(("list_intents", cursor, limit))
        return IntentIndexPage(("r-root", "r-other"), "next")

    def create_intent(self, record):
        self.calls.append(("create_intent", record))
        return ApplicationStatePutResult(StoreDisposition.STORED, 7)

    def get_intent(self, record_id):
        self.calls.append(("get_intent", record_id))
        return self.record if record_id == "r-root" else None

    def respond_to_intent(self, parent_record_id, record):
        self.calls.append(("respond_to_intent", parent_record_id, record))
        return ApplicationStatePutResult(StoreDisposition.DUPLICATE, None)

    def list_responses(self, parent_record_id, *, limit=64):
        self.calls.append(("list_responses", parent_record_id, limit))
        return ("r-response",)

    def sync(self, *, cursor=0, limit=128):
        self.calls.append(("sync", cursor, limit))
        return SyncPage((SyncChange(cursor + 1, "r-root", "UPSERT"),), cursor + 1, False)

    def sync_watermark(self):
        self.calls.append(("sync_watermark",))
        return 21


def decode_record(body: bytes):
    return json.loads(body.decode("utf-8"))


def encode_record(record: object) -> bytes:
    return json.dumps(record, sort_keys=True, separators=(",", ":")).encode("utf-8")


class M17ApplicationHttpTests(unittest.TestCase):
    def make_adapter(self):
        api = FakeApi()
        return MarketplaceApplicationHttpAdapter(
            api=api,
            decode_record_json=decode_record,
            encode_record_json=encode_record,
            create_product_listing=lambda fields: ApplicationStatePutResult(StoreDisposition.STORED, 9),
        ), api

    def request(self, method, path, *, query=(), content_type=None, body=b""):
        return ApplicationHttpRequest(method, path, query, content_type, body)

    def document(self, response):
        return json.loads(response.body.decode("utf-8"))

    def test_list_create_and_get_routes_delegate_to_existing_api(self):
        adapter, api = self.make_adapter()
        listed = adapter.handle(self.request("GET", "/api/intents", query=(("cursor", "c1"), ("limit", "2"))))
        self.assertEqual(listed.status_code, 200)
        self.assertEqual(self.document(listed), {"next_cursor": "next", "record_ids": ["r-root", "r-other"]})

        body = b'{"kind":"intent","record_id":"r-new"}'
        created = adapter.handle(self.request("POST", "/api/intents", content_type="application/json", body=body))
        self.assertEqual(created.status_code, 201)
        self.assertEqual(self.document(created), {"change_seq": 7, "disposition": "STORED"})

        fetched = adapter.handle(self.request("GET", "/api/intents/r-root"))
        self.assertEqual(fetched.status_code, 200)
        self.assertEqual(self.document(fetched), {"kind": "intent", "record_id": "r-root"})
        self.assertIn(("list_intents", "c1", 2), api.calls)
        self.assertIn(("get_intent", "r-root"), api.calls)

    def test_response_and_sync_routes_are_exact_and_bounded(self):
        adapter, api = self.make_adapter()
        response_body = b'{"kind":"proposal","record_id":"r-response"}'
        posted = adapter.handle(self.request(
            "POST",
            "/api/intents/r-root/responses",
            content_type="application/json",
            body=response_body,
        ))
        self.assertEqual(posted.status_code, 201)
        self.assertEqual(self.document(posted), {"change_seq": None, "disposition": "DUPLICATE"})

        listed = adapter.handle(self.request("GET", "/api/intents/r-root/responses", query=(("limit", "8"),)))
        self.assertEqual(self.document(listed), {"record_ids": ["r-response"]})

        synced = adapter.handle(self.request("GET", "/api/sync", query=(("cursor", "3"), ("limit", "16"))))
        self.assertEqual(
            self.document(synced),
            {"changes": [{"change_kind": "UPSERT", "record_id": "r-root", "seq": 4}], "has_more": False, "next_cursor": 4},
        )
        self.assertIn(("list_responses", "r-root", 8), api.calls)
        self.assertIn(("sync", 3, 16), api.calls)

    def test_invalid_queries_json_and_methods_fail_before_api_calls(self):
        adapter, api = self.make_adapter()
        cases = (
            self.request("GET", "/api/intents", query=(("limit", "2"), ("limit", "3"))),
            self.request("GET", "/api/intents", query=(("unknown", "x"),)),
            self.request("POST", "/api/intents", content_type="application/json", body=b'{"x":1,"x":2}'),
            self.request("POST", "/api/intents", content_type="text/plain", body=b"{}"),
        )
        for request in cases:
            with self.subTest(request=request):
                result = adapter.handle(request)
                self.assertIn(result.status_code, (400, 415))
        method = adapter.handle(self.request("DELETE", "/api/intents"))
        self.assertEqual(method.status_code, 405)
        self.assertEqual(api.calls, [])

    def test_not_found_and_application_errors_are_stable_non_reflective_json(self):
        adapter, api = self.make_adapter()
        missing = adapter.handle(self.request("GET", "/api/intents/r-missing"))
        self.assertEqual(missing.status_code, 404)
        self.assertEqual(self.document(missing)["error"]["code"], "INTENT_NOT_FOUND")

        hostile = "secret-hostile-payload"
        def fail_create(record):
            raise ApplicationApiError("RESPONSE_PARENT_MISMATCH", hostile)
        api.create_intent = fail_create
        failed = adapter.handle(self.request("POST", "/api/intents", content_type="application/json", body=b'{"x":1}'))
        self.assertEqual(failed.status_code, 400)
        text = failed.body.decode("utf-8")
        self.assertIn("RESPONSE_PARENT_MISMATCH", text)
        self.assertNotIn(hostile, text)


    def test_expired_sync_cursor_is_client_recoverable_without_storage_reflection(self):
        adapter, api = self.make_adapter()
        hostile = "hostile-storage-detail"

        def fail_sync(*, cursor=0, limit=128):
            raise ApplicationApiError("SYNC_CURSOR_EXPIRED", hostile)

        api.sync = fail_sync
        failed = adapter.handle(self.request("GET", "/api/sync", query=(("cursor", "3"),)))
        self.assertEqual(failed.status_code, 409)
        document = self.document(failed)
        self.assertEqual(document["error"]["code"], "SYNC_CURSOR_EXPIRED")
        self.assertIn("full resynchronization", document["error"]["message"])
        self.assertNotIn(hostile, failed.body.decode("utf-8"))

    def test_security_headers_and_response_bounds_are_always_applied(self):
        adapter, _ = self.make_adapter()
        response = adapter.handle(self.request("GET", "/api/intents"))
        headers = dict(response.headers)
        self.assertEqual(headers["Content-Type"], "application/json; charset=utf-8")
        self.assertEqual(headers["Cache-Control"], "no-store")
        self.assertEqual(headers["X-Content-Type-Options"], "nosniff")
        self.assertEqual(headers["Referrer-Policy"], "no-referrer")
        self.assertEqual(int(headers["Content-Length"]), len(response.body))



    def test_sync_without_cursor_returns_snapshot_watermark_for_full_resync(self):
        adapter, api = self.make_adapter()
        response = adapter.handle(self.request("GET", "/api/sync", query=(("limit", "16"),)))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            self.document(response),
            {"changes": [], "has_more": False, "next_cursor": 21},
        )
        self.assertIn(("sync_watermark",), api.calls)
        self.assertNotIn(("sync", 0, 16), api.calls)

if __name__ == "__main__":
    unittest.main()
