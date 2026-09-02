from __future__ import annotations

import unittest

from marketplace.application.api import (
    ApplicationApiError,
    IntentIndexPage,
    MarketplaceApplicationApiService,
)
from marketplace.application.postgres_state import ExpiryResult, SyncChange, SyncPage


class BoundaryState:
    def __init__(self) -> None:
        self.response_values: tuple[str, ...] = ()
        self.sync_page = SyncPage((), 0, False)

    def initialize(self):
        return ExpiryResult((), ())

    def peek(self, record_id):
        return object()

    def get(self, record_id):
        return object()

    def response_ids(self, record_id, *, limit):
        return self.response_values

    def sync_since(self, cursor, *, limit):
        return self.sync_page


class EmptyIntentQuery:
    def list_intent_ids(self, *, cursor, limit):
        return IntentIndexPage((), None)


class M17ApplicationApiBoundaryHardeningTests(unittest.TestCase):
    def make_api(self, state: BoundaryState) -> MarketplaceApplicationApiService:
        api = MarketplaceApplicationApiService(
            state=state,  # type: ignore[arg-type]
            intent_query=EmptyIntentQuery(),
            response_parent_ids=lambda record: (),
            is_intent_record=lambda record: True,
        )
        api.initialize()
        return api

    def test_response_page_cannot_exceed_requested_limit_or_duplicate_ids(self):
        state = BoundaryState()
        api = self.make_api(state)
        state.response_values = ("r1", "r2")
        with self.assertRaises(ApplicationApiError) as overrun:
            api.list_responses("r-parent", limit=1)
        self.assertEqual(overrun.exception.code, "RESPONSE_QUERY_LIMIT_EXCEEDED")
        state.response_values = ("r1", "r1")
        with self.assertRaises(ApplicationApiError) as duplicate:
            api.list_responses("r-parent", limit=2)
        self.assertEqual(duplicate.exception.code, "RESPONSE_QUERY_DUPLICATE_ID")

    def test_sync_page_cannot_exceed_requested_limit(self):
        state = BoundaryState()
        api = self.make_api(state)
        state.sync_page = SyncPage(
            (SyncChange(1, "r1", "UPSERT"), SyncChange(2, "r2", "UPSERT")),
            2,
            False,
        )
        with self.assertRaises(ApplicationApiError) as caught:
            api.sync(cursor=0, limit=1)
        self.assertEqual(caught.exception.code, "SYNC_QUERY_LIMIT_EXCEEDED")

    def test_sync_page_requires_exact_monotonic_shape(self):
        state = BoundaryState()
        api = self.make_api(state)
        bad_pages = (
            SyncPage((SyncChange(2, "r2", "UPSERT"), SyncChange(1, "r1", "DELETE")), 1, False),
            SyncPage((SyncChange(1, "r1", "OTHER"),), 1, False),
            SyncPage((SyncChange(1, "r1", "UPSERT"),), 9, False),
            SyncPage((), 0, 1),
        )
        for page in bad_pages:
            with self.subTest(page=page):
                state.sync_page = page
                with self.assertRaises(ApplicationApiError) as caught:
                    api.sync(cursor=0, limit=2)
                self.assertEqual(caught.exception.code, "SYNC_PAGE_INVALID")

    def test_sync_change_kind_rejects_hostile_equality_without_execution(self):
        class HostileKind:
            def __eq__(self, other):
                raise AssertionError("hostile equality executed")

        state = BoundaryState()
        api = self.make_api(state)
        state.sync_page = SyncPage((SyncChange(1, "r1", HostileKind()),), 1, False)
        with self.assertRaises(ApplicationApiError) as caught:
            api.sync(cursor=0, limit=1)
        self.assertEqual(caught.exception.code, "SYNC_PAGE_INVALID")

    def test_module_all_exports_intent_record_predicate(self):
        from marketplace.application import api as api_module

        self.assertIn("IntentRecordPredicate", api_module.__all__)


if __name__ == "__main__":
    unittest.main()
