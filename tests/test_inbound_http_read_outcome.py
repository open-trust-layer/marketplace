from __future__ import annotations

import inspect
import unittest

from marketplace.runtime.inbound_http import (
    BoundedInboundHttpApplicationAdapter,
    InboundHttpApplicationLimits,
)
from marketplace.runtime.inbound_http_read_outcome import (
    READ_OUTCOME_DATA,
    READ_OUTCOME_EOF,
    READ_OUTCOME_FAILURE,
    BoundedInboundHttpReadOutcomeHandler,
    InboundHttpReadOutcome,
    InboundHttpReadOutcomeError,
)
from marketplace.runtime.inbound_http_read_plan import READ_ACTION_COMPLETE, READ_ACTION_READ
from marketplace.runtime.inbound_http_read_session import BoundedInboundHttpReadSession
from marketplace.runtime.inbound_http_read_transition import BoundedInboundHttpReadTransitioner
from marketplace.runtime.inbound_http_stream import BoundedInboundHttpStreamAssembler
from marketplace.runtime.inbound_http_read_plan import BoundedInboundHttpReadPlanner
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
        raise AssertionError("M40 transport-free outcome handling MUST NOT reach disclosure")


class InboundHttpReadOutcomeTests(unittest.TestCase):
    def setUp(self):
        self.harness = _NoDisclosureHarness()
        wire = BoundedInboundHttpWireAdapter(
            application_adapter=self.harness.adapter,
            authority=AUTHORITY,
        )
        stream = BoundedInboundHttpStreamAssembler(wire_adapter=wire)
        planner = BoundedInboundHttpReadPlanner(stream_assembler=stream)
        transitioner = BoundedInboundHttpReadTransitioner(read_planner=planner)
        self.session = BoundedInboundHttpReadSession(read_transitioner=transitioner)
        self.handler = BoundedInboundHttpReadOutcomeHandler(read_session=self.session)
        self.raw = _get_request_bytes(f"/v1/records/{RECORD_ID}", AUTHORITY, 443)

    def test_canonical_outcome_factories_are_exact_and_transport_free(self):
        data = InboundHttpReadOutcome.data(b"GET ")
        eof = InboundHttpReadOutcome.eof()
        failure = InboundHttpReadOutcome.failure()

        self.assertEqual(data.kind, READ_OUTCOME_DATA)
        self.assertEqual(data.chunk, b"GET ")
        self.assertEqual(eof.kind, READ_OUTCOME_EOF)
        self.assertEqual(eof.chunk, b"")
        self.assertEqual(failure.kind, READ_OUTCOME_FAILURE)
        self.assertEqual(failure.chunk, b"")
        for outcome in (data, eof, failure):
            self.assertFalse(outcome.reader_invoked)
            self.assertFalse(outcome.socket_accessed)
            self.assertFalse(outcome.tls_terminated)
            self.assertFalse(outcome.transmitted)
            self.assertFalse(outcome.request_authenticated)
            self.assertFalse(outcome.peer_identity_proven)
            self.assertFalse(outcome.establishes_marketplace_truth)
            self.assertFalse(outcome.establishes_trust)
            self.assertFalse(outcome.establishes_authorization)
            self.assertFalse(outcome.authorizes_protected_side_effects)

    def test_invalid_outcome_shapes_fail_before_session_change(self):
        before = self.handler.progress()
        invalid = (
            lambda: InboundHttpReadOutcome(kind="OTHER"),
            lambda: InboundHttpReadOutcome(kind=READ_OUTCOME_DATA),
            lambda: InboundHttpReadOutcome(kind=READ_OUTCOME_DATA, chunk=bytearray(b"x")),
            lambda: InboundHttpReadOutcome(kind=READ_OUTCOME_EOF, chunk=b"x"),
            lambda: InboundHttpReadOutcome(kind=READ_OUTCOME_FAILURE, chunk=b"x"),
        )
        for make in invalid:
            with self.subTest(make=make):
                with self.assertRaises((TypeError, ValueError)):
                    make()
        after = self.handler.progress()
        self.assertEqual(after.plan.integrity_snapshot, before.plan.integrity_snapshot)
        self.assertFalse(self.handler.closed)

    def test_data_outcome_advances_m39_exactly_once(self):
        first = self.handler.accept_outcome(InboundHttpReadOutcome.data(self.raw[:4]))
        self.assertEqual(first.reads_completed, 1)
        self.assertEqual(first.buffered_bytes, 4)
        self.assertEqual(first.last_accepted_chunk_bytes, 4)
        self.assertEqual(first.plan.action, READ_ACTION_READ)

        second = self.handler.accept_outcome(InboundHttpReadOutcome.data(self.raw[4:]))
        self.assertEqual(second.reads_completed, 2)
        self.assertEqual(second.buffered_bytes, len(self.raw))
        self.assertEqual(second.last_accepted_chunk_bytes, len(self.raw) - 4)
        self.assertEqual(second.plan.action, READ_ACTION_COMPLETE)
        self.assertFalse(self.handler.closed)
        self.assertEqual(self.harness.calls, [])

    def test_eof_before_complete_closes_and_clears_partial_session(self):
        self.handler.accept_outcome(InboundHttpReadOutcome.data(b"GET "))
        self.assertNotEqual(self.session._prefix, b"")

        with self.assertRaises(InboundHttpReadOutcomeError) as caught:
            self.handler.accept_outcome(InboundHttpReadOutcome.eof())
        self.assertEqual(caught.exception.code, "READ_EOF_BEFORE_COMPLETE")
        self.assertTrue(self.handler.closed)
        self.assertTrue(self.session.closed)
        self.assertEqual(self.session._prefix, b"")
        self.assertEqual(self.harness.calls, [])

    def test_failure_before_complete_is_generic_and_clears_partial_session(self):
        self.handler.accept_outcome(InboundHttpReadOutcome.data(b"GET "))
        self.assertNotEqual(self.session._prefix, b"")
        parameters = tuple(inspect.signature(InboundHttpReadOutcome.failure).parameters)
        self.assertEqual(parameters, ())

        with self.assertRaises(InboundHttpReadOutcomeError) as caught:
            self.handler.accept_outcome(InboundHttpReadOutcome.failure())
        self.assertEqual(caught.exception.code, "READ_FAILURE_BEFORE_COMPLETE")
        self.assertNotIn("socket", str(caught.exception).lower())
        self.assertTrue(self.handler.closed)
        self.assertEqual(self.session._prefix, b"")
        self.assertEqual(self.harness.calls, [])

    def test_every_outcome_after_complete_is_rejected_and_clears(self):
        for outcome in (
            InboundHttpReadOutcome.data(b"x"),
            InboundHttpReadOutcome.eof(),
            InboundHttpReadOutcome.failure(),
        ):
            with self.subTest(kind=outcome.kind):
                self.setUp()
                progress = self.handler.accept_outcome(InboundHttpReadOutcome.data(self.raw))
                self.assertEqual(progress.plan.action, READ_ACTION_COMPLETE)
                self.assertNotEqual(self.session._prefix, b"")
                with self.assertRaises(InboundHttpReadOutcomeError) as caught:
                    self.handler.accept_outcome(outcome)
                self.assertEqual(caught.exception.code, "READ_OUTCOME_AFTER_COMPLETE")
                self.assertTrue(self.handler.closed)
                self.assertEqual(self.session._prefix, b"")
                self.assertEqual(self.harness.calls, [])

    def test_completion_handoff_is_exact_m39_one_shot(self):
        progress = self.handler.accept_outcome(InboundHttpReadOutcome.data(self.raw))
        self.assertEqual(progress.plan.action, READ_ACTION_COMPLETE)

        completed = self.handler.take_completed()
        self.assertEqual(completed.prefix, self.raw)
        self.assertEqual(completed.reads_completed, 1)
        self.assertEqual(completed.plan.action, READ_ACTION_COMPLETE)
        self.assertTrue(completed.session_closed)
        self.assertTrue(self.handler.closed)
        self.assertEqual(self.session._prefix, b"")

        with self.assertRaises(InboundHttpReadOutcomeError) as caught:
            self.handler.take_completed()
        self.assertEqual(caught.exception.code, "READ_OUTCOME_SESSION_CLOSED")
        self.assertEqual(self.harness.calls, [])

    def test_incomplete_completion_preserves_m39_reason_and_keeps_session_open(self):
        self.handler.accept_outcome(InboundHttpReadOutcome.data(b"GET "))
        with self.assertRaises(InboundHttpReadOutcomeError) as caught:
            self.handler.take_completed()
        self.assertEqual(caught.exception.code, "READ_SESSION_REJECTED")
        self.assertEqual(caught.exception.session_code, "READ_SESSION_INCOMPLETE")
        self.assertFalse(self.handler.closed)
        self.assertEqual(self.handler.progress().reads_completed, 1)

    def test_rejected_consumed_data_preserves_nested_codes_and_closes_session(self):
        malformed = (
            f"GET /v1/records/{RECORD_ID} HTTP/1.1\r\n"
            f"host: {AUTHORITY}\r\n"
            "Connection: close\r\n\r\n"
        ).encode("ascii")
        with self.assertRaises(InboundHttpReadOutcomeError) as caught:
            self.handler.accept_outcome(InboundHttpReadOutcome.data(malformed))
        self.assertEqual(caught.exception.code, "READ_SESSION_REJECTED")
        self.assertEqual(caught.exception.session_code, "READ_TRANSITION_REJECTED")
        self.assertEqual(caught.exception.transition_code, "READ_PLAN_REJECTED")
        self.assertEqual(caught.exception.plan_code, "STREAM_PROFILE_REJECTED")
        self.assertEqual(caught.exception.stream_code, "WIRE_PROFILE_REJECTED")
        self.assertEqual(caught.exception.wire_code, "NONCANONICAL_HEADER_NAME")
        self.assertTrue(self.handler.closed)
        self.assertEqual(self.session._prefix, b"")
        with self.assertRaises(InboundHttpReadOutcomeError) as after:
            self.handler.progress()
        self.assertEqual(after.exception.code, "READ_OUTCOME_SESSION_CLOSED")

    def test_close_is_idempotent_and_blocks_further_outcomes(self):
        self.handler.accept_outcome(InboundHttpReadOutcome.data(b"GET "))
        self.handler.close()
        self.handler.close()
        self.assertTrue(self.handler.closed)
        self.assertEqual(self.session._prefix, b"")
        for operation in (
            self.handler.progress,
            lambda: self.handler.accept_outcome(InboundHttpReadOutcome.data(b"x")),
            self.handler.take_completed,
        ):
            with self.assertRaises(InboundHttpReadOutcomeError) as caught:
                operation()
            self.assertEqual(caught.exception.code, "READ_OUTCOME_SESSION_CLOSED")


if __name__ == "__main__":
    unittest.main()
