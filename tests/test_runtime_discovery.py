from __future__ import annotations

import unittest
from dataclasses import dataclass
from typing import Callable

from olp import RecordV1, record_identity_text

from marketplace.runtime import (
    InMemoryEphemeralRecordRepository,
    InvalidDiscoveryEvaluatorResult,
    InvalidDiscoveryLimitError,
    LocalDiscoveryService,
    RepositoryReadLimitExceededError,
)
from marketplace_matching_v1 import MarketplaceDiscoveryError, evaluate_discovery
from marketplace_record_v1 import CORE_PROFILE, TYPE_INTENT


class FakeExpiryHandle:
    def __init__(self) -> None:
        self.cancelled = False

    def cancel(self) -> None:
        self.cancelled = True


@dataclass
class ScheduledExpiry:
    delay_seconds: float
    callback: Callable[[], None]
    handle: FakeExpiryHandle


class FakeExpiryScheduler:
    def __init__(self) -> None:
        self.events: list[ScheduledExpiry] = []

    def schedule(self, delay_seconds: float, callback: Callable[[], None]) -> FakeExpiryHandle:
        handle = FakeExpiryHandle()
        self.events.append(ScheduledExpiry(delay_seconds, callback, handle))
        return handle

    def fire(self, index: int, *, even_if_cancelled: bool = False) -> None:
        event = self.events[index]
        if even_if_cancelled or not event.handle.cancelled:
            event.callback()


class FakeBoundedSource:
    def __init__(self, records):
        self.records = tuple(records)
        self.calls: list[int] = []

    def snapshot(self, limit: int):
        self.calls.append(limit)
        return self.records


def intent(*, principal: str, subject: str, action: str) -> RecordV1:
    return RecordV1.from_mapping(
        {
            "envelope_version": 1,
            "type": TYPE_INTENT,
            "content": {
                "version": 1,
                "issuer": {"principal": principal},
                "subjects": [{"uri": subject}],
                "action": {"id": action},
                "terms": {},
            },
            "profiles": [CORE_PROFILE],
        }
    )


def malformed_intent() -> RecordV1:
    return RecordV1.from_mapping(
        {
            "envelope_version": 1,
            "type": TYPE_INTENT,
            "content": {"version": 1},
            "profiles": [CORE_PROFILE],
        }
    )


