from __future__ import annotations

import ast
import dataclasses
import inspect
import textwrap
import unittest

import marketplace.runtime as runtime_package
import marketplace.runtime.inbound_http_read_session as session_module
from marketplace.runtime.inbound_http import (
    BoundedInboundHttpApplicationAdapter,
    InboundHttpApplicationLimits,
)
from marketplace.runtime.inbound_http_read_plan import (
    BoundedInboundHttpReadPlanner,
    InboundHttpReadPlan,
)
from marketplace.runtime.inbound_http_read_session import (
    BoundedInboundHttpReadSession,
    CompletedInboundHttpReadSession,
    InboundHttpReadSessionError,
    InboundHttpReadSessionProgress,
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
        raise AssertionError("M39 MUST remain below application disclosure")


class InboundHttpReadSessionHardeningTests(unittest.TestCase):
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

    def test_public_runtime_exports_are_exact_m39_types(self):
        self.assertIs(runtime_package.BoundedInboundHttpReadSession, BoundedInboundHttpReadSession)
        self.assertIs(runtime_package.CompletedInboundHttpReadSession, CompletedInboundHttpReadSession)
        self.assertIs(runtime_package.InboundHttpReadSessionError, InboundHttpReadSessionError)
        self.assertIs(runtime_package.InboundHttpReadSessionProgress, InboundHttpReadSessionProgress)

    def test_constructor_exposes_no_initial_prefix_or_read_count(self):
        parameters = tuple(inspect.signature(BoundedInboundHttpReadSession).parameters)
        self.assertEqual(parameters, ("read_transitioner",))
        self.assertNotIn("prefix", parameters)
        self.assertNotIn("reads_completed", parameters)

    def test_public_progress_contains_no_raw_prefix_or_chunk(self):
        progress = self.session.accept_chunk(b"GET ")
        fields = {field.name for field in dataclasses.fields(progress)}
        self.assertNotIn("prefix", fields)
        self.assertNotIn("chunk", fields)
        self.assertNotIn("raw_prefix", fields)
        self.assertNotIn("raw_chunk", fields)
        self.assertNotIn(b"GET ", progress.integrity_snapshot)

    def test_private_read_count_reset_is_detected_by_state_witness(self):
        self.session.accept_chunk(b"G")
        object.__setattr__(self.session, "_reads_completed", 0)
        with self.assertRaises(InboundHttpReadSessionError) as caught:
            self.session.progress()
        self.assertEqual(caught.exception.code, "READ_SESSION_STATE_DRIFT")
        self.session.close()
        self.assertTrue(self.session.closed)
        self.assertEqual(self.session._prefix, b"")

    def test_private_prefix_rebinding_is_detected_by_state_witness(self):
        self.session.accept_chunk(b"G")
        object.__setattr__(self.session, "_prefix", b"X")
        with self.assertRaises(InboundHttpReadSessionError) as caught:
            self.session.progress()
        self.assertEqual(caught.exception.code, "READ_SESSION_STATE_DRIFT")
        self.session.close()
        self.assertEqual(self.session._prefix, b"")

    def test_public_m37_plan_and_m38_transition_replacement_cannot_substitute_authority(self):
        def hostile_plan(prefix, *, reads_completed):
            raise AssertionError("replacement M37 plan MUST NOT be invoked")

        def hostile_transition(prefix, *, reads_completed, chunk):
            raise AssertionError("replacement M38 transition MUST NOT be invoked")

        object.__setattr__(self.planner, "plan", hostile_plan)
        object.__setattr__(self.transitioner, "transition", hostile_transition)
        progress = self.session.accept_chunk(b"G")
        self.assertEqual(progress.buffered_bytes, 1)
        self.assertEqual(progress.reads_completed, 1)
        self.assertEqual(self.harness.calls, [])

    def test_m37_configuration_mutation_during_initial_plan_is_detected(self):
        planner = BoundedInboundHttpReadPlanner(stream_assembler=self.stream)
        transitioner = BoundedInboundHttpReadTransitioner(read_planner=planner)
        original_probe = planner._probe

        def hostile_probe(prefix):
            progress = original_probe(prefix)
            object.__setattr__(planner, "_max_read_bytes", 1)
            return progress

        object.__setattr__(planner, "_probe", hostile_probe)
        with self.assertRaises(InboundHttpReadSessionError) as caught:
            BoundedInboundHttpReadSession(read_transitioner=transitioner)
        self.assertEqual(caught.exception.code, "READ_CONFIGURATION_DRIFT")
        self.assertEqual(self.harness.calls, [])

    def test_m37_configuration_mutation_during_transition_is_detected_without_state_advance(self):
        original_probe = self.planner._probe

        def hostile_probe(prefix):
            progress = original_probe(prefix)
            object.__setattr__(self.planner, "_max_read_bytes", 1)
            return progress

        object.__setattr__(self.planner, "_probe", hostile_probe)
        with self.assertRaises(InboundHttpReadSessionError) as caught:
            self.session.accept_chunk(b"G")
        self.assertEqual(caught.exception.code, "READ_CONFIGURATION_DRIFT")
        self.assertEqual(self.session._prefix, b"")
        self.assertEqual(self.session._reads_completed, 0)
        self.assertEqual(self.harness.calls, [])

    def test_self_consistent_wrong_m38_prior_plan_cannot_rebind_session_state(self):
        original_authoritative_plan = self.transitioner._authoritative_plan
        calls = 0

        def hostile_authoritative_plan(prefix, *, reads_completed):
            nonlocal calls
            calls += 1
            plan = original_authoritative_plan(prefix, reads_completed=reads_completed)
            if calls == 1:
                return dataclasses.replace(plan, next_read_bytes=1, integrity_snapshot=None)
            return plan

        object.__setattr__(self.transitioner, "_authoritative_plan", hostile_authoritative_plan)
        with self.assertRaises(InboundHttpReadSessionError) as caught:
            self.session.accept_chunk(b"G")
        self.assertEqual(caught.exception.code, "READ_PRIOR_PLAN_DRIFT")
        self.assertEqual(self.session._prefix, b"")
        self.assertEqual(self.session._reads_completed, 0)
        self.assertEqual(self.harness.calls, [])

    def test_completed_handoff_integrity_blocks_rebinding_and_authority_promotion(self):
        self.session.accept_chunk(self.raw)
        completed = self.session.take_completed()
        forged_prefix = b"X" * len(completed.prefix)
        with self.assertRaises(ValueError):
            dataclasses.replace(completed, prefix=forged_prefix)
        with self.assertRaises(ValueError):
            dataclasses.replace(completed, reads_completed=completed.reads_completed + 1)
        forged_plan = dataclasses.replace(
            completed.plan,
            reads_completed=completed.plan.reads_completed + 1,
            integrity_snapshot=None,
        )
        with self.assertRaises(ValueError):
            dataclasses.replace(completed, plan=forged_plan)
        object.__setattr__(completed, "establishes_authorization", True)
        with self.assertRaises(ValueError):
            completed.__post_init__()

    def test_completed_handoff_witness_contains_digest_not_second_raw_prefix(self):
        self.session.accept_chunk(self.raw)
        completed = self.session.take_completed()
        self.assertNotIn(completed.prefix, completed.integrity_snapshot)
        self.assertFalse(any(value is completed.prefix for value in completed.integrity_snapshot))
        fields = {field.name for field in dataclasses.fields(completed)}
        self.assertEqual(tuple(name for name in fields if "prefix" in name), ("prefix",))
        self.assertNotIn("chunk", fields)
        self.assertNotIn("raw_chunk", fields)

    def test_accept_chunk_has_no_independent_accumulation_or_lower_layer_calls(self):
        source = inspect.getsource(BoundedInboundHttpReadSession.accept_chunk)
        tree = ast.parse(textwrap.dedent(source))
        self.assertFalse(any(isinstance(node, (ast.For, ast.While)) for node in ast.walk(tree)))
        self.assertNotIn(" + ", source)
        self.assertNotIn(".join(", source)
        self.assertNotIn("bytearray(", source)
        self.assertNotIn("memoryview(", source)
        for forbidden in (
            "stream_assembler",
            "wire_adapter",
            "application_adapter",
            ".probe(",
            ".prepare(",
            ".handle(",
        ):
            self.assertNotIn(forbidden, source)
        transition_calls = [
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "_transition"
        ]
        self.assertEqual(len(transition_calls), 1)

    def test_source_has_no_network_reader_writer_tls_server_process_persistence_or_background_surface(self):
        source = inspect.getsource(session_module)
        tree = ast.parse(source)
        forbidden_roots = {
            "socket",
            "ssl",
            "http",
            "urllib",
            "asyncio",
            "threading",
            "subprocess",
            "logging",
            "pathlib",
            "os",
        }
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name.split(".", 1)[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.split(".", 1)[0])
        self.assertTrue(imported.isdisjoint(forbidden_roots), imported & forbidden_roots)
        for token in (
            ".recv(",
            ".read(",
            ".send(",
            ".sendall(",
            ".write(",
            ".listen(",
            ".accept(",
            ".connect(",
            "open(",
        ):
            self.assertNotIn(token, source)

    def test_progress_and_completion_authority_flags_remain_false(self):
        progress = self.session.accept_chunk(self.raw)
        completed = self.session.take_completed()
        for value in (progress, completed):
            for name in (
                "reader_invoked",
                "socket_accessed",
                "tls_terminated",
                "transmitted",
                "request_authenticated",
                "peer_identity_proven",
                "establishes_marketplace_truth",
                "establishes_trust",
                "establishes_authorization",
                "authorizes_protected_side_effects",
            ):
                self.assertIs(getattr(value, name), False)


if __name__ == "__main__":
    unittest.main()
