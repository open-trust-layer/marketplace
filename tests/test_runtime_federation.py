from __future__ import annotations

import unittest
from unittest.mock import patch

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
    StoreDisposition,
    compose_offline_federation_service,
    create_in_memory_runtime,
)


SOURCE = "urn:example:source:remote-m24"
ACTION = "https://example.test/actions/sell"
SUBJECT = "urn:example:item:m24"


def intent(principal: str, *, subject: str = SUBJECT) -> RecordV1:
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


def request(*, page_size: int = 4, operation: str = federation_v1.OP_SNAPSHOT) -> dict[str, object]:
    capability = {
        federation_v1.OP_SNAPSHOT: federation_v1.CAP_SNAPSHOT,
        federation_v1.OP_SYNC: federation_v1.CAP_SYNC,
    }[operation]
    return {
        "version": 1,
        "source": SOURCE,
        "operation": operation,
        "scope": scope(),
        "required_capabilities": [capability],
        "page_size": page_size,
    }


def response_payload(
    records: list[RecordV1],
    *,
    source: str = SOURCE,
    operation: str = federation_v1.OP_SNAPSHOT,
    scope_fingerprint: str | None = None,
    completeness: str = "PARTIAL_SOURCE",
    next_cursor: bytes | None = None,
) -> dict[str, object]:
    result: dict[str, object] = {
        "version": 1,
        "source": source,
        "operation": operation,
        "scope_fingerprint": scope_fingerprint or federation_v1.scope_fingerprint(scope()),
        "record_ids": sorted(record_identity_text(record) for record in records),
        "source_completeness": completeness,
        "page_truncated": next_cursor is not None,
    }
    if next_cursor is not None:
        result["next_cursor"] = next_cursor
    return result


