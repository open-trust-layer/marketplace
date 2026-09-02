from __future__ import annotations

import unittest

from marketplace.application.postgres_state import (
    ApplicationStatePutResult,
    ExpiryResult,
    PreparedApplicationRecord,
    StoreDisposition,
    SyncChange,
    SyncPage,
)
from marketplace.application.state import (
    ApplicationStateServiceError,
    MarketplaceApplicationStateService,
)


class FakeStore:
    def __init__(self) -> None:
        self.put_calls = []
        self.get_calls = []
        self.response_calls = []
        self.sync_calls = []
        self.initialize_calls = 0
        self.prepared = None

    def initialize(self):
        self.initialize_calls += 1
        return ExpiryResult((), ())

    def put(self, prepared):
        self.put_calls.append(prepared)
        return ApplicationStatePutResult(StoreDisposition.STORED, 11)

    def get(self, record_id):
        self.get_calls.append(record_id)
        return self.prepared

    def list_response_ids(self, record_id, *, limit):
        self.response_calls.append((record_id, limit))
        return ("r1_response",)

    def sync_since(self, cursor, *, limit):
        self.sync_calls.append((cursor, limit))
        return SyncPage((SyncChange(12, "r1", "UPSERT"),), 12, False)


class M17ApplicationStateServiceTests(unittest.TestCase):
    def test_product_operations_require_successful_startup_initialization(self):
        store = FakeStore()
        service = MarketplaceApplicationStateService(
            store=store, prepare_record=lambda value: value, decode_record=lambda value: value
        )
        operations = (
            lambda: service.publish(PreparedApplicationRecord("r1", b"canonical")),
            lambda: service.get("r1"),
            lambda: service.response_ids("r1", limit=8),
            lambda: service.sync_since(0, limit=8),
        )
        for operation in operations:
            with self.assertRaises(ApplicationStateServiceError) as caught:
                operation()
            self.assertEqual(caught.exception.code, "APPLICATION_STATE_NOT_INITIALIZED")
        self.assertEqual(store.initialize_calls, 0)
        self.assertEqual(store.put_calls, [])
        self.assertEqual(store.get_calls, [])
        self.assertEqual(store.response_calls, [])
        self.assertEqual(store.sync_calls, [])

        self.assertEqual(service.initialize(), ExpiryResult((), ()))
        self.assertEqual(store.initialize_calls, 1)

    def test_publish_uses_one_shared_semantic_preparer_before_store(self):
        store = FakeStore()
        prepared = PreparedApplicationRecord("r1", b"canonical")
        calls = []

        def prepare(value):
            calls.append(value)
            return prepared

        service = MarketplaceApplicationStateService(
            store=store, prepare_record=prepare, decode_record=lambda value: value
        )
        service.initialize()
        source = {"type": "MarketIntent"}
        result = service.publish(source)
        self.assertEqual(calls, [source])
        self.assertEqual(store.put_calls, [prepared])
        self.assertEqual(result.change_seq, 11)

    def test_get_decodes_only_canonical_bytes_from_exact_identity(self):
        store = FakeStore()
        store.prepared = PreparedApplicationRecord("r1", b"canonical", ("parent",))
        decoded = object()
        decode_calls = []

        def decode(value):
            decode_calls.append(value)
            return decoded

        service = MarketplaceApplicationStateService(
            store=store, prepare_record=lambda value: value, decode_record=decode
        )
        service.initialize()
        self.assertIs(service.get("r1"), decoded)
        self.assertEqual(store.get_calls, ["r1"])
        self.assertEqual(decode_calls, [b"canonical"])

    def test_response_and_sync_queries_delegate_without_semantic_promotion(self):
        store = FakeStore()
        service = MarketplaceApplicationStateService(
            store=store, prepare_record=lambda value: value, decode_record=lambda value: value
        )
        service.initialize()
        self.assertEqual(service.response_ids("r1_parent", limit=8), ("r1_response",))
        page = service.sync_since(10, limit=16)
        self.assertEqual(page.next_cursor, 12)
        self.assertEqual(store.response_calls, [("r1_parent", 8)])
        self.assertEqual(store.sync_calls, [(10, 16)])
        self.assertFalse(hasattr(page, "agreement"))
        self.assertFalse(hasattr(page, "global_truth"))


if __name__ == "__main__":
    unittest.main()
