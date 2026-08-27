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
)
from marketplace.runtime.inbound_http_read_transition import (
    BoundedInboundHttpReadTransitioner,
    InboundHttpReadTransitionError,
)
from marketplace.runtime.inbound_http_stream import BoundedInboundHttpStreamAssembler
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


class InboundHttpReadTransitionTests(unittest.TestCase):
    def setUp(self):
        self.harness = _ApplicationHarness()
        self.wire = BoundedInboundHttpWireAdapter(
            application_adapter=self.harness.adapter,
            authority=AUTHORITY,
        )
        self.stream = BoundedInboundHttpStreamAssembler(wire_adapter=self.wire)
        self.planner = BoundedInboundHttpReadPlanner(stream_assembler=self.stream)
        self.transitioner = BoundedInboundHttpReadTransitioner(read_planner=self.planner)

    def test_in_budget_header_chunk_advances_state_without_disclosure(self):
        transition = self.transitioner.transition(
            b"",
            reads_completed=0,
            chunk=b"GET ",
        )
        self.assertEqual(transition.prefix, b"GET ")
        self.assertEqual(transition.reads_completed, 1)
        self.assertEqual(transition.accepted_chunk_bytes, 4)
        self.assertEqual(transition.prior_plan.action, READ_ACTION_READ)
        self.assertEqual(transition.next_plan.action, READ_ACTION_READ)
        self.assertEqual(transition.next_plan.buffered_bytes, 4)
        self.assertFalse(transition.reader_invoked)
        self.assertFalse(transition.socket_accessed)
        self.assertFalse(transition.transmitted)
        self.assertEqual(self.harness.calls, [])

    def test_exact_final_body_chunk_yields_complete_next_plan(self):
        prefix = _post_prefix(declared=5, body=b"abc")
        transition = self.transitioner.transition(
            prefix,
            reads_completed=2,
            chunk=b"de",
        )
        self.assertEqual(transition.prefix, prefix + b"de")
        self.assertEqual(transition.accepted_chunk_bytes, 2)
        self.assertEqual(transition.reads_completed, 3)
        self.assertEqual(transition.prior_plan.next_read_bytes, 2)
        self.assertEqual(transition.next_plan.action, READ_ACTION_COMPLETE)
        self.assertEqual(transition.next_plan.next_read_bytes, 0)
        self.assertTrue(transition.next_plan.request_complete)
        self.assertEqual(self.harness.calls, [])

    def test_chunk_exactly_at_current_budget_is_accepted(self):
        planner = BoundedInboundHttpReadPlanner(
            stream_assembler=self.stream,
            limits=InboundHttpReadLimits(max_read_calls=8, max_read_bytes=4),
        )
        transitioner = BoundedInboundHttpReadTransitioner(read_planner=planner)
        transition = transitioner.transition(b"", reads_completed=0, chunk=b"GET ")
        self.assertEqual(transition.prior_plan.next_read_bytes, 4)
        self.assertEqual(transition.accepted_chunk_bytes, 4)

    def test_oversized_chunk_is_rejected(self):
        planner = BoundedInboundHttpReadPlanner(
            stream_assembler=self.stream,
            limits=InboundHttpReadLimits(max_read_calls=8, max_read_bytes=4),
        )
        transitioner = BoundedInboundHttpReadTransitioner(read_planner=planner)
        with self.assertRaises(InboundHttpReadTransitionError) as caught:
            transitioner.transition(b"", reads_completed=0, chunk=b"GET /v1")
        self.assertEqual(caught.exception.code, "READ_CHUNK_EXCEEDS_PLAN")
        self.assertEqual(self.harness.calls, [])

    def test_empty_chunk_is_explicitly_rejected(self):
        with self.assertRaises(InboundHttpReadTransitionError) as caught:
            self.transitioner.transition(b"", reads_completed=0, chunk=b"")
        self.assertEqual(caught.exception.code, "EMPTY_READ_CHUNK")
        self.assertEqual(self.harness.calls, [])

    def test_chunk_after_complete_request_is_rejected(self):
        raw = _get_request_bytes(f"/v1/records/{RECORD_ID}", AUTHORITY, 443)
        with self.assertRaises(InboundHttpReadTransitionError) as caught:
            self.transitioner.transition(raw, reads_completed=1, chunk=b"x")
        self.assertEqual(caught.exception.code, "READ_AFTER_COMPLETE")
        self.assertEqual(self.harness.calls, [])

    def test_malformed_prefix_preserves_nested_reason_codes(self):
        raw = (
            f"GET /v1/records/{RECORD_ID} HTTP/1.1\r\n"
            f"host: {AUTHORITY}\r\n"
            "Connection: close\r\n\r\n"
        ).encode("ascii")
        with self.assertRaises(InboundHttpReadTransitionError) as caught:
            self.transitioner.transition(raw, reads_completed=1, chunk=b"x")
        self.assertEqual(caught.exception.code, "READ_PLAN_REJECTED")
        self.assertEqual(caught.exception.plan_code, "STREAM_PROFILE_REJECTED")
        self.assertEqual(caught.exception.stream_code, "WIRE_PROFILE_REJECTED")
        self.assertEqual(caught.exception.wire_code, "NONCANONICAL_HEADER_NAME")
        self.assertEqual(self.harness.calls, [])

    def test_invalid_prefix_chunk_and_read_count_types_fail_closed(self):
        with self.assertRaises(InboundHttpReadTransitionError) as bad_prefix:
            self.transitioner.transition(bytearray(b""), reads_completed=0, chunk=b"x")
        self.assertEqual(bad_prefix.exception.code, "INVALID_READ_PREFIX")

        with self.assertRaises(InboundHttpReadTransitionError) as bad_chunk:
            self.transitioner.transition(b"", reads_completed=0, chunk=bytearray(b"x"))
        self.assertEqual(bad_chunk.exception.code, "INVALID_READ_CHUNK")

        for value in (-1, True, 1.0, "1"):
            with self.subTest(value=value):
                with self.assertRaises(InboundHttpReadTransitionError) as bad_count:
                    self.transitioner.transition(b"", reads_completed=value, chunk=b"x")
                self.assertEqual(bad_count.exception.code, "INVALID_READ_COUNT")

    def test_last_permitted_incomplete_read_preserves_m37_exhaustion_code(self):
        planner = BoundedInboundHttpReadPlanner(
            stream_assembler=self.stream,
            limits=InboundHttpReadLimits(max_read_calls=1, max_read_bytes=4),
        )
        transitioner = BoundedInboundHttpReadTransitioner(read_planner=planner)
        with self.assertRaises(InboundHttpReadTransitionError) as caught:
            transitioner.transition(b"", reads_completed=0, chunk=b"GET ")
        self.assertEqual(caught.exception.code, "READ_PLAN_REJECTED")
        self.assertEqual(caught.exception.plan_code, "READ_CALL_LIMIT_EXHAUSTED")
        self.assertEqual(self.harness.calls, [])


if __name__ == "__main__":
    unittest.main()
