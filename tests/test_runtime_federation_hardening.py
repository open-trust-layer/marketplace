from __future__ import annotations

import unittest

from olp import RecordV1

from marketplace.reference import (
    CORE_PROFILE,
    TYPE_INTENT,
    evaluate_discovery,
    evaluate_match,
    federation_v1,
    record_identity_text,
    validate_market_record,
)
from marketplace.runtime import (
    FederationOperationProfile,
    OfflineFederationError,
    compose_offline_federation_service,
    create_in_memory_runtime,
)

SOURCE = "urn:example:source:remote-m24-hardening"
ACTION = "https://example.test/actions/sell"


def intent(principal: str, subject: str) -> RecordV1:
    return RecordV1.from_mapping(
        {
            "envelope_version": 1,
            "type": TYPE_INTENT,
            "content": {
                "version": 1,
                "issuer": {"principal": principal},
                "subjects": [{"uri": subject}],
                "action": {"id": ACTION},
                "terms": {},
            },
            "profiles": [CORE_PROFILE],
        }
    )


def scope() -> dict[str, object]:
    return {"version": 1, "record_types": [TYPE_INTENT]}


def snapshot_request(page_size: int = 4) -> dict[str, object]:
    return {
        "version": 1,
        "source": SOURCE,
        "operation": federation_v1.OP_SNAPSHOT,
        "scope": scope(),
        "required_capabilities": [federation_v1.CAP_SNAPSHOT],
        "page_size": page_size,
    }


def result_payload(records, *, operation=federation_v1.OP_SNAPSHOT, next_cursor=None):
    value = {
        "version": 1,
        "source": SOURCE,
        "operation": operation,
        "scope_fingerprint": federation_v1.scope_fingerprint(scope()),
        "record_ids": sorted(record_identity_text(record) for record in records),
        "source_completeness": "PARTIAL_SOURCE",
        "page_truncated": next_cursor is not None,
    }
    if next_cursor is not None:
        value["next_cursor"] = next_cursor
    return value


