from __future__ import annotations

import ast
import inspect
import unittest
from dataclasses import fields, replace
from pathlib import Path

import marketplace.runtime as runtime
from marketplace.runtime.inbound_http import (
    BoundedInboundHttpApplicationAdapter,
    InboundHttpApplicationLimits,
)
from marketplace.runtime.inbound_http_read_outcome import (
    READ_OUTCOME_DATA,
    READ_OUTCOME_EOF,
    READ_OUTCOME_FAILURE,
    BoundedInboundHttpReadOutcomeHandler,
    InboundHttpReadOutcome,
    InboundHttpReadOutcomeError,
)
from marketplace.runtime.inbound_http_read_plan import BoundedInboundHttpReadPlanner
from marketplace.runtime.inbound_http_read_session import (
    BoundedInboundHttpReadSession,
    CompletedInboundHttpReadSession,
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
        raise AssertionError("M40 MUST remain below application disclosure")


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
    return harness, session, handler, raw


class InboundHttpReadOutcomeHardeningTests(unittest.TestCase):
    def test_public_runtime_exports_are_exact_m40_types_and_constants(self):
        self.assertIs(runtime.BoundedInboundHttpReadOutcomeHandler, BoundedInboundHttpReadOutcomeHandler)
        self.assertIs(runtime.InboundHttpReadOutcome, InboundHttpReadOutcome)
        self.assertIs(runtime.InboundHttpReadOutcomeError, InboundHttpReadOutcomeError)
        self.assertEqual(runtime.READ_OUTCOME_DATA, READ_OUTCOME_DATA)
        self.assertEqual(runtime.READ_OUTCOME_EOF, READ_OUTCOME_EOF)
        self.assertEqual(runtime.READ_OUTCOME_FAILURE, READ_OUTCOME_FAILURE)

    def test_api_accepts_no_reader_callback_socket_or_external_count(self):
        constructor = tuple(inspect.signature(BoundedInboundHttpReadOutcomeHandler).parameters)
        apply_parameters = tuple(
            inspect.signature(BoundedInboundHttpReadOutcomeHandler.accept_outcome).parameters
        )
        self.assertEqual(constructor, ("read_session",))
        self.assertEqual(apply_parameters, ("self", "outcome"))
        for forbidden in ("reader", "callback", "socket", "reads_completed", "prefix"):
            self.assertNotIn(forbidden, apply_parameters)

    def test_outcome_witness_binds_digest_not_second_raw_chunk(self):
        raw = b"secret-request-fragment"
        outcome = InboundHttpReadOutcome.data(raw)
        self.assertEqual(outcome.chunk, raw)
        self.assertNotIn(raw, outcome.integrity_snapshot)
        self.assertEqual(tuple(field.name for field in fields(outcome)).count("chunk"), 1)

        with self.assertRaises(ValueError):
            replace(outcome, chunk=b"different")
        with self.assertRaises(ValueError):
            replace(outcome, kind=READ_OUTCOME_EOF)

    def test_public_progress_is_exact_m39_progress_and_contains_no_raw_prefix(self):
        _, _, handler, _ = _build()
        progress = handler.accept_outcome(InboundHttpReadOutcome.data(b"GET "))
        self.assertIs(type(progress), InboundHttpReadSessionProgress)
        field_names = {field.name for field in fields(progress)}
        self.assertNotIn("prefix", field_names)
        self.assertNotIn("chunk", field_names)
        self.assertNotIn("raw_prefix", field_names)

    def test_public_m39_method_replacement_after_construction_cannot_substitute_authority(self):
        harness, session, handler, raw = _build()
        originals = (
            BoundedInboundHttpReadSession.progress,
            BoundedInboundHttpReadSession.accept_chunk,
            BoundedInboundHttpReadSession.take_completed,
            BoundedInboundHttpReadSession.close,
        )

        def hostile(*args, **kwargs):
            raise AssertionError("replaced public M39 method MUST NOT be invoked")

        try:
            BoundedInboundHttpReadSession.progress = hostile
            BoundedInboundHttpReadSession.accept_chunk = hostile
            BoundedInboundHttpReadSession.take_completed = hostile
            BoundedInboundHttpReadSession.close = hostile
            progress = handler.accept_outcome(InboundHttpReadOutcome.data(raw))
            self.assertEqual(progress.buffered_bytes, len(raw))
            completed = handler.take_completed()
            self.assertEqual(completed.prefix, raw)
            self.assertTrue(handler.closed)
        finally:
            (
                BoundedInboundHttpReadSession.progress,
                BoundedInboundHttpReadSession.accept_chunk,
                BoundedInboundHttpReadSession.take_completed,
                BoundedInboundHttpReadSession.close,
            ) = originals

        self.assertEqual(harness.calls, [])
        self.assertTrue(session.closed)

    def test_private_captured_helper_rebinding_fails_closed_before_data_adoption(self):
        _, session, handler, _ = _build()
        before = handler.progress()
        handler._accept = handler._progress
        with self.assertRaises(InboundHttpReadOutcomeError) as caught:
            handler.accept_outcome(InboundHttpReadOutcome.data(b"GET "))
        self.assertEqual(caught.exception.code, "READ_OUTCOME_BINDING_DRIFT")
        self.assertEqual(session._prefix, b"")
        self.assertEqual(session._reads_completed, before.reads_completed)

    def test_forged_progress_witness_is_rejected(self):
        _, _, handler, _ = _build()
        progress = handler.progress()
        forged = object.__new__(InboundHttpReadSessionProgress)
        object.__setattr__(forged, "buffered_bytes", progress.buffered_bytes + 1)
        object.__setattr__(forged, "reads_completed", progress.reads_completed)
        object.__setattr__(forged, "last_accepted_chunk_bytes", progress.last_accepted_chunk_bytes)
        object.__setattr__(forged, "plan", progress.plan)
        object.__setattr__(forged, "integrity_snapshot", progress.integrity_snapshot)
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
            object.__setattr__(forged, name, False)
        with self.assertRaises(InboundHttpReadOutcomeError) as caught:
            handler._replay_progress(forged)
        self.assertEqual(caught.exception.code, "READ_OUTCOME_PROGRESS_DRIFT")

    def test_forged_completion_witness_is_rejected_by_m39_replay(self):
        _, _, handler, raw = _build()
        handler.accept_outcome(InboundHttpReadOutcome.data(raw))
        completed = handler.take_completed()
        self.assertIs(type(completed), CompletedInboundHttpReadSession)
        with self.assertRaises(ValueError):
            replace(completed, prefix=b"different")

    def test_terminal_eof_and_failure_are_destructive_and_close_is_still_idempotent(self):
        for outcome, code in (
            (InboundHttpReadOutcome.eof(), "READ_EOF_BEFORE_COMPLETE"),
            (InboundHttpReadOutcome.failure(), "READ_FAILURE_BEFORE_COMPLETE"),
        ):
            with self.subTest(kind=outcome.kind):
                _, session, handler, _ = _build()
                handler.accept_outcome(InboundHttpReadOutcome.data(b"GET "))
                with self.assertRaises(InboundHttpReadOutcomeError) as caught:
                    handler.accept_outcome(outcome)
                self.assertEqual(caught.exception.code, code)
                self.assertEqual(session._prefix, b"")
                self.assertTrue(handler.closed)
                handler.close()
                self.assertTrue(handler.closed)

    def test_authority_negative_facts_remain_false_on_outcome_progress_and_completion(self):
        _, _, handler, raw = _build()
        outcome = InboundHttpReadOutcome.data(raw)
        progress = handler.accept_outcome(outcome)
        completed = handler.take_completed()
        for value in (outcome, progress, completed):
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

    def test_source_has_no_network_reader_writer_tls_server_process_persistence_or_background_surface(self):
        source_path = (
            Path(__file__).resolve().parents[1]
            / "src/marketplace/runtime/inbound_http_read_outcome.py"
        )
        source = source_path.read_text(encoding="utf-8")
        tree = ast.parse(source)

        forbidden_import_roots = {
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
                    self.assertNotIn(
                        node.func.attr,
                        {"recv", "recv_into", "send", "sendall", "listen", "connect", "bind"},
                    )

        accept_source = inspect.getsource(BoundedInboundHttpReadOutcomeHandler.accept_outcome)
        for forbidden in (
            "prefix +",
            ".join(",
            "bytearray(",
            "memoryview(",
            ".recv(",
            ".read(",
            ".send(",
            ".write(",
        ):
            self.assertNotIn(forbidden, accept_source)
        self.assertEqual(accept_source.count("self._accept("), 1)


if __name__ == "__main__":
    unittest.main()
