from __future__ import annotations

import ast
import inspect
import unittest
from dataclasses import fields, replace

import marketplace.runtime.inbound_http_response_prepare as m43
from marketplace.runtime.inbound_http import (
    ROUTE_FEDERATION_CONTROL,
    ROUTE_IMMUTABLE_RECORD,
    BoundedInboundHttpApplicationAdapter,
    InboundHttpApplicationLimits,
    PreparedInboundHttpResponse,
)
from marketplace.runtime.inbound_http_read_driver import BoundedInboundHttpReadDriver
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
from marketplace.runtime.inbound_http_read_transition import (
    BoundedInboundHttpReadTransitioner,
)
from marketplace.runtime.inbound_http_response_prepare import (
    BoundedInboundHttpResponsePreparer,
    InboundHttpResponsePreparationError,
    PreparedInboundHttpReadResponse,
)
from marketplace.runtime.inbound_http_stream import BoundedInboundHttpStreamAssembler
from marketplace.runtime.inbound_http_wire import BoundedInboundHttpWireAdapter
from marketplace.runtime.inbound_record import INBOUND_RECORD_RETRIEVAL_OPERATION
from marketplace.runtime.record_retrieval import _get_request_bytes

AUTHORITY = "market.example"
RECORD_ID = "r1_qcU6rT-ADJiC75Bg9w7qLSvauhY6zcEmy1dk-LrRlZc"


class _ApplicationHarness:
    def __init__(self):
        self.calls = []
        self.wrong_route = False
        self.install_transient_validator = False
        self.original_validator = None
        adapter = object.__new__(BoundedInboundHttpApplicationAdapter)
        object.__setattr__(adapter, "_limits", InboundHttpApplicationLimits())
        object.__setattr__(adapter, "handle", self._handle)
        self.adapter = adapter

    def _handle(self, request):
        self.calls.append(request)
        body = b'{"record":"prepared"}'
        route_kind = ROUTE_IMMUTABLE_RECORD
        route_operation = INBOUND_RECORD_RETRIEVAL_OPERATION
        message_type = "record"
        if self.wrong_route:
            route_kind = ROUTE_FEDERATION_CONTROL
            route_operation = "https://example.test/runtime/operation/wrong"
            message_type = "marketplace.snapshot.result.v1"

        if self.install_transient_validator:
            original = self.original_validator
            if original is None:
                raise AssertionError("test harness missing original validator")

            def hostile_validator(wire_self, result, *, request):
                BoundedInboundHttpWireAdapter._validated_application_response = original
                return result

            BoundedInboundHttpWireAdapter._validated_application_response = hostile_validator

        return PreparedInboundHttpResponse(
            request=request,
            route_kind=route_kind,
            route_operation=route_operation,
            status_code=200,
            headers=(
                ("connection", "close"),
                ("content-length", str(len(body))),
                ("content-type", "application/json"),
            ),
            body=body,
            olp_message_type=message_type,
        )


def _build(
    reader,
    *,
    max_read_bytes=64 * 1024,
    max_read_calls=64,
):
    harness = _ApplicationHarness()
    wire = BoundedInboundHttpWireAdapter(
        application_adapter=harness.adapter,
        authority=AUTHORITY,
    )
    stream = BoundedInboundHttpStreamAssembler(wire_adapter=wire)
    planner = BoundedInboundHttpReadPlanner(
        stream_assembler=stream,
        limits=InboundHttpReadLimits(
            max_read_calls=max_read_calls,
            max_read_bytes=max_read_bytes,
        ),
    )
    transitioner = BoundedInboundHttpReadTransitioner(read_planner=planner)
    session = BoundedInboundHttpReadSession(read_transitioner=transitioner)
    handler = BoundedInboundHttpReadOutcomeHandler(read_session=session)
    invoker = BoundedInboundHttpReadInvoker(
        read_outcome_handler=handler,
        reader=reader,
    )
    driver = BoundedInboundHttpReadDriver(
        read_invoker=invoker,
        clock=lambda: 0.0,
    )
    raw = _get_request_bytes(
        f"/v1/records/{RECORD_ID}",
        AUTHORITY,
        443,
    )
    return harness, wire, stream, session, driver, raw


