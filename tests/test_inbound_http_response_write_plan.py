from __future__ import annotations

import ast
import inspect
import unittest
from dataclasses import replace

import marketplace.runtime.inbound_http_response_write_plan as m44
from marketplace.runtime.inbound_http import (
    ROUTE_IMMUTABLE_RECORD,
    BoundedInboundHttpApplicationAdapter,
    InboundHttpApplicationLimits,
    PreparedInboundHttpResponse,
)
from marketplace.runtime.inbound_http_read_driver import BoundedInboundHttpReadDriver
from marketplace.runtime.inbound_http_read_invoke import BoundedInboundHttpReadInvoker
from marketplace.runtime.inbound_http_read_outcome import BoundedInboundHttpReadOutcomeHandler, InboundHttpReadOutcome
from marketplace.runtime.inbound_http_read_plan import BoundedInboundHttpReadPlanner, InboundHttpReadLimits
from marketplace.runtime.inbound_http_read_session import BoundedInboundHttpReadSession
from marketplace.runtime.inbound_http_read_transition import BoundedInboundHttpReadTransitioner
from marketplace.runtime.inbound_http_response_prepare import BoundedInboundHttpResponsePreparer
from marketplace.runtime.inbound_http_response_write_plan import (
    WRITE_ACTION_COMPLETE,
    WRITE_ACTION_WRITE,
    BoundedInboundHttpResponseWritePlanner,
    InboundHttpResponseWriteLimits,
    InboundHttpResponseWritePlanError,
)
from marketplace.runtime.inbound_http_stream import BoundedInboundHttpStreamAssembler
from marketplace.runtime.inbound_http_wire import BoundedInboundHttpWireAdapter
from marketplace.runtime.inbound_record import INBOUND_RECORD_RETRIEVAL_OPERATION
from marketplace.runtime.record_retrieval import _get_request_bytes

AUTHORITY = "market.example"
RECORD_ID = "r1_qcU6rT-ADJiC75Bg9w7qLSvauhY6zcEmy1dk-LrRlZc"


class _ApplicationHarness:
    def __init__(self):
        adapter = object.__new__(BoundedInboundHttpApplicationAdapter)
        object.__setattr__(adapter, "_limits", InboundHttpApplicationLimits())
        object.__setattr__(adapter, "handle", self._handle)
        self.adapter = adapter

    def _handle(self, request):
        body = b'{"record":"prepared"}'
        return PreparedInboundHttpResponse(
            request=request,
            route_kind=ROUTE_IMMUTABLE_RECORD,
            route_operation=INBOUND_RECORD_RETRIEVAL_OPERATION,
            status_code=200,
            headers=(("connection", "close"), ("content-length", str(len(body))), ("content-type", "application/json")),
            body=body,
            olp_message_type="record",
        )


def _prepared():
    harness = _ApplicationHarness()
    wire = BoundedInboundHttpWireAdapter(application_adapter=harness.adapter, authority=AUTHORITY)
    stream = BoundedInboundHttpStreamAssembler(wire_adapter=wire)
    planner = BoundedInboundHttpReadPlanner(
        stream_assembler=stream,
        limits=InboundHttpReadLimits(max_read_calls=64, max_read_bytes=64 * 1024),
    )
    transitioner = BoundedInboundHttpReadTransitioner(read_planner=planner)
    session = BoundedInboundHttpReadSession(read_transitioner=transitioner)
    handler = BoundedInboundHttpReadOutcomeHandler(read_session=session)
    raw = _get_request_bytes(f"/v1/records/{RECORD_ID}", AUTHORITY, 443)
    invoker = BoundedInboundHttpReadInvoker(
        read_outcome_handler=handler,
        reader=lambda _: InboundHttpReadOutcome.data(raw),
    )
    driver = BoundedInboundHttpReadDriver(read_invoker=invoker, clock=lambda: 0.0)
    return BoundedInboundHttpResponsePreparer(read_driver=driver).prepare()


