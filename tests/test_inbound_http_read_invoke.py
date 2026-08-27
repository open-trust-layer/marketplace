from __future__ import annotations

import unittest

from marketplace.runtime.inbound_http import (
    BoundedInboundHttpApplicationAdapter,
    InboundHttpApplicationLimits,
)
from marketplace.runtime.inbound_http_read_invoke import (
    READ_INVOCATION_COMPLETED,
    READ_INVOCATION_PROGRESS,
    BoundedInboundHttpReadInvoker,
    InboundHttpReadInvocationError,
)
from marketplace.runtime.inbound_http_read_outcome import (
    BoundedInboundHttpReadOutcomeHandler,
    InboundHttpReadOutcome,
)
from marketplace.runtime.inbound_http_read_plan import (
    READ_ACTION_COMPLETE,
    BoundedInboundHttpReadPlanner,
)
from marketplace.runtime.inbound_http_read_session import BoundedInboundHttpReadSession
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
        raise AssertionError("M41 read invocation MUST NOT reach disclosure")


def _build(reader):
    harness = _NoDisclosureHarness()
    wire = BoundedInboundHttpWireAdapter(
        application_adapter=harness.adapter,
        authority=AUTHORITY,
    )
    stream = BoundedInboundHttpStreamAssembler(wire_adapter=wire)
    planner = BoundedInboundHttpReadPlanner(stream_assembler=stream)
    transitioner = BoundedInboundHttpReadTransitioner(read_planner=planner)
    session = BoundedInboundHttpReadSession(read_transitioner=transitioner)
    handler = BoundedInboundHttpReadOutcomeHandler(read_session=session)
    invoker = BoundedInboundHttpReadInvoker(
        read_outcome_handler=handler,
        reader=reader,
    )
    raw = _get_request_bytes(f"/v1/records/{RECORD_ID}", AUTHORITY, 443)
    return harness, session, handler, invoker, raw


