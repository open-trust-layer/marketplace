from __future__ import annotations

import ast
from dataclasses import replace
from pathlib import Path
import unittest

from olp import RecordV1

from marketplace.reference import CORE_PROFILE, TYPE_INTENT, record_identity_text, validate_market_record
from marketplace.reference.record_serving_v1 import (
    RecordServingReferenceError,
    make_record_transport_envelope,
    market_record_transport_payload,
    verify_prepared_record_transport_envelope,
)
from marketplace.runtime.inbound_record import BoundedInboundRecordResponder, InboundRecordError
from marketplace.runtime.prepared_integrity import (
    MAX_PREPARED_SNAPSHOT_DEPTH,
    MAX_PREPARED_SNAPSHOT_ITEMS,
)

SOURCE = "urn:example:source:m33-hardening"
ACTION = "https://example.test/actions/sell"
SUBJECT = "urn:example:item:m33-hardening"


def record_mapping(principal: str = "did:example:alice", *, subject: str = SUBJECT) -> dict[str, object]:
    return {
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


def record(principal: str = "did:example:alice", *, subject: str = SUBJECT) -> RecordV1:
    return RecordV1.from_mapping(record_mapping(principal, subject=subject))


class FakeSource:
    def __init__(self, value):
        self.value = value
        self.calls: list[str] = []

    def get(self, record_id: str):
        self.calls.append(record_id)
        return self.value


class InboundRecordHardeningTests(unittest.TestCase):
    def responder(self, source, **overrides):
        values = {
            "local_source": SOURCE,
            "record_source": source,
            "authorize_disclosure": lambda context: True,
            "validate_record": validate_market_record,
            "record_identity": record_identity_text,
            "prepare_payload": market_record_transport_payload,
            "make_record_envelope": make_record_transport_envelope,
            "verify_record_envelope": verify_prepared_record_transport_envelope,
        }
        values.update(overrides)
        return BoundedInboundRecordResponder(**values)

    def test_payload_alias_mutation_after_return_cannot_change_prepared_body(self):
        expected_record = record()
        record_id = record_identity_text(expected_record)
        source = FakeSource(expected_record)
        alias: dict[str, object] = {}

        def payload_provider(value, *, expected_record_identity):
            alias.update(market_record_transport_payload(value, expected_record_identity=expected_record_identity))
            return alias

        def envelope_maker(detached_payload):
            alias["type"] = "https://example.test/attacker-type"
            content = alias.get("content")
            if isinstance(content, dict):
                content["terms"] = {"https://example.test/attacker": True}
            return make_record_transport_envelope(detached_payload)

        prepared = self.responder(
            source,
            prepare_payload=payload_provider,
            make_record_envelope=envelope_maker,
        ).prepare(requested_record_identity=record_id)

        verified = verify_prepared_record_transport_envelope(
            prepared.envelope,
            expected_record_identity=record_id,
        )
        self.assertTrue(verified["identity_verified"])
        self.assertEqual(verified["recomputed_record_identity"], record_id)

    def test_custom_mapping_payload_is_rejected_by_bounded_detacher(self):
        expected_record = record()
        record_id = record_identity_text(expected_record)

        class CustomDict(dict):
            pass

        responder = self.responder(
            FakeSource(expected_record),
            prepare_payload=lambda value, **kwargs: CustomDict(record_mapping()),
        )
        with self.assertRaises(InboundRecordError) as raised:
            responder.prepare(requested_record_identity=record_id)
        self.assertEqual(raised.exception.code, "UNSAFE_RECORD_PAYLOAD")

    def test_reference_payload_conversion_rejects_excessive_depth_before_unbounded_copy(self):
        nested: object = "leaf"
        for index in range(MAX_PREPARED_SNAPSHOT_DEPTH + 2):
            nested = {f"level-{index}": nested}
        value = record()
        value = RecordV1.from_mapping(
            {
                **record_mapping(),
                "extensions": {"https://example.test/deep": nested},
            }
        )
        value.validate()
        validate_market_record(value)
        record_id = record_identity_text(value)

        with self.assertRaises(RecordServingReferenceError) as raised:
            market_record_transport_payload(value, expected_record_identity=record_id)

        self.assertEqual(raised.exception.code, "PAYLOAD_DEPTH_EXCEEDED")

    def test_reference_payload_conversion_rejects_oversized_collection_before_copy(self):
        oversized = {f"item-{index}": index for index in range(MAX_PREPARED_SNAPSHOT_ITEMS + 1)}
        value = RecordV1.from_mapping(
            {
                **record_mapping(),
                "extensions": {"https://example.test/wide": oversized},
            }
        )
        value.validate()
        validate_market_record(value)
        record_id = record_identity_text(value)

        with self.assertRaises(RecordServingReferenceError) as raised:
            market_record_transport_payload(value, expected_record_identity=record_id)

        self.assertEqual(raised.exception.code, "PAYLOAD_ITEM_LIMIT")

    def test_payload_helper_record_mutation_is_detected_before_envelope_creation(self):
        original_id = record_identity_text(record())
        other_id = record_identity_text(record("did:example:bob", subject="urn:example:item:other"))
        mutable_record = {"id": original_id, "valid": True}
        calls: list[str] = []

        def mutate_payload(value, *, expected_record_identity):
            value["id"] = other_id
            return record_mapping()

        responder = BoundedInboundRecordResponder(
            local_source=SOURCE,
            record_source=FakeSource(mutable_record),
            authorize_disclosure=lambda context: True,
            validate_record=lambda value: None,
            record_identity=lambda value: value["id"],
            prepare_payload=mutate_payload,
            make_record_envelope=lambda payload: calls.append("envelope") or make_record_transport_envelope(payload),
            verify_record_envelope=verify_prepared_record_transport_envelope,
        )
        with self.assertRaises(InboundRecordError) as raised:
            responder.prepare(requested_record_identity=original_id)
        self.assertEqual(raised.exception.code, "LOCAL_RECORD_IDENTITY_MISMATCH")
        self.assertEqual(calls, [])

    def test_envelope_maker_cannot_change_message_type_or_payload(self):
        expected_record = record()
        record_id = record_identity_text(expected_record)
        source = FakeSource(expected_record)

        with self.assertRaises(InboundRecordError) as wrong_type:
            self.responder(
                source,
                make_record_envelope=lambda payload: ("OLP-TRANSPORT", 1, "proof", payload),
            ).prepare(requested_record_identity=record_id)
        self.assertEqual(wrong_type.exception.code, "RECORD_MESSAGE_TYPE_REQUIRED")

        with self.assertRaises(InboundRecordError) as wrong_payload:
            self.responder(
                FakeSource(expected_record),
                make_record_envelope=lambda payload: ("OLP-TRANSPORT", 1, "record", {"changed": True}),
            ).prepare(requested_record_identity=record_id)
        self.assertEqual(wrong_payload.exception.code, "RECORD_ENVELOPE_PAYLOAD_DRIFT")

    def test_hostile_verifier_cannot_drift_identity_or_promote_authority(self):
        expected_record = record()
        record_id = record_identity_text(expected_record)
        other_id = record_identity_text(record("did:example:bob", subject="urn:example:item:other"))

        good = verify_prepared_record_transport_envelope(
            make_record_transport_envelope(
                market_record_transport_payload(expected_record, expected_record_identity=record_id)
            ),
            expected_record_identity=record_id,
        )

        drifted = dict(good)
        drifted["recomputed_record_identity"] = other_id
        with self.assertRaises(InboundRecordError) as identity_drift:
            self.responder(
                FakeSource(expected_record),
                verify_record_envelope=lambda envelope, **kwargs: drifted,
            ).prepare(requested_record_identity=record_id)
        self.assertEqual(identity_drift.exception.code, "RECORD_VERIFICATION_IDENTITY_DRIFT")

        promoted = dict(good)
        promoted["establishes_truth"] = True
        with self.assertRaises(InboundRecordError) as authority:
            self.responder(
                FakeSource(expected_record),
                verify_record_envelope=lambda envelope, **kwargs: promoted,
            ).prepare(requested_record_identity=record_id)
        self.assertEqual(authority.exception.code, "RECORD_VERIFICATION_AUTHORITY_ESCALATION")

    def test_verifier_base_dict_mutation_cannot_change_authoritative_envelope(self):
        expected_record = record()
        record_id = record_identity_text(expected_record)

        def hostile_verifier(envelope, *, expected_record_identity):
            payload = envelope[3]
            dict.__setitem__(payload, "type", "https://example.test/attacker")
            return verify_prepared_record_transport_envelope(
                envelope,
                expected_record_identity=expected_record_identity,
            )

        prepared = self.responder(
            FakeSource(expected_record),
            verify_record_envelope=hostile_verifier,
        ).prepare(requested_record_identity=record_id)
        verified = verify_prepared_record_transport_envelope(
            prepared.envelope,
            expected_record_identity=record_id,
        )
        self.assertEqual(verified["recomputed_record_identity"], record_id)

    def test_prepared_response_integrity_snapshot_blocks_rebinding(self):
        expected_record = record()
        record_id = record_identity_text(expected_record)
        prepared = self.responder(FakeSource(expected_record)).prepare(
            requested_record_identity=record_id
        )
        payload = prepared.envelope[3].copy()
        payload["type"] = TYPE_INTENT
        content = dict(payload["content"])
        content["issuer"] = {"principal": "did:example:mallory"}
        payload["content"] = content
        altered = ("OLP-TRANSPORT", 1, "record", payload)

        with self.assertRaises(ValueError):
            replace(prepared, envelope=altered)

    def test_identity_provider_must_return_exact_canonical_record_identity(self):
        expected_record = record()
        record_id = record_identity_text(expected_record)
        with self.assertRaises(InboundRecordError) as raised:
            self.responder(
                FakeSource(expected_record),
                record_identity=lambda value: True,
            ).prepare(requested_record_identity=record_id)
        self.assertEqual(raised.exception.code, "INVALID_IDENTITY_PROVIDER_RESULT")

    def test_m33_source_has_no_network_server_filesystem_background_or_logging_surface(self):
        source_path = Path(__file__).resolve().parents[1] / "src" / "marketplace" / "runtime" / "inbound_record.py"
        tree = ast.parse(source_path.read_text(encoding="utf-8"))
        imported_roots: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported_roots.update(alias.name.split(".", 1)[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported_roots.add(node.module.split(".", 1)[0])
        forbidden = {
            "socket",
            "ssl",
            "http",
            "urllib",
            "asyncio",
            "threading",
            "subprocess",
            "logging",
            "os",
            "pathlib",
        }
        self.assertTrue(imported_roots.isdisjoint(forbidden), imported_roots & forbidden)

    def test_m33_reference_adapter_has_no_network_or_process_surface(self):
        source_path = Path(__file__).resolve().parents[1] / "src" / "marketplace" / "reference" / "record_serving_v1.py"
        tree = ast.parse(source_path.read_text(encoding="utf-8"))
        imported_roots: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported_roots.update(alias.name.split(".", 1)[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported_roots.add(node.module.split(".", 1)[0])
        forbidden = {"socket", "ssl", "http", "urllib", "asyncio", "threading", "subprocess", "logging", "os", "pathlib"}
        self.assertTrue(imported_roots.isdisjoint(forbidden), imported_roots & forbidden)


if __name__ == "__main__":
    unittest.main()
