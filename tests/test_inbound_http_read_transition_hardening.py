from __future__ import annotations

import ast
import dataclasses
import inspect
import textwrap
import unittest

import marketplace.runtime as runtime_package
import marketplace.runtime.inbound_http_read_transition as transition_module
from marketplace.runtime.inbound_http import (
    BoundedInboundHttpApplicationAdapter,
    InboundHttpApplicationLimits,
)
from marketplace.runtime.inbound_http_read_plan import (
    BoundedInboundHttpReadPlanner,
    InboundHttpReadLimits,
)
from marketplace.runtime.inbound_http_read_transition import (
    BoundedInboundHttpReadTransitioner,
    InboundHttpReadTransition,
    InboundHttpReadTransitionError,
)
from marketplace.runtime.inbound_http_stream import BoundedInboundHttpStreamAssembler
from marketplace.runtime.inbound_http_wire import BoundedInboundHttpWireAdapter

AUTHORITY = "market.example"


class _NoDisclosureHarness:
    def __init__(self):
        self.calls = []
        adapter = object.__new__(BoundedInboundHttpApplicationAdapter)
        object.__setattr__(adapter, "_limits", InboundHttpApplicationLimits())
        object.__setattr__(adapter, "handle", self._handle)
        self.adapter = adapter

    def _handle(self, request):
        self.calls.append(request)
        raise AssertionError("M38 transport-free transition MUST NOT reach application disclosure")


