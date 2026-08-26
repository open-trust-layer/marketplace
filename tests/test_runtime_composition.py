from __future__ import annotations

import unittest
from dataclasses import dataclass
from typing import Callable

from olp import RecordV1, record_identity_text

from marketplace.runtime import (
    RepositoryClosedError,
    create_in_memory_runtime,
)
from marketplace_matching_v1 import evaluate_discovery, evaluate_match
from marketplace_record_v1 import CORE_PROFILE, TYPE_INTENT, validate_market_record


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


class RuntimeCompositionTests(unittest.TestCase):
    def runtime(self, scheduler: FakeExpiryScheduler | None = None):
        return create_in_memory_runtime(
            validate_record=validate_market_record,
            record_identity_text=record_identity_text,
            evaluate_discovery=evaluate_discovery,
            evaluate_match=evaluate_match,
            scheduler=scheduler,
            max_entries=8,
        )

    def test_factory_preserves_ephemeral_retention_and_bounded_capacity(self):
        scheduler = FakeExpiryScheduler()
        runtime = self.runtime(scheduler)
        self.assertEqual(runtime.node.retention_class, "EPHEMERAL")
        self.assertEqual(runtime.node.retention_seconds, 10.0)
        self.assertEqual(runtime.repository.max_entries, 8)
        runtime.close()

    def test_factory_rejects_retention_above_project_maximum(self):
        with self.assertRaises(ValueError):
            create_in_memory_runtime(
                validate_record=validate_market_record,
                record_identity_text=record_identity_text,
                evaluate_discovery=evaluate_discovery,
                evaluate_match=evaluate_match,
                retention_seconds=10.001,
            )

    def test_ingest_is_immediately_visible_to_discovery_and_matching(self):
        scheduler = FakeExpiryScheduler()
        runtime = self.runtime(scheduler)
        buy = intent(
            principal="did:example:alice",
            subject="urn:example:item:1",
            action="https://example.test/actions/buy",
        )
        sell = intent(
            principal="did:example:bob",
            subject="urn:example:item:1",
            action="https://example.test/actions/sell",
        )

        buy_outcome = runtime.node.ingest(buy)
        sell_outcome = runtime.node.ingest(sell)

        discovery = runtime.discovery.discover(
            {"version": 1, "action_ids_any": ["https://example.test/actions/sell"]},
            source="urn:example:source:local-runtime",
            completeness="COMPLETE_FOR_DECLARED_SOURCE",
            freshness="FRESH",
            max_records=8,
        )
        self.assertEqual(discovery["result_refs"], [sell_outcome.record_id])
        self.assertEqual(discovery["global_completeness"], "UNKNOWN")

        match = runtime.matching.evaluate(
            buy_outcome.record_id,
            sell_outcome.record_id,
            method="https://example.test/method/exact-v1",
            base_status="SATISFIED",
            observations=(),
            evidence_completeness="COMPLETE_FOR_METHOD_INPUTS",
        )
        self.assertEqual(match["conclusion"], "COMPATIBLE_UNDER_METHOD")
        self.assertFalse(match["protocol_truth"])
        self.assertFalse(match["creates_agreement"])
        self.assertEqual(runtime.node.get(buy_outcome.record_id), buy)
        self.assertEqual(len(runtime.repository), 2)

        runtime.close()

    def test_all_services_share_one_repository_lifecycle(self):
        scheduler = FakeExpiryScheduler()
        runtime = self.runtime(scheduler)
        record = intent(
            principal="did:example:alice",
            subject="urn:example:item:1",
            action="https://example.test/actions/sell",
        )
        outcome = runtime.node.ingest(record)

        self.assertIs(runtime.discovery.record_source, runtime.repository)
        self.assertIs(runtime.matching.record_source, runtime.repository)
        self.assertEqual(runtime.node.get(outcome.record_id), record)

        runtime.close()
        runtime.close()
        self.assertEqual(len(runtime.repository), 0)
        self.assertTrue(all(event.handle.cancelled for event in scheduler.events))

        with self.assertRaises(RepositoryClosedError):
            runtime.node.get(outcome.record_id)
        with self.assertRaises(RepositoryClosedError):
            runtime.discovery.discover(
                {"version": 1},
                source="urn:example:source:local-runtime",
                completeness="UNKNOWN_SOURCE",
                freshness="UNKNOWN",
                max_records=8,
            )

    def test_context_manager_closes_transient_state_on_normal_exit(self):
        scheduler = FakeExpiryScheduler()
        runtime = self.runtime(scheduler)
        record = intent(
            principal="did:example:alice",
            subject="urn:example:item:1",
            action="https://example.test/actions/sell",
        )

        with runtime as opened:
            opened.node.ingest(record)
            self.assertEqual(len(opened.repository), 1)

        self.assertEqual(len(runtime.repository), 0)
        self.assertTrue(all(event.handle.cancelled for event in scheduler.events))
        with self.assertRaises(RepositoryClosedError):
            runtime.node.get(record_identity_text(record))

    def test_context_manager_closes_transient_state_on_exception(self):
        scheduler = FakeExpiryScheduler()
        runtime = self.runtime(scheduler)
        record = intent(
            principal="did:example:alice",
            subject="urn:example:item:1",
            action="https://example.test/actions/sell",
        )

        with self.assertRaisesRegex(RuntimeError, "application failure"):
            with runtime as opened:
                opened.node.ingest(record)
                raise RuntimeError("application failure")

        self.assertEqual(len(runtime.repository), 0)
        self.assertTrue(all(event.handle.cancelled for event in scheduler.events))


if __name__ == "__main__":
    unittest.main()
