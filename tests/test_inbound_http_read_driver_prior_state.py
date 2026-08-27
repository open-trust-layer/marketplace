from __future__ import annotations

import unittest

from marketplace.runtime.inbound_http import (
    BoundedInboundHttpApplicationAdapter,
    InboundHttpApplicationLimits,
)
from marketplace.runtime.inbound_http_read_driver import BoundedInboundHttpReadDriver
from marketplace.runtime.inbound_http_read_invoke import BoundedInboundHttpReadInvoker
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
        adapter = object.__new__(BoundedInboundHttpApplicationAdapter)
        object.__setattr__(adapter, "_limits", InboundHttpApplicationLimits())
        object.__setattr__(adapter, "handle", self._handle)
        self.adapter = adapter

    def _handle(self, request):
        raise AssertionError("M42 prior-state test MUST NOT reach disclosure")


def _build():
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
    raw = _get_request_bytes(f"/v1/records/{RECORD_ID}", AUTHORITY, 443)
    return session, handler, raw


class InboundHttpReadDriverPriorStateTests(unittest.TestCase):
    def test_completed_prior_state_is_cumulative_accounting_not_m42_reader_calls(self):
        session, handler, raw = _build()
        first = handler.accept_outcome(InboundHttpReadOutcome.data(raw[:4]))
        self.assertEqual(first.reads_completed, 1)
        second = handler.accept_outcome(InboundHttpReadOutcome.data(raw[4:]))
        self.assertEqual(second.reads_completed, 2)
        self.assertEqual(second.plan.action, READ_ACTION_COMPLETE)

        reader_calls = []

        def reader(max_bytes):
            reader_calls.append(max_bytes)
            raise AssertionError("M41 reader MUST NOT run for pre-completed M39 state")

        invoker = BoundedInboundHttpReadInvoker(
            read_outcome_handler=handler,
            reader=reader,
        )
        clock_values = iter((0.0, 0.0, 0.1))
        driver = BoundedInboundHttpReadDriver(
            read_invoker=invoker,
            clock=lambda: next(clock_values),
        )

        result = driver.run_to_completion()

        self.assertEqual(result.completed.prefix, raw)
        self.assertEqual(result.driver_steps, 1)
        self.assertEqual(result.reader_invocations, 0)
        self.assertEqual(result.reads_completed, 2)
        self.assertEqual(result.completed.reads_completed, 2)
        self.assertGreater(result.reads_completed, result.driver_steps)
        self.assertEqual(reader_calls, [])
        self.assertTrue(driver.closed)
        self.assertTrue(session.closed)
        self.assertEqual(session._prefix, b"")


if __name__ == "__main__":
    unittest.main()
