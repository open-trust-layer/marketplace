from __future__ import annotations

import unittest

from marketplace.runtime.https_transport import _request_bytes
from marketplace.runtime.inbound_http import (
    ROUTE_FEDERATION_CONTROL,
    ROUTE_IMMUTABLE_RECORD,
    BoundedInboundHttpApplicationAdapter,
    InboundHttpApplicationLimits,
    PreparedInboundHttpResponse,
)
from marketplace.runtime.inbound_http_stream import (
    PROGRESS_COMPLETE,
    PROGRESS_NEED_MORE,
    BoundedInboundHttpStreamAssembler,
    InboundHttpStreamError,
    InboundHttpStreamLimits,
)
from marketplace.runtime.inbound_http_wire import (
    BoundedInboundHttpWireAdapter,
    InboundHttpWireLimits,
)
from marketplace.runtime.inbound_record import INBOUND_RECORD_RETRIEVAL_OPERATION
from marketplace.runtime.record_retrieval import _get_request_bytes

AUTHORITY = "market.example"
CONTROL_OPERATION = "https://example.test/runtime/operation/snapshot"
CONTROL_PATH = "/v1/federation/snapshot"
RECORD_ID = "r1_qcU6rT-ADJiC75Bg9w7qLSvauhY6zcEmy1dk-LrRlZc"


class _ApplicationHarness:
    def __init__(self):
        self.calls = []
        adapter = object.__new__(BoundedInboundHttpApplicationAdapter)
        object.__setattr__(adapter, "_limits", InboundHttpApplicationLimits())
        object.__setattr__(adapter, "handle", self._handle)
        self.adapter = adapter

    def _handle(self, request):
        self.calls.append(request)
        body = b'{"olp":"prepared"}'
        if request.method == "POST":
            route_kind = ROUTE_FEDERATION_CONTROL
            route_operation = CONTROL_OPERATION
            message_type = "marketplace.snapshot.result.v1"
        else:
            route_kind = ROUTE_IMMUTABLE_RECORD
            route_operation = INBOUND_RECORD_RETRIEVAL_OPERATION
            message_type = "record"
        return PreparedInboundHttpResponse(
            request=request,
            route_kind=route_kind,
            route_operation=route_operation,
            status_code=200,
            headers=(
                ("connection", "close"),
                ("content-length", str(len(body))),
                ("content-type", "application/json"),
            ),
            body=body,
            olp_message_type=message_type,
        )


