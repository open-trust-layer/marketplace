from __future__ import annotations

from dataclasses import FrozenInstanceError
from urllib.parse import urlencode
import unittest

from marketplace.reference.local_ui_loopback_v1 import (
    LOCAL_UI_LOOPBACK_EXECUTION_OPT_IN,
    LOCAL_UI_LOOPBACK_HOST,
    MAX_LOCAL_UI_LOOPBACK_PORT,
    MIN_LOCAL_UI_LOOPBACK_PORT,
    LocalUiLoopbackError,
    LocalUiLoopbackResult,
    plan_local_ui_loopback_once,
    serve_local_ui_loopback_once,
)


FIELDS = {
    "seller_principal": "did:example:seller",
    "subject_uri": "urn:example:product:bicycle-1",
    "title": "City bicycle",
    "description": "One carefully maintained bicycle.",
    "consideration": "125.00",
    "currency_code": "EUR",
    "quantity": "1",
    "unit_uri": "https://open-trust-layer.github.io/marketplace/semantics/v1/profile/product-listing-v1/unit/item",
    "latitude": "52.520000",
    "longitude": "13.405000",
    "buyer_principal": "did:example:buyer",
    "buyer_action_uri": "https://example.test/actions/buy",
}


class FakeConnection:
    def __init__(self, chunks: list[bytes], *, send_limit: int | None = None, close_error: bool = False) -> None:
        self._chunks = list(chunks)
        self._send_limit = send_limit
        self._close_error = close_error
        self.recv_calls = 0
        self.send_calls = 0
        self.closed = 0
        self.timeout_values: list[float] = []
        self.sent = bytearray()

    def settimeout(self, value: float) -> None:
        self.timeout_values.append(value)

    def recv(self, limit: int) -> bytes:
        self.recv_calls += 1
        if not self._chunks:
            return b""
        chunk = self._chunks.pop(0)
        if len(chunk) <= limit:
            return chunk
        self._chunks.insert(0, chunk[limit:])
        return chunk[:limit]

    def send(self, data: bytes) -> int:
        self.send_calls += 1
        count = len(data) if self._send_limit is None else min(len(data), self._send_limit)
        self.sent.extend(data[:count])
        return count

    def close(self) -> None:
        self.closed += 1
        if self._close_error:
            raise RuntimeError("HOSTILE-CLOSE-TEXT")


class FakeListener:
    def __init__(self, connection: FakeConnection, *, peer=("127.0.0.1", 49152), close_error: bool = False) -> None:
        self.connection = connection
        self.peer = peer
        self._close_error = close_error
        self.bound = None
        self.backlogs: list[int] = []
        self.accept_calls = 0
        self.closed = 0
        self.timeout_values: list[float] = []

    def settimeout(self, value: float) -> None:
        self.timeout_values.append(value)

    def bind(self, endpoint) -> None:
        self.bound = endpoint

    def listen(self, backlog: int) -> None:
        self.backlogs.append(backlog)

    def accept(self):
        self.accept_calls += 1
        return self.connection, self.peer

    def close(self) -> None:
        self.closed += 1
        if self._close_error:
            raise RuntimeError("HOSTILE-LISTENER-CLOSE-TEXT")


class FakeConstructor:
    def __init__(self, listener: FakeListener) -> None:
        self.listener = listener
        self.calls: list[tuple[object, object, object]] = []

    def __call__(self, family, kind, protocol):
        self.calls.append((family, kind, protocol))
        return self.listener


def get_wire(port: int) -> bytes:
    return (
        f"GET / HTTP/1.1\r\nHost: 127.0.0.1:{port}\r\n"
        "User-Agent: deterministic-test\r\nConnection: keep-alive\r\n\r\n"
    ).encode("ascii")


def post_wire(port: int) -> bytes:
    body = urlencode(FIELDS).encode("ascii")
    return (
        f"POST /local-buy-sell HTTP/1.1\r\nHost: 127.0.0.1:{port}\r\n"
        "Content-Type: application/x-www-form-urlencoded\r\n"
        f"Content-Length: {len(body)}\r\nConnection: keep-alive\r\n\r\n"
    ).encode("ascii") + body


