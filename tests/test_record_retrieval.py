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
from marketplace.reference.record_retrieval_v1 import (
    RetrievedRecordVerificationError,
    verify_retrieved_market_record,
)
from marketplace.reference.transport_json_v1 import (
    decode_transport_envelope_json,
    encode_transport_envelope_json,
)
from marketplace.runtime import (
    FederationOperationProfile,
    compose_offline_federation_service,
    create_in_memory_runtime,
)
from marketplace.runtime.https_transport import HttpsFederationTransportLimits
from marketplace.runtime.network_policy import FederationEgressPolicy, authorize_federation_endpoint
from marketplace.runtime.record_retrieval import (
    RECORD_RETRIEVAL_OPERATION,
    AuthorizedHttpsRecordRetriever,
    RecordRetrievalTransportError,
)

HOST = "records.example.com"
SOURCE = "urn:example:source:m27"
ACTION = "https://example.test/actions/sell"
SUBJECT = "urn:example:item:m27"


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


def record_body(mapping: dict[str, object]) -> bytes:
    return encode_transport_envelope_json(("OLP-TRANSPORT", 1, "record", mapping))


def http_response(body: bytes, *, status: int = 200) -> bytes:
    return (
        f"HTTP/1.1 {status} {'OK' if status == 200 else 'Other'}\r\n"
        "Content-Type: application/json\r\n"
        f"Content-Length: {len(body)}\r\n"
        "\r\n"
    ).encode("ascii") + body


class FakeConnection:
    def __init__(self, response: bytes):
        self.response = bytearray(response)
        self.sent = bytearray()
        self.timeouts: list[float] = []
        self.closed = False

    def sendall(self, data: bytes) -> None:
        self.sent.extend(data)

    def recv(self, size: int) -> bytes:
        if not self.response:
            return b""
        chunk = bytes(self.response[:size])
        del self.response[:size]
        return chunk

    def settimeout(self, value: float) -> None:
        self.timeouts.append(value)

    def close(self) -> None:
        self.closed = True


class FakeConnector:
    def __init__(self, connection: FakeConnection):
        self.connection = connection
        self.calls: list[dict[str, object]] = []

    def __call__(self, **kwargs):
        self.calls.append(dict(kwargs))
        return self.connection


