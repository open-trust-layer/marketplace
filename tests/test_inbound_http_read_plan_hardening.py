from __future__ import annotations

import ast
import dataclasses
import inspect
import textwrap
import unittest

import marketplace.runtime.inbound_http_read_plan as read_plan_module
from marketplace.runtime.inbound_http import (
    ROUTE_IMMUTABLE_RECORD,
    BoundedInboundHttpApplicationAdapter,
    InboundHttpApplicationLimits,
    PreparedInboundHttpResponse,
)
from marketplace.runtime.inbound_http_read_plan import (
    READ_ACTION_READ,
    BoundedInboundHttpReadPlanner,
    InboundHttpReadLimits,
    InboundHttpReadPlanError,
)
from marketplace.runtime.inbound_http_stream import (
    PROGRESS_COMPLETE,
    BoundedInboundHttpStreamAssembler,
    InboundHttpStreamLimits,
)
from marketplace.runtime.inbound_http_wire import BoundedInboundHttpWireAdapter
from marketplace.runtime.inbound_record import INBOUND_RECORD_RETRIEVAL_OPERATION
from marketplace.runtime.record_retrieval import _get_request_bytes

AUTHORITY = "market.example"
RECORD_ID = "r1_qcU6rT-ADJiC75Bg9w7qLSvauhY6zcEmy1dk-LrRlZc"


class _ApplicationHarness:
    def __init__(self):
        self.calls = []
        adapter = object.__new__(BoundedInboundHttpApplicationAdapter)
        object.__setattr__(adapter, "_limits", InboundHttpApplicationLimits())
        object.__setattr__(adapter, "handle", self._handle)
        self.adapter = adapter

    def _handle(self, request):
        self.calls.append(request)
        body = b'{"olp":"prepared"}'
        return PreparedInboundHttpResponse(
            request=request,
            route_kind=ROUTE_IMMUTABLE_RECORD,
            route_operation=INBOUND_RECORD_RETRIEVAL_OPERATION,
            status_code=200,
            headers=(
                ("connection", "close"),
                ("content-length", str(len(body))),
                ("content-type", "application/json"),
            ),
            body=body,
            olp_message_type="record",
        )


