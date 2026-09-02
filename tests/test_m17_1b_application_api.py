from __future__ import annotations

import unittest

from marketplace.application.postgres_state import (
    ApplicationStatePutResult,
    ExpiryResult,
    StoreDisposition,
    SyncChange,
    SyncPage,
)


class FakeStateService:
    def __init__(self) -> None:
        self.initialize_calls = 0
        self.publish_calls = []
        self.get_calls = []
        self.peek_calls = []
        self.response_calls = []
        self.sync_calls = []
        self.records = {}

    def initialize(self):
        self.initialize_calls += 1
        return ExpiryResult((), ())

    def publish(self, record):
        self.publish_calls.append(record)
        return ApplicationStatePutResult(StoreDisposition.STORED, 7)

    def get(self, record_id):
        self.get_calls.append(record_id)
        return self.records.get(record_id)

    def peek(self, record_id):
        self.peek_calls.append(record_id)
        return self.records.get(record_id)

    def response_ids(self, record_id, *, limit=64):
        self.response_calls.append((record_id, limit))
        return ("r-response",)

    def sync_since(self, cursor, *, limit=128):
        self.sync_calls.append((cursor, limit))
        return SyncPage((SyncChange(8, "r-root", "UPSERT"),), 8, False)


class FakeIntentQuery:
    def __init__(self) -> None:
        self.calls = []

    def list_intent_ids(self, *, cursor, limit):
        self.calls.append((cursor, limit))
        return IntentIndexPage(("r-root", "r-other"), "next")


from marketplace.application.api import (
    ApplicationApiError,
    IntentIndexPage,
    MarketplaceApplicationApiService,
)