class OfflineFederationRuntimeTests(unittest.TestCase):
    def runtime_and_service(self):
        runtime = create_in_memory_runtime(
            validate_record=validate_market_record,
            record_identity_text=record_identity_text,
            evaluate_discovery=evaluate_discovery,
            evaluate_match=evaluate_match,
            max_entries=16,
        )
        service = compose_offline_federation_service(
            runtime,
            validate_record=validate_market_record,
            record_identity_text=record_identity_text,
            validate_exchange_request=federation_v1.validate_exchange_request,
            make_transport_envelope=federation_v1.make_transport_envelope,
            validate_transport_envelope=federation_v1.validate_transport_envelope,
            validate_exchange_result=federation_v1.validate_exchange_result,
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
        return runtime, service

    def result_envelope(self, payload: dict[str, object], *, message_type: str = federation_v1.MSG_SNAPSHOT_RESULT):
        return federation_v1.make_transport_envelope(message_type, payload)

    def test_prepare_is_explicitly_unsent_and_binds_exact_request_semantics(self):
        runtime, service = self.runtime_and_service()
        try:
            prepared = service.prepare(request(page_size=3))
            self.assertFalse(prepared.transmitted)
            self.assertEqual(prepared.binding.source, SOURCE)
            self.assertEqual(prepared.binding.operation, federation_v1.OP_SNAPSHOT)
            self.assertEqual(prepared.binding.page_size, 3)
            self.assertEqual(prepared.binding.required_capabilities, (federation_v1.CAP_SNAPSHOT,))
            self.assertEqual(
                prepared.binding.expected_result_message_type,
                federation_v1.MSG_SNAPSHOT_RESULT,
            )
            self.assertEqual(prepared.envelope[2], federation_v1.MSG_SNAPSHOT_REQUEST)
            self.assertEqual(len(runtime.repository), 0)
        finally:
            runtime.close()

    def test_validate_page_is_side_effect_free_and_preserves_binding(self):
        runtime, service = self.runtime_and_service()
        try:
            record = intent("did:example:alice")
            record_id = record_identity_text(record)
            cursor = b"opaque-m28-preview"
            prepared = service.prepare(request(page_size=3))
            validated = service.validate_page(
                prepared,
                self.result_envelope(response_payload([record], next_cursor=cursor)),
            )
            self.assertEqual(validated.source, SOURCE)
            self.assertEqual(validated.operation, federation_v1.OP_SNAPSHOT)
            self.assertEqual(validated.scope_fingerprint, prepared.binding.scope_fingerprint)
            self.assertEqual(validated.page_size, 3)
            self.assertEqual(validated.record_ids, (record_id,))
            self.assertEqual(validated.source_completeness, "PARTIAL_SOURCE")
            self.assertTrue(validated.page_truncated)
            self.assertEqual(validated.next_cursor, cursor)
            self.assertEqual(validated.global_completeness, "UNKNOWN")
            self.assertFalse(validated.absence_is_deletion_evidence)
            self.assertFalse(validated.creates_agreement)
            self.assertFalse(validated.authorizes_side_effects)
            self.assertEqual(len(runtime.repository), 0)
        finally:
            runtime.close()

    def test_accept_page_reuses_side_effect_free_validate_page(self):
        runtime, service = self.runtime_and_service()
        try:
            record = intent("did:example:alice")
            prepared = service.prepare(request())
            envelope = self.result_envelope(response_payload([record]))
            with patch.object(service, "validate_page", wraps=service.validate_page) as validator:
                outcome = service.accept_page(prepared, envelope, [record])
            validator.assert_called_once_with(prepared, envelope)
            self.assertEqual(outcome.record_ids, (record_identity_text(record),))
        finally:
            runtime.close()

    def test_valid_page_is_fully_validated_then_ingested_locally(self):
        runtime, service = self.runtime_and_service()
        try:
            record = intent("did:example:alice")
            prepared = service.prepare(request())
            outcome = service.accept_page(
                prepared,
                self.result_envelope(response_payload([record])),
                [record],
            )
            record_id = record_identity_text(record)
            self.assertEqual(outcome.record_ids, (record_id,))
            self.assertEqual(outcome.stored_record_ids, (record_id,))
            self.assertEqual(outcome.duplicate_record_ids, ())
            self.assertEqual(outcome.global_completeness, "UNKNOWN")
            self.assertFalse(outcome.absence_is_deletion_evidence)
            self.assertFalse(outcome.transport_exactly_once_claimed)
            self.assertFalse(outcome.transport_was_invoked)
            self.assertFalse(outcome.creates_agreement)
            self.assertFalse(outcome.authorizes_side_effects)
            self.assertEqual(runtime.node.get(record_id), record)
        finally:
            runtime.close()

    def test_replayed_identical_page_is_local_duplicate_not_exactly_once_claim(self):
        runtime, service = self.runtime_and_service()
        try:
            record = intent("did:example:alice")
            prepared = service.prepare(request())
            envelope = self.result_envelope(response_payload([record]))
            first = service.accept_page(prepared, envelope, [record])
            second = service.accept_page(prepared, envelope, [record])
            record_id = record_identity_text(record)
            self.assertEqual(first.stored_record_ids, (record_id,))
            self.assertEqual(second.stored_record_ids, ())
            self.assertEqual(second.duplicate_record_ids, (record_id,))
            self.assertFalse(second.transport_exactly_once_claimed)
            self.assertEqual(len(runtime.repository), 1)
        finally:
            runtime.close()

    def test_wrong_source_fails_before_any_local_ingest(self):
        runtime, service = self.runtime_and_service()
        try:
            record = intent("did:example:alice")
            prepared = service.prepare(request())
            with self.assertRaises(OfflineFederationError) as caught:
                service.accept_page(
                    prepared,
                    self.result_envelope(response_payload([record], source="urn:example:source:other")),
                    [record],
                )
            self.assertEqual(caught.exception.code, "FEDERATION_SOURCE_MISMATCH")
            self.assertEqual(len(runtime.repository), 0)
        finally:
            runtime.close()

    def test_wrong_scope_fingerprint_fails_before_any_local_ingest(self):
        runtime, service = self.runtime_and_service()
        try:
            record = intent("did:example:alice")
            prepared = service.prepare(request())
            other_scope = {"version": 1, "record_types": [TYPE_INTENT], "profiles_all": [CORE_PROFILE]}
            with self.assertRaises(OfflineFederationError) as caught:
                service.accept_page(
                    prepared,
                    self.result_envelope(
                        response_payload(
                            [record],
                            scope_fingerprint=federation_v1.scope_fingerprint(other_scope),
                        )
                    ),
                    [record],
                )
            self.assertEqual(caught.exception.code, "FEDERATION_SCOPE_MISMATCH")
            self.assertEqual(len(runtime.repository), 0)
        finally:
            runtime.close()

    def test_response_record_identity_set_must_exactly_match_supplied_records(self):
        runtime, service = self.runtime_and_service()
        try:
            declared = intent("did:example:alice")
            supplied = intent("did:example:bob", subject="urn:example:item:other")
            prepared = service.prepare(request())
            with self.assertRaises(OfflineFederationError) as caught:
                service.accept_page(
                    prepared,
                    self.result_envelope(response_payload([declared])),
                    [supplied],
                )
            self.assertEqual(caught.exception.code, "FEDERATION_RECORD_SET_MISMATCH")
            self.assertEqual(len(runtime.repository), 0)
        finally:
            runtime.close()

    def test_response_cannot_exceed_original_requested_page_size(self):
        runtime, service = self.runtime_and_service()
        try:
            left = intent("did:example:alice", subject="urn:example:item:a")
            right = intent("did:example:bob", subject="urn:example:item:b")
            prepared = service.prepare(request(page_size=1))
            with self.assertRaises(OfflineFederationError) as caught:
                service.accept_page(
                    prepared,
                    self.result_envelope(response_payload([left, right])),
                    [left, right],
                )
            self.assertEqual(caught.exception.code, "FEDERATION_PAGE_SIZE_EXCEEDED")
            self.assertEqual(len(runtime.repository), 0)
        finally:
            runtime.close()

    def test_opaque_next_cursor_is_preserved_without_interpretation(self):
        runtime, service = self.runtime_and_service()
        try:
            record = intent("did:example:alice")
            cursor = b"opaque-next-page\x00\xff"
            prepared = service.prepare(request())
            outcome = service.accept_page(
                prepared,
                self.result_envelope(response_payload([record], next_cursor=cursor)),
                [record],
            )
            self.assertTrue(outcome.page_truncated)
            self.assertEqual(outcome.next_cursor, cursor)
        finally:
            runtime.close()

    def test_wrong_response_message_type_is_rejected_without_ingest(self):
        runtime, service = self.runtime_and_service()
        try:
            record = intent("did:example:alice")
            prepared = service.prepare(request())
            envelope = self.result_envelope(
                response_payload([record]),
                message_type=federation_v1.MSG_SYNC_RESULT,
            )
            with self.assertRaises(Exception):
                service.accept_page(prepared, envelope, [record])
            self.assertEqual(len(runtime.repository), 0)
        finally:
            runtime.close()

    def test_duplicate_supplied_identity_is_rejected_before_ingest(self):
        runtime, service = self.runtime_and_service()
        try:
            record = intent("did:example:alice")
            prepared = service.prepare(request())
            with self.assertRaises(OfflineFederationError) as caught:
                service.accept_page(
                    prepared,
                    self.result_envelope(response_payload([record])),
                    [record, record],
                )
            self.assertEqual(caught.exception.code, "FEDERATION_DUPLICATE_SUPPLIED_RECORD")
            self.assertEqual(len(runtime.repository), 0)
        finally:
            runtime.close()


class PackagedFederationReferenceParityTests(unittest.TestCase):
    def test_historical_m8_tool_path_reexports_packaged_single_source(self):
        import marketplace_federation_v1 as wrapper

        self.assertIs(wrapper.validate_exchange_request, federation_v1.validate_exchange_request)
        self.assertIs(wrapper.validate_exchange_result, federation_v1.validate_exchange_result)
        self.assertIs(wrapper.make_transport_envelope, federation_v1.make_transport_envelope)
        self.assertIs(wrapper.evaluate_exchange_page, federation_v1.evaluate_exchange_page)


if __name__ == "__main__":
    unittest.main()
