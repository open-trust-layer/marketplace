from __future__ import annotations

import unittest

from marketplace.runtime.inbound_http import (
    BoundedInboundHttpApplicationAdapter,
    InboundHttpApplicationLimits,
)
from marketplace.runtime.inbound_http_read_outcome import (
    BoundedInboundHttpReadOutcomeHandler,
    InboundHttpReadOutcome,
    InboundHttpReadOutcomeError,
)
from marketplace.runtime.inbound_http_read_plan import BoundedInboundHttpReadPlanner
from marketplace.runtime.inbound_http_read_session import BoundedInboundHttpReadSession
from marketplace.runtime.inbound_http_read_transition import BoundedInboundHttpReadTransitioner
from marketplace.runtime.inbound_http_stream import BoundedInboundHttpStreamAssembler
from marketplace.runtime.inbound_http_wire import BoundedInboundHttpWireAdapter

AUTHORITY = "market.example"


def _build():
    adapter = object.__new__(BoundedInboundHttpApplicationAdapter)
    object.__setattr__(adapter, "_limits", InboundHttpApplicationLimits())
    object.__setattr__(
        adapter,
        "handle",
        lambda request: (_ for _ in ()).throw(
            AssertionError("M40 security review path MUST NOT reach disclosure")
        ),
    )
    wire = BoundedInboundHttpWireAdapter(application_adapter=adapter, authority=AUTHORITY)
    stream = BoundedInboundHttpStreamAssembler(wire_adapter=wire)
    planner = BoundedInboundHttpReadPlanner(stream_assembler=stream)
    transitioner = BoundedInboundHttpReadTransitioner(read_planner=planner)
    session = BoundedInboundHttpReadSession(read_transitioner=transitioner)
    return session, BoundedInboundHttpReadOutcomeHandler(read_session=session)


class InboundHttpReadOutcomeSecurityReviewTests(unittest.TestCase):
    def test_coherent_private_function_and_bound_rebinding_fails_binding_witness(self):
        session, handler = _build()
        handler._accept_function = handler._progress_function
        handler._accept = handler._progress

        with self.assertRaises(InboundHttpReadOutcomeError) as caught:
            handler.accept_outcome(InboundHttpReadOutcome.data(b"GET "))
        self.assertEqual(caught.exception.code, "READ_OUTCOME_BINDING_DRIFT")
        self.assertFalse(session.closed)
        self.assertEqual(session._prefix, b"")
        self.assertEqual(session._reads_completed, 0)

    def test_rejected_already_returned_data_is_terminal_not_retryable(self):
        session, handler = _build()
        oversized = b"x" * (handler.progress().plan.next_read_bytes + 1)

        with self.assertRaises(InboundHttpReadOutcomeError) as caught:
            handler.accept_outcome(InboundHttpReadOutcome.data(oversized))
        self.assertEqual(caught.exception.code, "READ_SESSION_REJECTED")
        self.assertEqual(caught.exception.session_code, "READ_TRANSITION_REJECTED")
        self.assertEqual(caught.exception.transition_code, "READ_CHUNK_EXCEEDS_PLAN")
        self.assertTrue(handler.closed)
        self.assertTrue(session.closed)
        self.assertEqual(session._prefix, b"")

        with self.assertRaises(InboundHttpReadOutcomeError) as retry:
            handler.accept_outcome(InboundHttpReadOutcome.data(b"GET "))
        self.assertEqual(retry.exception.code, "READ_OUTCOME_SESSION_CLOSED")


if __name__ == "__main__":
    unittest.main()