class InboundHttpResponseWritePlanTests(unittest.TestCase):
    def test_zero_progress_plans_bounded_write_without_writer(self):
        prepared = _prepared()
        planner = BoundedInboundHttpResponseWritePlanner(
            limits=InboundHttpResponseWriteLimits(max_write_calls=4, max_write_bytes=7)
        )
        plan = planner.plan(prepared, write_calls_completed=0, bytes_written=0)
        self.assertEqual(plan.action, WRITE_ACTION_WRITE)
        self.assertEqual(plan.response_bytes, prepared.response_bytes)
        self.assertEqual(plan.next_write_bytes, 7)
        self.assertEqual(plan.remaining_bytes, prepared.response_bytes)
        self.assertFalse(plan.writer_invoked)
        self.assertFalse(plan.transmitted)

    def test_partial_progress_plans_exact_remaining_cap(self):
        prepared = _prepared()
        planner = BoundedInboundHttpResponseWritePlanner(
            limits=InboundHttpResponseWriteLimits(max_write_calls=8, max_write_bytes=10)
        )
        offset = prepared.response_bytes - 3
        plan = planner.plan(prepared, write_calls_completed=2, bytes_written=offset)
        self.assertEqual(plan.action, WRITE_ACTION_WRITE)
        self.assertEqual(plan.next_write_bytes, 3)
        self.assertEqual(plan.remaining_bytes, 3)

    def test_complete_is_local_accounting_not_transmission(self):
        prepared = _prepared()
        planner = BoundedInboundHttpResponseWritePlanner(
            limits=InboundHttpResponseWriteLimits(max_write_calls=1, max_write_bytes=1)
        )
        plan = planner.plan(
            prepared,
            write_calls_completed=1,
            bytes_written=prepared.response_bytes,
        )
        self.assertEqual(plan.action, WRITE_ACTION_COMPLETE)
        self.assertEqual(plan.next_write_bytes, 0)
        self.assertEqual(plan.remaining_bytes, 0)
        self.assertFalse(plan.writer_invoked)
        self.assertFalse(plan.socket_accessed)
        self.assertFalse(plan.transmitted)

    def test_incomplete_at_call_limit_fails_closed(self):
        prepared = _prepared()
        planner = BoundedInboundHttpResponseWritePlanner(
            limits=InboundHttpResponseWriteLimits(max_write_calls=1, max_write_bytes=1)
        )
        with self.assertRaises(InboundHttpResponseWritePlanError) as ctx:
            planner.plan(prepared, write_calls_completed=1, bytes_written=0)
        self.assertEqual(ctx.exception.code, "WRITE_CALL_LIMIT_EXHAUSTED")

    def test_invalid_counts_fail_closed(self):
        prepared = _prepared()
        planner = BoundedInboundHttpResponseWritePlanner()
        for calls in (True, -1, 1.0):
            with self.assertRaises(InboundHttpResponseWritePlanError):
                planner.plan(prepared, write_calls_completed=calls, bytes_written=0)
        for count in (True, -1, prepared.response_bytes + 1):
            with self.assertRaises(InboundHttpResponseWritePlanError):
                planner.plan(prepared, write_calls_completed=0, bytes_written=count)

    def test_tampered_m43_result_is_rejected(self):
        prepared = _prepared()
        object.__setattr__(prepared, "request_bytes", prepared.request_bytes + 1)
        with self.assertRaises(InboundHttpResponseWritePlanError) as ctx:
            BoundedInboundHttpResponseWritePlanner().plan(
                prepared, write_calls_completed=0, bytes_written=0
            )
        self.assertEqual(ctx.exception.code, "WRITE_PREPARED_RESPONSE_DRIFT")

    def test_plan_integrity_blocks_rebinding(self):
        prepared = _prepared()
        plan = BoundedInboundHttpResponseWritePlanner().plan(
            prepared, write_calls_completed=0, bytes_written=0
        )
        with self.assertRaises(ValueError):
            replace(plan, bytes_written=1)

    def test_public_limits_are_detached(self):
        limits = InboundHttpResponseWriteLimits(max_write_calls=3, max_write_bytes=5)
        planner = BoundedInboundHttpResponseWritePlanner(limits=limits)
        self.assertEqual(planner.limits, limits)
        self.assertIsNot(planner.limits, planner.limits)

    def test_source_has_no_writer_network_or_background_surface(self):
        source = inspect.getsource(m44)
        tree = ast.parse(source)
        imports = {
            alias.name.split(".")[0]
            for node in ast.walk(tree)
            if isinstance(node, (ast.Import, ast.ImportFrom))
            for alias in node.names
        }
        self.assertTrue(imports.isdisjoint({"socket", "ssl", "http", "urllib", "requests", "subprocess", "asyncio", "threading", "logging", "pathlib"}))
        plan_source = inspect.getsource(m44.BoundedInboundHttpResponseWritePlanner.plan)
        self.assertNotIn("writer(", plan_source)
        self.assertNotIn("send(", plan_source)

    def test_plan_witness_has_no_raw_response_copy(self):
        prepared = _prepared()
        plan = BoundedInboundHttpResponseWritePlanner().plan(
            prepared, write_calls_completed=0, bytes_written=0
        )
        raw = prepared.wire_exchange.response_bytes
        self.assertNotIn(raw, plan.integrity_snapshot)
        self.assertEqual(plan.prepared_response_integrity, prepared.integrity_snapshot)


if __name__ == "__main__":
    unittest.main()
