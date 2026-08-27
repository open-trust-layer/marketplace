from __future__ import annotations

import ast
import inspect
import textwrap
import unittest
from dataclasses import fields, replace
from pathlib import Path

import marketplace.runtime as runtime
from marketplace.runtime.inbound_http import BoundedInboundHttpApplicationAdapter, InboundHttpApplicationLimits
from marketplace.runtime.inbound_http_read_invoke import (
    READ_INVOCATION_COMPLETED,
    READ_INVOCATION_PROGRESS,
    BoundedInboundHttpReadInvoker,
    InboundHttpReadInvocationError,
    InboundHttpReadInvocationResult,
)
from marketplace.runtime.inbound_http_read_outcome import BoundedInboundHttpReadOutcomeHandler, InboundHttpReadOutcome
from marketplace.runtime.inbound_http_read_plan import BoundedInboundHttpReadPlanner
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
        raise AssertionError("M41 MUST remain below application disclosure")


def _parts(reader):
    harness = _NoDisclosureHarness()
    wire = BoundedInboundHttpWireAdapter(application_adapter=harness.adapter, authority=AUTHORITY)
    stream = BoundedInboundHttpStreamAssembler(wire_adapter=wire)
    planner = BoundedInboundHttpReadPlanner(stream_assembler=stream)
    transitioner = BoundedInboundHttpReadTransitioner(read_planner=planner)
    session = BoundedInboundHttpReadSession(read_transitioner=transitioner)
    handler = BoundedInboundHttpReadOutcomeHandler(read_session=session)
    invoker = BoundedInboundHttpReadInvoker(read_outcome_handler=handler, reader=reader)
    raw = _get_request_bytes(f"/v1/records/{RECORD_ID}", AUTHORITY, 443)
    return session, handler, invoker, raw


class _OutcomeSubclass(InboundHttpReadOutcome):
    pass


