from __future__ import annotations

import inspect
import unittest

from marketplace.runtime.inbound_http import (
    BoundedInboundHttpApplicationAdapter,
    InboundHttpApplicationLimits,
)
from marketplace.runtime.inbound_http_read_plan import (
    READ_ACTION_COMPLETE,
    READ_ACTION_READ,
    BoundedInboundHttpReadPlanner,
    InboundHttpReadLimits,
)
from marketplace.runtime.inbound_http_read_session import (
    BoundedInboundHttpReadSession,
    InboundHttpReadSessionError,
)
from marketplace.runtime.inbound_http_read_transition import BoundedInboundHttpReadTransitioner
from marketplace.runtime.inbound_http_stream import BoundedInboundHttpStreamAssembler
from marketplace.runtime.inbound_http_wire import BoundedInboundHttpWireAdapter
from marketplace.runtime.record_retrieval import _get_request_bytes

AUTHORITY = "market.example"
RECORD_ID = "r1_qcU6rT-ADJiC75Bg9w7qLSvauhY6zcEmy1dk-LrRlZc"


class _NoDisclosureHarness:
    def __init__(self):
        self.calls = []
        adapter = object.__new__(BoundedInboundHttpApplicationAdapter)
        object.__setattr__(adapter, "_limits", InboundHttpApplicationLimits())
        object.__setattr__(adapter, "handle", self._handle)
        self.adapter = adapter

    def _handle(self, request):
        self.calls.append(request)
        raise AssertionError("M39 transport-free session MUST NOT reach application disclosure")


