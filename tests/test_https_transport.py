from __future__ import annotations

import threading
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from marketplace.runtime.federation import FederationRequestBinding, PreparedFederationExchange
from marketplace.runtime.https_transport import (
    AuthorizedHttpsFederationTransport,
    FederationHttpsTransportError,
    HttpsFederationTransportLimits,
    _default_secure_connector,
)
from marketplace.runtime.network_policy import FederationEgressPolicy, authorize_federation_endpoint


OPERATION = "https://open-trust-layer.github.io/marketplace/semantics/v1/federation/operation/snapshot-v1"
MESSAGE_TYPE = "https://open-trust-layer.github.io/marketplace/semantics/v1/federation/message/snapshot-request-v1"
ENDPOINT = "https://federation.example.com/federation/v1"


class FakeConnection:
    def __init__(self, response: bytes, *, block_recv: threading.Event | None = None, entered_recv: threading.Event | None = None):
        self.response = bytearray(response)
        self.sent = bytearray()
        self.timeouts: list[float] = []
        self.closed = False
        self.block_recv = block_recv
        self.entered_recv = entered_recv

    def sendall(self, data: bytes) -> None:
        self.sent.extend(data)

    def recv(self, size: int) -> bytes:
        if self.entered_recv is not None:
            self.entered_recv.set()
        if self.block_recv is not None:
            self.block_recv.wait(timeout=2)
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
    def __init__(self, connection: FakeConnection | None = None, error: Exception | None = None):
        self.connection = connection
        self.error = error
        self.calls: list[dict[str, object]] = []

    def __call__(self, **kwargs):
        self.calls.append(dict(kwargs))
        if self.error is not None:
            raise self.error
        assert self.connection is not None
        return self.connection


def response(body: bytes = b'{"ok":true}', *, status: int = 200, headers: tuple[tuple[str, str], ...] = ()) -> bytes:
    base = [
        f"HTTP/1.1 {status} {'OK' if status == 200 else 'Other'}",
        "Content-Type: application/json",
        f"Content-Length: {len(body)}",
    ]
    base.extend(f"{name}: {value}" for name, value in headers)
    return ("\r\n".join(base) + "\r\n\r\n").encode("ascii") + body