class InboundHttpReadPlanHardeningTests(unittest.TestCase):
    def setUp(self):
        self.harness = _ApplicationHarness()
        self.wire = BoundedInboundHttpWireAdapter(
            application_adapter=self.harness.adapter,
            authority=AUTHORITY,
        )
        self.stream = BoundedInboundHttpStreamAssembler(wire_adapter=self.wire)
        self.planner = BoundedInboundHttpReadPlanner(stream_assembler=self.stream)
        self.raw = _get_request_bytes(f"/v1/records/{RECORD_ID}", AUTHORITY, 443)

    def test_read_limits_are_detached_from_caller_alias(self):
        limits = InboundHttpReadLimits(max_read_calls=2, max_read_bytes=128)
        planner = BoundedInboundHttpReadPlanner(stream_assembler=self.stream, limits=limits)
        object.__setattr__(limits, "max_read_calls", 64)
        object.__setattr__(limits, "max_read_bytes", 16 * 1024)
        self.assertEqual(planner.limits, InboundHttpReadLimits(max_read_calls=2, max_read_bytes=128))

    def test_public_limit_views_are_fresh_and_cannot_mutate_authority(self):
        read_view = self.planner.limits
        stream_view = self.planner.stream_limits
        wire_view = self.planner.wire_limits
        object.__setattr__(read_view, "max_read_bytes", 1)
        object.__setattr__(stream_view, "max_chunk_bytes", 1)
        object.__setattr__(wire_view, "max_header_bytes", 1)
        self.assertEqual(self.planner.limits.max_read_bytes, 16 * 1024)
        self.assertEqual(self.planner.stream_limits.max_chunk_bytes, 64 * 1024)
        self.assertEqual(self.planner.wire_limits.max_header_bytes, 32 * 1024)
        plan = self.planner.plan(b"", reads_completed=0)
        self.assertEqual(plan.action, READ_ACTION_READ)
        self.assertEqual(plan.next_read_bytes, 16 * 1024)

    def test_m36_stream_configuration_drift_fails_before_probe(self):
        object.__setattr__(self.stream, "_max_chunk_bytes", 32 * 1024)
        with self.assertRaises(InboundHttpReadPlanError) as caught:
            self.planner.plan(b"", reads_completed=0)
        self.assertEqual(caught.exception.code, "STREAM_CONFIGURATION_DRIFT")
        self.assertEqual(self.harness.calls, [])

    def test_underlying_m35_configuration_drift_is_preserved_through_m36(self):
        object.__setattr__(self.wire, "_authority", "other.example")
        with self.assertRaises(InboundHttpReadPlanError) as caught:
            self.planner.plan(self.raw, reads_completed=1)
        self.assertEqual(caught.exception.code, "STREAM_PROFILE_REJECTED")
        self.assertEqual(caught.exception.stream_code, "WIRE_CONFIGURATION_DRIFT")
        self.assertEqual(self.harness.calls, [])

    def test_m35_mutation_during_m36_probe_is_detected(self):
        original_parse = self.wire.parse_request

        def hostile_parse(raw):
            result = original_parse(raw)
            object.__setattr__(self.wire, "_authority", "other.example")
            return result

        object.__setattr__(self.wire, "parse_request", hostile_parse)
        with self.assertRaises(InboundHttpReadPlanError) as caught:
            self.planner.plan(self.raw, reads_completed=1)
        self.assertEqual(caught.exception.code, "STREAM_PROFILE_REJECTED")
        self.assertEqual(caught.exception.stream_code, "WIRE_CONFIGURATION_DRIFT")
        self.assertEqual(self.harness.calls, [])

    def test_m36_stream_limit_mutation_during_probe_is_detected(self):
        original_parse = self.wire.parse_request

        def hostile_parse(raw):
            result = original_parse(raw)
            object.__setattr__(self.stream, "_max_chunk_bytes", 32 * 1024)
            return result

        object.__setattr__(self.wire, "parse_request", hostile_parse)
        with self.assertRaises(InboundHttpReadPlanError) as caught:
            self.planner.plan(self.raw, reads_completed=1)
        self.assertEqual(caught.exception.code, "STREAM_CONFIGURATION_DRIFT")
        self.assertEqual(self.harness.calls, [])

    def test_replacing_public_m36_probe_after_construction_cannot_substitute_authority(self):
        def hostile_probe(prefix):
            raise AssertionError("replacement M36 probe MUST NOT be invoked")

        object.__setattr__(self.stream, "probe", hostile_probe)
        plan = self.planner.plan(b"", reads_completed=0)
        self.assertEqual(plan.action, READ_ACTION_READ)
        self.assertEqual(plan.next_read_bytes, 16 * 1024)

    def test_mutated_m36_progress_fails_invariant_replay(self):
        progress = self.stream.probe(b"")
        object.__setattr__(progress, "state", PROGRESS_COMPLETE)
        object.__setattr__(self.planner, "_probe", lambda prefix: progress)
        with self.assertRaises(InboundHttpReadPlanError) as caught:
            self.planner.plan(b"", reads_completed=0)
        self.assertEqual(caught.exception.code, "STREAM_PROGRESS_DRIFT")

    def test_non_m36_progress_type_fails_closed(self):
        object.__setattr__(self.planner, "_probe", lambda prefix: object())
        with self.assertRaises(InboundHttpReadPlanError) as caught:
            self.planner.plan(b"", reads_completed=0)
        self.assertEqual(caught.exception.code, "INVALID_STREAM_PROGRESS")

    def test_read_plan_integrity_witness_blocks_dataclass_rebinding(self):
        plan = self.planner.plan(b"", reads_completed=0)
        with self.assertRaises(ValueError):
            dataclasses.replace(plan, next_read_bytes=plan.next_read_bytes - 1)
        object.__setattr__(plan, "establishes_authorization", True)
        with self.assertRaises(ValueError):
            plan.__post_init__()

    def test_read_plan_does_not_retain_raw_request_prefix(self):
        plan = self.planner.plan(self.raw, reads_completed=1)
        fields = {field.name for field in dataclasses.fields(plan)}
        self.assertNotIn("prefix", fields)
        self.assertNotIn("raw_request", fields)
        self.assertNotIn("request_bytes", fields)
        self.assertFalse(any(value is self.raw for value in vars(plan).values()))

    def test_plan_uses_one_m36_probe_and_no_prefix_copy_loop(self):
        source = inspect.getsource(BoundedInboundHttpReadPlanner.plan)
        tree = ast.parse(textwrap.dedent(source))
        probe_calls = [
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "_probe_with_configuration_guard"
        ]
        self.assertEqual(len(probe_calls), 1)
        self.assertFalse(any(isinstance(node, (ast.For, ast.While)) for node in ast.walk(tree)))
        self.assertNotIn(".join(", source)
        self.assertNotIn("bytearray(", source)
        self.assertNotIn("memoryview(", source)

    def test_progress_is_replayed_before_planning(self):
        source = inspect.getsource(BoundedInboundHttpReadPlanner._probe_with_configuration_guard)
        self.assertIn("witnessed = replace(progress)", source)
        self.assertLess(source.index("witnessed = replace(progress)"), source.index("return witnessed"))

    def test_source_has_no_network_reader_writer_tls_server_process_or_persistence_surface(self):
        source = inspect.getsource(read_plan_module)
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

    def test_custom_m37_limits_remain_within_custom_m36_limits(self):
        stream = BoundedInboundHttpStreamAssembler(
            wire_adapter=self.wire,
            limits=InboundHttpStreamLimits(max_chunks=3, max_chunk_bytes=256),
        )
        planner = BoundedInboundHttpReadPlanner(
            stream_assembler=stream,
            limits=InboundHttpReadLimits(max_read_calls=3, max_read_bytes=256),
        )
        self.assertEqual(planner.limits.max_read_calls, 3)
        self.assertEqual(planner.limits.max_read_bytes, 256)
        object.__setattr__(stream, "_max_chunks", 4)
        with self.assertRaises(InboundHttpReadPlanError) as caught:
            planner.plan(b"", reads_completed=0)
        self.assertEqual(caught.exception.code, "STREAM_CONFIGURATION_DRIFT")


if __name__ == "__main__":
    unittest.main()
