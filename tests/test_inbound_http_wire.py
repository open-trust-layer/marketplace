from __future__ import annotations

import unittest

from marketplace.runtime.https_transport import (
    HttpsFederationTransportLimits,
    _read_response,
    _request_bytes,
)
from marketplace.runtime.inbound_http import (
    ROUTE_FEDERATION_CONTROL,
    ROUTE_IMMUTABLE_RECORD,
    BoundedInboundHttpApplicationAdapter,
    InboundHttpApplicationLimits,
    InboundHttpError,
    PreparedInboundHttpResponse,
)
from marketplace.runtime.inbound_http_wire import (
    BoundedInboundHttpWireAdapter,
    InboundHttpWireError,
    InboundHttpWireLimits,
)
from marketplace.runtime.record_retrieval import _get_request_bytes

CONTROL_OPERATION = "https://example.test/runtime/operation/snapshot"
CONTROL_PATH = "/v1/federation/snapshot"
RECORD_ID = "r1_qcU6rT-ADJiC75Bg9w7qLSvauhY6zcEmy1dk-LrRlZc"
AUTHORITY = "market.example"


class _BufferedResponseConnection:
    def __init__(self, payload: bytes):
        self._payload = payload
        self._sent = False
        self.timeouts: list[float] = []

    def recv(self, size: int) -> bytes:
        if self._sent:
            return b""
        self._sent = True
        return self._payload[:size] if len(self._payload) > size else self._payload

    def settimeout(self, value: float) -> None:
        self.timeouts.append(value)


class _ApplicationHarness:
    def __init__(self):
        self.calls = []
        adapter = object.__new__(BoundedInboundHttpApplicationAdapter)
        object.__setattr__(adapter, "_limits", InboundHttpApplicationLimits())
        object.__setattr__(adapter, "handle", self._handle)
        self.adapter = adapter
        self.promote_transmitted = False

    def _handle(self, request):
        self.calls.append(request)
        headers = dict(request.headers)
        if request.method == "POST":
            declared = headers.get("content-length")
            if declared != str(len(request.body)):
                raise InboundHttpError("CONTENT_LENGTH_MISMATCH", "synthetic M34 mismatch")
            route_kind = ROUTE_FEDERATION_CONTROL
            operation = CONTROL_OPERATION
            message_type = "marketplace.snapshot.result.v1"
        else:
            route_kind = ROUTE_IMMUTABLE_RECORD
            operation = "https://open-trust-layer.github.io/marketplace/runtime/v1/operation/olp-record-retrieval"
            message_type = "record"
        body = b'{"olp":"prepared"}'
        result = PreparedInboundHttpResponse(
            request=request,
            route_kind=route_kind,
            route_operation=operation,
            status_code=200,
            headers=(
                ("connection", "close"),
                ("content-length", str(len(body))),
                ("content-type", "application/json"),
            ),
            body=body,
            olp_message_type=message_type,
        )
        if self.promote_transmitted:
            object.__setattr__(result, "transmitted", True)
        return result