class HttpsFederationTransportTests(unittest.TestCase):
    def policy(self) -> FederationEgressPolicy:
        return FederationEgressPolicy(
            policy_id="https://open-trust-layer.github.io/marketplace/policy/egress-v1",
            policy_version=1,
            allowed_hosts=("federation.example.com",),
        )

    def authorization(self, **changes):
        authorization = authorize_federation_endpoint(
            endpoint=ENDPOINT,
            allowed_operations=(OPERATION,),
            authorization_id="m26-egress-auth",
            issued_at_epoch=1_000,
            expires_at_epoch=1_120,
            policy=self.policy(),
        )
        return replace(authorization, **changes) if changes else authorization

    def prepared(self, *, transmitted: bool = False) -> PreparedFederationExchange:
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
            transmitted=transmitted,
        )

    def transport(self, connector: FakeConnector, *, resolver=None, limits=None, wall_clock=None, monotonic_clock=None):
        return AuthorizedHttpsFederationTransport(
            policy=self.policy(),
            encode_envelope_json=lambda envelope: b'{"olp":1,"payload":{"$olp":"map","v":[]},"type":"x"}',
            decode_envelope_json=lambda body: ("decoded", body),
            limits=limits,
            resolver=resolver or (lambda host, port: ("1.1.1.1", "2606:4700:4700::1111")),
            connector=connector,
            wall_clock=wall_clock or (lambda: 1_050.0),
            monotonic_clock=monotonic_clock or (lambda: 10.0),
        )

    def assert_transport_error(self, code: str, fn, *args, **kwargs):
        with self.assertRaises(FederationHttpsTransportError) as caught:
            fn(*args, **kwargs)
        self.assertEqual(caught.exception.code, code)

    def test_one_authorized_exchange_connects_numeric_address_with_authorized_tls_hostname(self):
        body = b'{"olp":1}'
        connection = FakeConnection(response(body))
        connector = FakeConnector(connection)
        transport = AuthorizedHttpsFederationTransport(
            policy=self.policy(),
            encode_envelope_json=lambda envelope: b'{"olp":1}',
            decode_envelope_json=lambda raw: ("decoded", raw),
            resolver=lambda host, port: ("2606:4700:4700::1111", "1.1.1.1"),
            connector=connector,
            wall_clock=lambda: 1_050.0,
            monotonic_clock=lambda: 10.0,
        )
        result = transport.exchange(self.prepared(), endpoint=ENDPOINT, authorization=self.authorization())
        self.assertEqual(result.http_status, 200)
        self.assertEqual(result.selected_address, "1.1.1.1")
        self.assertEqual(result.tls_server_hostname, "federation.example.com")
        self.assertEqual(result.response_envelope, ("decoded", body))
        self.assertEqual(result.connection_attempts, 1)
        self.assertEqual(result.redirects_followed, 0)
        self.assertEqual(result.retries_performed, 0)
        self.assertFalse(result.proxy_used)
        self.assertFalse(result.credentials_used)
        self.assertFalse(result.establishes_peer_trust)
        self.assertFalse(result.establishes_marketplace_truth)
        self.assertFalse(result.establishes_agreement)
        self.assertFalse(result.establishes_authorization)
        self.assertEqual(len(connector.calls), 1)
        self.assertEqual(connector.calls[0]["address"], "1.1.1.1")
        self.assertEqual(connector.calls[0]["server_hostname"], "federation.example.com")
        self.assertTrue(connection.closed)

    def test_request_is_exact_post_without_credentials_proxy_cookie_or_redirect_surface(self):
        connection = FakeConnection(response())
        connector = FakeConnector(connection)
        self.transport(connector).exchange(self.prepared(), endpoint=ENDPOINT, authorization=self.authorization())
        head, body = bytes(connection.sent).split(b"\r\n\r\n", 1)
        text = head.decode("ascii")
        self.assertTrue(text.startswith("POST /federation/v1 HTTP/1.1\r\n"))
        self.assertIn("Host: federation.example.com\r\n", text + "\r\n")
        self.assertIn("Content-Type: application/json", text)
        self.assertIn("Accept: application/json", text)
        self.assertIn("Connection: close", text)
        self.assertIn(f"Content-Length: {len(body)}", text)
        for forbidden in ("Authorization:", "Cookie:", "Proxy-Authorization:", "Referer:", "Location:"):
            self.assertNotIn(forbidden, text)

    def test_expired_authorization_blocks_before_fresh_resolver_or_connector(self):
        calls: list[str] = []
        connector = FakeConnector(FakeConnection(response()))
        transport = self.transport(
            connector,
            resolver=lambda host, port: calls.append("resolver") or ("1.1.1.1",),
            wall_clock=lambda: 1_120.0,
        )
        with self.assertRaises(Exception) as caught:
            transport.exchange(self.prepared(), endpoint=ENDPOINT, authorization=self.authorization())
        self.assertEqual(getattr(caught.exception, "code", None), "AUTHORIZATION_EXPIRED")
        self.assertEqual(calls, [])
        self.assertEqual(connector.calls, [])

    def test_any_unsafe_fresh_dns_result_blocks_connection(self):
        connector = FakeConnector(FakeConnection(response()))
        transport = self.transport(
            connector,
            resolver=lambda host, port: ("1.1.1.1", "127.0.0.1"),
        )
        self.assert_transport_error(
            "UNSAFE_RESOLUTION",
            transport.exchange,
            self.prepared(),
            endpoint=ENDPOINT,
            authorization=self.authorization(),
        )
        self.assertEqual(connector.calls, [])

    def test_previously_transmitted_prepared_exchange_is_rejected_without_network(self):
        connector = FakeConnector(FakeConnection(response()))
        transport = self.transport(connector)
        self.assert_transport_error(
            "PREPARED_EXCHANGE_STATE",
            transport.exchange,
            self.prepared(transmitted=True),
            endpoint=ENDPOINT,
            authorization=self.authorization(),
        )
        self.assertEqual(connector.calls, [])

    def test_connector_failure_is_one_attempt_and_never_retried(self):
        connector = FakeConnector(error=OSError("network down"))
        transport = self.transport(connector)
        self.assert_transport_error(
            "TLS_CONNECTION_FAILED",
            transport.exchange,
            self.prepared(),
            endpoint=ENDPOINT,
            authorization=self.authorization(),
        )
        self.assertEqual(len(connector.calls), 1)

    def test_response_rejects_non_200_content_type_transfer_encoding_compression_and_missing_length(self):
        cases = (
            ("HTTP_STATUS_REJECTED", response(status=302)),
            (
                "HTTP_CONTENT_TYPE_REJECTED",
                b"HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\nContent-Length: 2\r\n\r\n{}",
            ),
            (
                "HTTP_TRANSFER_ENCODING_REJECTED",
                response(headers=(("Transfer-Encoding", "chunked"),)),
            ),
            (
                "HTTP_CONTENT_ENCODING_REJECTED",
                response(headers=(("Content-Encoding", "gzip"),)),
            ),
            (
                "HTTP_CONTENT_LENGTH_REQUIRED",
                b"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n\r\n{}",
            ),
        )
        for code, raw in cases:
            with self.subTest(code=code):
                connector = FakeConnector(FakeConnection(raw))
                transport = self.transport(connector)
                self.assert_transport_error(
                    code,
                    transport.exchange,
                    self.prepared(),
                    endpoint=ENDPOINT,
                    authorization=self.authorization(),
                )

    def test_response_limits_and_declared_body_shape_fail_closed(self):
        limits = HttpsFederationTransportLimits(max_response_bytes=8, max_header_bytes=1024)
        raw = b"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: 9\r\n\r\n123456789"
        transport = self.transport(FakeConnector(FakeConnection(raw)), limits=limits)
        self.assert_transport_error(
            "HTTP_BODY_LIMIT",
            transport.exchange,
            self.prepared(),
            endpoint=ENDPOINT,
            authorization=self.authorization(),
        )

        overflow = b"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: 2\r\n\r\n{}extra"
        transport = self.transport(FakeConnector(FakeConnection(overflow)))
        self.assert_transport_error(
            "HTTP_BODY_OVERFLOW",
            transport.exchange,
            self.prepared(),
            endpoint=ENDPOINT,
            authorization=self.authorization(),
        )

    def test_request_body_limit_is_checked_before_dns(self):
        calls: list[str] = []
        connector = FakeConnector(FakeConnection(response()))
        transport = AuthorizedHttpsFederationTransport(
            policy=self.policy(),
            encode_envelope_json=lambda envelope: b"x" * 9,
            decode_envelope_json=lambda body: body,
            limits=HttpsFederationTransportLimits(max_request_bytes=8),
            resolver=lambda host, port: calls.append("resolver") or ("1.1.1.1",),
            connector=connector,
            wall_clock=lambda: 1_050.0,
            monotonic_clock=lambda: 10.0,
        )
        self.assert_transport_error(
            "REQUEST_BODY_LIMIT",
            transport.exchange,
            self.prepared(),
            endpoint=ENDPOINT,
            authorization=self.authorization(),
        )
        self.assertEqual(calls, [])
        self.assertEqual(connector.calls, [])

    def test_total_timeout_can_expire_after_resolution_before_connection(self):
        values = iter((0.0, 20.0))
        connector = FakeConnector(FakeConnection(response()))
        transport = self.transport(
            connector,
            limits=HttpsFederationTransportLimits(total_timeout_seconds=15.0),
            monotonic_clock=lambda: next(values),
        )
        self.assert_transport_error(
            "TOTAL_TIMEOUT",
            transport.exchange,
            self.prepared(),
            endpoint=ENDPOINT,
            authorization=self.authorization(),
        )
        self.assertEqual(connector.calls, [])

    def test_concurrency_limit_fails_nonblocking_and_does_not_start_second_connection(self):
        release = threading.Event()
        entered = threading.Event()
        first_connection = FakeConnection(response(), block_recv=release, entered_recv=entered)
        first_connector = FakeConnector(first_connection)
        transport = self.transport(
            first_connector,
            limits=HttpsFederationTransportLimits(max_concurrent_exchanges=1),
        )
        errors: list[BaseException] = []

        def run_first():
            try:
                transport.exchange(self.prepared(), endpoint=ENDPOINT, authorization=self.authorization())
            except BaseException as exc:
                errors.append(exc)

        thread = threading.Thread(target=run_first)
        thread.start()
        self.assertTrue(entered.wait(timeout=2))
        self.assert_transport_error(
            "CONCURRENCY_LIMIT",
            transport.exchange,
            self.prepared(),
            endpoint=ENDPOINT,
            authorization=self.authorization(),
        )
        self.assertEqual(len(first_connector.calls), 1)
        release.set()
        thread.join(timeout=2)
        self.assertFalse(thread.is_alive())
        self.assertEqual(errors, [])

    @patch("marketplace.runtime.https_transport.ssl.create_default_context")
    @patch("marketplace.runtime.https_transport.socket.socket")
    def test_default_connector_pins_numeric_address_and_verifies_authorized_hostname(self, socket_factory, context_factory):
        class RawSocket:
            def __init__(self):
                self.timeouts = []
                self.destinations = []
                self.closed = False

            def settimeout(self, value):
                self.timeouts.append(value)

            def connect(self, destination):
                self.destinations.append(destination)

            def close(self):
                self.closed = True

        class TlsSocket:
            def selected_alpn_protocol(self):
                return "http/1.1"

            def close(self):
                pass

        class Context:
            def __init__(self):
                self.minimum_version = None
                self.check_hostname = None
                self.verify_mode = None
                self.alpn = None
                self.wrap_calls = []

            def set_alpn_protocols(self, values):
                self.alpn = values

            def wrap_socket(self, raw, *, server_hostname):
                self.wrap_calls.append((raw, server_hostname))
                return TlsSocket()

        raw = RawSocket()
        context = Context()
        socket_factory.return_value = raw
        context_factory.return_value = context
        tls = _default_secure_connector(
            address="1.1.1.1",
            port=443,
            server_hostname="federation.example.com",
            connect_timeout_seconds=3.0,
        )
        self.assertIsInstance(tls, TlsSocket)
        socket_factory.assert_called_once()
        self.assertEqual(raw.destinations, [("1.1.1.1", 443)])
        self.assertEqual(context.wrap_calls, [(raw, "federation.example.com")])
        self.assertEqual(context.minimum_version, __import__("ssl").TLSVersion.TLSv1_2)
        self.assertTrue(context.check_hostname)
        self.assertEqual(context.verify_mode, __import__("ssl").CERT_REQUIRED)
        self.assertEqual(context.alpn, ["http/1.1"])

    def test_module_avoids_environment_aware_http_proxy_credential_and_process_clients(self):
        source = (Path(__file__).resolve().parents[1] / "src/marketplace/runtime/https_transport.py").read_text(encoding="utf-8-sig")
        for forbidden in (
            "urllib.request",
            "http.client",
            "requests",
            "httpx",
            "aiohttp",
            "netrc",
            "subprocess",
            "os.environ",
            "getenv(",
            "Authorization:",
            "Proxy-Authorization:",
            "Cookie:",
        ):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
