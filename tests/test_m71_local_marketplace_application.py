from __future__ import annotations

import unittest

from marketplace.application import (
    LocalMarketplaceApplication,
    MarketplaceApplicationError,
    PublishedRecord,
)
from marketplace.runtime import StoreDisposition


class FakeNode:
    def __init__(self) -> None:
        self.ingest_calls: list[object] = []
        self.get_calls: list[str] = []
        self.records: dict[str, object] = {}
        self.ingest_error: Exception | None = None

    def ingest(self, record: object):
        self.ingest_calls.append(record)
        if self.ingest_error is not None:
            raise self.ingest_error
        return type("Outcome", (), {
            "record_id": "r1_listing",
            "disposition": StoreDisposition.STORED,
        })()

    def get(self, record_id: str):
        self.get_calls.append(record_id)
        return self.records.get(record_id)


class FakeDiscovery:
    def __init__(self) -> None:
        self.calls: list[tuple[object, dict[str, object]]] = []
        self.result: object = {
            "source": "urn:marketplace:local",
            "completeness": "PARTIAL_SOURCE",
            "freshness": "FRESH",
            "global_completeness": "UNKNOWN",
            "absence_is_negative_evidence": False,
            "ordering": "REPRODUCIBLE_IDENTITY_ORDER_NOT_RANKING",
            "result_refs": [],
            "result_count": 0,
        }

    def discover(self, query: object, **kwargs: object):
        self.calls.append((query, dict(kwargs)))
        return self.result


class M71LocalMarketplaceApplicationTests(unittest.TestCase):
    def app(self):
        node = FakeNode()
        discovery = FakeDiscovery()
        return (
            LocalMarketplaceApplication(
                node=node,
                discovery=discovery,
                source="urn:marketplace:local",
            ),
            node,
            discovery,
        )

    def test_publish_delegates_to_existing_node_and_returns_immutable_receipt(self):
        app, node, _ = self.app()
        record = {"kind": "market-intent"}

        result = app.publish(record)

        self.assertEqual(node.ingest_calls, [record])
        self.assertEqual(
            result,
            PublishedRecord(
                record_id="r1_listing",
                disposition=StoreDisposition.STORED,
            ),
        )

    def test_publish_preserves_existing_validation_failure(self):
        app, node, _ = self.app()
        node.ingest_error = ValueError("invalid marketplace record")

        with self.assertRaisesRegex(ValueError, "invalid marketplace record"):
            app.publish({"invalid": True})

    def test_get_uses_exact_record_identity_without_fallback(self):
        app, node, _ = self.app()
        record = object()
        node.records["r1_exact"] = record

        self.assertIs(app.get("r1_exact"), record)
        self.assertEqual(node.get_calls, ["r1_exact"])

    def test_empty_search_preserves_nonadverse_source_metadata(self):
        app, node, discovery = self.app()

        result = app.search(
            {"version": 1},
            completeness="PARTIAL_SOURCE",
            freshness="FRESH",
            max_records=8,
        )

        self.assertEqual(len(discovery.calls), 1)
        self.assertEqual(node.get_calls, [])
        self.assertEqual(result.source, "urn:marketplace:local")
        self.assertEqual(result.completeness, "PARTIAL_SOURCE")
        self.assertEqual(result.freshness, "FRESH")
        self.assertEqual(result.global_completeness, "UNKNOWN")
        self.assertFalse(result.absence_is_negative_evidence)
        self.assertEqual(result.record_ids, ())
        self.assertEqual(result.records, ())

    def test_search_resolves_exact_result_references_in_order(self):
        app, node, discovery = self.app()
        first = object()
        second = object()
        node.records.update({"r1_a": first, "r1_b": second})
        discovery.result = {
            "source": "urn:marketplace:local",
            "completeness": "PARTIAL_SOURCE",
            "freshness": "FRESH",
            "global_completeness": "UNKNOWN",
            "absence_is_negative_evidence": False,
            "ordering": "REPRODUCIBLE_IDENTITY_ORDER_NOT_RANKING",
            "result_refs": ["r1_a", "r1_b"],
            "result_count": 2,
        }

        result = app.search({"version": 1}, max_records=8)

        self.assertEqual(result.record_ids, ("r1_a", "r1_b"))
        self.assertEqual(result.records, (first, second))
        self.assertEqual(node.get_calls, ["r1_a", "r1_b"])

    def test_search_fails_closed_when_result_reference_is_not_locally_resolvable(self):
        app, _, discovery = self.app()
        discovery.result = {
            "source": "urn:marketplace:local",
            "completeness": "PARTIAL_SOURCE",
            "freshness": "FRESH",
            "global_completeness": "UNKNOWN",
            "absence_is_negative_evidence": False,
            "ordering": "REPRODUCIBLE_IDENTITY_ORDER_NOT_RANKING",
            "result_refs": ["r1_missing"],
            "result_count": 1,
        }

        with self.assertRaises(MarketplaceApplicationError) as caught:
            app.search({"version": 1}, max_records=8)

        self.assertEqual(caught.exception.code, "LOCAL_SEARCH_RESULT_MISSING_RECORD")

    def test_search_rejects_malformed_or_cross_source_result(self):
        app, _, discovery = self.app()
        for bad in (
            [],
            {"source": "urn:other"},
            {
                "source": "urn:marketplace:local",
                "completeness": "PARTIAL_SOURCE",
                "freshness": "FRESH",
                "global_completeness": "UNKNOWN",
                "absence_is_negative_evidence": False,
                "ordering": "REPRODUCIBLE_IDENTITY_ORDER_NOT_RANKING",
                "result_refs": ["r1_a"],
                "result_count": 0,
            },
        ):
            discovery.result = bad
            with self.subTest(result=bad):
                with self.assertRaises(MarketplaceApplicationError) as caught:
                    app.search({"version": 1}, max_records=8)
                self.assertEqual(caught.exception.code, "LOCAL_SEARCH_RESULT_INVALID")


if __name__ == "__main__":
    unittest.main()