class InboundHttpWireTests(unittest.TestCase):
    def setUp(self):
        self.harness = _ApplicationHarness()
        self.adapter = BoundedInboundHttpWireAdapter(
            application_adapter=self.harness.adapter,
            authority=AUTHORITY,
        )

    def test_exact_m26_control_post_wire_shape_is_accepted(self):
        body = b'{"request":"snapshot"}'
        raw = _request_bytes(CONTROL_PATH, AUTHORITY, 443, body)
        prepared = self.adapter.prepare(raw)
        self.assertEqual(len(self.harness.calls), 1)
        request = self.harness.calls[0]
        self.assertEqual(request.method, "POST")
        self.assertEqual(request.path, CONTROL_PATH)
        self.assertEqual(request.body, body)
        self.assertNotIn("host", dict(request.headers))
        self.assertTrue(prepared.host_authority_validated)
        self.assertFalse(prepared.tls_sni_bound)
        self.assertFalse(prepared.transmitted)
        self.assertEqual(prepared.route_kind, ROUTE_FEDERATION_CONTROL)

    def test_exact_m27_record_get_wire_shape_is_accepted(self):
        path = f"/v1/records/{RECORD_ID}"
        raw = _get_request_bytes(path, AUTHORITY, 443)
        prepared = self.adapter.prepare(raw)
        self.assertEqual(len(self.harness.calls), 1)
        request = self.harness.calls[0]
        self.assertEqual(request.method, "GET")
        self.assertEqual(request.path, path)
        self.assertEqual(request.body, b"")
        self.assertEqual(prepared.route_kind, ROUTE_IMMUTABLE_RECORD)
        self.assertEqual(prepared.olp_message_type, "record")

    def test_m35_response_is_accepted_by_existing_m26_response_parser(self):
        raw = _get_request_bytes(f"/v1/records/{RECORD_ID}", AUTHORITY, 443)
        prepared = self.adapter.prepare(raw)
        connection = _BufferedResponseConnection(prepared.response_bytes)
        status, body = _read_response(
            connection,
            start=0.0,
            limits=HttpsFederationTransportLimits(),
            monotonic=lambda: 0.0,
        )
        self.assertEqual(status, 200)
        self.assertEqual(body, b'{"olp":"prepared"}')

    def test_host_is_required_and_exact_before_application_adapter(self):
        for host in (
            "example.market",
            "MARKET.EXAMPLE",
            "market.example.",
            "market.example:443",
            "evil.market.example",
            "market.example.evil",
        ):
            with self.subTest(host=host):
                self.harness.calls.clear()
                raw = (
                    f"GET /v1/records/{RECORD_ID} HTTP/1.1\r\n"
                    f"Host: {host}\r\n"
                    "Accept: application/json\r\n"
                    "Connection: close\r\n\r\n"
                ).encode("ascii")
                with self.assertRaises(InboundHttpWireError) as caught:
                    self.adapter.prepare(raw)
                self.assertEqual(caught.exception.code, "HOST_AUTHORITY_MISMATCH")
                self.assertEqual(self.harness.calls, [])

    def test_missing_or_wrong_connection_close_fails_before_application_adapter(self):
        missing = (
            f"GET /v1/records/{RECORD_ID} HTTP/1.1\r\n"
            f"Host: {AUTHORITY}\r\n"
            "Accept: application/json\r\n\r\n"
        ).encode("ascii")
        wrong = (
            f"GET /v1/records/{RECORD_ID} HTTP/1.1\r\n"
            f"Host: {AUTHORITY}\r\n"
            "Connection: keep-alive\r\n\r\n"
        ).encode("ascii")
        for raw in (missing, wrong):
            with self.assertRaises(InboundHttpWireError) as caught:
                self.adapter.prepare(raw)
            self.assertEqual(caught.exception.code, "CONNECTION_CLOSE_REQUIRED")
        self.assertEqual(self.harness.calls, [])

    def test_declared_length_mismatch_or_pipelined_bytes_fail_before_application(self):
        raw = (
            f"POST {CONTROL_PATH} HTTP/1.1\r\n"
            f"Host: {AUTHORITY}\r\n"
            "Content-Type: application/json\r\n"
            "Accept: application/json\r\n"
            "Connection: close\r\n"
            "Content-Length: 2\r\n\r\n"
        ).encode("ascii") + b"{}GET / HTTP/1.1\r\n\r\n"
        with self.assertRaises(InboundHttpWireError) as caught:
            self.adapter.prepare(raw)
        self.assertEqual(caught.exception.code, "CONTENT_LENGTH_MISMATCH")
        self.assertEqual(self.harness.calls, [])

    def test_response_authority_promotion_is_rejected(self):
        self.harness.promote_transmitted = True
        raw = _get_request_bytes(f"/v1/records/{RECORD_ID}", AUTHORITY, 443)
        with self.assertRaises(InboundHttpWireError) as caught:
            self.adapter.prepare(raw)
        self.assertEqual(caught.exception.code, "APPLICATION_AUTHORITY_ESCALATION")

    def test_response_frame_is_exact_and_content_length_matches_body(self):
        raw = _get_request_bytes(f"/v1/records/{RECORD_ID}", AUTHORITY, 443)
        prepared = self.adapter.prepare(raw)
        prefix = (
            "HTTP/1.1 200 OK\r\n"
            "Content-Type: application/json\r\n"
            "Content-Length: 18\r\n"
            "Connection: close\r\n\r\n"
        ).encode("ascii")
        self.assertEqual(prepared.response_bytes, prefix + b'{"olp":"prepared"}')
        self.assertEqual(prepared.response_body_bytes, 18)

    def test_wire_limits_cannot_exceed_application_limits(self):
        app = object.__new__(BoundedInboundHttpApplicationAdapter)
        object.__setattr__(
            app,
            "_limits",
            InboundHttpApplicationLimits(
                max_request_body_bytes=8,
                max_response_body_bytes=8,
                max_header_bytes=128,
            ),
        )
        object.__setattr__(app, "handle", lambda request: None)
        with self.assertRaises(ValueError):
            BoundedInboundHttpWireAdapter(
                application_adapter=app,
                authority=AUTHORITY,
                limits=InboundHttpWireLimits(max_body_bytes=9, max_response_body_bytes=8, max_header_bytes=128),
            )


if __name__ == "__main__":
    unittest.main()
