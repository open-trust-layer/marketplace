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
from marketplace.runtime.inbound_http_read_plan import BoundedInboundHttpReadPlanner
from marketplace.runtime.inbound_http_read_session import BoundedInboundHttpReadSession
from marketplace.runtime.inbound_http_read_transition import BoundedInboundHttpReadTransitioner
from marketplace.runtime.inbound_http_response_prepare import (
    BoundedInboundHttpResponsePreparer,
    InboundHttpResponsePreparationError,
)
from marketplace.runtime.inbound_http_stream import BoundedInboundHttpStreamAssembler
from marketplace.runtime.inbound_http_wire import BoundedInboundHttpWireAdapter

AUTHORITY = "market.example"


class _NoCallApplication:
    def __init__(self):
        self.calls = 0
        adapter = object.__new__(BoundedInboundHttpApplicationAdapter)
        object.__setattr__(adapter, "_limits", InboundHttpApplicationLimits())
        object.__setattr__(adapter, "handle", self._handle)
        self.adapter = adapter

    def _handle(self, request):
        self.calls += 1
        raise AssertionError("pre-run cleanup tests MUST NOT reach M34")


def _partial_chain():
    reader_calls = []

    def reader(max_bytes):
        reader_calls.append(max_bytes)
        return InboundHttpReadOutcome.eof()

    application = _NoCallApplication()
    wire = BoundedInboundHttpWireAdapter(
        application_adapter=application.adapter,
        authority=AUTHORITY,
    )
    stream = BoundedInboundHttpStreamAssembler(wire_adapter=wire)
    planner = BoundedInboundHttpReadPlanner(stream_assembler=stream)
    transitioner = BoundedInboundHttpReadTransitioner(read_planner=planner)
    session = BoundedInboundHttpReadSession(read_transitioner=transitioner)
    session.accept_chunk(b"GET ")
    handler = BoundedInboundHttpReadOutcomeHandler(read_session=session)
    invoker = BoundedInboundHttpReadInvoker(
        read_outcome_handler=handler,
        reader=reader,
    )
    driver = BoundedInboundHttpReadDriver(
        read_invoker=invoker,
        clock=lambda: 0.0,
    )
    return application, wire, session, driver, reader_calls


class InboundHttpResponsePreparationCleanupTests(unittest.TestCase):
    def test_pre_run_m35_configuration_drift_clears_partial_request_state(self):
        application, wire, session, driver, reader_calls = _partial_chain()
        preparer = BoundedInboundHttpResponsePreparer(read_driver=driver)
        self.assertEqual(getattr(session, "_prefix"), b"GET ")
        self.assertFalse(getattr(session, "_closed"))

        object.__setattr__(wire, "_authority", "other.example")

        with self.assertRaises(InboundHttpResponsePreparationError) as caught:
            preparer.prepare()

        self.assertEqual(
            caught.exception.code,
            "RESPONSE_PREPARATION_CONFIGURATION_DRIFT",
        )
        self.assertTrue(preparer.used)
        self.assertTrue(getattr(session, "_closed"))
        self.assertEqual(getattr(session, "_prefix"), b"")
        self.assertEqual(reader_calls, [])
        self.assertEqual(application.calls, 0)

    def test_explicit_close_clears_partial_state_even_after_downstream_drift(self):
        application, wire, session, driver, reader_calls = _partial_chain()
        preparer = BoundedInboundHttpResponsePreparer(read_driver=driver)
        object.__setattr__(wire, "_authority", "other.example")

        preparer.close()
        preparer.close()

        self.assertTrue(preparer.used)
        self.assertTrue(getattr(session, "_closed"))
        self.assertEqual(getattr(session, "_prefix"), b"")
        self.assertEqual(reader_calls, [])
        self.assertEqual(application.calls, 0)

    def test_cleanup_binding_drift_reports_uncertain_without_claiming_clear(self):
        application, _, session, driver, reader_calls = _partial_chain()
        preparer = BoundedInboundHttpResponsePreparer(read_driver=driver)
        preparer._session_close = lambda: None
        preparer._prepare = lambda _: None

        with self.assertRaises(InboundHttpResponsePreparationError) as caught:
            preparer.prepare()

        self.assertEqual(
            caught.exception.code,
            "RESPONSE_PREPARATION_CLEANUP_UNCERTAIN",
        )
        self.assertTrue(preparer.used)
        self.assertEqual(getattr(session, "_prefix"), b"GET ")
        self.assertFalse(getattr(session, "_closed"))
        self.assertEqual(reader_calls, [])
        self.assertEqual(application.calls, 0)


if __name__ == "__main__":
    unittest.main()