class M78LocalUiLoopbackTransportTests(unittest.TestCase):
    def test_dry_run_plan_is_exact_loopback_and_authority_negative(self):
        plan = plan_local_ui_loopback_once(8767)
        self.assertEqual(plan.host, LOCAL_UI_LOOPBACK_HOST)
        self.assertEqual(plan.port, 8767)
        self.assertTrue(plan.one_shot)
        self.assertFalse(plan.network_invoked)
        self.assertFalse(plan.external_authorization_established)
        self.assertFalse(plan.deployment_authorized)

    def test_missing_opt_in_and_invalid_port_fail_before_constructor(self):
        connection = FakeConnection([get_wire(8767)])
        constructor = FakeConstructor(FakeListener(connection))
        cases = (
            (8767, ""),
            (8767, "EXECUTE_SOMETHING_ELSE"),
            (MIN_LOCAL_UI_LOOPBACK_PORT - 1, LOCAL_UI_LOOPBACK_EXECUTION_OPT_IN),
            (MAX_LOCAL_UI_LOOPBACK_PORT + 1, LOCAL_UI_LOOPBACK_EXECUTION_OPT_IN),
            (True, LOCAL_UI_LOOPBACK_EXECUTION_OPT_IN),
        )
        for port, token in cases:
            with self.subTest(port=port, token=token):
                with self.assertRaises(LocalUiLoopbackError):
                    serve_local_ui_loopback_once(
                        port=port,  # type: ignore[arg-type]
                        execution_opt_in=token,
                        socket_constructor=constructor,
                    )
        self.assertEqual(constructor.calls, [])

    def test_get_binds_exact_loopback_accepts_once_and_closes(self):
        port = 8767
        connection = FakeConnection([get_wire(port)], send_limit=137)
        listener = FakeListener(connection)
        constructor = FakeConstructor(listener)

        result = serve_local_ui_loopback_once(
            port=port,
            execution_opt_in=LOCAL_UI_LOOPBACK_EXECUTION_OPT_IN,
            socket_constructor=constructor,
        )

        self.assertIs(type(result), LocalUiLoopbackResult)
        self.assertEqual(listener.bound, ("127.0.0.1", port))
        self.assertEqual(listener.backlogs, [1])
        self.assertEqual(listener.accept_calls, 1)
        self.assertEqual(listener.closed, 1)
        self.assertEqual(connection.closed, 1)
        self.assertEqual(result.request_method, "GET")
        self.assertEqual(result.request_target, "/")
        self.assertEqual(result.status_code, 200)
        self.assertTrue(result.network_invoked)
        self.assertFalse(result.external_authorization_established)
        self.assertFalse(result.deployment_authorized)
        self.assertIn(b"HTTP/1.1 200 OK\r\n", connection.sent)
        self.assertIn(b"Connection: close\r\n", connection.sent)
        self.assertIn(b"Marketplace local buy/sell", connection.sent)

    def test_post_delegates_to_m77_and_does_not_return_human_content(self):
        port = 8768
        wire = post_wire(port)
        split = [wire[:81], wire[81:211], wire[211:]]
        connection = FakeConnection(split, send_limit=251)
        listener = FakeListener(connection)

        result = serve_local_ui_loopback_once(
            port=port,
            execution_opt_in=LOCAL_UI_LOOPBACK_EXECUTION_OPT_IN,
            socket_constructor=FakeConstructor(listener),
        )

        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.request_method, "POST")
        self.assertEqual(result.request_target, "/local-buy-sell")
        self.assertIn(b"COMPATIBLE_UNDER_METHOD", connection.sent)
        self.assertIn(b"protocol_truth=false", connection.sent)
        self.assertIn(b"creates_agreement=false", connection.sent)
        self.assertNotIn(FIELDS["description"].encode(), repr(result).encode())
        self.assertNotIn(FIELDS["buyer_principal"].encode(), repr(result).encode())

    def test_host_mismatch_sensitive_headers_and_pipelining_fail_closed(self):
        port = 8769
        cases = (
            get_wire(port).replace(f"127.0.0.1:{port}".encode(), b"localhost:8769"),
            get_wire(port).replace(b"User-Agent: deterministic-test\r\n", b"Cookie: secret=value\r\n"),
            get_wire(port) + get_wire(port),
        )
        for wire in cases:
            with self.subTest(wire=wire[:80]):
                connection = FakeConnection([wire])
                listener = FakeListener(connection)
                with self.assertRaises(LocalUiLoopbackError) as raised:
                    serve_local_ui_loopback_once(
                        port=port,
                        execution_opt_in=LOCAL_UI_LOOPBACK_EXECUTION_OPT_IN,
                        socket_constructor=FakeConstructor(listener),
                    )
                self.assertIn(raised.exception.code, {"REQUEST_INVALID", "REQUEST_TRAILING_BYTES"})
                self.assertNotIn("secret=value", str(raised.exception))
                self.assertEqual(connection.closed, 1)
                self.assertEqual(listener.closed, 1)

    def test_non_loopback_peer_is_rejected_before_request_read(self):
        connection = FakeConnection([get_wire(8770)])
        listener = FakeListener(connection, peer=("192.0.2.10", 44321))
        with self.assertRaises(LocalUiLoopbackError) as raised:
            serve_local_ui_loopback_once(
                port=8770,
                execution_opt_in=LOCAL_UI_LOOPBACK_EXECUTION_OPT_IN,
                socket_constructor=FakeConstructor(listener),
            )
        self.assertEqual(raised.exception.code, "PEER_NOT_LOOPBACK")
        self.assertEqual(connection.recv_calls, 0)
        self.assertEqual(connection.closed, 1)
        self.assertEqual(listener.closed, 1)

    def test_cleanup_failure_is_stable_and_non_reflective(self):
        connection = FakeConnection([get_wire(8771)], close_error=True)
        listener = FakeListener(connection, close_error=True)
        with self.assertRaises(LocalUiLoopbackError) as raised:
            serve_local_ui_loopback_once(
                port=8771,
                execution_opt_in=LOCAL_UI_LOOPBACK_EXECUTION_OPT_IN,
                socket_constructor=FakeConstructor(listener),
            )
        self.assertEqual(raised.exception.code, "CLEANUP_UNCERTAIN")
        self.assertNotIn("HOSTILE", str(raised.exception))
        self.assertEqual(connection.closed, 1)
        self.assertEqual(listener.closed, 1)

    def test_result_is_frozen_and_retains_metadata_only(self):
        connection = FakeConnection([get_wire(8772)])
        result = serve_local_ui_loopback_once(
            port=8772,
            execution_opt_in=LOCAL_UI_LOOPBACK_EXECUTION_OPT_IN,
            socket_constructor=FakeConstructor(FakeListener(connection)),
        )
        with self.assertRaises(FrozenInstanceError):
            result.status_code = 500  # type: ignore[misc]
        self.assertFalse(hasattr(result, "request_bytes"))
        self.assertFalse(hasattr(result, "response_bytes"))
        self.assertFalse(hasattr(result, "body"))
        self.assertFalse(hasattr(result, "transcript"))


if __name__ == "__main__":
    unittest.main()