class InboundHttpResponsePreparationTests(unittest.TestCase):
    def test_one_read_prepares_exactly_one_unsent_response(self):
        holder = {}
        reader_calls = []

        def reader(max_bytes):
            reader_calls.append(max_bytes)
            return InboundHttpReadOutcome.data(holder["raw"])

        harness, _, _, session, driver, raw = _build(reader)
        holder["raw"] = raw
        preparer = BoundedInboundHttpResponsePreparer(read_driver=driver)

        result = preparer.prepare()

        self.assertIs(type(result), PreparedInboundHttpReadResponse)
        self.assertEqual(len(reader_calls), 1)
        self.assertEqual(len(harness.calls), 1)
        self.assertTrue(session.closed)
        self.assertTrue(preparer.used)
        self.assertEqual(result.driver_steps, 2)
        self.assertEqual(result.reader_invocations, 1)
        self.assertEqual(result.reads_completed, 1)
        self.assertEqual(result.request_bytes, len(raw))
        self.assertEqual(result.completion_plan.buffered_bytes, len(raw))
        self.assertEqual(
            result.completion_plan.reads_completed,
            result.reads_completed,
        )
        self.assertEqual(result.wire_exchange.route_kind, ROUTE_IMMUTABLE_RECORD)
        self.assertTrue(result.response_prepared)
        self.assertFalse(result.transmitted)
        self.assertFalse(result.wire_exchange.transmitted)

    def test_multi_read_aggregate_larger_than_one_m36_chunk_prepares(self):
        holder = {"offset": 0}
        reader_calls = []

        def reader(max_bytes):
            reader_calls.append(max_bytes)
            start = holder["offset"]
            end = min(start + max_bytes, len(holder["raw"]))
            holder["offset"] = end
            return InboundHttpReadOutcome.data(holder["raw"][start:end])

        harness, _, stream, _, driver, raw = _build(
            reader,
            max_read_bytes=8,
            max_read_calls=64,
        )
        holder["raw"] = raw
        self.assertGreater(len(raw), 8)

        def forbidden_prepare_chunks(_):
            raise AssertionError("M43 MUST NOT reinterpret aggregate bytes as one M36 chunk")

        stream.prepare_chunks = forbidden_prepare_chunks
        result = BoundedInboundHttpResponsePreparer(read_driver=driver).prepare()

        self.assertGreater(result.reader_invocations, 1)
        self.assertEqual(result.reads_completed, result.reader_invocations)
        self.assertEqual(result.request_bytes, len(raw))
        self.assertEqual(len(harness.calls), 1)

    def test_precompleted_session_requires_zero_new_reader_calls(self):
        reader_calls = []

        def reader(max_bytes):
            reader_calls.append(max_bytes)
            return InboundHttpReadOutcome.eof()

        harness, _, _, session, driver, raw = _build(reader)
        session.accept_chunk(raw)
        preparer = BoundedInboundHttpResponsePreparer(read_driver=driver)

        result = preparer.prepare()

        self.assertEqual(reader_calls, [])
        self.assertEqual(result.reader_invocations, 0)
        self.assertEqual(result.reads_completed, 1)
        self.assertEqual(result.driver_steps, 1)
        self.assertEqual(result.request_bytes, len(raw))
        self.assertEqual(len(harness.calls), 1)

    def test_prepare_is_one_shot(self):
        holder = {}

        def reader(_):
            return InboundHttpReadOutcome.data(holder["raw"])

        _, _, _, _, driver, raw = _build(reader)
        holder["raw"] = raw
        preparer = BoundedInboundHttpResponsePreparer(read_driver=driver)
        preparer.prepare()

        with self.assertRaises(InboundHttpResponsePreparationError) as caught:
            preparer.prepare()
        self.assertEqual(caught.exception.code, "RESPONSE_PREPARER_USED")

    def test_terminal_m42_failure_never_retries_or_reaches_application(self):
        calls = []

        def reader(max_bytes):
            calls.append(max_bytes)
            return InboundHttpReadOutcome.eof()

        harness, _, _, _, driver, _ = _build(reader)
        preparer = BoundedInboundHttpResponsePreparer(read_driver=driver)

        with self.assertRaises(InboundHttpResponsePreparationError) as caught:
            preparer.prepare()

        self.assertEqual(caught.exception.code, "RESPONSE_PREPARATION_READ_REJECTED")
        self.assertEqual(len(calls), 1)
        self.assertEqual(harness.calls, [])

    def test_public_m35_prepare_replacement_cannot_substitute_captured_authority(self):
        holder = {}

        def reader(_):
            return InboundHttpReadOutcome.data(holder["raw"])

        harness, wire, _, _, driver, raw = _build(reader)
        holder["raw"] = raw
        preparer = BoundedInboundHttpResponsePreparer(read_driver=driver)
        wire.prepare = lambda _: (_ for _ in ()).throw(
            AssertionError("replacement M35 prepare MUST NOT run")
        )

        result = preparer.prepare()

        self.assertEqual(result.request_bytes, len(raw))
        self.assertEqual(len(harness.calls), 1)

    def test_private_captured_prepare_rebind_fails_before_reader_or_application(self):
        reader_calls = []

        def reader(max_bytes):
            reader_calls.append(max_bytes)
            return InboundHttpReadOutcome.eof()

        harness, _, _, _, driver, _ = _build(reader)
        preparer = BoundedInboundHttpResponsePreparer(read_driver=driver)
        preparer._prepare = lambda _: None

        with self.assertRaises(InboundHttpResponsePreparationError) as caught:
            preparer.prepare()

        self.assertEqual(caught.exception.code, "RESPONSE_PREPARATION_BINDING_DRIFT")
        self.assertEqual(reader_calls, [])
        self.assertEqual(harness.calls, [])

    def test_wire_configuration_drift_fails_before_reader_or_application(self):
        reader_calls = []

        def reader(max_bytes):
            reader_calls.append(max_bytes)
            return InboundHttpReadOutcome.eof()

        harness, wire, _, _, driver, _ = _build(reader)
        preparer = BoundedInboundHttpResponsePreparer(read_driver=driver)
        object.__setattr__(wire, "_authority", "other.example")

        with self.assertRaises(InboundHttpResponsePreparationError) as caught:
            preparer.prepare()

        self.assertEqual(
            caught.exception.code,
            "RESPONSE_PREPARATION_CONFIGURATION_DRIFT",
        )
        self.assertEqual(reader_calls, [])
        self.assertEqual(harness.calls, [])

    def test_transient_hostile_m35_validator_is_caught_by_independent_replay(self):
        holder = {}

        def reader(_):
            return InboundHttpReadOutcome.data(holder["raw"])

        harness, _, _, _, driver, raw = _build(reader)
        holder["raw"] = raw
        preparer = BoundedInboundHttpResponsePreparer(read_driver=driver)
        original = BoundedInboundHttpWireAdapter._validated_application_response
        harness.original_validator = original
        harness.wrong_route = True
        harness.install_transient_validator = True

        try:
            with self.assertRaises(InboundHttpResponsePreparationError) as caught:
                preparer.prepare()
        finally:
            BoundedInboundHttpWireAdapter._validated_application_response = original

        self.assertEqual(
            caught.exception.code,
            "RESPONSE_PREPARATION_RESPONSE_REJECTED",
        )
        self.assertEqual(caught.exception.wire_code, "APPLICATION_ROUTE_BINDING_DRIFT")
        self.assertEqual(len(harness.calls), 1)

    def test_result_rebinding_cannot_change_request_accounting_or_nested_authority(self):
        holder = {}

        def reader(_):
            return InboundHttpReadOutcome.data(holder["raw"])

        _, _, _, _, driver, raw = _build(reader)
        holder["raw"] = raw
        result = BoundedInboundHttpResponsePreparer(read_driver=driver).prepare()

        with self.assertRaises(ValueError):
            replace(result, request_bytes=result.request_bytes + 1)
        object.__setattr__(result.wire_exchange, "transmitted", True)
        with self.assertRaises(InboundHttpResponsePreparationError):
            replace(result)

    def test_result_has_no_completed_raw_prefix_field_and_authority_stays_negative(self):
        holder = {}

        def reader(_):
            return InboundHttpReadOutcome.data(holder["raw"])

        _, _, _, _, driver, raw = _build(reader)
        holder["raw"] = raw
        result = BoundedInboundHttpResponsePreparer(read_driver=driver).prepare()

        names = {item.name for item in fields(PreparedInboundHttpReadResponse)}
        self.assertNotIn("prefix", names)
        self.assertNotIn("raw_request", names)
        self.assertNotIn("chunk", names)
        for name in (
            "transmitted",
            "socket_access_proven",
            "network_origin_proven",
            "request_authenticated",
            "peer_identity_proven",
            "establishes_marketplace_truth",
            "establishes_trust",
            "establishes_authorization",
            "authorizes_protected_side_effects",
        ):
            self.assertFalse(getattr(result, name))


