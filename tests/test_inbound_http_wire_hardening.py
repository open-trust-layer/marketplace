from __future__ import annotations

import ast
import dataclasses
import inspect
import unittest

import marketplace.runtime.inbound_http_wire as wire_module
from marketplace.runtime.inbound_http import (
    ROUTE_IMMUTABLE_RECORD,
    BoundedInboundHttpApplicationAdapter,
    InboundHttpApplicationLimits,
    PreparedInboundHttpResponse,
)
from marketplace.runtime.inbound_http_wire import (
    BoundedInboundHttpWireAdapter,
    InboundHttpWireError,
    InboundHttpWireLimits,
)

AUTHORITY = "market.example"
RECORD_ID = "r1_qcU6rT-ADJiC75Bg9w7qLSvauhY6zcEmy1dk-LrRlZc"


class _Harness:
    def __init__(self):
        self.calls = []
        adapter = object.__new__(BoundedInboundHttpApplicationAdapter)
        object.__setattr__(adapter, "_limits", InboundHttpApplicationLimits())
        object.__setattr__(adapter, "handle", self._handle)
        self.adapter = adapter

    def _handle(self, request):
        self.calls.append(request)
        body = b'{"olp":"prepared"}'
        return PreparedInboundHttpResponse(
            request=request,
            route_kind=ROUTE_IMMUTABLE_RECORD,
            route_operation="https://open-trust-layer.github.io/marketplace/runtime/v1/operation/olp-record-retrieval",
            status_code=200,
            headers=(
                ("connection", "close"),
                ("content-length", str(len(body))),
                ("content-type", "application/json"),
            ),
            body=body,
            olp_message_type="record",
        )


def _get(*extra_headers: str, suffix: bytes = b"") -> bytes:
    lines = [
        f"GET /v1/records/{RECORD_ID} HTTP/1.1",
        f"Host: {AUTHORITY}",
        "Accept: application/json",
        "Connection: close",
        *extra_headers,
        "",
        "",
    ]
    return "\r\n".join(lines).encode("ascii") + suffix


