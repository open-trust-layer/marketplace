from __future__ import annotations

import unittest

from olp import RecordV1

from marketplace.reference import CORE_PROFILE, TYPE_INTENT, record_identity_text, validate_market_record
from marketplace.reference.record_retrieval_v1 import verify_retrieved_market_record
from marketplace.reference.record_serving_v1 import (
    make_record_transport_envelope,
    market_record_transport_payload,
    verify_prepared_record_transport_envelope,
)
from marketplace.runtime.inbound_record import (
    INBOUND_RECORD_RETRIEVAL_OPERATION,
    BoundedInboundRecordResponder,
    InboundRecordError,
)
from marketplace.runtime.record_retrieval import RECORD_RETRIEVAL_OPERATION

SOURCE = "urn:example:source:m33"
ACTION = "https://example.test/actions/sell"
SUBJECT = "urn:example:item:m33"


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


class InboundRecordTests(unittest.TestCase):
    def responder(self, source: FakeSource, authorizer=lambda context: True, **overrides):
        values = {
            "local_source": SOURCE,
            "record_source": source,
            "authorize_disclosure": authorizer,
            "validate_record": validate_market_record,
            "record_identity": record_identity_text,
            "prepare_payload": market_record_transport_payload,
            "make_record_envelope": make_record_transport_envelope,
            "verify_record_envelope": verify_prepared_record_transport_envelope,
        }
        values.update(overrides)
        return BoundedInboundRecordResponder(**values)

    def test_operation_matches_m27_retrieval_operation(self):
        self.assertEqual(INBOUND_RECORD_RETRIEVAL_OPERATION, RECORD_RETRIEVAL_OPERATION)

    def test_one_exact_record_is_prepared_but_not_transmitted(self):
        expected_record = record()
        record_id = record_identity_text(expected_record)
        source = FakeSource(expected_record)
        contexts = []
        responder = self.responder(source, authorizer=lambda context: contexts.append(context) or True)

        prepared = responder.prepare(requested_record_identity=record_id)

        self.assertEqual(source.calls, [record_id])
        self.assertEqual(len(contexts), 1)
        self.assertEqual(contexts[0].requested_record_identity, record_id)
        self.assertEqual(contexts[0].local_source, SOURCE)
        self.assertEqual(contexts[0].operation, RECORD_RETRIEVAL_OPERATION)
        self.assertFalse(contexts[0].request_authenticated)
        self.assertFalse(contexts[0].peer_identity_proven)
        self.assertFalse(contexts[0].prior_page_membership_is_authorization)
        self.assertEqual(prepared.envelope[:3], ("OLP-TRANSPORT", 1, "record"))
        self.assertFalse(prepared.transmitted)
        self.assertTrue(prepared.local_record_found)
        self.assertTrue(prepared.identity_verified)
        self.assertTrue(prepared.marketplace_semantics_verified)
        self.assertFalse(prepared.proofs_verified)
        self.assertEqual(prepared.global_existence, "UNKNOWN")
        self.assertFalse(prepared.absence_is_deletion_evidence)
        self.assertFalse(prepared.establishes_truth)
        self.assertFalse(prepared.establishes_ownership)
        self.assertFalse(prepared.establishes_authority)
        self.assertFalse(prepared.establishes_trust)
        self.assertFalse(prepared.establishes_authorization)
        self.assertFalse(prepared.authorizes_protected_side_effects)

        verified = verify_retrieved_market_record(
            prepared.envelope,
            expected_record_identity=record_id,
        )
        self.assertEqual(verified.record, expected_record)
        self.assertEqual(verified.recomputed_record_identity, record_id)

    def test_malformed_identity_fails_before_authorizer_or_source(self):
        source = FakeSource(record())
        calls: list[str] = []
        responder = self.responder(source, authorizer=lambda context: calls.append("auth") or True)

        with self.assertRaises(InboundRecordError) as raised:
            responder.prepare(requested_record_identity="not-a-record-id")

        self.assertEqual(raised.exception.code, "INVALID_RECORD_IDENTITY_SHAPE")
        self.assertEqual(calls, [])
        self.assertEqual(source.calls, [])

    def test_disclosure_denial_stops_before_record_source(self):
        expected_record = record()
        record_id = record_identity_text(expected_record)
        source = FakeSource(expected_record)
        calls: list[str] = []
        responder = self.responder(source, authorizer=lambda context: calls.append("auth") or False)

        with self.assertRaises(InboundRecordError) as raised:
            responder.prepare(requested_record_identity=record_id)

        self.assertEqual(raised.exception.code, "DISCLOSURE_DENIED")
        self.assertEqual(calls, ["auth"])
        self.assertEqual(source.calls, [])

    def test_nonboolean_disclosure_decision_fails_closed(self):
        expected_record = record()
        record_id = record_identity_text(expected_record)
        source = FakeSource(expected_record)
        responder = self.responder(source, authorizer=lambda context: 1)

        with self.assertRaises(InboundRecordError) as raised:
            responder.prepare(requested_record_identity=record_id)

        self.assertEqual(raised.exception.code, "INVALID_DISCLOSURE_DECISION")
        self.assertEqual(source.calls, [])

    def test_local_miss_is_not_global_nonexistence_or_deletion_evidence(self):
        record_id = record_identity_text(record())
        source = FakeSource(None)
        responder = self.responder(source)

        with self.assertRaises(InboundRecordError) as raised:
            responder.prepare(requested_record_identity=record_id)

        self.assertEqual(raised.exception.code, "LOCAL_RECORD_NOT_FOUND")
        self.assertIn("global existence is unknown", str(raised.exception))
        self.assertEqual(source.calls, [record_id])

    def test_wrong_local_record_identity_fails_before_payload_or_envelope(self):
        requested = record()
        wrong = record("did:example:bob", subject="urn:example:item:other")
        requested_id = record_identity_text(requested)
        source = FakeSource(wrong)
        calls: list[str] = []
        responder = self.responder(
            source,
            prepare_payload=lambda *args, **kwargs: calls.append("payload") or {},
            make_record_envelope=lambda payload: calls.append("envelope") or (),
        )

        with self.assertRaises(InboundRecordError) as raised:
            responder.prepare(requested_record_identity=requested_id)

        self.assertEqual(raised.exception.code, "LOCAL_RECORD_IDENTITY_MISMATCH")
        self.assertEqual(calls, [])

    def test_invalid_marketplace_record_fails_before_payload(self):
        invalid = RecordV1.from_mapping(
            {
                "envelope_version": 1,
                "type": "https://example.test/not-marketplace",
                "content": {},
            }
        )
        record_id = record_identity_text(invalid)
        source = FakeSource(invalid)
        calls: list[str] = []
        responder = self.responder(
            source,
            prepare_payload=lambda *args, **kwargs: calls.append("payload") or {},
        )

        with self.assertRaises(InboundRecordError) as raised:
            responder.prepare(requested_record_identity=record_id)

        self.assertEqual(raised.exception.code, "INVALID_LOCAL_RECORD")
        self.assertEqual(calls, [])

    def test_record_source_is_called_exactly_once_after_authorization(self):
        expected_record = record()
        record_id = record_identity_text(expected_record)
        source = FakeSource(expected_record)
        order: list[str] = []

        class OrderedSource(FakeSource):
            def get(self, record_id):
                order.append("source")
                return super().get(record_id)

        source = OrderedSource(expected_record)
        responder = self.responder(source, authorizer=lambda context: order.append("auth") or True)
        responder.prepare(requested_record_identity=record_id)

        self.assertEqual(order[:2], ["auth", "source"])
        self.assertEqual(source.calls, [record_id])

    def test_prior_m32_page_membership_is_neither_required_nor_authorization(self):
        expected_record = record()
        record_id = record_identity_text(expected_record)
        source = FakeSource(expected_record)
        responder = self.responder(source, authorizer=lambda context: False)

        with self.assertRaises(InboundRecordError) as raised:
            responder.prepare(requested_record_identity=record_id)

        self.assertEqual(raised.exception.code, "DISCLOSURE_DENIED")
        self.assertEqual(source.calls, [])


if __name__ == "__main__":
    unittest.main()
