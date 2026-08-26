from __future__ import annotations

import unittest
from unittest.mock import patch

from marketplace.runtime.federation import FederationRequestBinding, PreparedFederationExchange
from marketplace.runtime.https_transport import (
    AuthorizedHttpsFederationTransport,
    FederationHttpsTransportError,
    _default_secure_connector,
)
from marketplace.runtime.network_policy import FederationEgressPolicy, authorize_federation_endpoint

OPERATION = "https://open-trust-layer.github.io/marketplace/semantics/v1/federation/operation/snapshot-v1"
MESSAGE_TYPE = "https://open-trust-layer.github.io/marketplace/semantics/v1/federation/message/snapshot-request-v1"
ENDPOINT = "https://federation.example.com/federation/v1"


class FakeConnection:
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
        pass

    def close(self) -> None:
        self.closed = True


class RecordingConnector:
    def __init__(self, response: bytes):
        self.response = response
        self.calls: list[dict[str, object]] = []

    def __call__(self, **kwargs):
        self.calls.append(dict(kwargs))
        return FakeConnection(self.response)


def response(body: bytes = b'{"olp":1}') -> bytes:
    return (
        b"HTTP/1.1 200 OK\r\n"
        b"Content-Type: application/json\r\n"
        + f"Content-Length: {len(body)}\r\n".encode("ascii")
        + b"\r\n"
        + body
    )


class HttpsFederationTransportHardeningTests(unittest.TestCase):
    def policy(self) -> FederationEgressPolicy:
        return FederationEgressPolicy(
            policy_id="https://open-trust-layer.github.io/marketplace/policy/egress-v1",
            policy_version=1,
            allowed_hosts=("federation.example.com",),
        )

    def authorization(self):
        return authorize_federation_endpoint(
            endpoint=ENDPOINT,
            allowed_operations=(OPERATION,),
            authorization_id="m26-hardening-auth",
            issued_at_epoch=1_000,
            expires_at_epoch=1_120,
            policy=self.policy(),
        )

    def prepared(self) -> PreparedFederationExchange:
        return PreparedFederationExchange(
            binding=FederationRequestBinding(
                source="https://source.example",
                operation=OPERATION,
                scope_fingerprint="scope",
                required_capabilities=("https://example.com/capability",),
                page_size=10,
                expected_result_message_type="https://example.com/result",
            ),
            envelope=("OLP-TRANSPORT", 1, MESSAGE_TYPE, {"version": 1}),
            transmitted=False,
        )

    def make_transport(self, *, connector, wall_clock, decoder=None):
        return AuthorizedHttpsFederationTransport(
            policy=self.policy(),
            encode_envelope_json=lambda envelope: b'{"olp":1}',
            decode_envelope_json=decoder or (
                lambda body: ("OLP-TRANSPORT", 1, "https://example.com/result", {})
            ),
            resolver=lambda host, port: ("1.1.1.1",),
            connector=connector,
            wall_clock=wall_clock,
            monotonic_clock=lambda: 10.0,
        )

    def test_authorization_is_revalidated_after_dns_immediately_before_connect(self):
        clock_values = iter((1_050.0, 1_120.0))
        connector = RecordingConnector(response())
        transport = self.make_transport(
            connector=connector,
            wall_clock=lambda: next(clock_values),
        )
        with self.assertRaises(Exception) as caught:
            transport.exchange(
                self.prepared(),
                endpoint=ENDPOINT,
                authorization=self.authorization(),
            )
        self.assertEqual(getattr(caught.exception, "code", None), "AUTHORIZATION_EXPIRED")
        self.assertEqual(connector.calls, [])

    def test_hostile_decoder_cannot_return_non_envelope_as_success(self):
        connector = RecordingConnector(response())
        transport = self.make_transport(
            connector=connector,
            wall_clock=lambda: 1_050.0,
            decoder=lambda body: {"not": "an envelope"},
        )
        with self.assertRaises(FederationHttpsTransportError) as caught:
            transport.exchange(
                self.prepared(),
                endpoint=ENDPOINT,
                authorization=self.authorization(),
            )
        self.assertEqual(caught.exception.code, "INVALID_RESPONSE_ENVELOPE")

    def test_ascii_control_byte_in_response_header_value_is_rejected(self):
        body = b'{"olp":1}'
        raw = (
            b"HTTP/1.1 200 OK\r\n"
            b"Content-Type: application/json\r\n"
            + f"Content-Length: {len(body)}\r\n".encode("ascii")
            + b"X-Test: ok\x00bad\r\n"
            + b"\r\n"
            + body
        )
        connector = RecordingConnector(raw)
        transport = self.make_transport(connector=connector, wall_clock=lambda: 1_050.0)
        with self.assertRaises(FederationHttpsTransportError) as caught:
            transport.exchange(
                self.prepared(),
                endpoint=ENDPOINT,
                authorization=self.authorization(),
            )
        self.assertEqual(caught.exception.code, "INVALID_HTTP_HEADERS")

    @patch("marketplace.runtime.https_transport.socket.socket", side_effect=OSError("unavailable"))
    def test_default_connector_maps_socket_creation_failure_to_stable_transport_error(self, socket_factory):
        with self.assertRaises(FederationHttpsTransportError) as caught:
            _default_secure_connector(
                address="1.1.1.1",
                port=443,
                server_hostname="federation.example.com",
                connect_timeout_seconds=1.0,
            )
        self.assertEqual(caught.exception.code, "TLS_CONNECTION_FAILED")
        socket_factory.assert_called_once()


if __name__ == "__main__":
    unittest.main()
