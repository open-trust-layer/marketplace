from __future__ import annotations

import unittest

from marketplace.application.api import ApplicationApiError, IntentIndexPage
from marketplace.application.root_intent_filter import (
    MAX_ROOT_INTENT_FILTER_SCAN_PAGES,
    MarketplaceRootIntentQueryFilter,
)


class ScriptedRootQuery:
    def __init__(self, pages):
        self.pages = pages
        self.calls = []

    def list_intent_ids(self, *, cursor, limit):
        self.calls.append((cursor, limit))
        return self.pages[cursor]


class MarketplaceRootIntentFilterTests(unittest.TestCase):
    def test_filters_persisted_acceptance_events_and_agreements(self):
        roots = ScriptedRootQuery({
            None: IntentIndexPage(
                ("r-a-listing", "r-b-acceptance", "r-c-agreement", "r-d-listing"),
                None,
            ),
        })
        filter_query = MarketplaceRootIntentQueryFilter(
            root_query=roots,
            is_root_intent=lambda record_id: record_id.endswith("-listing"),
        )

        result = filter_query.list_intent_ids(cursor=None, limit=5)
        self.assertEqual(result, IntentIndexPage(("r-a-listing", "r-d-listing"), None))
        self.assertEqual(roots.calls, [(None, 256)])

    def test_keyset_pagination_does_not_return_event_cursor(self):
        roots = ScriptedRootQuery({
            None: IntentIndexPage(
                ("r-a-listing", "r-b-acceptance", "r-c-listing"),
                "r-c-listing",
            ),
            "r-c-listing": IntentIndexPage(
                ("r-d-agreement", "r-e-listing"),
                None,
            ),
        })
        classifier = lambda record_id: record_id.endswith("-listing")
        filter_query = MarketplaceRootIntentQueryFilter(
            root_query=roots, is_root_intent=classifier,
        )

        first = filter_query.list_intent_ids(limit=2)
        self.assertEqual(first, IntentIndexPage(("r-a-listing", "r-c-listing"), "r-c-listing"))
        second = filter_query.list_intent_ids(cursor=first.next_cursor, limit=2)
        self.assertEqual(second, IntentIndexPage(("r-e-listing",), None))

    def test_all_non_intent_roots_produce_empty_page(self):
        roots = ScriptedRootQuery({
            None: IntentIndexPage(("r-event", "r-agreement"), None),
        })
        filter_query = MarketplaceRootIntentQueryFilter(
            root_query=roots, is_root_intent=lambda _: False,
        )
        self.assertEqual(filter_query.list_intent_ids(), IntentIndexPage((), None))

    def test_event_cursor_is_rejected_before_root_query(self):
        roots = ScriptedRootQuery({})
        filter_query = MarketplaceRootIntentQueryFilter(
            root_query=roots,
            is_root_intent=lambda record_id: record_id != "r-event",
        )
        with self.assertRaises(ApplicationApiError) as caught:
            filter_query.list_intent_ids(cursor="r-event", limit=2)
        self.assertEqual(caught.exception.code, "INTENT_CURSOR_INVALID")
        self.assertEqual(roots.calls, [])

    def test_classifier_failure_does_not_reflect_record_or_secret(self):
        roots = ScriptedRootQuery({
            None: IntentIndexPage(("r-secret",), None),
        })
        def fail(_record_id):
            raise RuntimeError("postgres://password-secret")
        filter_query = MarketplaceRootIntentQueryFilter(
            root_query=roots, is_root_intent=fail,
        )
        with self.assertRaises(ApplicationApiError) as caught:
            filter_query.list_intent_ids()
        self.assertEqual(caught.exception.code, "INTENT_CLASSIFICATION_FAILED")
        self.assertNotIn("password-secret", str(caught.exception))
        self.assertIsNone(caught.exception.__cause__)

    def test_bounded_scan_fails_closed_without_false_empty_result(self):
        class EndlessEvents:
            def __init__(self):
                self.calls = 0

            def list_intent_ids(self, *, cursor, limit):
                self.calls += 1
                return IntentIndexPage(
                    (f"r-{self.calls:04d}-event",),
                    f"r-{self.calls:04d}-event",
                )

        roots = EndlessEvents()
        filter_query = MarketplaceRootIntentQueryFilter(
            root_query=roots, is_root_intent=lambda _: False,
        )
        with self.assertRaises(ApplicationApiError) as caught:
            filter_query.list_intent_ids(limit=2)
        self.assertEqual(caught.exception.code, "INTENT_FILTER_SCAN_LIMIT")
        self.assertEqual(roots.calls, MAX_ROOT_INTENT_FILTER_SCAN_PAGES)

    def test_malformed_underlying_cursor_fails_closed(self):
        roots = ScriptedRootQuery({
            None: IntentIndexPage(("r-a",), "r-unrelated"),
        })
        filter_query = MarketplaceRootIntentQueryFilter(
            root_query=roots, is_root_intent=lambda _: False,
        )
        with self.assertRaises(ApplicationApiError) as caught:
            filter_query.list_intent_ids()
        self.assertEqual(caught.exception.code, "INTENT_FILTER_PAGE_INVALID")


if __name__ == "__main__":
    unittest.main()