class InboundHttpStreamTests(unittest.TestCase):
    def setUp(self):
        self.harness = _ApplicationHarness()
        self.wire = BoundedInboundHttpWireAdapter(
            application_adapter=self.harness.adapter,
            authority=AUTHORITY,
        )
        self.assembler = BoundedInboundHttpStreamAssembler(wire_adapter=self.wire)

    def test_m26_control_post_split_across_chunks_invokes_application_once(self):
        body = b'{"request":"snapshot"}'
        raw = _request_bytes(CONTROL_PATH, AUTHORITY, 443, body)
        cuts = (7, 31, 64, len(raw) - 5)
        chunks = (
            raw[: cuts[0]],
            raw[cuts[0] : cuts[1]],
            raw[cuts[1] : cuts[2]],
            raw[cuts[2] : cuts[3]],
            raw[cuts[3] :],
        )
        prepared = self.assembler.prepare_chunks(chunks)
        self.assertEqual(len(self.harness.calls), 1)
        self.assertEqual(prepared.chunk_count, len(chunks))
        self.assertEqual(prepared.request_bytes, len(raw))
        self.assertEqual(prepared.wire_exchange.route_kind, ROUTE_FEDERATION_CONTROL)
        self.assertFalse(prepared.network_read_performed)
        self.assertFalse(prepared.transmitted)

    def test_m27_record_get_can_be_split_at_every_byte_boundary(self):
        raw = _get_request_bytes(f"/v1/records/{RECORD_ID}", AUTHORITY, 443)
        assembler = BoundedInboundHttpStreamAssembler(
            wire_adapter=self.wire,
            limits=InboundHttpStreamLimits(max_chunks=512, max_chunk_bytes=1),
        )
        prepared = assembler.prepare_chunks(tuple(bytes((byte,)) for byte in raw))
        self.assertEqual(len(self.harness.calls), 1)
        self.assertEqual(prepared.chunk_count, len(raw))
        self.assertEqual(prepared.wire_exchange.route_kind, ROUTE_IMMUTABLE_RECORD)
        self.assertEqual(prepared.wire_exchange.olp_message_type, "record")

    def test_probe_before_header_terminator_needs_more_without_application_call(self):
        prefix = b"GET /v1/records/example HTTP/1.1\r\nHost: market.example\r\n"
        progress = self.assembler.probe(prefix)
        self.assertEqual(progress.state, PROGRESS_NEED_MORE)
        self.assertFalse(progress.head_complete)
        self.assertIsNone(progress.expected_total_bytes)
        self.assertEqual(self.harness.calls, [])

    def test_probe_partial_declared_body_reports_exact_missing_bytes(self):
        raw = (
            "POST /v1/federation/snapshot HTTP/1.1\r\n"
            f"Host: {AUTHORITY}\r\n"
            "Content-Type: application/json\r\n"
            "Accept: application/json\r\n"
            "Connection: close\r\n"
            "Content-Length: 5\r\n\r\n"
        ).encode("ascii") + b"abc"
        progress = self.assembler.probe(raw)
        self.assertEqual(progress.state, PROGRESS_NEED_MORE)
        self.assertTrue(progress.head_complete)
        self.assertTrue(progress.head_validated)
        self.assertEqual(progress.missing_bytes, 2)
        self.assertEqual(progress.expected_total_bytes, len(raw) + 2)
        self.assertEqual(self.harness.calls, [])

    def test_probe_exact_request_is_complete_without_application_call(self):
        raw = _get_request_bytes(f"/v1/records/{RECORD_ID}", AUTHORITY, 443)
        progress = self.assembler.probe(raw)
        self.assertEqual(progress.state, PROGRESS_COMPLETE)
        self.assertEqual(progress.expected_total_bytes, len(raw))
        self.assertEqual(progress.missing_bytes, 0)
        self.assertTrue(progress.request_complete)
        self.assertEqual(self.harness.calls, [])

    def test_trailing_or_pipelined_bytes_fail_before_application_prepare(self):
        raw = _get_request_bytes(f"/v1/records/{RECORD_ID}", AUTHORITY, 443)
        with self.assertRaises(InboundHttpStreamError) as caught:
            self.assembler.prepare_chunks((raw + b"GET / HTTP/1.1\r\n\r\n",))
        self.assertEqual(caught.exception.code, "TRAILING_OR_PIPELINED_BYTES")
        self.assertEqual(self.harness.calls, [])

    def test_request_completing_before_later_chunk_fails_before_application(self):
        raw = _get_request_bytes(f"/v1/records/{RECORD_ID}", AUTHORITY, 443)
        with self.assertRaises(InboundHttpStreamError) as caught:
            self.assembler.prepare_chunks((raw, b"x"))
        self.assertEqual(caught.exception.code, "TRAILING_OR_PIPELINED_BYTES")
        self.assertEqual(self.harness.calls, [])

    def test_incomplete_final_chunks_fail_without_application(self):
        raw = (
            "POST /v1/federation/snapshot HTTP/1.1\r\n"
            f"Host: {AUTHORITY}\r\n"
            "Content-Type: application/json\r\n"
            "Accept: application/json\r\n"
            "Connection: close\r\n"
            "Content-Length: 5\r\n\r\n"
        ).encode("ascii") + b"abc"
        with self.assertRaises(InboundHttpStreamError) as caught:
            self.assembler.prepare_chunks((raw,))
        self.assertEqual(caught.exception.code, "INCOMPLETE_REQUEST")
        self.assertEqual(self.harness.calls, [])

    def test_empty_tuple_and_empty_chunk_fail_closed(self):
        with self.assertRaises(InboundHttpStreamError) as empty_collection:
            self.assembler.prepare_chunks(())
        self.assertEqual(empty_collection.exception.code, "INCOMPLETE_REQUEST")
        with self.assertRaises(InboundHttpStreamError) as empty_chunk:
            self.assembler.prepare_chunks((b"",))
        self.assertEqual(empty_chunk.exception.code, "INVALID_CHUNK")
        self.assertEqual(self.harness.calls, [])

    def test_wire_limits_remain_authoritative_for_stream_aggregate(self):
        harness = _ApplicationHarness()
        wire = BoundedInboundHttpWireAdapter(
            application_adapter=harness.adapter,
            authority=AUTHORITY,
            limits=InboundHttpWireLimits(
                max_header_bytes=256,
                max_body_bytes=8,
                max_response_body_bytes=64,
            ),
        )
        assembler = BoundedInboundHttpStreamAssembler(wire_adapter=wire)
        with self.assertRaises(InboundHttpStreamError) as caught:
            assembler.probe(b"x" * 265)
        self.assertEqual(caught.exception.code, "STREAM_TOTAL_LIMIT_EXCEEDED")
        self.assertEqual(harness.calls, [])


if __name__ == "__main__":
    unittest.main()
