from __future__ import annotations

import unittest

from marketplace.runtime.inbound_http import (
    ROUTE_IMMUTABLE_RECORD,
    BoundedInboundHttpApplicationAdapter,
    InboundHttpApplicationLimits,
    PreparedInboundHttpResponse,
)
from marketplace.runtime.inbound_http_read_plan import (
    READ_ACTION_COMPLETE,
    READ_ACTION_READ,
    BoundedInboundHttpReadPlanner,
    InboundHttpReadLimits,
    InboundHttpReadPlanError,
)
from marketplace.runtime.inbound_http_stream import (
    BoundedInboundHttpStreamAssembler,
    InboundHttpStreamLimits,
)
from marketplace.runtime.inbound_http_wire import BoundedInboundHttpWireAdapter
from marketplace.runtime.inbound_record import INBOUND_RECORD_RETRIEVAL_OPERATION
from marketplace.runtime.record_retrieval import _get_request_bytes

AUTHORITY = "market.example"
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
        return PreparedInboundHttpResponse(
            request=request,
            route_kind=ROUTE_IMMUTABLE_RECORD,
            route_operation=INBOUND_RECORD_RETRIEVAL_OPERATION,
            status_code=200,
            headers=(
                ("connection", "close"),
                ("content-length", str(len(body))),
                ("content-type", "application/json"),
            ),
            body=body,
            olp_message_type="record",
        )


def _post_prefix(*, declared: int, body: bytes = b"") -> bytes:
    return (
        "POST /v1/federation/snapshot HTTP/1.1\r\n"
        f"Host: {AUTHORITY}\r\n"
        "Content-Type: application/json\r\n"
        "Accept: application/json\r\n"
        "Connection: close\r\n"
        f"Content-Length: {declared}\r\n\r\n"
    ).encode("ascii") + body


