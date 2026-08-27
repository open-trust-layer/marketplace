from __future__ import annotations

import unittest

from marketplace.runtime.inbound_http import (
    BoundedInboundHttpApplicationAdapter,
    InboundHttpApplicationLimits,
)
from marketplace.runtime.inbound_http_read_invoke import (
    BoundedInboundHttpReadInvoker,
    InboundHttpReadInvocationError,
)
from marketplace.runtime.inbound_http_read_outcome import (
    BoundedInboundHttpReadOutcomeHandler,
    InboundHttpReadOutcome,
)
from marketplace.runtime.inbound_http_read_plan import BoundedInboundHttpReadPlanner
from marketplace.runtime.inbound_http_read_session import BoundedInboundHttpReadSession
from marketplace.runtime.inbound_http_read_transition import BoundedInboundHttpReadTransitioner
from marketplace.runtime.inbound_http_stream import BoundedInboundHttpStreamAssembler
from marketplace.runtime.inbound_http_wire import BoundedInboundHttpWireAdapter

AUTHORITY = "market.example"


class _NoDisclosureHarness:
    def __init__(self):
        adapter = object.__new__(BoundedInboundHttpApplicationAdapter)
        object.__setattr__(adapter, "_limits", InboundHttpApplicationLimits())
        object.__setattr__(adapter, "handle", self._handle)
        self.adapter = adapter

    def _handle(self, request):
        raise AssertionError("M41 hardening MUST NOT reach disclosure")


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
    return session, invoker


class InboundHttpReadInvokePostReaderHardeningTests(unittest.TestCase):
    def test_reader_binding_drift_after_invocation_closes_before_error(self):
        holder = {}
        calls = []

        def reader(max_bytes):
            calls.append(max_bytes)
            holder["invoker"]._accept = holder["invoker"]._progress
            return InboundHttpReadOutcome.data(b"GET ")

        session, invoker = _build(reader)
        holder["invoker"] = invoker

        with self.assertRaises(InboundHttpReadInvocationError) as caught:
            invoker.invoke_once()

        self.assertEqual(caught.exception.code, "READ_INVOCATION_BINDING_DRIFT")
        self.assertEqual(len(calls), 1)
        self.assertTrue(session.closed)
        self.assertEqual(session._prefix, b"")

    def test_reader_binding_drift_plus_exception_still_closes_without_retry(self):
        holder = {}
        calls = []

        def reader(max_bytes):
            calls.append(max_bytes)
            holder["invoker"]._reader = lambda size: InboundHttpReadOutcome.eof()
            raise RuntimeError("SECRET reader exception must never leak")

        session, invoker = _build(reader)
        holder["invoker"] = invoker

        with self.assertRaises(InboundHttpReadInvocationError) as caught:
            invoker.invoke_once()

        self.assertEqual(caught.exception.code, "READ_INVOCATION_BINDING_DRIFT")
        self.assertNotIn("SECRET", str(caught.exception))
        self.assertEqual(len(calls), 1)
        self.assertTrue(session.closed)
        self.assertEqual(session._prefix, b"")

    def test_drifted_cleanup_authority_reports_uncertain_without_substitution(self):
        holder = {}
        calls = []

        def reader(max_bytes):
            calls.append(max_bytes)
            holder["invoker"]._accept = holder["invoker"]._progress
            holder["invoker"]._close = holder["invoker"]._progress
            return InboundHttpReadOutcome.data(b"GET ")

        session, invoker = _build(reader)
        holder["invoker"] = invoker

        with self.assertRaises(InboundHttpReadInvocationError) as caught:
            invoker.invoke_once()

        self.assertEqual(caught.exception.code, "READ_INVOCATION_CLEANUP_UNCERTAIN")
        self.assertEqual(len(calls), 1)
        self.assertFalse(session.closed)
        self.assertEqual(session._prefix, b"")


if __name__ == "__main__":
    unittest.main()
