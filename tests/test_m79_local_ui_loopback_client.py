from __future__ import annotations

from dataclasses import FrozenInstanceError
from urllib.parse import urlencode
import unittest

from marketplace.reference.local_ui_http_v1 import LocalUiHttpRequest
from marketplace.reference.local_ui_loopback_client_v1 import (
    LOCAL_UI_LOOPBACK_CLIENT_EXECUTION_OPT_IN,
    LOCAL_UI_LOOPBACK_CLIENT_HOST,
    MAX_LOCAL_UI_LOOPBACK_CLIENT_PORT,
    MIN_LOCAL_UI_LOOPBACK_CLIENT_PORT,
    LocalUiLoopbackClientError,
    LocalUiLoopbackClientResult,
    plan_local_ui_loopback_client_once,
    run_local_ui_loopback_client_once,
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


def response_wire(
    body: bytes = b"<html>ok</html>",
    *,
    status: str = "200 OK",
    extra_headers: tuple[tuple[str, str], ...] = (),
) -> bytes:
    headers = (
        ("Content-Type", "text/html; charset=utf-8"),
        ("Content-Length", str(len(body))),
        ("Cache-Control", "no-store"),
        ("X-Content-Type-Options", "nosniff"),
        ("Referrer-Policy", "no-referrer"),
        (
            "Content-Security-Policy",
            "default-src 'none'; style-src 'unsafe-inline'; form-action 'self'; base-uri 'none'; frame-ancestors 'none'",
        ),
        ("Connection", "close"),
    ) + extra_headers
    head = f"HTTP/1.1 {status}\r\n".encode("ascii")
    head += b"".join(f"{name}: {value}\r\n".encode("ascii") for name, value in headers)
    return head + b"\r\n" + body


class FakeSocket:
    def __init__(
        self,
        chunks: list[bytes],
        *,
        send_limit: int | None = None,
        connect_error: bool = False,
        send_error: bool = False,
        recv_error: bool = False,
        close_error: bool = False,
    ) -> None:
        self._chunks = list(chunks)
        self._send_limit = send_limit
        self._connect_error = connect_error
        self._send_error = send_error
        self._recv_error = recv_error
        self._close_error = close_error
        self.connected = None
        self.timeout_values: list[float] = []
        self.send_calls = 0
        self.recv_calls = 0
        self.closed = 0
        self.sent = bytearray()

    def settimeout(self, value: float) -> None:
        self.timeout_values.append(value)

    def connect(self, endpoint) -> None:
        if self._connect_error:
            raise RuntimeError("HOSTILE-CONNECT-TEXT")
        self.connected = endpoint

    def send(self, data: bytes) -> int:
        self.send_calls += 1
        if self._send_error:
            raise RuntimeError("HOSTILE-SEND-TEXT")
        count = len(data) if self._send_limit is None else min(self._send_limit, len(data))
        self.sent.extend(data[:count])
        return count

    def recv(self, limit: int) -> bytes:
        self.recv_calls += 1
        if self._recv_error:
            raise RuntimeError("HOSTILE-RECV-TEXT")
        if not self._chunks:
            return b""
        chunk = self._chunks.pop(0)
        if len(chunk) <= limit:
            return chunk
        self._chunks.insert(0, chunk[limit:])
        return chunk[:limit]

    def close(self) -> None:
        self.closed += 1
        if self._close_error:
            raise RuntimeError("HOSTILE-CLOSE-TEXT")


class FakeConstructor:
    def __init__(self, sock: FakeSocket) -> None:
        self.sock = sock
        self.calls: list[tuple[object, object, object]] = []

    def __call__(self, family, kind, protocol):
        self.calls.append((family, kind, protocol))
        return self.sock


def get_request() -> LocalUiHttpRequest:
    return LocalUiHttpRequest("GET", "/", None, b"")


def post_request() -> LocalUiHttpRequest:
    body = urlencode(FIELDS).encode("ascii")
    return LocalUiHttpRequest("POST", "/local-buy-sell", "application/x-www-form-urlencoded", body)


class M79LocalUiLoopbackClientTests(unittest.TestCase):
    def test_dry_run_plan_is_exact_loopback_and_authority_negative(self):
        plan = plan_local_ui_loopback_client_once(8780, get_request())
        self.assertEqual(plan.host, LOCAL_UI_LOOPBACK_CLIENT_HOST)
        self.assertEqual(plan.port, 8780)
        self.assertEqual(plan.request_method, "GET")
        self.assertEqual(plan.request_target, "/")
        self.assertTrue(plan.one_shot)
        self.assertFalse(plan.network_invoked)
        self.assertFalse(plan.external_authorization_established)
        self.assertFalse(plan.deployment_authorized)

    def test_invalid_authority_inputs_fail_before_constructor(self):
        constructor = FakeConstructor(FakeSocket([response_wire()]))
        cases = (
            (8780, get_request(), ""),
            (8780, get_request(), "EXECUTE_SOMETHING_ELSE"),
            (MIN_LOCAL_UI_LOOPBACK_CLIENT_PORT - 1, get_request(), LOCAL_UI_LOOPBACK_CLIENT_EXECUTION_OPT_IN),
            (MAX_LOCAL_UI_LOOPBACK_CLIENT_PORT + 1, get_request(), LOCAL_UI_LOOPBACK_CLIENT_EXECUTION_OPT_IN),
            (True, get_request(), LOCAL_UI_LOOPBACK_CLIENT_EXECUTION_OPT_IN),
            (8780, object(), LOCAL_UI_LOOPBACK_CLIENT_EXECUTION_OPT_IN),
            (
                8780,
                LocalUiHttpRequest("GET", "/elsewhere", None, b""),
                LOCAL_UI_LOOPBACK_CLIENT_EXECUTION_OPT_IN,
            ),
        )
        for port, request, token in cases:
            with self.subTest(port=port, token=token):
                with self.assertRaises(LocalUiLoopbackClientError):
                    run_local_ui_loopback_client_once(
                        port=port,  # type: ignore[arg-type]
                        request=request,  # type: ignore[arg-type]
                        execution_opt_in=token,
                        socket_constructor=constructor,
                    )
        self.assertEqual(constructor.calls, [])

    def test_get_connects_exact_loopback_writes_exact_request_and_validates_response(self):
        sock = FakeSocket([response_wire(b"<html>Local Marketplace Buy/Sell</html>")], send_limit=23)
        result = run_local_ui_loopback_client_once(
            port=8781,
            request=get_request(),
            execution_opt_in=LOCAL_UI_LOOPBACK_CLIENT_EXECUTION_OPT_IN,
            socket_constructor=FakeConstructor(sock),
        )

        self.assertEqual(sock.connected, ("127.0.0.1", 8781))
        self.assertEqual(
            bytes(sock.sent),
            b"GET / HTTP/1.1\r\nHost: 127.0.0.1:8781\r\nConnection: close\r\n\r\n",
        )
        self.assertEqual(sock.closed, 1)
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.request_method, "GET")
        self.assertEqual(result.request_target, "/")
        self.assertTrue(result.network_invoked)
        self.assertFalse(result.external_authorization_established)
        self.assertFalse(result.deployment_authorized)

    def test_post_preserves_exact_m77_body_without_retaining_human_content(self):
        request = post_request()
        sock = FakeSocket([response_wire(b"<html>protocol_truth=false creates_agreement=false</html>")])
        result = run_local_ui_loopback_client_once(
            port=8782,
            request=request,
            execution_opt_in=LOCAL_UI_LOOPBACK_CLIENT_EXECUTION_OPT_IN,
            socket_constructor=FakeConstructor(sock),
        )

        self.assertIn(b"POST /local-buy-sell HTTP/1.1\r\n", sock.sent)
        self.assertIn(b"Content-Type: application/x-www-form-urlencoded\r\n", sock.sent)
        self.assertIn(f"Content-Length: {len(request.body)}\r\n".encode("ascii"), sock.sent)
        self.assertTrue(bytes(sock.sent).endswith(b"\r\n\r\n" + request.body))
        self.assertNotIn(FIELDS["description"], repr(result))
        self.assertNotIn(FIELDS["buyer_principal"], repr(result))

    def test_connect_send_and_recv_failures_are_stable_and_non_reflective(self):
        cases = (
            (FakeSocket([response_wire()], connect_error=True), "CONNECT_FAILED"),
            (FakeSocket([response_wire()], send_error=True), "WRITE_FAILED"),
            (FakeSocket([], recv_error=True), "READ_FAILED"),
        )
        for sock, code in cases:
            with self.subTest(code=code):
                with self.assertRaises(LocalUiLoopbackClientError) as raised:
                    run_local_ui_loopback_client_once(
                        port=8783,
                        request=get_request(),
                        execution_opt_in=LOCAL_UI_LOOPBACK_CLIENT_EXECUTION_OPT_IN,
                        socket_constructor=FakeConstructor(sock),
                    )
                self.assertEqual(raised.exception.code, code)
                self.assertNotIn("HOSTILE", str(raised.exception))
                self.assertEqual(sock.closed, 1)

    def test_malformed_or_ambiguous_response_framing_fails_closed(self):
        good = response_wire()
        cases = (
            good.replace(b"Content-Length: 15", b"Content-Length: 14"),
            good.replace(b"Cache-Control: no-store\r\n", b""),
            good.replace(b"Connection: close\r\n", b"Transfer-Encoding: chunked\r\n"),
            good + b"TRAILING",
        )
        for wire in cases:
            with self.subTest(wire=wire[:80]):
                sock = FakeSocket([wire])
                with self.assertRaises(LocalUiLoopbackClientError) as raised:
                    run_local_ui_loopback_client_once(
                        port=8784,
                        request=get_request(),
                        execution_opt_in=LOCAL_UI_LOOPBACK_CLIENT_EXECUTION_OPT_IN,
                        socket_constructor=FakeConstructor(sock),
                    )
                self.assertIn(
                    raised.exception.code,
                    {"RESPONSE_INVALID", "RESPONSE_TRAILING_BYTES", "RESPONSE_INCOMPLETE"},
                )
                self.assertEqual(sock.closed, 1)

    def test_cleanup_failure_is_stable(self):
        sock = FakeSocket([response_wire()], close_error=True)
        with self.assertRaises(LocalUiLoopbackClientError) as raised:
            run_local_ui_loopback_client_once(
                port=8785,
                request=get_request(),
                execution_opt_in=LOCAL_UI_LOOPBACK_CLIENT_EXECUTION_OPT_IN,
                socket_constructor=FakeConstructor(sock),
            )
        self.assertEqual(raised.exception.code, "CLEANUP_UNCERTAIN")
        self.assertNotIn("HOSTILE", str(raised.exception))
        self.assertEqual(sock.closed, 1)

    def test_result_is_frozen_and_metadata_only(self):
        result = run_local_ui_loopback_client_once(
            port=8786,
            request=get_request(),
            execution_opt_in=LOCAL_UI_LOOPBACK_CLIENT_EXECUTION_OPT_IN,
            socket_constructor=FakeConstructor(FakeSocket([response_wire()])),
        )
        self.assertIs(type(result), LocalUiLoopbackClientResult)
        with self.assertRaises(FrozenInstanceError):
            result.status_code = 500  # type: ignore[misc]
        for forbidden in ("request_bytes", "response_bytes", "body", "transcript", "form_values"):
            self.assertFalse(hasattr(result, forbidden))


if __name__ == "__main__":
    unittest.main()