class RuntimeDiscoveryTests(unittest.TestCase):
    def repository(self, *, max_entries: int = 16):
        scheduler = FakeExpiryScheduler()
        repository = InMemoryEphemeralRecordRepository(
            scheduler=scheduler,
            max_entries=max_entries,
        )
        return repository, scheduler

    def test_snapshot_overflow_fails_without_refreshing_any_record(self):
        repository, scheduler = self.repository(max_entries=3)
        repository.put("r1_a", {"value": "a"})
        repository.put("r1_b", {"value": "b"})

        with self.assertRaises(RepositoryReadLimitExceededError) as raised:
            repository.snapshot(1)

        self.assertEqual(raised.exception.code, "REPOSITORY_READ_LIMIT_EXCEEDED")
        self.assertEqual(len(scheduler.events), 2)
        self.assertFalse(scheduler.events[0].handle.cancelled)
        self.assertFalse(scheduler.events[1].handle.cancelled)

    def test_snapshot_is_identity_ordered_refreshes_and_rejects_stale_expiry(self):
        repository, scheduler = self.repository(max_entries=2)
        repository.put("r1_b", {"value": "b"})
        repository.put("r1_a", {"value": "a"})

        snapshot = repository.snapshot(2)

        self.assertEqual(snapshot, ({"value": "a"}, {"value": "b"}))
        self.assertTrue(scheduler.events[0].handle.cancelled)
        self.assertTrue(scheduler.events[1].handle.cancelled)
        self.assertEqual(len(scheduler.events), 4)

        scheduler.fire(0, even_if_cancelled=True)
        scheduler.fire(1, even_if_cancelled=True)
        self.assertEqual(len(repository), 2)

        scheduler.fire(2)
        scheduler.fire(3)
        self.assertEqual(len(repository), 0)

    def test_invalid_runtime_limit_is_rejected_before_evaluator_or_source(self):
        source = FakeBoundedSource(())
        evaluator_calls = 0

        def evaluator(*args, **kwargs):
            nonlocal evaluator_calls
            evaluator_calls += 1
            return {}

        service = LocalDiscoveryService(record_source=source, evaluate_discovery=evaluator)
        with self.assertRaises(InvalidDiscoveryLimitError):
            service.discover(
                {"version": 1},
                source="urn:example:source:local",
                completeness="COMPLETE_FOR_DECLARED_SOURCE",
                freshness="FRESH",
                max_records=0,
            )
        self.assertEqual(evaluator_calls, 0)
        self.assertEqual(source.calls, [])

    def test_actual_m5_invalid_query_does_not_refresh_local_evidence(self):
        repository, scheduler = self.repository()
        record = intent(
            principal="did:example:alice",
            subject="urn:example:item:1",
            action="https://example.test/actions/sell",
        )
        repository.put(record_identity_text(record), record)
        service = LocalDiscoveryService(
            record_source=repository,
            evaluate_discovery=evaluate_discovery,
        )

        with self.assertRaises(MarketplaceDiscoveryError):
            service.discover(
                {"version": 2},
                source="urn:example:source:local",
                completeness="COMPLETE_FOR_DECLARED_SOURCE",
                freshness="FRESH",
                max_records=8,
            )

        self.assertEqual(len(scheduler.events), 1)
        self.assertFalse(scheduler.events[0].handle.cancelled)

    def test_actual_m5_empty_source_preserves_scope_and_nonadverse_absence(self):
        repository, _ = self.repository()
        service = LocalDiscoveryService(
            record_source=repository,
            evaluate_discovery=evaluate_discovery,
        )

        result = service.discover(
            {"version": 1},
            source="urn:example:source:local",
            completeness="COMPLETE_FOR_DECLARED_SOURCE",
            freshness="FRESH",
            max_records=8,
        )

        self.assertEqual(result["source"], "urn:example:source:local")
        self.assertEqual(result["result_count"], 0)
        self.assertEqual(result["completeness"], "COMPLETE_FOR_DECLARED_SOURCE")
        self.assertEqual(result["global_completeness"], "UNKNOWN")
        self.assertFalse(result["absence_is_negative_evidence"])
        self.assertEqual(result["ordering"], "REPRODUCIBLE_IDENTITY_ORDER_NOT_RANKING")

    def test_actual_m5_exact_query_returns_only_matching_intent_and_refreshes_source(self):
        repository, scheduler = self.repository()
        sell = intent(
            principal="did:example:alice",
            subject="urn:example:item:1",
            action="https://example.test/actions/sell",
        )
        buy = intent(
            principal="did:example:bob",
            subject="urn:example:item:2",
            action="https://example.test/actions/buy",
        )
        repository.put(record_identity_text(sell), sell)
        repository.put(record_identity_text(buy), buy)
        service = LocalDiscoveryService(
            record_source=repository,
            evaluate_discovery=evaluate_discovery,
        )

        result = service.discover(
            {"version": 1, "action_ids_any": ["https://example.test/actions/sell"]},
            source="urn:example:source:local",
            completeness="PARTIAL_SOURCE",
            freshness="FRESH",
            max_records=8,
        )

        self.assertEqual(result["result_refs"], [record_identity_text(sell)])
        self.assertEqual(result["result_count"], 1)
        self.assertEqual(result["completeness"], "PARTIAL_SOURCE")
        self.assertEqual(result["global_completeness"], "UNKNOWN")
        self.assertFalse(result["absence_is_negative_evidence"])
        self.assertTrue(scheduler.events[0].handle.cancelled)
        self.assertTrue(scheduler.events[1].handle.cancelled)
        self.assertEqual(len(scheduler.events), 4)

    def test_actual_m5_malformed_marketplace_candidate_is_reported_by_m5(self):
        repository, _ = self.repository()
        good = intent(
            principal="did:example:alice",
            subject="urn:example:item:1",
            action="https://example.test/actions/sell",
        )
        bad = malformed_intent()
        repository.put(record_identity_text(good), good)
        repository.put(record_identity_text(bad), bad)
        service = LocalDiscoveryService(
            record_source=repository,
            evaluate_discovery=evaluate_discovery,
        )

        result = service.discover(
            {"version": 1},
            source="urn:example:source:local",
            completeness="PARTIAL_SOURCE",
            freshness="UNKNOWN",
            max_records=8,
        )

        self.assertEqual(result["result_count"], 1)
        self.assertEqual(result["nonconforming_candidates_ignored"], 1)
        self.assertIn(record_identity_text(good), result["result_refs"])

    def test_actual_m5_discovery_fails_closed_when_local_source_exceeds_bound(self):
        repository, scheduler = self.repository(max_entries=2)
        first = intent(
            principal="did:example:alice",
            subject="urn:example:item:1",
            action="https://example.test/actions/sell",
        )
        second = intent(
            principal="did:example:bob",
            subject="urn:example:item:2",
            action="https://example.test/actions/buy",
        )
        repository.put(record_identity_text(first), first)
        repository.put(record_identity_text(second), second)
        service = LocalDiscoveryService(
            record_source=repository,
            evaluate_discovery=evaluate_discovery,
        )

        with self.assertRaises(RepositoryReadLimitExceededError):
            service.discover(
                {"version": 1},
                source="urn:example:source:local",
                completeness="PARTIAL_SOURCE",
                freshness="FRESH",
                max_records=1,
            )

        self.assertEqual(len(scheduler.events), 2)
        self.assertFalse(scheduler.events[0].handle.cancelled)
        self.assertFalse(scheduler.events[1].handle.cancelled)

    def test_service_returns_evaluator_mapping_without_reinterpreting_it(self):
        source = FakeBoundedSource(({"record": 1},))
        observed = {}
        expected = {
            "method_relative": True,
            "canonical_ranking": False,
            "global_completeness": "UNKNOWN",
        }

        def evaluator(records, query, **kwargs):
            observed["records"] = tuple(records)
            observed["query"] = query
            observed.update(kwargs)
            return expected

        service = LocalDiscoveryService(record_source=source, evaluate_discovery=evaluator)
        result = service.discover(
            {"version": 1},
            source="urn:example:source:local",
            completeness="UNKNOWN_SOURCE",
            freshness="UNKNOWN",
            max_records=4,
        )

        self.assertIs(result, expected)
        self.assertEqual(source.calls, [4])
        self.assertEqual(observed["records"], ({"record": 1},))
        self.assertEqual(observed["source"], "urn:example:source:local")
        self.assertEqual(observed["max_records"], 4)

    def test_nonmapping_evaluator_result_is_rejected(self):
        source = FakeBoundedSource(())
        service = LocalDiscoveryService(
            record_source=source,
            evaluate_discovery=lambda *args, **kwargs: [],
        )

        with self.assertRaises(InvalidDiscoveryEvaluatorResult) as raised:
            service.discover(
                {"version": 1},
                source="urn:example:source:local",
                completeness="UNKNOWN_SOURCE",
                freshness="UNKNOWN",
                max_records=4,
            )
        self.assertEqual(raised.exception.code, "INVALID_DISCOVERY_EVALUATOR_RESULT")


if __name__ == "__main__":
    unittest.main()