class InboundHttpResponsePreparationSourceTests(unittest.TestCase):
    def test_public_prepare_has_no_reader_prefix_count_socket_writer_or_transport_parameter(self):
        signature = inspect.signature(BoundedInboundHttpResponsePreparer.prepare)
        self.assertEqual(tuple(signature.parameters), ("self",))

    def test_source_has_no_concrete_external_io_or_background_import_surface(self):
        source = inspect.getsource(m43)
        tree = ast.parse(source)
        forbidden_roots = {
            "socket",
            "ssl",
            "http",
            "urllib",
            "requests",
            "subprocess",
            "asyncio",
            "threading",
            "multiprocessing",
            "logging",
            "pathlib",
        }
        imported_roots = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported_roots.update(alias.name.split(".", 1)[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported_roots.add(node.module.split(".", 1)[0])
        self.assertTrue(imported_roots.isdisjoint(forbidden_roots))

        prepare_source = inspect.getsource(BoundedInboundHttpResponsePreparer.prepare)
        self.assertNotIn("prepare_chunks(", prepare_source)
        self.assertNotIn(".send(", prepare_source)
        self.assertNotIn(".write(", prepare_source)
        self.assertNotIn(".recv(", prepare_source)
        self.assertNotIn(".read(", prepare_source)