class InboundHttpReadPlanTests(unittest.TestCase):
    def setUp(self):
        self.harness = _ApplicationHarness()
        self.wire = BoundedInboundHttpWireAdapter(
            application_adapter=self.harness.adapter,
            authority=AUTHORITY,
        )
        self.stream = BoundedInboundHttpStreamAssembler(wire_adapter=self.wire)
        self.planner = BoundedInboundHttpReadPlanner(stream_assembler=self.stream)

    def test_empty_prefix_plans_bounded_header_read_without_disclosure(self):
        plan = self.planner.plan(b"", reads_completed=0)
        self.assertEqual(plan.action, READ_ACTION_READ)
        self.assertEqual(plan.buffered_bytes, 0)
        self.assertEqual(plan.next_read_bytes, 16 * 1024)
        self.assertIsNone(plan.expected_total_bytes)
        self.assertFalse(plan.head_complete)
        self.assertFalse(plan.request_complete)
        self.assertFalse(plan.network_read_performed)
        self.assertFalse(plan.socket_bound)
        self.assertFalse(plan.transmitted)
        self.assertEqual(self.harness.calls, [])

    def test_header_phase_never_exceeds_remaining_m35_header_capacity(self):
        header_limit = self.planner.wire_limits.max_header_bytes
        prefix = b"x" * (header_limit - 7)
        plan = self.planner.plan(prefix, reads_completed=3)
        self.assertEqual(plan.action, READ_ACTION_READ)
        self.assertEqual(plan.next_read_bytes, 7)
        self.assertIsNone(plan.expected_total_bytes)
        self.assertEqual(self.harness.calls, [])

    def test_validated_partial_body_plans_exact_missing_bytes(self):
        prefix = _post_prefix(declared=5, body=b"abc")
        plan = self.planner.plan(prefix, reads_completed=2)
        self.assertEqual(plan.action, READ_ACTION_READ)
        self.assertEqual(plan.next_read_bytes, 2)
        self.assertEqual(plan.missing_bytes, 2)
        self.assertTrue(plan.head_complete)
        self.assertTrue(plan.head_validated)
        self.assertEqual(self.harness.calls, [])

    def test_large_remaining_body_is_capped_by_per_read_limit(self):
        prefix = _post_prefix(declared=20_000)
        plan = self.planner.plan(prefix, reads_completed=1)
        self.assertEqual(plan.action, READ_ACTION_READ)
        self.assertEqual(plan.missing_bytes, 20_000)
        self.assertEqual(plan.next_read_bytes, 16 * 1024)
        self.assertEqual(self.harness.calls, [])

    def test_complete_request_plans_zero_further_bytes(self):
        raw = _get_request_bytes(f"/v1/records/{RECORD_ID}", AUTHORITY, 443)
        plan = self.planner.plan(raw, reads_completed=1)
        self.assertEqual(plan.action, READ_ACTION_COMPLETE)
        self.assertEqual(plan.next_read_bytes, 0)
        self.assertEqual(plan.expected_total_bytes, len(raw))
        self.assertEqual(plan.missing_bytes, 0)
        self.assertTrue(plan.request_complete)
        self.assertEqual(self.harness.calls, [])

    def test_complete_request_is_allowed_at_exact_read_call_limit(self):
        raw = _get_request_bytes(f"/v1/records/{RECORD_ID}", AUTHORITY, 443)
        planner = BoundedInboundHttpReadPlanner(
            stream_assembler=self.stream,
            limits=InboundHttpReadLimits(max_read_calls=1, max_read_bytes=1024),
        )
        plan = planner.plan(raw, reads_completed=1)
        self.assertEqual(plan.action, READ_ACTION_COMPLETE)
        self.assertEqual(plan.next_read_bytes, 0)

    def test_incomplete_request_fails_when_read_call_limit_is_exhausted(self):
        planner = BoundedInboundHttpReadPlanner(
            stream_assembler=self.stream,
            limits=InboundHttpReadLimits(max_read_calls=1, max_read_bytes=1024),
        )
        with self.assertRaises(InboundHttpReadPlanError) as caught:
            planner.plan(b"GET /v1/records/example HTTP/1.1\r\n", reads_completed=1)
        self.assertEqual(caught.exception.code, "READ_CALL_LIMIT_EXHAUSTED")
        self.assertEqual(self.harness.calls, [])

    def test_malformed_complete_head_preserves_m36_and_m35_reason_codes(self):
        raw = (
            f"GET /v1/records/{RECORD_ID} HTTP/1.1\r\n"
            f"host: {AUTHORITY}\r\n"
            "Connection: close\r\n\r\n"
        ).encode("ascii")
        with self.assertRaises(InboundHttpReadPlanError) as caught:
            self.planner.plan(raw, reads_completed=1)
        self.assertEqual(caught.exception.code, "STREAM_PROFILE_REJECTED")
        self.assertEqual(caught.exception.stream_code, "WIRE_PROFILE_REJECTED")
        self.assertEqual(caught.exception.wire_code, "NONCANONICAL_HEADER_NAME")
        self.assertEqual(self.harness.calls, [])

    def test_invalid_prefix_and_read_count_types_fail_closed(self):
        with self.assertRaises(InboundHttpReadPlanError) as bad_prefix:
            self.planner.plan(bytearray(b"x"), reads_completed=0)
        self.assertEqual(bad_prefix.exception.code, "INVALID_READ_PREFIX")
        for value in (-1, True, 1.0, "1"):
            with self.subTest(value=value):
                with self.assertRaises(InboundHttpReadPlanError) as bad_count:
                    self.planner.plan(b"", reads_completed=value)
                self.assertEqual(bad_count.exception.code, "INVALID_READ_COUNT")

    def test_m37_limits_cannot_exceed_m36_chunk_limits(self):
        stream = BoundedInboundHttpStreamAssembler(
            wire_adapter=self.wire,
            limits=InboundHttpStreamLimits(max_chunks=2, max_chunk_bytes=128),
        )
        with self.assertRaises(ValueError):
            BoundedInboundHttpReadPlanner(
                stream_assembler=stream,
                limits=InboundHttpReadLimits(max_read_calls=3, max_read_bytes=128),
            )
        with self.assertRaises(ValueError):
            BoundedInboundHttpReadPlanner(
                stream_assembler=stream,
                limits=InboundHttpReadLimits(max_read_calls=2, max_read_bytes=129),
            )


if __name__ == "__main__":
    unittest.main()