class InboundHttpReadTransitionHardeningTests(unittest.TestCase):
    def setUp(self):
        self.harness = _NoDisclosureHarness()
        self.wire = BoundedInboundHttpWireAdapter(
            application_adapter=self.harness.adapter,
            authority=AUTHORITY,
        )
        self.stream = BoundedInboundHttpStreamAssembler(wire_adapter=self.wire)
        self.planner = BoundedInboundHttpReadPlanner(stream_assembler=self.stream)
        self.transitioner = BoundedInboundHttpReadTransitioner(read_planner=self.planner)

    def test_public_runtime_exports_are_exact_m38_types(self):
        self.assertIs(
            runtime_package.BoundedInboundHttpReadTransitioner,
            BoundedInboundHttpReadTransitioner,
        )
        self.assertIs(runtime_package.InboundHttpReadTransition, InboundHttpReadTransition)
        self.assertIs(runtime_package.InboundHttpReadTransitionError, InboundHttpReadTransitionError)

    def test_public_configuration_views_are_detached(self):
        read_view = self.transitioner.read_limits
        stream_view = self.transitioner.stream_limits
        wire_view = self.transitioner.wire_limits
        object.__setattr__(read_view, "max_read_bytes", 1)
        object.__setattr__(stream_view, "max_chunk_bytes", 1)
        object.__setattr__(wire_view, "max_header_bytes", 1)
        self.assertEqual(self.transitioner.read_limits.max_read_bytes, 16 * 1024)
        self.assertEqual(self.transitioner.stream_limits.max_chunk_bytes, 64 * 1024)
        self.assertEqual(self.transitioner.wire_limits.max_header_bytes, 32 * 1024)

    def test_m37_configuration_drift_fails_before_transition(self):
        object.__setattr__(self.planner, "_max_read_bytes", 1)
        with self.assertRaises(InboundHttpReadTransitionError) as caught:
            self.transitioner.transition(b"", reads_completed=0, chunk=b"x")
        self.assertEqual(caught.exception.code, "READ_CONFIGURATION_DRIFT")
        self.assertEqual(self.harness.calls, [])

    def test_m37_configuration_mutation_during_first_planning_is_detected(self):
        original_probe = self.planner._probe

        def hostile_probe(prefix):
            progress = original_probe(prefix)
            object.__setattr__(self.planner, "_max_read_bytes", 1)
            return progress

        object.__setattr__(self.planner, "_probe", hostile_probe)
        with self.assertRaises(InboundHttpReadTransitionError) as caught:
            self.transitioner.transition(b"", reads_completed=0, chunk=b"x")
        self.assertEqual(caught.exception.code, "READ_CONFIGURATION_DRIFT")
        self.assertEqual(self.harness.calls, [])

    def test_m37_configuration_mutation_during_second_planning_is_detected(self):
        original_probe = self.planner._probe
        calls = 0

        def hostile_probe(prefix):
            nonlocal calls
            calls += 1
            progress = original_probe(prefix)
            if calls == 2:
                object.__setattr__(self.planner, "_max_read_bytes", 1)
            return progress

        object.__setattr__(self.planner, "_probe", hostile_probe)
        with self.assertRaises(InboundHttpReadTransitionError) as caught:
            self.transitioner.transition(b"", reads_completed=0, chunk=b"G")
        self.assertEqual(calls, 2)
        self.assertEqual(caught.exception.code, "READ_CONFIGURATION_DRIFT")
        self.assertEqual(self.harness.calls, [])

    def test_replacing_public_m37_plan_after_construction_cannot_substitute_authority(self):
        def hostile_plan(prefix, *, reads_completed):
            raise AssertionError("replacement M37 plan MUST NOT be invoked")

        object.__setattr__(self.planner, "plan", hostile_plan)
        transition = self.transitioner.transition(b"", reads_completed=0, chunk=b"G")
        self.assertEqual(transition.prefix, b"G")
        self.assertEqual(transition.reads_completed, 1)
        self.assertEqual(self.harness.calls, [])

    def test_transition_integrity_witness_blocks_rebinding(self):
        transition = self.transitioner.transition(b"", reads_completed=0, chunk=b"G")
        with self.assertRaises(ValueError):
            dataclasses.replace(transition, prefix=b"X")
        with self.assertRaises(ValueError):
            dataclasses.replace(transition, reads_completed=2)
        forged_next = dataclasses.replace(
            transition.next_plan,
            reads_completed=transition.next_plan.reads_completed + 1,
            integrity_snapshot=None,
        )
        with self.assertRaises(ValueError):
            dataclasses.replace(transition, next_plan=forged_next)
        object.__setattr__(transition, "establishes_authorization", True)
        with self.assertRaises(ValueError):
            transition.__post_init__()

    def test_integrity_snapshot_contains_digest_not_raw_prefix(self):
        chunk = b"GET "
        transition = self.transitioner.transition(b"", reads_completed=0, chunk=chunk)
        self.assertEqual(transition.prefix, chunk)
        self.assertNotIn(chunk, transition.integrity_snapshot)
        self.assertFalse(any(value is chunk for value in transition.integrity_snapshot))
        fields = {field.name for field in dataclasses.fields(transition)}
        self.assertNotIn("chunk", fields)
        self.assertNotIn("raw_chunk", fields)

    def test_transition_uses_only_m37_planning_and_one_append_without_accumulation_loop(self):
        source = inspect.getsource(BoundedInboundHttpReadTransitioner.transition)
        tree = ast.parse(textwrap.dedent(source))
        self.assertFalse(any(isinstance(node, (ast.For, ast.While)) for node in ast.walk(tree)))
        self.assertNotIn(".join(", source)
        self.assertNotIn("bytearray(", source)
        self.assertNotIn("memoryview(", source)
        self.assertEqual(source.count("prefix + chunk"), 1)
        plan_calls = [
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "_authoritative_plan"
        ]
        self.assertEqual(len(plan_calls), 2)
        for forbidden in (
            "stream_assembler",
            "wire_adapter",
            "application_adapter",
            ".probe(",
            ".prepare(",
            ".handle(",
        ):
            self.assertNotIn(forbidden, source)

    def test_source_has_no_network_reader_writer_tls_server_process_or_persistence_surface(self):
        source = inspect.getsource(transition_module)
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

    def test_authority_negative_flags_remain_false(self):
        transition = self.transitioner.transition(b"", reads_completed=0, chunk=b"G")
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
            self.assertIs(getattr(transition, name), False)

    def test_m38_does_not_widen_m37_limits(self):
        planner = BoundedInboundHttpReadPlanner(
            stream_assembler=self.stream,
            limits=InboundHttpReadLimits(max_read_calls=3, max_read_bytes=8),
        )
        transitioner = BoundedInboundHttpReadTransitioner(read_planner=planner)
        self.assertEqual(transitioner.read_limits, InboundHttpReadLimits(max_read_calls=3, max_read_bytes=8))
        transition = transitioner.transition(b"", reads_completed=0, chunk=b"12345678")
        self.assertEqual(transition.accepted_chunk_bytes, 8)


if __name__ == "__main__":
    unittest.main()