class M17ApplicationApiTests(unittest.TestCase):
    def make_service(self, *, parents=None):
        state = FakeStateService()
        query = FakeIntentQuery()
        parent_map = {} if parents is None else dict(parents)
        api = MarketplaceApplicationApiService(
            state=state,
            intent_query=query,
            response_parent_ids=lambda record: tuple(parent_map.get(id(record), ())),
            is_intent_record=lambda record: True,
        )
        return api, state, query, parent_map

    def test_initialize_delegates_to_shared_state_startup(self):
        api, state, _, _ = self.make_service()
        self.assertEqual(api.initialize(), ExpiryResult((), ()))
        self.assertEqual(state.initialize_calls, 1)

    def test_create_intent_rejects_response_bound_record_before_publish(self):
        record = object()
        api, state, _, parents = self.make_service()
        parents[id(record)] = ("r-parent",)
        api.initialize()
        with self.assertRaises(ApplicationApiError) as caught:
            api.create_intent(record)
        self.assertEqual(caught.exception.code, "ROOT_INTENT_RESPONSE_FORBIDDEN")
        self.assertEqual(state.publish_calls, [])

    def test_create_and_get_intent_delegate_without_protocol_promotion(self):
        record = object()
        api, state, _, _ = self.make_service()
        state.records["r-root"] = record
        api.initialize()
        created = api.create_intent(record)
        self.assertEqual(created.change_seq, 7)
        self.assertIs(api.get_intent("r-root"), record)
        self.assertEqual(state.publish_calls, [record])
        self.assertEqual(state.peek_calls, ["r-root"])
        self.assertEqual(state.get_calls, ["r-root"])

    def test_respond_requires_existing_parent_and_exact_response_binding(self):
        response = object()
        api, state, _, parents = self.make_service()
        parents[id(response)] = ("r-parent",)
        api.initialize()
        with self.assertRaises(ApplicationApiError) as missing:
            api.respond_to_intent("r-parent", response)
        self.assertEqual(missing.exception.code, "PARENT_INTENT_NOT_FOUND")
        state.records["r-parent"] = object()
        parents[id(response)] = ()
        with self.assertRaises(ApplicationApiError) as mismatch:
            api.respond_to_intent("r-parent", response)
        self.assertEqual(mismatch.exception.code, "RESPONSE_PARENT_MISMATCH")
        parents[id(response)] = ("r-parent", "r-prior-proposal")
        result = api.respond_to_intent("r-parent", response)
        self.assertEqual(result.change_seq, 7)
        self.assertEqual(state.publish_calls, [response])

    def test_list_intents_uses_separate_query_port(self):
        api, _, query, _ = self.make_service()
        api.initialize()
        page = api.list_intents(cursor="cursor-1", limit=32)
        self.assertEqual(page, IntentIndexPage(("r-root", "r-other"), "next"))
        self.assertEqual(query.calls, [("cursor-1", 32)])
        self.assertFalse(hasattr(page, "ranking"))
        self.assertFalse(hasattr(page, "truth"))

    def test_response_listing_and_sync_remain_bounded_delegations(self):
        api, state, _, _ = self.make_service()
        api.initialize()
        self.assertEqual(api.list_responses("r-root", limit=8), ("r-response",))
        page = api.sync(cursor=3, limit=16)
        self.assertEqual(page.next_cursor, 8)
        self.assertEqual(state.response_calls, [("r-root", 8)])
        self.assertEqual(state.sync_calls, [(3, 16)])

    def test_invalid_query_page_type_fails_closed(self):
        api, _, query, _ = self.make_service()
        query.list_intent_ids = lambda **kwargs: ("r-root",)  # type: ignore[method-assign]
        api.initialize()
        with self.assertRaises(TypeError):
            api.list_intents()


    def test_response_parent_mismatch_does_not_touch_parent_retention(self):
        response = object()
        api, state, _, _ = self.make_service()
        state.records["r-parent"] = object()
        api.initialize()
        with self.assertRaises(ApplicationApiError) as caught:
            api.respond_to_intent("r-parent", response)
        self.assertEqual(caught.exception.code, "RESPONSE_PARENT_MISMATCH")
        self.assertEqual(state.get_calls, [])
        self.assertEqual(state.publish_calls, [])

    def test_list_responses_requires_live_intent_parent_before_query_or_refresh(self):
        parent = object()
        state = FakeStateService()
        state.records["r-parent"] = parent
        api = MarketplaceApplicationApiService(
            state=state,
            intent_query=FakeIntentQuery(),
            response_parent_ids=lambda record: (),
            is_intent_record=lambda record: False,
        )
        api.initialize()
        with self.assertRaises(ApplicationApiError) as caught:
            api.list_responses("r-parent", limit=8)
        self.assertEqual(caught.exception.code, "PARENT_RECORD_NOT_INTENT")
        self.assertEqual(state.peek_calls, ["r-parent"])
        self.assertEqual(state.get_calls, [])
        self.assertEqual(state.response_calls, [])

    def test_query_port_cannot_exceed_requested_page_limit(self):
        api, _, query, _ = self.make_service()
        query.list_intent_ids = lambda **kwargs: IntentIndexPage(("r1", "r2"), None)  # type: ignore[method-assign]
        api.initialize()
        with self.assertRaises(ApplicationApiError) as caught:
            api.list_intents(limit=1)
        self.assertEqual(caught.exception.code, "INTENT_QUERY_LIMIT_EXCEEDED")


    def test_create_rejects_non_intent_record_before_publish(self):
        state = FakeStateService()
        query = FakeIntentQuery()
        api = MarketplaceApplicationApiService(
            state=state,
            intent_query=query,
            response_parent_ids=lambda record: (),
            is_intent_record=lambda record: False,
        )
        api.initialize()
        with self.assertRaises(ApplicationApiError) as caught:
            api.create_intent(object())
        self.assertEqual(caught.exception.code, "INTENT_RECORD_REQUIRED")
        self.assertEqual(state.publish_calls, [])

    def test_get_non_intent_does_not_refresh_retention(self):
        record = object()
        state = FakeStateService()
        state.records["r-not-intent"] = record
        api = MarketplaceApplicationApiService(
            state=state,
            intent_query=FakeIntentQuery(),
            response_parent_ids=lambda value: (),
            is_intent_record=lambda value: False,
        )
        api.initialize()
        with self.assertRaises(ApplicationApiError) as caught:
            api.get_intent("r-not-intent")
        self.assertEqual(caught.exception.code, "INTENT_RECORD_REQUIRED")
        self.assertEqual(state.peek_calls, ["r-not-intent"])
        self.assertEqual(state.get_calls, [])

    def test_response_parent_must_resolve_to_intent_record(self):
        response = object()
        parent = object()
        state = FakeStateService()
        state.records["r-parent"] = parent
        query = FakeIntentQuery()
        api = MarketplaceApplicationApiService(
            state=state,
            intent_query=query,
            response_parent_ids=lambda record: ("r-parent",) if record is response else (),
            is_intent_record=lambda record: record is response,
        )
        api.initialize()
        with self.assertRaises(ApplicationApiError) as caught:
            api.respond_to_intent("r-parent", response)
        self.assertEqual(caught.exception.code, "PARENT_RECORD_NOT_INTENT")
        self.assertEqual(state.peek_calls, ["r-parent"])
        self.assertEqual(state.get_calls, [])
        self.assertEqual(state.publish_calls, [])


if __name__ == "__main__":
    unittest.main()