class InboundHttpReadInvokeTests(unittest.TestCase):
    def test_read_invokes_exactly_once_with_exact_current_budget(self):
        calls = []

        def reader(max_bytes):
            calls.append(max_bytes)
            return InboundHttpReadOutcome.data(b"GET ")

        harness, _, handler, invoker, _ = _build(reader)
        expected_budget = handler.progress().plan.next_read_bytes
        result = invoker.invoke_once()

        self.assertEqual(calls, [expected_budget])
        self.assertEqual(result.state, READ_INVOCATION_PROGRESS)
        self.assertTrue(result.reader_invoked)
        self.assertEqual(result.requested_bytes, expected_budget)
        self.assertEqual(result.progress.reads_completed, 1)
        self.assertEqual(result.progress.buffered_bytes, 4)
        self.assertFalse(result.socket_access_proven)
        self.assertFalse(result.network_origin_proven)
        self.assertEqual(harness.calls, [])

    def test_data_reaching_complete_never_implicitly_reads_or_transfers_twice(self):
        calls = []
        holder = {}

        def reader(max_bytes):
            calls.append(max_bytes)
            return InboundHttpReadOutcome.data(holder["raw"])

        harness, _, _, invoker, raw = _build(reader)
        holder["raw"] = raw

        first = invoker.invoke_once()
        self.assertEqual(first.state, READ_INVOCATION_PROGRESS)
        self.assertEqual(first.progress.plan.action, READ_ACTION_COMPLETE)
        self.assertEqual(len(calls), 1)
        self.assertFalse(invoker.closed)

        second = invoker.invoke_once()
        self.assertEqual(second.state, READ_INVOCATION_COMPLETED)
        self.assertFalse(second.reader_invoked)
        self.assertEqual(second.requested_bytes, 0)
        self.assertEqual(second.completed.prefix, raw)
        self.assertEqual(len(calls), 1)
        self.assertTrue(invoker.closed)
        self.assertEqual(harness.calls, [])

    def test_complete_at_entry_transfers_without_reader_call(self):
        calls = []

        def reader(max_bytes):
            calls.append(max_bytes)
            raise AssertionError("reader MUST NOT run for COMPLETE")

        _, _, handler, invoker, raw = _build(reader)
        handler.accept_outcome(InboundHttpReadOutcome.data(raw))
        result = invoker.invoke_once()
        self.assertEqual(result.state, READ_INVOCATION_COMPLETED)
        self.assertEqual(result.completed.prefix, raw)
        self.assertEqual(calls, [])
        self.assertTrue(invoker.closed)

    def test_eof_is_terminal_and_clears_session(self):
        calls = []

        def reader(max_bytes):
            calls.append(max_bytes)
            return InboundHttpReadOutcome.eof()

        _, session, _, invoker, _ = _build(reader)
        with self.assertRaises(InboundHttpReadInvocationError) as caught:
            invoker.invoke_once()
        self.assertEqual(caught.exception.code, "READ_INVOCATION_OUTCOME_REJECTED")
        self.assertEqual(caught.exception.outcome_code, "READ_EOF_BEFORE_COMPLETE")
        self.assertEqual(len(calls), 1)
        self.assertTrue(invoker.closed)
        self.assertEqual(session._prefix, b"")

    def test_explicit_failure_is_terminal_and_clears_session(self):
        def reader(max_bytes):
            return InboundHttpReadOutcome.failure()

        _, session, _, invoker, _ = _build(reader)
        with self.assertRaises(InboundHttpReadInvocationError) as caught:
            invoker.invoke_once()
        self.assertEqual(caught.exception.code, "READ_INVOCATION_OUTCOME_REJECTED")
        self.assertEqual(caught.exception.outcome_code, "READ_FAILURE_BEFORE_COMPLETE")
        self.assertTrue(invoker.closed)
        self.assertEqual(session._prefix, b"")

    def test_reader_exception_becomes_generic_terminal_failure_without_text(self):
        calls = []

        def reader(max_bytes):
            calls.append(max_bytes)
            raise RuntimeError("SECRET remote diagnostic socket credential")

        _, session, _, invoker, _ = _build(reader)
        with self.assertRaises(InboundHttpReadInvocationError) as caught:
            invoker.invoke_once()
        self.assertEqual(caught.exception.code, "READ_INVOCATION_READER_FAILURE")
        self.assertEqual(caught.exception.outcome_code, "READ_FAILURE_BEFORE_COMPLETE")
        self.assertNotIn("SECRET", str(caught.exception))
        self.assertNotIn("credential", str(caught.exception).lower())
        self.assertEqual(len(calls), 1)
        self.assertTrue(invoker.closed)
        self.assertEqual(session._prefix, b"")

    def test_non_outcome_reader_result_fails_closed_without_retry(self):
        for value in (b"GET ", None, {"kind": "DATA"}):
            with self.subTest(value=value):
                calls = []

                def reader(max_bytes, result=value):
                    calls.append(max_bytes)
                    return result

                _, session, _, invoker, _ = _build(reader)
                with self.assertRaises(InboundHttpReadInvocationError) as caught:
                    invoker.invoke_once()
                self.assertEqual(caught.exception.code, "INVALID_READER_RESULT")
                self.assertEqual(len(calls), 1)
                self.assertTrue(invoker.closed)
                self.assertEqual(session._prefix, b"")

    def test_oversized_consumed_data_preserves_lower_failure_and_is_terminal(self):
        def reader(max_bytes):
            return InboundHttpReadOutcome.data(b"x" * (max_bytes + 1))

        _, session, _, invoker, _ = _build(reader)
        with self.assertRaises(InboundHttpReadInvocationError) as caught:
            invoker.invoke_once()
        self.assertEqual(caught.exception.code, "READ_INVOCATION_OUTCOME_REJECTED")
        self.assertEqual(caught.exception.outcome_code, "READ_SESSION_REJECTED")
        self.assertTrue(invoker.closed)
        self.assertEqual(session._prefix, b"")

    def test_close_is_idempotent_and_blocks_future_invocation(self):
        def reader(max_bytes):
            raise AssertionError("closed invoker MUST NOT call reader")

        _, _, _, invoker, _ = _build(reader)
        invoker.close()
        invoker.close()
        self.assertTrue(invoker.closed)
        with self.assertRaises(InboundHttpReadInvocationError) as caught:
            invoker.invoke_once()
        self.assertEqual(caught.exception.code, "READ_INVOCATION_SESSION_CLOSED")


if __name__ == "__main__":
    unittest.main()
