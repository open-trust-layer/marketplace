from __future__ import annotations

import ast
from dataclasses import replace
import inspect
import textwrap
import unittest

import marketplace.runtime as runtime
from marketplace.runtime.inbound_http import (
    BoundedInboundHttpApplicationAdapter,
    InboundHttpApplicationLimits,
)
from marketplace.runtime.inbound_http_read_driver import (
    BoundedInboundHttpReadDriver,
    CompletedInboundHttpReadDriverResult,
    InboundHttpReadDriverError,
    InboundHttpReadDriverLimits,
)
from marketplace.runtime.inbound_http_read_invoke import BoundedInboundHttpReadInvoker
from marketplace.runtime.inbound_http_read_outcome import (
    BoundedInboundHttpReadOutcomeHandler,
    InboundHttpReadOutcome,
)
from marketplace.runtime.inbound_http_read_plan import (
    BoundedInboundHttpReadPlanner,
    InboundHttpReadLimits,
)
from marketplace.runtime.inbound_http_read_session import BoundedInboundHttpReadSession
from marketplace.runtime.inbound_http_read_transition import BoundedInboundHttpReadTransitioner
from marketplace.runtime.inbound_http_stream import BoundedInboundHttpStreamAssembler
from marketplace.runtime.inbound_http_wire import BoundedInboundHttpWireAdapter
from marketplace.runtime.record_retrieval import _get_request_bytes
import marketplace.runtime.inbound_http_read_driver as driver_module

AUTHORITY = "market.example"
RECORD_ID = "r1_qcU6rT-ADJiC75Bg9w7qLSvauhY6zcEmy1dk-LrRlZc"


class _NoDisclosureHarness:
    def __init__(self):
        adapter = object.__new__(BoundedInboundHttpApplicationAdapter)
        object.__setattr__(adapter, "_limits", InboundHttpApplicationLimits())
        object.__setattr__(adapter, "handle", self._handle)
        self.adapter = adapter

    def _handle(self, request):
        raise AssertionError("M42 MUST NOT reach application disclosure")


def _build(reader, *, max_read_calls=64):
    harness = _NoDisclosureHarness()
    wire = BoundedInboundHttpWireAdapter(
        application_adapter=harness.adapter,
        authority=AUTHORITY,
    )
    stream = BoundedInboundHttpStreamAssembler(wire_adapter=wire)
    planner = BoundedInboundHttpReadPlanner(
        stream_assembler=stream,
        limits=InboundHttpReadLimits(max_read_calls=max_read_calls),
    )
    transitioner = BoundedInboundHttpReadTransitioner(read_planner=planner)
    session = BoundedInboundHttpReadSession(read_transitioner=transitioner)
    handler = BoundedInboundHttpReadOutcomeHandler(read_session=session)
    invoker = BoundedInboundHttpReadInvoker(
        read_outcome_handler=handler,
        reader=reader,
    )
    raw = _get_request_bytes(f"/v1/records/{RECORD_ID}", AUTHORITY, 443)
    return session, handler, invoker, raw


class _MutatingClock:
    def __init__(self, mutation):
        self.calls = 0
        self.mutation = mutation

    def __call__(self):
        self.calls += 1
        if self.calls == 3:
            self.mutation()
        return float(self.calls - 1) / 10.0


def _contains_exact_bytes(value, target):
    if type(value) is bytes:
        return value == target
    if type(value) in (tuple, list):
        return any(_contains_exact_bytes(item, target) for item in value)
    if type(value) is dict:
        return any(
            _contains_exact_bytes(key, target) or _contains_exact_bytes(item, target)
            for key, item in value.items()
        )
    return False