class InboundHttpReadInvokeHardeningTests(unittest.TestCase):
    def test_public_runtime_exports_are_exact_m41_symbols(self):
        self.assertIs(runtime.BoundedInboundHttpReadInvoker, BoundedInboundHttpReadInvoker)
        self.assertIs(runtime.InboundHttpReadInvocationError, InboundHttpReadInvocationError)
        self.assertIs(runtime.InboundHttpReadInvocationResult, InboundHttpReadInvocationResult)
        self.assertEqual(runtime.READ_INVOCATION_PROGRESS, READ_INVOCATION_PROGRESS)
        self.assertEqual(runtime.READ_INVOCATION_COMPLETED, READ_INVOCATION_COMPLETED)

    def test_public_api_has_one_explicit_reader_and_no_transport_parameters(self):
        constructor = tuple(inspect.signature(BoundedInboundHttpReadInvoker).parameters)
        invoke = tuple(inspect.signature(BoundedInboundHttpReadInvoker.invoke_once).parameters)
        self.assertEqual(constructor, ("read_outcome_handler", "reader"))
        self.assertEqual(invoke, ("self",))
        for forbidden in ("socket", "host", "port", "tls", "retry", "timeout"):
            self.assertNotIn(forbidden, constructor)

    def test_result_has_no_direct_raw_chunk_or_prefix_field_and_witness_does_not_copy_data(self):
        chunk = b"GET "
        _, _, invoker, _ = _parts(lambda max_bytes: InboundHttpReadOutcome.data(chunk))
        result = invoker.invoke_once()
        names = {field.name for field in fields(result)}
        self.assertNotIn("chunk", names)
        self.assertNotIn("prefix", names)
        self.assertNotIn(chunk, result.integrity_snapshot)
        self.assertEqual(result.state, READ_INVOCATION_PROGRESS)
        with self.assertRaises(ValueError):
            replace(result, requested_bytes=result.requested_bytes + 1)

    def test_completed_result_witness_does_not_duplicate_completion_prefix(self):
        holder = {}
        _, _, invoker, raw = _parts(lambda max_bytes: InboundHttpReadOutcome.data(holder["raw"]))
        holder["raw"] = raw
        invoker.invoke_once()
        completed = invoker.invoke_once()
        self.assertEqual(completed.state, READ_INVOCATION_COMPLETED)
        self.assertEqual(completed.completed.prefix, raw)
        self.assertNotIn(raw, completed.integrity_snapshot)

    def test_outcome_subclass_is_not_accepted_as_exact_reader_result(self):
        calls = []
        def reader(max_bytes):
            calls.append(max_bytes)
            return _OutcomeSubclass.data(b"GET ")
        session, _, invoker, _ = _parts(reader)
        with self.assertRaises(InboundHttpReadInvocationError) as caught:
            invoker.invoke_once()
        self.assertEqual(caught.exception.code, "INVALID_READER_RESULT")
        self.assertEqual(len(calls), 1)
        self.assertTrue(session.closed)
        self.assertEqual(session._prefix, b"")

    def test_public_m40_method_replacement_after_construction_cannot_substitute_authority(self):
        holder = {}
        _, _, invoker, raw = _parts(lambda max_bytes: InboundHttpReadOutcome.data(holder["raw"]))
        holder["raw"] = raw
        originals = (
            BoundedInboundHttpReadOutcomeHandler.progress,
            BoundedInboundHttpReadOutcomeHandler.accept_outcome,
            BoundedInboundHttpReadOutcomeHandler.take_completed,
            BoundedInboundHttpReadOutcomeHandler.close,
        )
        def hostile(*args, **kwargs):
            raise AssertionError("replaced public M40 method MUST NOT run")
        try:
            BoundedInboundHttpReadOutcomeHandler.progress = hostile
            BoundedInboundHttpReadOutcomeHandler.accept_outcome = hostile
            BoundedInboundHttpReadOutcomeHandler.take_completed = hostile
            BoundedInboundHttpReadOutcomeHandler.close = hostile
            self.assertEqual(invoker.invoke_once().state, READ_INVOCATION_PROGRESS)
            second = invoker.invoke_once()
            self.assertEqual(second.state, READ_INVOCATION_COMPLETED)
            self.assertEqual(second.completed.prefix, raw)
        finally:
            (
                BoundedInboundHttpReadOutcomeHandler.progress,
                BoundedInboundHttpReadOutcomeHandler.accept_outcome,
                BoundedInboundHttpReadOutcomeHandler.take_completed,
                BoundedInboundHttpReadOutcomeHandler.close,
            ) = originals

    def test_private_captured_binding_rebind_fails_before_reader_invocation(self):
        calls = []
        def reader(max_bytes):
            calls.append(max_bytes)
            return InboundHttpReadOutcome.data(b"GET ")
        session, _, invoker, _ = _parts(reader)
        invoker._accept = invoker._progress
        with self.assertRaises(InboundHttpReadInvocationError) as caught:
            invoker.invoke_once()
        self.assertEqual(caught.exception.code, "READ_INVOCATION_BINDING_DRIFT")
        self.assertEqual(calls, [])
        self.assertFalse(session.closed)
        self.assertEqual(session._prefix, b"")

    def test_reader_binding_replacement_is_detected_before_call(self):
        calls = []
        def reader(max_bytes):
            calls.append(max_bytes)
            return InboundHttpReadOutcome.data(b"GET ")
        _, _, invoker, _ = _parts(reader)
        invoker._reader = lambda max_bytes: InboundHttpReadOutcome.eof()
        with self.assertRaises(InboundHttpReadInvocationError) as caught:
            invoker.invoke_once()
        self.assertEqual(caught.exception.code, "READ_INVOCATION_BINDING_DRIFT")
        self.assertEqual(calls, [])

    def test_success_result_never_promotes_origin_authentication_or_authority(self):
        _, _, invoker, _ = _parts(lambda max_bytes: InboundHttpReadOutcome.data(b"GET "))
        result = invoker.invoke_once()
        self.assertTrue(result.reader_invoked)
        for name in (
            "socket_access_proven", "network_origin_proven", "request_authenticated",
            "peer_identity_proven", "establishes_marketplace_truth", "establishes_trust",
            "establishes_authorization", "authorizes_protected_side_effects",
        ):
            self.assertIs(getattr(result, name), False)

    def test_source_has_no_concrete_network_process_persistence_or_logging_surface_and_invoke_has_no_loop(self):
        source_path = Path(__file__).resolve().parents[1] / "src/marketplace/runtime/inbound_http_read_invoke.py"
        source = source_path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        forbidden_import_roots = {"socket", "ssl", "http", "urllib", "asyncio", "threading", "subprocess", "logging", "pathlib", "os"}
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    self.assertNotIn(alias.name.split(".", 1)[0], forbidden_import_roots)
            elif isinstance(node, ast.ImportFrom) and node.module:
                self.assertNotIn(node.module.split(".", 1)[0], forbidden_import_roots)
            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    self.assertNotIn(node.func.id, {"open", "exec", "eval", "compile"})
                elif isinstance(node.func, ast.Attribute):
                    self.assertNotIn(node.func.attr, {"recv", "recv_into", "read", "send", "sendall", "write", "listen", "connect", "bind", "accept", "sleep"})

        invoke_source = textwrap.dedent(inspect.getsource(BoundedInboundHttpReadInvoker.invoke_once))
        invoke_tree = ast.parse(invoke_source)
        self.assertEqual(invoke_source.count("self._reader("), 1)
        self.assertFalse(any(isinstance(node, (ast.For, ast.AsyncFor, ast.While)) for node in ast.walk(invoke_tree)))


if __name__ == "__main__":
    unittest.main()