class InboundHttpWireHardeningTests(unittest.TestCase):
    def setUp(self):
        self.harness = _Harness()
        self.adapter = BoundedInboundHttpWireAdapter(
            application_adapter=self.harness.adapter,
            authority=AUTHORITY,
        )

    def test_http_version_absolute_target_and_request_line_ambiguity_fail_closed(self):
        variants = (
            f"GET /v1/records/{RECORD_ID} HTTP/1.0\r\nHost: {AUTHORITY}\r\nConnection: close\r\n\r\n",
            f"GET http://{AUTHORITY}/v1/records/{RECORD_ID} HTTP/1.1\r\nHost: {AUTHORITY}\r\nConnection: close\r\n\r\n",
            f"GET  /v1/records/{RECORD_ID} HTTP/1.1\r\nHost: {AUTHORITY}\r\nConnection: close\r\n\r\n",
            f"GET\t/v1/records/{RECORD_ID}\tHTTP/1.1\r\nHost: {AUTHORITY}\r\nConnection: close\r\n\r\n",
        )
        for text in variants:
            with self.subTest(text=text[:20]):
                with self.assertRaises(InboundHttpWireError):
                    self.adapter.prepare(text.encode("ascii"))
        self.assertEqual(self.harness.calls, [])

    def test_bare_lf_cr_and_obs_fold_fail_before_application(self):
        variants = (
            f"GET /v1/records/{RECORD_ID} HTTP/1.1\nHost: {AUTHORITY}\nConnection: close\n\n".encode("ascii"),
            f"GET /v1/records/{RECORD_ID} HTTP/1.1\rHost: {AUTHORITY}\rConnection: close\r\r".encode("ascii"),
            (
                f"GET /v1/records/{RECORD_ID} HTTP/1.1\r\n"
                f"Host: {AUTHORITY}\r\n"
                " Connection: close\r\n\r\n"
            ).encode("ascii"),
        )
        for raw in variants:
            with self.subTest(raw=raw[:20]):
                with self.assertRaises(InboundHttpWireError):
                    self.adapter.prepare(raw)
        self.assertEqual(self.harness.calls, [])

    def test_duplicate_headers_are_case_insensitive_even_when_second_spelling_is_noncanonical(self):
        raw = (
            f"GET /v1/records/{RECORD_ID} HTTP/1.1\r\n"
            f"Host: {AUTHORITY}\r\n"
            f"host: {AUTHORITY}\r\n"
            "Connection: close\r\n\r\n"
        ).encode("ascii")
        with self.assertRaises(InboundHttpWireError) as caught:
            self.adapter.prepare(raw)
        self.assertEqual(caught.exception.code, "DUPLICATE_HEADER")
        self.assertEqual(self.harness.calls, [])

    def test_unknown_sensitive_and_transfer_headers_fail_before_application(self):
        names = (
            "Transfer-Encoding: chunked",
            "Content-Encoding: gzip",
            "Upgrade: websocket",
            "Authorization: secret",
            "Cookie: a=b",
            "Proxy-Authorization: secret",
            "Forwarded: host=evil",
            "X-Forwarded-Host: evil",
            "X-HTTP-Method-Override: POST",
            "Range: bytes=0-1",
            "Trailer: x",
            "TE: trailers",
            "X-Unknown: value",
        )
        for header in names:
            with self.subTest(header=header):
                self.harness.calls.clear()
                with self.assertRaises(InboundHttpWireError) as caught:
                    self.adapter.prepare(_get(header))
                self.assertEqual(caught.exception.code, "UNSUPPORTED_HEADER")
                self.assertEqual(self.harness.calls, [])

    def test_header_colon_spacing_and_canonical_name_spelling_are_exact(self):
        variants = (
            f"GET /v1/records/{RECORD_ID} HTTP/1.1\r\nHost:{AUTHORITY}\r\nConnection: close\r\n\r\n",
            f"GET /v1/records/{RECORD_ID} HTTP/1.1\r\nhost: {AUTHORITY}\r\nConnection: close\r\n\r\n",
            f"GET /v1/records/{RECORD_ID} HTTP/1.1\r\nHost:  {AUTHORITY}\r\nConnection: close\r\n\r\n",
        )
        for text in variants:
            with self.subTest(text=text.split("\r\n")[1]):
                with self.assertRaises(InboundHttpWireError):
                    self.adapter.prepare(text.encode("ascii"))
        self.assertEqual(self.harness.calls, [])

    def test_resource_limits_fail_before_application(self):
        small_limits = InboundHttpWireLimits(
            max_header_bytes=128,
            max_body_bytes=8,
            max_response_body_bytes=64,
        )
        adapter = BoundedInboundHttpWireAdapter(
            application_adapter=self.harness.adapter,
            authority=AUTHORITY,
            limits=small_limits,
        )
        with self.assertRaises(InboundHttpWireError):
            adapter.prepare(_get("Accept: " + "a" * 100))
        self.assertEqual(self.harness.calls, [])

        post = (
            "POST /control HTTP/1.1\r\n"
            f"Host: {AUTHORITY}\r\n"
            "Content-Type: application/json\r\n"
            "Connection: close\r\n"
            "Content-Length: 9\r\n\r\n"
        ).encode("ascii") + b"123456789"
        with self.assertRaises(InboundHttpWireError) as caught:
            adapter.prepare(post)
        self.assertIn(caught.exception.code, {"REQUEST_WIRE_LIMIT_EXCEEDED", "HTTP_BODY_LIMIT_EXCEEDED"})
        self.assertEqual(self.harness.calls, [])

    def test_wire_limits_are_detached_from_caller_alias(self):
        limits = InboundHttpWireLimits(max_header_bytes=512, max_body_bytes=512, max_response_body_bytes=512)
        adapter = BoundedInboundHttpWireAdapter(
            application_adapter=self.harness.adapter,
            authority=AUTHORITY,
            limits=limits,
        )
        object.__setattr__(limits, "max_header_bytes", 131072)
        object.__setattr__(limits, "max_body_bytes", 16777216)
        self.assertEqual(adapter.limits.max_header_bytes, 512)
        self.assertEqual(adapter.limits.max_body_bytes, 512)

    def test_large_decimal_content_length_is_not_parsed_as_integer_by_m35(self):
        source = inspect.getsource(wire_module)
        tree = ast.parse(source)
        int_calls = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "int":
                int_calls.append(ast.unparse(node.args[0]) if node.args else "")
        self.assertEqual(int_calls, ["port_text"])

        body = b"{}"
        raw = (
            "POST /control HTTP/1.1\r\n"
            f"Host: {AUTHORITY}\r\n"
            "Content-Type: application/json\r\n"
            "Connection: close\r\n"
            f"Content-Length: {'9' * 1024}\r\n\r\n"
        ).encode("ascii") + body
        with self.assertRaises(InboundHttpWireError):
            self.adapter.prepare(raw)

    def test_prepared_witness_blocks_dataclass_rebinding(self):
        prepared = self.adapter.prepare(_get())
        with self.assertRaises(ValueError):
            dataclasses.replace(prepared, route_operation="https://example.test/other")

    def test_raw_request_bytes_are_not_retained_by_prepared_result(self):
        raw = _get()
        prepared = self.adapter.prepare(raw)
        field_names = {field.name for field in dataclasses.fields(prepared)}
        self.assertNotIn("raw_request", field_names)
        self.assertNotIn("request_bytes", field_names)
        self.assertNotEqual(prepared.response_bytes, raw)

    def test_m35_source_has_no_network_server_tls_process_background_filesystem_or_logging_imports(self):
        source = inspect.getsource(wire_module)
        tree = ast.parse(source)
        forbidden_roots = {
            "socket",
            "ssl",
            "http",
            "urllib",
            "asyncio",
            "threading",
            "subprocess",
            "logging",
            "pathlib",
            "os",
        }
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name.split(".", 1)[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.split(".", 1)[0])
        self.assertTrue(imported.isdisjoint(forbidden_roots), imported & forbidden_roots)
        self.assertNotIn(".listen(", source)
        self.assertNotIn(".accept(", source)
        self.assertNotIn("sendall(", source)


if __name__ == "__main__":
    unittest.main()