class InboundHttpReadSessionTests(unittest.TestCase):
    def setUp(self):
        self.harness = _NoDisclosureHarness()
        self.wire = BoundedInboundHttpWireAdapter(
            application_adapter=self.harness.adapter,
            authority=AUTHORITY,
        )
        self.stream = BoundedInboundHttpStreamAssembler(wire_adapter=self.wire)
        self.planner = BoundedInboundHttpReadPlanner(stream_assembler=self.stream)
        self.transitioner = BoundedInboundHttpReadTransitioner(read_planner=self.planner)
        self.session = BoundedInboundHttpReadSession(read_transitioner=self.transitioner)
        self.raw = _get_request_bytes(f"/v1/records/{RECORD_ID}", AUTHORITY, 443)

    def test_session_starts_at_canonical_empty_zero_state(self):
        progress = self.session.progress()
        self.assertEqual(progress.buffered_bytes, 0)
        self.assertEqual(progress.reads_completed, 0)
        self.assertEqual(progress.last_accepted_chunk_bytes, 0)
        self.assertEqual(progress.plan.action, READ_ACTION_READ)
        self.assertFalse(self.session.closed)
        self.assertEqual(self.harness.calls, [])

    def test_accept_api_has_no_external_read_count_or_prefix_reset_parameter(self):
        parameters = tuple(inspect.signature(BoundedInboundHttpReadSession.accept_chunk).parameters)
        self.assertEqual(parameters, ("self", "chunk"))

    def test_sequential_chunks_advance_owned_state_exactly_once(self):
        first = self.session.accept_chunk(self.raw[:4])
        self.assertEqual(first.reads_completed, 1)
        self.assertEqual(first.buffered_bytes, 4)
        self.assertEqual(first.last_accepted_chunk_bytes, 4)
        self.assertEqual(first.plan.action, READ_ACTION_READ)

        second = self.session.accept_chunk(self.raw[4:])
        self.assertEqual(second.reads_completed, 2)
        self.assertEqual(second.buffered_bytes, len(self.raw))
        self.assertEqual(second.last_accepted_chunk_bytes, len(self.raw) - 4)
        self.assertEqual(second.plan.action, READ_ACTION_COMPLETE)
        self.assertEqual(self.harness.calls, [])

    def test_rejected_chunk_does_not_mutate_session_state(self):
        planner = BoundedInboundHttpReadPlanner(
            stream_assembler=self.stream,
            limits=InboundHttpReadLimits(max_read_calls=8, max_read_bytes=4),
        )
        transitioner = BoundedInboundHttpReadTransitioner(read_planner=planner)
        session = BoundedInboundHttpReadSession(read_transitioner=transitioner)
        before = session.progress()

        with self.assertRaises(InboundHttpReadSessionError) as caught:
            session.accept_chunk(b"12345")
        self.assertEqual(caught.exception.code, "READ_TRANSITION_REJECTED")
        self.assertEqual(caught.exception.transition_code, "READ_CHUNK_EXCEEDS_PLAN")

        after = session.progress()
        self.assertEqual(after.buffered_bytes, before.buffered_bytes)
        self.assertEqual(after.reads_completed, before.reads_completed)
        self.assertEqual(after.plan.integrity_snapshot, before.plan.integrity_snapshot)
        self.assertEqual(self.harness.calls, [])

    def test_complete_request_transfers_once_and_clears_closes_session(self):
        progress = self.session.accept_chunk(self.raw)
        self.assertEqual(progress.plan.action, READ_ACTION_COMPLETE)
        self.assertEqual(progress.reads_completed, 1)

        completed = self.session.take_completed()
        self.assertEqual(completed.prefix, self.raw)
        self.assertEqual(completed.reads_completed, 1)
        self.assertEqual(completed.plan.action, READ_ACTION_COMPLETE)
        self.assertTrue(completed.session_closed)
        self.assertTrue(self.session.closed)
        self.assertEqual(self.session._prefix, b"")

        with self.assertRaises(InboundHttpReadSessionError) as caught:
            self.session.take_completed()
        self.assertEqual(caught.exception.code, "READ_SESSION_CLOSED")
        self.assertEqual(self.harness.calls, [])

    def test_incomplete_completion_handoff_fails_without_closing(self):
        self.session.accept_chunk(b"GET ")
        with self.assertRaises(InboundHttpReadSessionError) as caught:
            self.session.take_completed()
        self.assertEqual(caught.exception.code, "READ_SESSION_INCOMPLETE")
        self.assertFalse(self.session.closed)
        self.assertEqual(self.session.progress().reads_completed, 1)

    def test_invalid_or_empty_chunk_fails_without_state_change(self):
        before = self.session.progress()
        for chunk, code in ((b"", "EMPTY_READ_CHUNK"), (bytearray(b"x"), "INVALID_READ_CHUNK")):
            with self.subTest(chunk=chunk):
                with self.assertRaises(InboundHttpReadSessionError) as caught:
                    self.session.accept_chunk(chunk)
                self.assertEqual(caught.exception.code, code)
        after = self.session.progress()
        self.assertEqual(after.buffered_bytes, before.buffered_bytes)
        self.assertEqual(after.reads_completed, before.reads_completed)

    def test_malformed_completed_wire_shape_preserves_nested_reason_codes(self):
        raw = (
            f"GET /v1/records/{RECORD_ID} HTTP/1.1\r\n"
            f"host: {AUTHORITY}\r\n"
            "Connection: close\r\n\r\n"
        ).encode("ascii")
        with self.assertRaises(InboundHttpReadSessionError) as caught:
            self.session.accept_chunk(raw)
        self.assertEqual(caught.exception.code, "READ_TRANSITION_REJECTED")
        self.assertEqual(caught.exception.transition_code, "READ_PLAN_REJECTED")
        self.assertEqual(caught.exception.plan_code, "STREAM_PROFILE_REJECTED")
        self.assertEqual(caught.exception.stream_code, "WIRE_PROFILE_REJECTED")
        self.assertEqual(caught.exception.wire_code, "NONCANONICAL_HEADER_NAME")
        self.assertEqual(self.session.progress().reads_completed, 0)

    def test_close_is_idempotent_clears_prefix_and_blocks_reuse(self):
        self.session.accept_chunk(b"GET ")
        self.assertNotEqual(self.session._prefix, b"")
        self.session.close()
        self.session.close()
        self.assertTrue(self.session.closed)
        self.assertEqual(self.session._prefix, b"")

        for operation in (
            self.session.progress,
            lambda: self.session.accept_chunk(b"x"),
            self.session.take_completed,
        ):
            with self.assertRaises(InboundHttpReadSessionError) as caught:
                operation()
            self.assertEqual(caught.exception.code, "READ_SESSION_CLOSED")


if __name__ == "__main__":
    unittest.main()