class AuthorizedRecordRetrievalTests(unittest.TestCase):
    def policy(self) -> FederationEgressPolicy:
        return FederationEgressPolicy(
            policy_id="https://open-trust-layer.github.io/marketplace/policy/m27-egress-v1",
            policy_version=1,
            allowed_hosts=(HOST,),
        )

    def endpoint(self, record_id: str) -> str:
        return f"https://{HOST}/olp/v1/records/{record_id}"

    def authorization(self, record_id: str):
        return authorize_federation_endpoint(
            endpoint=self.endpoint(record_id),
            allowed_operations=(RECORD_RETRIEVAL_OPERATION,),
            authorization_id="m27-record-get",
            issued_at_epoch=1_000,
            expires_at_epoch=1_120,
            policy=self.policy(),
        )

    def retriever(
        self,
        connection: FakeConnection,
        *,
        resolver=None,
        wall_clock=None,
        limits=None,
    ) -> tuple[AuthorizedHttpsRecordRetriever, FakeConnector]:
        connector = FakeConnector(connection)
        retriever = AuthorizedHttpsRecordRetriever(
            policy=self.policy(),
            decode_envelope_json=decode_transport_envelope_json,
            limits=limits,
            resolver=resolver or (lambda host, port: ("1.1.1.1",)),
            connector=connector,
            wall_clock=wall_clock or (lambda: 1_050.0),
            monotonic_clock=lambda: 10.0,
        )
        return retriever, connector

    def test_one_exact_get_is_transport_only_until_local_identity_verification(self):
        expected_record = record()
        record_id = record_identity_text(expected_record)
        connection = FakeConnection(http_response(record_body(record_mapping())))
        retriever, connector = self.retriever(connection)

        result = retriever.retrieve(
            endpoint=self.endpoint(record_id),
            authorization=self.authorization(record_id),
            expected_record_identity=record_id,
        )

        request = bytes(connection.sent)
        self.assertTrue(request.startswith(f"GET /olp/v1/records/{record_id} HTTP/1.1\r\n".encode("ascii")))
        self.assertIn(f"Host: {HOST}\r\n".encode("ascii"), request)
        self.assertIn(b"Accept: application/json\r\n", request)
        self.assertIn(b"Connection: close\r\n", request)
        self.assertNotIn(b"Content-Length:", request)
        self.assertNotIn(b"Authorization:", request)
        self.assertTrue(request.endswith(b"\r\n\r\n"))
        self.assertEqual(len(connector.calls), 1)
        self.assertEqual(connector.calls[0]["address"], "1.1.1.1")
        self.assertEqual(connector.calls[0]["server_hostname"], HOST)
        self.assertTrue(connection.closed)

        self.assertEqual(result.response_envelope[2], "record")
        self.assertFalse(result.identity_verified)
        self.assertFalse(result.marketplace_semantics_verified)
        self.assertFalse(result.proofs_verified)
        self.assertFalse(result.establishes_truth)
        self.assertFalse(result.establishes_authorization)
        self.assertFalse(result.automatically_ingested)

        verified = verify_retrieved_market_record(
            result.response_envelope,
            expected_record_identity=record_id,
        )
        self.assertEqual(verified.record, expected_record)
        self.assertEqual(verified.recomputed_record_identity, record_id)
        self.assertTrue(verified.identity_verified)
        self.assertTrue(verified.marketplace_semantics_verified)
        self.assertFalse(verified.proofs_verified)
        self.assertFalse(verified.establishes_truth)
        self.assertFalse(verified.establishes_ownership)
        self.assertFalse(verified.establishes_authority)
        self.assertFalse(verified.establishes_trust)
        self.assertFalse(verified.establishes_authorization)
        self.assertFalse(verified.automatically_ingested)

    def test_invalid_expected_identity_shape_and_path_mismatch_fail_before_dns(self):
        calls: list[str] = []
        expected_record = record()
        record_id = record_identity_text(expected_record)
        connection = FakeConnection(http_response(record_body(record_mapping())))
        retriever, connector = self.retriever(
            connection,
            resolver=lambda host, port: calls.append("dns") or ("1.1.1.1",),
        )

        with self.assertRaises(RecordRetrievalTransportError) as bad_shape:
            retriever.retrieve(
                endpoint=self.endpoint(record_id),
                authorization=self.authorization(record_id),
                expected_record_identity="not-a-record-id",
            )
        self.assertEqual(bad_shape.exception.code, "INVALID_EXPECTED_RECORD_IDENTITY_SHAPE")

        other = record_identity_text(record("did:example:bob", subject="urn:example:item:other"))
        with self.assertRaises(RecordRetrievalTransportError) as mismatch:
            retriever.retrieve(
                endpoint=self.endpoint(record_id),
                authorization=self.authorization(record_id),
                expected_record_identity=other,
            )
        self.assertEqual(mismatch.exception.code, "ENDPOINT_RECORD_IDENTITY_MISMATCH")
        self.assertEqual(calls, [])
        self.assertEqual(connector.calls, [])

    def test_unsafe_resolution_and_post_dns_authorization_expiry_prevent_connect(self):
        expected_record = record()
        record_id = record_identity_text(expected_record)
        connection = FakeConnection(http_response(record_body(record_mapping())))
        retriever, connector = self.retriever(
            connection,
            resolver=lambda host, port: ("1.1.1.1", "127.0.0.1"),
        )
        with self.assertRaises(RecordRetrievalTransportError) as unsafe:
            retriever.retrieve(
                endpoint=self.endpoint(record_id),
                authorization=self.authorization(record_id),
                expected_record_identity=record_id,
            )
        self.assertEqual(unsafe.exception.code, "UNSAFE_RESOLUTION")
        self.assertEqual(connector.calls, [])

        clocks = iter((1_050.0, 1_120.0))
        connection = FakeConnection(http_response(record_body(record_mapping())))
        retriever, connector = self.retriever(connection, wall_clock=lambda: next(clocks))
        with self.assertRaises(Exception) as expired:
            retriever.retrieve(
                endpoint=self.endpoint(record_id),
                authorization=self.authorization(record_id),
                expected_record_identity=record_id,
            )
        self.assertEqual(getattr(expired.exception, "code", None), "AUTHORIZATION_EXPIRED")
        self.assertEqual(connector.calls, [])

    def test_wrong_olp_message_type_is_rejected_by_transport(self):
        expected_record = record()
        record_id = record_identity_text(expected_record)
        body = encode_transport_envelope_json(("OLP-TRANSPORT", 1, "error", {"code": "example"}))
        retriever, _ = self.retriever(FakeConnection(http_response(body)))
        with self.assertRaises(RecordRetrievalTransportError) as caught:
            retriever.retrieve(
                endpoint=self.endpoint(record_id),
                authorization=self.authorization(record_id),
                expected_record_identity=record_id,
            )
        self.assertEqual(caught.exception.code, "RECORD_MESSAGE_TYPE_REQUIRED")

    def test_reference_verifier_rejects_identity_mismatch_and_noncanonical_expected_identity(self):
        requested = record()
        requested_id = record_identity_text(requested)
        different_mapping = record_mapping("did:example:bob", subject="urn:example:item:other")
        envelope = decode_transport_envelope_json(record_body(different_mapping))
        with self.assertRaises(RetrievedRecordVerificationError) as mismatch:
            verify_retrieved_market_record(envelope, expected_record_identity=requested_id)
        self.assertEqual(mismatch.exception.code, "RECORD_IDENTITY_MISMATCH")

        noncanonical = "r1_" + ("A" * 42) + "B"
        with self.assertRaises(RetrievedRecordVerificationError) as bad_expected:
            verify_retrieved_market_record(envelope, expected_record_identity=noncanonical)
        self.assertEqual(bad_expected.exception.code, "INVALID_EXPECTED_RECORD_IDENTITY")

    def test_reference_verifier_rejects_malformed_or_non_marketplace_record(self):
        expected_record = record()
        record_id = record_identity_text(expected_record)
        malformed = ("OLP-TRANSPORT", 1, "record", {"envelope_version": 1})
        with self.assertRaises(RetrievedRecordVerificationError) as invalid:
            verify_retrieved_market_record(malformed, expected_record_identity=record_id)
        self.assertEqual(invalid.exception.code, "INVALID_OLP_RECORD")

        non_market_mapping = dict(record_mapping())
        non_market_mapping["type"] = "https://example.test/record/not-marketplace"
        non_market = RecordV1.from_mapping(non_market_mapping)
        non_market_id = record_identity_text(non_market)
        envelope = ("OLP-TRANSPORT", 1, "record", non_market_mapping)
        with self.assertRaises(RetrievedRecordVerificationError) as semantic:
            verify_retrieved_market_record(envelope, expected_record_identity=non_market_id)
        self.assertEqual(semantic.exception.code, "INVALID_MARKETPLACE_RECORD")

    def test_transport_response_limit_is_inherited_from_m26(self):
        expected_record = record()
        record_id = record_identity_text(expected_record)
        body = record_body(record_mapping())
        limits = HttpsFederationTransportLimits(max_response_bytes=max(1, len(body) - 1))
        retriever, _ = self.retriever(FakeConnection(http_response(body)), limits=limits)
        with self.assertRaises(FederationHttpsTransportError) as caught:
            retriever.retrieve(
                endpoint=self.endpoint(record_id),
                authorization=self.authorization(record_id),
                expected_record_identity=record_id,
            )
        self.assertEqual(caught.exception.code, "HTTP_BODY_LIMIT")

    def test_verified_retrieved_record_flows_through_existing_m24_accept_page_before_storage(self):
        expected_record = record()
        record_id = record_identity_text(expected_record)
        connection = FakeConnection(http_response(record_body(record_mapping())))
        retriever, _ = self.retriever(connection)

        retrieved = retriever.retrieve(
            endpoint=self.endpoint(record_id),
            authorization=self.authorization(record_id),
            expected_record_identity=record_id,
        )
        verified = verify_retrieved_market_record(
            retrieved.response_envelope,
            expected_record_identity=record_id,
        )

        runtime = create_in_memory_runtime(
            validate_record=validate_market_record,
            record_identity_text=record_identity_text,
            evaluate_discovery=evaluate_discovery,
            evaluate_match=evaluate_match,
            max_entries=8,
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
            ),
        )
        try:
            self.assertEqual(len(runtime.repository), 0)
            scope = {"version": 1, "record_types": [TYPE_INTENT]}
            request = {
                "version": 1,
                "source": SOURCE,
                "operation": federation_v1.OP_SNAPSHOT,
                "scope": scope,
                "required_capabilities": [federation_v1.CAP_SNAPSHOT],
                "page_size": 1,
            }
            prepared = service.prepare(request)
            result_payload = {
                "version": 1,
                "source": SOURCE,
                "operation": federation_v1.OP_SNAPSHOT,
                "scope_fingerprint": federation_v1.scope_fingerprint(scope),
                "record_ids": [record_id],
                "source_completeness": "PARTIAL_SOURCE",
                "page_truncated": False,
            }
            result_envelope = federation_v1.make_transport_envelope(
                federation_v1.MSG_SNAPSHOT_RESULT,
                result_payload,
            )
            outcome = service.accept_page(prepared, result_envelope, [verified.record])
            self.assertEqual(outcome.stored_record_ids, (record_id,))
            self.assertEqual(runtime.node.get(record_id), verified.record)
        finally:
            runtime.close()


if __name__ == "__main__":
    unittest.main()