class OfflineFederationHardeningTests(unittest.TestCase):
    def runtime(self):
        return create_in_memory_runtime(
            validate_record=validate_market_record,
            record_identity_text=record_identity_text,
            evaluate_discovery=evaluate_discovery,
            evaluate_match=evaluate_match,
            max_entries=16,
        )

    def service(self, runtime, *, result_validator=federation_v1.validate_exchange_result):
        return compose_offline_federation_service(
            runtime,
            validate_record=validate_market_record,
            record_identity_text=record_identity_text,
            validate_exchange_request=federation_v1.validate_exchange_request,
            make_transport_envelope=federation_v1.make_transport_envelope,
            validate_transport_envelope=federation_v1.validate_transport_envelope,
            validate_exchange_result=result_validator,
            operation_profiles=(
                FederationOperationProfile(
                    federation_v1.OP_SNAPSHOT,
                    federation_v1.MSG_SNAPSHOT_REQUEST,
                    federation_v1.MSG_SNAPSHOT_RESULT,
                ),
                FederationOperationProfile(
                    federation_v1.OP_SYNC,
                    federation_v1.MSG_SYNC_REQUEST,
                    federation_v1.MSG_SYNC_RESULT,
                ),
            ),
        )

    def envelope(self, payload):
        return federation_v1.make_transport_envelope(
            federation_v1.MSG_SNAPSHOT_RESULT,
            payload,
        )

    def test_correct_message_type_with_wrong_operation_still_fails_before_ingest(self):
        runtime = self.runtime()
        try:
            record = intent("did:example:alice", "urn:example:item:operation")
            service = self.service(runtime)
            prepared = service.prepare(snapshot_request())
            payload = result_payload([record], operation=federation_v1.OP_SYNC)
            with self.assertRaises(OfflineFederationError) as caught:
                service.accept_page(prepared, self.envelope(payload), [record])
            self.assertEqual(caught.exception.code, "FEDERATION_OPERATION_MISMATCH")
            self.assertEqual(len(runtime.repository), 0)
        finally:
            runtime.close()

    def test_nonconforming_marketplace_record_fails_before_any_ingest(self):
        runtime = self.runtime()
        try:
            service = self.service(runtime)
            prepared = service.prepare(snapshot_request())
            malformed = RecordV1.from_mapping(
                {
                    "envelope_version": 1,
                    "type": TYPE_INTENT,
                    "content": {
                        "version": 1,
                        "issuer": {"principal": "did:example:alice"},
                        "subjects": [{"uri": "urn:example:item:malformed"}],
                        "action": {"id": ACTION},
                    },
                    "profiles": [CORE_PROFILE],
                }
            )
            payload = {
                "version": 1,
                "source": SOURCE,
                "operation": federation_v1.OP_SNAPSHOT,
                "scope_fingerprint": federation_v1.scope_fingerprint(scope()),
                "record_ids": [record_identity_text(malformed)],
                "source_completeness": "PARTIAL_SOURCE",
                "page_truncated": False,
            }
            with self.assertRaises(Exception):
                service.accept_page(prepared, self.envelope(payload), [malformed])
            self.assertEqual(len(runtime.repository), 0)
        finally:
            runtime.close()

    def test_hostile_result_validator_cannot_promote_global_completeness(self):
        runtime = self.runtime()
        try:
            record = intent("did:example:alice", "urn:example:item:global")

            def hostile(payload):
                result = dict(federation_v1.validate_exchange_result(payload))
                result["global_completeness"] = "COMPLETE"
                return result

            service = self.service(runtime, result_validator=hostile)
            prepared = service.prepare(snapshot_request())
            with self.assertRaises(OfflineFederationError) as caught:
                service.accept_page(prepared, self.envelope(result_payload([record])), [record])
            self.assertEqual(caught.exception.code, "FEDERATION_GLOBAL_COMPLETENESS_FORBIDDEN")
            self.assertEqual(len(runtime.repository), 0)
        finally:
            runtime.close()

    def test_hostile_result_validator_cannot_turn_absence_into_deletion_evidence(self):
        runtime = self.runtime()
        try:
            record = intent("did:example:alice", "urn:example:item:deletion")

            def hostile(payload):
                result = dict(federation_v1.validate_exchange_result(payload))
                result["absence_is_deletion_evidence"] = True
                return result

            service = self.service(runtime, result_validator=hostile)
            prepared = service.prepare(snapshot_request())
            with self.assertRaises(OfflineFederationError) as caught:
                service.accept_page(prepared, self.envelope(result_payload([record])), [record])
            self.assertEqual(caught.exception.code, "FEDERATION_DELETION_INFERENCE_FORBIDDEN")
            self.assertEqual(len(runtime.repository), 0)
        finally:
            runtime.close()

    def test_supplied_record_iterator_is_consumed_only_to_page_size_plus_one(self):
        runtime = self.runtime()
        try:
            first = intent("did:example:alice", "urn:example:item:first")
            second = intent("did:example:bob", "urn:example:item:second")
            service = self.service(runtime)
            prepared = service.prepare(snapshot_request(page_size=1))
            consumed = 0

            def records():
                nonlocal consumed
                consumed += 1
                yield first
                consumed += 1
                yield second
                raise AssertionError("offline federation consumed beyond page_size + 1")

            with self.assertRaises(OfflineFederationError) as caught:
                service.accept_page(
                    prepared,
                    self.envelope(result_payload([first])),
                    records(),
                )
            self.assertEqual(caught.exception.code, "FEDERATION_SUPPLIED_RECORD_LIMIT_EXCEEDED")
            self.assertEqual(consumed, 2)
            self.assertEqual(len(runtime.repository), 0)
        finally:
            runtime.close()

    def test_oversized_cursor_is_rejected_before_ingest(self):
        runtime = self.runtime()
        try:
            record = intent("did:example:alice", "urn:example:item:cursor")
            service = self.service(runtime)
            prepared = service.prepare(snapshot_request())
            payload = result_payload([record], next_cursor=b"x" * (federation_v1.MAX_CURSOR_BYTES + 1))
            with self.assertRaises(Exception):
                service.accept_page(prepared, self.envelope(payload), [record])
            self.assertEqual(len(runtime.repository), 0)
        finally:
            runtime.close()


if __name__ == "__main__":
    unittest.main()
