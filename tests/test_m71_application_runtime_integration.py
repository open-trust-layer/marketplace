from __future__ import annotations

import unittest

from olp import RecordV1

from marketplace.application import LocalMarketplaceApplication
from marketplace.reference import (
    CORE_PROFILE,
    TYPE_INTENT,
    evaluate_discovery,
    evaluate_match,
    record_identity_text,
    validate_market_record,
)
from marketplace.runtime import create_in_memory_runtime


class FakeExpiryHandle:
    def cancel(self) -> None:
        pass


class FakeExpiryScheduler:
    def schedule(self, _delay_seconds: float, _callback):
        return FakeExpiryHandle()


class M71ApplicationRuntimeIntegrationTests(unittest.TestCase):
    def test_real_market_intent_can_publish_retrieve_and_search_locally(self):
        action_id = "https://example.test/actions/sell"
        record = RecordV1.from_mapping(
            {
                "envelope_version": 1,
                "type": TYPE_INTENT,
                "content": {
                    "version": 1,
                    "issuer": {"principal": "did:example:alice"},
                    "subjects": [{"uri": "urn:example:product:bicycle-1"}],
                    "action": {"id": action_id},
                    "terms": {},
                },
                "profiles": [CORE_PROFILE],
            }
        )

        runtime = create_in_memory_runtime(
            validate_record=validate_market_record,
            record_identity_text=record_identity_text,
            evaluate_discovery=evaluate_discovery,
            evaluate_match=evaluate_match,
            scheduler=FakeExpiryScheduler(),
        )
        self.addCleanup(runtime.close)
        app = LocalMarketplaceApplication(
            node=runtime.node,
            discovery=runtime.discovery,
            source="urn:marketplace:local",
        )

        published = app.publish(record)
        self.assertEqual(published.record_id, record_identity_text(record))
        self.assertIs(app.get(published.record_id), record)
        self.assertEqual(runtime.repository.retention_class, "EPHEMERAL")
        self.assertEqual(runtime.repository.retention_seconds, 10.0)

        result = app.search(
            {"version": 1, "action_ids_any": [action_id]},
            completeness="PARTIAL_SOURCE",
            freshness="FRESH",
            max_records=8,
        )

        self.assertEqual(result.record_ids, (published.record_id,))
        self.assertEqual(result.records, (record,))
        self.assertEqual(result.global_completeness, "UNKNOWN")
        self.assertFalse(result.absence_is_negative_evidence)


if __name__ == "__main__":
    unittest.main()
