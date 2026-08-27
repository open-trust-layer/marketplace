from __future__ import annotations

import unittest

from marketplace.reference import TYPE_INTENT, federation_v1
from marketplace.reference.transport_json_v1 import encode_transport_envelope_json
from marketplace.runtime import FederationOperationProfile, compose_offline_federation_service, create_in_memory_runtime
from marketplace.runtime.https_transport import AuthorizedHttpsFederationTransport
from marketplace.runtime.network_policy import FederationEgressPolicy, authorize_federation_endpoint

SOURCE = "https://peer.example/federation"
ENDPOINT = "https://federation.example.com/federation/v1"


class _FakeConnection:
    def __init__(self, response: bytes):
        self.response = bytearray(response)
        self.sent = bytearray()
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
        return None

    def close(self) -> None:
        self.closed = True


def _http_response(body: bytes = b"{}") -> bytes:
    return (
        b"HTTP/1.1 200 OK\r\n"
        b"Content-Type: application/json\r\n"
        + f"Content-Length: {len(body)}\r\n\r\n".encode("ascii")
        + body
    )


def _request() -> dict[str, object]:
    return {
        "version": 1,
        "source": SOURCE,
        "operation": federation_v1.OP_SYNC,
        "scope": {"version": 1, "record_types": [TYPE_INTENT]},
        "required_capabilities": [federation_v1.CAP_SYNC],
        "page_size": 4,
        "cursor": b"page-2",
    }


class PreparedExchangeM26RegressionTests(unittest.TestCase):
    def test_mutating_original_request_after_prepare_cannot_change_m26_transmitted_body(self):
        runtime = create_in_memory_runtime(
            validate_record=lambda value: value,
            record_identity_text=lambda value: "r1_" + "A" * 43,
            evaluate_discovery=lambda *args, **kwargs: {},
            evaluate_match=lambda *args, **kwargs: {},
            max_entries=8,
        )
        try:
            service = compose_offline_federation_service(
                runtime,
                validate_record=lambda value: value,
                record_identity_text=lambda value: "r1_" + "A" * 43,
                validate_exchange_request=federation_v1.validate_exchange_request,
                make_transport_envelope=federation_v1.make_transport_envelope,
                validate_transport_envelope=federation_v1.validate_transport_envelope,
                validate_exchange_result=federation_v1.validate_exchange_result,
                operation_profiles=(
                    FederationOperationProfile(
                        federation_v1.OP_SYNC,
                        federation_v1.MSG_SYNC_REQUEST,
                        federation_v1.MSG_SYNC_RESULT,
                    ),
                ),
            )

            original = _request()
            expected_original = _request()
            prepared = service.prepare(original)

            # Reproduce the exact historical alias/TOCTOU shape: the caller still
            # owns the request object and mutates top-level and nested values after
            # M24 preparation but before M26 serialization/network use.
            original["source"] = "https://attacker.example/federation"
            original["operation"] = federation_v1.OP_SNAPSHOT
            original["page_size"] = 1
            original["cursor"] = b"attacker-cursor"
            original["scope"]["record_types"].clear()
            original["required_capabilities"].clear()

            policy = FederationEgressPolicy(
                policy_id="https://open-trust-layer.github.io/marketplace/policy/egress-v1",
                policy_version=1,
                allowed_hosts=("federation.example.com",),
            )
            authorization = authorize_federation_endpoint(
                endpoint=ENDPOINT,
                allowed_operations=(federation_v1.OP_SYNC,),
                authorization_id="m30-regression-auth",
                issued_at_epoch=1_000,
                expires_at_epoch=1_120,
                policy=policy,
            )
            connection = _FakeConnection(_http_response())
            connector_calls: list[dict[str, object]] = []

            def connector(**kwargs):
                connector_calls.append(dict(kwargs))
                return connection

            transport = AuthorizedHttpsFederationTransport(
                policy=policy,
                encode_envelope_json=encode_transport_envelope_json,
                decode_envelope_json=lambda body: (
                    "OLP-TRANSPORT",
                    1,
                    federation_v1.MSG_SYNC_RESULT,
                    {"ok": True},
                ),
                resolver=lambda host, port: ("1.1.1.1",),
                connector=connector,
                wall_clock=lambda: 1_050.0,
                monotonic_clock=lambda: 10.0,
            )
            result = transport.exchange(
                prepared,
                endpoint=ENDPOINT,
                authorization=authorization,
            )

            self.assertEqual(result.http_status, 200)
            self.assertEqual(len(connector_calls), 1)
            self.assertTrue(connection.closed)

            request_head, transmitted_body = bytes(connection.sent).split(b"\r\n\r\n", 1)
            self.assertTrue(request_head.startswith(b"POST /federation/v1 HTTP/1.1\r\n"))

            expected_envelope = federation_v1.make_transport_envelope(
                federation_v1.MSG_SYNC_REQUEST,
                expected_original,
            )
            expected_body = encode_transport_envelope_json(expected_envelope)
            attacker_envelope = federation_v1.make_transport_envelope(
                federation_v1.MSG_SYNC_REQUEST,
                original,
            )
            attacker_body = encode_transport_envelope_json(attacker_envelope)

            self.assertEqual(transmitted_body, expected_body)
            self.assertNotEqual(transmitted_body, attacker_body)
            self.assertEqual(prepared.binding.operation, federation_v1.OP_SYNC)
            self.assertEqual(prepared.envelope[3], expected_original)
        finally:
            runtime.close()


if __name__ == "__main__":
    unittest.main()
