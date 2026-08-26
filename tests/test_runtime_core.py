from __future__ import annotations

import unittest
from dataclasses import dataclass
from typing import Callable

from olp import RecordV1, record_identity_text

from marketplace.runtime import (
    DEFAULT_EPHEMERAL_RETENTION_SECONDS,
    InMemoryEphemeralRecordRepository,
    InvalidIdentityProviderResult,
    MarketplaceNode,
    RecordIdentityCollisionError,
    RepositoryCapacityExceededError,
    RepositoryClosedError,
    StoreDisposition,
)
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

    def fire(self, index: int, *, even_if_cancelled: bool = False) -> None:
        event = self.events[index]
        if even_if_cancelled or not event.handle.cancelled:
            event.callback()


class RuntimeCoreTests(unittest.TestCase):
    def repository(self, *, max_entries: int = 1024):
        scheduler = FakeExpiryScheduler()
        repository = InMemoryEphemeralRecordRepository(
            scheduler=scheduler,
            max_entries=max_entries,
        )
        return repository, scheduler

    def test_default_retention_is_ephemeral_ten_seconds(self):
        repository, _ = self.repository()
        self.assertEqual(repository.retention_class, "EPHEMERAL")
        self.assertEqual(repository.retention_seconds, DEFAULT_EPHEMERAL_RETENTION_SECONDS)
        self.assertEqual(repository.retention_seconds, 10.0)

    def test_retention_cannot_exceed_ephemeral_maximum(self):
        with self.assertRaises(ValueError):
            InMemoryEphemeralRecordRepository(retention_seconds=10.001)
        with self.assertRaises(ValueError):
            InMemoryEphemeralRecordRepository(retention_seconds=0)

    def test_validation_precedes_identity_derivation_and_storage(self):
        repository, scheduler = self.repository()
        identity_calls = 0

        def reject(_record):
            raise ValueError("invalid Marketplace record")

        def identity(_record):
            nonlocal identity_calls
            identity_calls += 1
            return "r1_should-not-be-used"

        node = MarketplaceNode(
            validate_record=reject,
            record_identity_text=identity,
            repository=repository,
        )
        with self.assertRaisesRegex(ValueError, "invalid Marketplace record"):
            node.ingest({"payload": "invalid"})
        self.assertEqual(identity_calls, 0)
        self.assertEqual(len(repository), 0)
        self.assertEqual(scheduler.events, [])

    def test_ingest_duplicate_and_read_refresh_expiry(self):
        repository, scheduler = self.repository()
        record = {"id": "r1_example", "payload": "same"}
        node = MarketplaceNode(
            validate_record=lambda _record: None,
            record_identity_text=lambda item: item["id"],
            repository=repository,
        )

        first = node.ingest(record)
        self.assertEqual(first.disposition, StoreDisposition.STORED)
        self.assertEqual(scheduler.events[0].delay_seconds, 10.0)

        duplicate = node.ingest(dict(record))
        self.assertEqual(duplicate.disposition, StoreDisposition.DUPLICATE)
        self.assertTrue(scheduler.events[0].handle.cancelled)

        self.assertEqual(node.get("r1_example"), record)
        self.assertTrue(scheduler.events[1].handle.cancelled)
        self.assertEqual(len(scheduler.events), 3)

    def test_stale_expiry_callback_cannot_delete_refreshed_entry(self):
        repository, scheduler = self.repository()
        record = {"payload": "evidence"}
        repository.put("r1_refresh", record)
        self.assertEqual(repository.get("r1_refresh"), record)

        scheduler.fire(0, even_if_cancelled=True)
        self.assertEqual(len(repository), 1)
        self.assertEqual(repository.get("r1_refresh"), record)

        latest = len(scheduler.events) - 1
        scheduler.fire(latest)
        self.assertEqual(len(repository), 0)

    def test_identity_collision_fails_closed(self):
        repository, _ = self.repository()
        repository.put("r1_same", {"payload": "first"})
        with self.assertRaises(RecordIdentityCollisionError) as raised:
            repository.put("r1_same", {"payload": "different"})
        self.assertEqual(raised.exception.code, "RECORD_IDENTITY_COLLISION")
        self.assertEqual(len(repository), 1)

    def test_capacity_is_bounded(self):
        repository, _ = self.repository(max_entries=1)
        repository.put("r1_one", {"payload": 1})
        with self.assertRaises(RepositoryCapacityExceededError) as raised:
            repository.put("r1_two", {"payload": 2})
        self.assertEqual(raised.exception.code, "REPOSITORY_CAPACITY_EXCEEDED")
        self.assertEqual(len(repository), 1)

    def test_current_expiry_removes_content_automatically(self):
        repository, scheduler = self.repository()
        repository.put("r1_expire", {"payload": "temporary"})
        scheduler.fire(0)
        self.assertEqual(len(repository), 0)
        self.assertIsNone(repository.get("r1_expire"))

    def test_close_clears_content_cancels_expiry_and_is_idempotent(self):
        repository, scheduler = self.repository()
        repository.put("r1_close", {"payload": "temporary"})
        repository.close()
        repository.close()

        self.assertEqual(len(repository), 0)
        self.assertTrue(scheduler.events[0].handle.cancelled)
        with self.assertRaises(RepositoryClosedError):
            repository.get("r1_close")
        with self.assertRaises(RepositoryClosedError):
            repository.put("r1_new", {"payload": "no"})

    def test_invalid_identity_provider_result_does_not_store(self):
        repository, scheduler = self.repository()
        node = MarketplaceNode(
            validate_record=lambda _record: None,
            record_identity_text=lambda _record: "",
            repository=repository,
        )
        with self.assertRaises(InvalidIdentityProviderResult) as raised:
            node.ingest({"payload": "valid semantics, bad identity adapter"})
        self.assertEqual(raised.exception.code, "INVALID_IDENTITY_PROVIDER_RESULT")
        self.assertEqual(len(repository), 0)
        self.assertEqual(scheduler.events, [])

    def test_real_marketplace_validator_and_olp_identity_compose_with_node(self):
        repository, _ = self.repository()
        record = RecordV1.from_mapping(
            {
                "envelope_version": 1,
                "type": TYPE_INTENT,
                "content": {
                    "version": 1,
                    "issuer": {"principal": "did:example:alice"},
                    "subjects": [{"uri": "urn:example:runtime-subject:1"}],
                    "action": {"id": "https://example.test/actions/request"},
                    "terms": {},
                },
                "profiles": [CORE_PROFILE],
            }
        )
        node = MarketplaceNode(
            validate_record=validate_market_record,
            record_identity_text=record_identity_text,
            repository=repository,
        )

        outcome = node.ingest(record)
        self.assertEqual(outcome.disposition, StoreDisposition.STORED)
        self.assertEqual(outcome.record_id, record_identity_text(record))
        self.assertEqual(node.get(outcome.record_id), record)


if __name__ == "__main__":
    unittest.main()