class InboundHttpReadDriverHardeningTests(unittest.TestCase):
    def test_public_runtime_exports_are_exact_m42_symbols(self):
        self.assertIs(runtime.BoundedInboundHttpReadDriver, BoundedInboundHttpReadDriver)
        self.assertIs(runtime.CompletedInboundHttpReadDriverResult, CompletedInboundHttpReadDriverResult)
        self.assertIs(runtime.InboundHttpReadDriverError, InboundHttpReadDriverError)
        self.assertIs(runtime.InboundHttpReadDriverLimits, InboundHttpReadDriverLimits)

    def test_constructor_has_no_reader_or_transport_parameter(self):
        parameters = inspect.signature(BoundedInboundHttpReadDriver).parameters
        self.assertEqual(set(parameters), {"read_invoker", "clock", "limits"})
        for forbidden in ("reader", "socket", "transport", "listener", "tls", "writer"):
            self.assertNotIn(forbidden, parameters)

    def test_public_m41_method_replacement_after_construction_cannot_substitute_authority(self):
        holder = {}

        def reader(max_bytes):
            return InboundHttpReadOutcome.data(holder["raw"])

        _, _, invoker, raw = _build(reader)
        holder["raw"] = raw
        values = iter((0.0, 0.0, 0.1, 0.1, 0.2))
        driver = BoundedInboundHttpReadDriver(read_invoker=invoker, clock=lambda: next(values))
        original = BoundedInboundHttpReadInvoker.invoke_once
        calls = []

        def hostile(self):
            calls.append("hostile")
            raise AssertionError("public replacement MUST NOT substitute captured M41 authority")

        BoundedInboundHttpReadInvoker.invoke_once = hostile
        try:
            result = driver.run_to_completion()
        finally:
            BoundedInboundHttpReadInvoker.invoke_once = original

        self.assertEqual(result.completed.prefix, raw)
        self.assertEqual(calls, [])

    def test_private_captured_invoke_rebind_fails_closed_before_input_consumption(self):
        calls = []

        def reader(max_bytes):
            calls.append(max_bytes)
            return InboundHttpReadOutcome.eof()

        session, _, invoker, _ = _build(reader)
        driver = BoundedInboundHttpReadDriver(read_invoker=invoker, clock=lambda: 0.0)
        object.__setattr__(driver, "_invoke", lambda: None)
        with self.assertRaises(InboundHttpReadDriverError) as caught:
            driver.run_to_completion()
        self.assertEqual(caught.exception.code, "READ_DRIVER_BINDING_DRIFT")
        self.assertEqual(calls, [])
        self.assertTrue(session.closed)
        self.assertEqual(session._prefix, b"")

    def test_retained_m37_limit_drift_after_consumption_closes_before_error(self):
        session, _, invoker, _ = _build(
            lambda _: InboundHttpReadOutcome.data(b"GET ")
        )
        clock = _MutatingClock(lambda: object.__setattr__(session, "_max_read_calls", 63))
        driver = BoundedInboundHttpReadDriver(read_invoker=invoker, clock=clock)

        with self.assertRaises(InboundHttpReadDriverError) as caught:
            driver.run_to_completion()
        self.assertEqual(caught.exception.code, "READ_DRIVER_CONFIGURATION_DRIFT")
        self.assertTrue(invoker.closed)
        self.assertEqual(session._prefix, b"")

    def test_drifted_cleanup_binding_reports_uncertain_instead_of_claiming_clear(self):
        session, _, invoker, _ = _build(
            lambda _: InboundHttpReadOutcome.data(b"GET ")
        )
        holder = {}

        def mutate_cleanup():
            object.__setattr__(holder["driver"], "_close", lambda: None)

        clock = _MutatingClock(mutate_cleanup)
        driver = BoundedInboundHttpReadDriver(read_invoker=invoker, clock=clock)
        holder["driver"] = driver

        with self.assertRaises(InboundHttpReadDriverError) as caught:
            driver.run_to_completion()
        self.assertEqual(caught.exception.code, "READ_DRIVER_CLEANUP_UNCERTAIN")
        self.assertFalse(session.closed)
        self.assertEqual(session._prefix, b"GET ")
        session.close()

    def test_completion_rebinding_fails_and_authority_promotion_cannot_survive_replay(self):
        holder = {}

        def reader(max_bytes):
            return InboundHttpReadOutcome.data(holder["raw"])

        _, _, invoker, raw = _build(reader)
        holder["raw"] = raw
        values = iter((0.0, 0.0, 0.1, 0.1, 0.2))
        result = BoundedInboundHttpReadDriver(
            read_invoker=invoker,
            clock=lambda: next(values),
        ).run_to_completion()

        object.__setattr__(result.completed, "prefix", raw + b"X")
        with self.assertRaises(ValueError):
            CompletedInboundHttpReadDriverResult(
                completed=result.completed,
                driver_steps=result.driver_steps,
                reader_invocations=result.reader_invocations,
                elapsed_seconds=result.elapsed_seconds,
                integrity_snapshot=result.integrity_snapshot,
            )

        _, _, invoker2, raw2 = _build(lambda _: InboundHttpReadOutcome.data(raw))
        values2 = iter((0.0, 0.0, 0.1, 0.1, 0.2))
        result2 = BoundedInboundHttpReadDriver(
            read_invoker=invoker2,
            clock=lambda: next(values2),
        ).run_to_completion()
        object.__setattr__(result2, "establishes_authorization", True)
        with self.assertRaises(ValueError):
            result2.__post_init__()
        replayed = replace(result2)
        self.assertIs(replayed.establishes_authorization, False)
        self.assertEqual(replayed.integrity_snapshot, result2.integrity_snapshot)
        self.assertEqual(raw2, raw)

    def test_result_witness_contains_no_second_raw_request_copy(self):
        holder = {}

        def reader(max_bytes):
            return InboundHttpReadOutcome.data(holder["raw"])

        _, _, invoker, raw = _build(reader)
        holder["raw"] = raw
        values = iter((0.0, 0.0, 0.1, 0.1, 0.2))
        result = BoundedInboundHttpReadDriver(
            read_invoker=invoker,
            clock=lambda: next(values),
        ).run_to_completion()
        self.assertFalse(_contains_exact_bytes(result.integrity_snapshot, raw))
        self.assertEqual(result.completed.prefix, raw)

    def test_success_never_promotes_origin_authentication_trust_or_authority(self):
        holder = {}
        _, _, invoker, raw = _build(lambda _: InboundHttpReadOutcome.data(holder["raw"]))
        holder["raw"] = raw
        values = iter((0, 0, 0, 0, 0))
        result = BoundedInboundHttpReadDriver(
            read_invoker=invoker,
            clock=lambda: next(values),
        ).run_to_completion()
        for name in (
            "socket_access_proven",
            "network_origin_proven",
            "request_authenticated",
            "peer_identity_proven",
            "establishes_marketplace_truth",
            "establishes_trust",
            "establishes_authorization",
            "authorizes_protected_side_effects",
        ):
            self.assertIs(getattr(result, name), False)

    def test_run_to_completion_contains_exactly_one_bounded_loop(self):
        source = textwrap.dedent(inspect.getsource(BoundedInboundHttpReadDriver.run_to_completion))
        tree = ast.parse(source)
        loops = [node for node in ast.walk(tree) if isinstance(node, (ast.For, ast.While, ast.AsyncFor))]
        self.assertEqual(len(loops), 1)
        self.assertIsInstance(loops[0], ast.For)
        self.assertIsInstance(loops[0].iter, ast.Call)
        self.assertIsInstance(loops[0].iter.func, ast.Name)
        self.assertEqual(loops[0].iter.func.id, "range")

    def test_source_has_no_direct_reader_network_tls_process_persistence_logging_or_concurrency_surface(self):
        source = inspect.getsource(driver_module)
        tree = ast.parse(source)
        forbidden_import_roots = {
            "socket",
            "ssl",
            "asyncio",
            "threading",
            "subprocess",
            "multiprocessing",
            "logging",
            "pathlib",
            "os",
            "signal",
        }
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    self.assertNotIn(alias.name.split(".")[0], forbidden_import_roots)
            if isinstance(node, ast.ImportFrom) and node.module:
                self.assertNotIn(node.module.split(".")[0], forbidden_import_roots)
            if isinstance(node, ast.Attribute):
                self.assertNotEqual(node.attr, "_reader")
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    self.assertNotIn(node.func.id, {"open", "exec", "eval"})
                if isinstance(node.func, ast.Attribute):
                    self.assertNotIn(
                        node.func.attr,
                        {
                            "recv",
                            "read",
                            "send",
                            "write",
                            "accept",
                            "connect",
                            "bind",
                            "listen",
                            "sleep",
                        },
                    )


if __name__ == "__main__":
    unittest.main()
