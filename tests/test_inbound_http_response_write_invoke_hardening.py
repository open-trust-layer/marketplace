from __future__ import annotations

import ast
import inspect
import unittest
from unittest.mock import patch

from marketplace.runtime.inbound_http_response_write_invoke import (
    BoundedInboundHttpResponseWriteInvoker,
    InboundHttpResponseWriteInvocationError,
)
from marketplace.runtime.inbound_http_response_write_outcome import (
    BoundedInboundHttpResponseWriteOutcomeHandler,
    InboundHttpResponseWriteOutcome,
)
from test_inbound_http_response_write_outcome import _parts


class InboundHttpResponseWriteInvocationHardeningTests(unittest.TestCase):
    def test_promoted_original_writer_outcome_is_rejected_and_cleared(self):
        _, _, _, session, handler = _parts()
        def writer(data: bytes):
            outcome = InboundHttpResponseWriteOutcome.progress(1)
            object.__setattr__(outcome, "transmitted", True)
            return outcome
        invoker = BoundedInboundHttpResponseWriteInvoker(write_outcome_handler=handler, writer=writer)
        with self.assertRaises(InboundHttpResponseWriteInvocationError) as ctx:
            invoker.invoke_once()
        self.assertEqual(ctx.exception.code, "WRITE_INVOCATION_OUTCOME_AUTHORITY")
        self.assertTrue(session.closed)
        self.assertIsNone(invoker._prepared_response)

    def test_writer_mutating_m47_binding_after_call_is_terminal_but_m46_is_cleared(self):
        _, _, _, session, handler = _parts()
        invoker = None
        def writer(data: bytes):
            handler._session = object()
            return InboundHttpResponseWriteOutcome.progress(1)
        invoker = BoundedInboundHttpResponseWriteInvoker(write_outcome_handler=handler, writer=writer)
        with self.assertRaises(InboundHttpResponseWriteInvocationError) as ctx:
            invoker.invoke_once()
        self.assertEqual(ctx.exception.code, "WRITE_INVOCATION_BINDING_DRIFT")
        self.assertTrue(session.closed)
        self.assertIsNone(session._prepared_response)
        self.assertIsNone(invoker._prepared_response)

    def test_drifted_cleanup_binding_reports_uncertain(self):
        _, _, _, session, handler = _parts()
        invoker = None
        def writer(data: bytes):
            invoker._session_close = lambda: None
            return InboundHttpResponseWriteOutcome.progress(1)
        invoker = BoundedInboundHttpResponseWriteInvoker(write_outcome_handler=handler, writer=writer)
        with self.assertRaises(InboundHttpResponseWriteInvocationError) as ctx:
            invoker.invoke_once()
        self.assertEqual(ctx.exception.code, "WRITE_INVOCATION_CLEANUP_UNCERTAIN")
        self.assertFalse(session._closed)

    def test_public_m47_method_replacement_cannot_substitute_captured_authority(self):
        _, _, _, _, handler = _parts()
        calls = []
        invoker = BoundedInboundHttpResponseWriteInvoker(
            write_outcome_handler=handler,
            writer=lambda data: (calls.append(data), InboundHttpResponseWriteOutcome.progress(1))[1],
        )
        with patch.object(BoundedInboundHttpResponseWriteOutcomeHandler, "progress", lambda self: None):
            result = invoker.invoke_once()
        self.assertEqual(result.progress.bytes_written, 1)
        self.assertEqual(len(calls), 1)

    def test_pre_writer_prepared_authority_drift_never_calls_writer(self):
        prepared, _, _, _, handler = _parts()
        calls = 0
        def writer(data: bytes):
            nonlocal calls
            calls += 1
            return InboundHttpResponseWriteOutcome.progress(1)
        invoker = BoundedInboundHttpResponseWriteInvoker(write_outcome_handler=handler, writer=writer)
        object.__setattr__(prepared, "transmitted", True)
        with self.assertRaises((InboundHttpResponseWriteInvocationError, Exception)):
            invoker.invoke_once()
        self.assertEqual(calls, 0)

    def test_result_and_witness_never_retain_raw_response_bytes(self):
        prepared, _, _, _, handler = _parts()
        invoker = BoundedInboundHttpResponseWriteInvoker(
            write_outcome_handler=handler,
            writer=lambda data: InboundHttpResponseWriteOutcome.progress(1),
        )
        result = invoker.invoke_once()
        raw = prepared.wire_exchange.response_bytes
        self.assertNotIn(raw, result.__dict__.values())
        self.assertNotIn(raw, result.integrity_snapshot)
        self.assertFalse(result.transmitted)
        self.assertFalse(result.establishes_authorization)

    def test_public_api_exposes_only_injected_writer_not_transport_configuration(self):
        signature = inspect.signature(BoundedInboundHttpResponseWriteInvoker.__init__)
        self.assertEqual(tuple(signature.parameters), ("self", "write_outcome_handler", "writer"))
        invoke = inspect.signature(BoundedInboundHttpResponseWriteInvoker.invoke_once)
        self.assertEqual(tuple(invoke.parameters), ("self",))

    def test_invoke_once_contains_no_loop_or_retry_surface(self):
        source = inspect.getsource(BoundedInboundHttpResponseWriteInvoker.invoke_once)
        tree = ast.parse(source.lstrip())
        self.assertFalse(any(isinstance(node, (ast.For, ast.While, ast.AsyncFor)) for node in ast.walk(tree)))
        lowered = source.lower()
        for forbidden in ("socket", "ssl", "http.client", "subprocess", "thread", "sleep("):
            self.assertNotIn(forbidden, lowered)


if __name__ == "__main__":
    unittest.main()
