from __future__ import annotations

import unittest

from marketplace.runtime.inbound_http_response_write_invoke import (
    WRITE_INVOCATION_COMPLETED,
    WRITE_INVOCATION_PROGRESS,
    BoundedInboundHttpResponseWriteInvoker,
    InboundHttpResponseWriteInvocationError,
)
from marketplace.runtime.inbound_http_response_write_outcome import InboundHttpResponseWriteOutcome
from test_inbound_http_response_write_outcome import _parts


class InboundHttpResponseWriteInvocationTests(unittest.TestCase):
    def test_one_writer_call_receives_exact_current_bounded_slice(self):
        prepared, _, _, _, handler = _parts(max_write_bytes=7)
        calls: list[bytes] = []
        def writer(data: bytes):
            calls.append(data)
            return InboundHttpResponseWriteOutcome.progress(3)
        invoker = BoundedInboundHttpResponseWriteInvoker(write_outcome_handler=handler, writer=writer)
        result = invoker.invoke_once()
        raw = prepared.wire_exchange.response_bytes
        self.assertEqual(calls, [raw[:7]])
        self.assertEqual(result.state, WRITE_INVOCATION_PROGRESS)
        self.assertTrue(result.writer_invoked)
        self.assertEqual(result.offered_bytes, 7)
        self.assertEqual(result.progress.bytes_written, 3)
        self.assertFalse(result.transmitted)
        self.assertFalse(result.socket_access_proven)

    def test_partial_writes_advance_without_overlap_or_retry(self):
        prepared, _, _, _, handler = _parts(max_write_bytes=5, max_write_calls=20)
        calls: list[bytes] = []
        def writer(data: bytes):
            calls.append(data)
            return InboundHttpResponseWriteOutcome.progress(min(2, len(data)))
        invoker = BoundedInboundHttpResponseWriteInvoker(write_outcome_handler=handler, writer=writer)
        first = invoker.invoke_once()
        second = invoker.invoke_once()
        raw = prepared.wire_exchange.response_bytes
        self.assertEqual(calls[0], raw[:5])
        self.assertEqual(calls[1], raw[2:7])
        self.assertEqual((first.progress.bytes_written, second.progress.bytes_written), (2, 4))
        self.assertEqual(len(calls), 2)

    def test_final_progress_requires_zero_writer_completion_transfer(self):
        prepared, _, _, session, handler = _parts(max_write_bytes=1_000_000)
        calls = 0
        def writer(data: bytes):
            nonlocal calls
            calls += 1
            return InboundHttpResponseWriteOutcome.progress(len(data))
        invoker = BoundedInboundHttpResponseWriteInvoker(write_outcome_handler=handler, writer=writer)
        progress = invoker.invoke_once()
        self.assertEqual(progress.state, WRITE_INVOCATION_PROGRESS)
        self.assertEqual(progress.progress.bytes_written, prepared.response_bytes)
        completed = invoker.invoke_once()
        self.assertEqual(completed.state, WRITE_INVOCATION_COMPLETED)
        self.assertFalse(completed.writer_invoked)
        self.assertEqual(calls, 1)
        self.assertTrue(session.closed)
        self.assertIsNone(invoker._prepared_response)

    def test_zero_and_failure_outcomes_are_terminal(self):
        for factory, expected in (
            (InboundHttpResponseWriteOutcome.zero, "WRITE_ZERO_BEFORE_COMPLETE"),
            (InboundHttpResponseWriteOutcome.failure, "WRITE_FAILURE_BEFORE_COMPLETE"),
        ):
            with self.subTest(expected=expected):
                _, _, _, session, handler = _parts()
                invoker = BoundedInboundHttpResponseWriteInvoker(
                    write_outcome_handler=handler, writer=lambda data, f=factory: f()
                )
                with self.assertRaises(InboundHttpResponseWriteInvocationError) as ctx:
                    invoker.invoke_once()
                self.assertEqual(ctx.exception.code, "WRITE_INVOCATION_OUTCOME_REJECTED")
                self.assertEqual(ctx.exception.outcome_code, expected)
                self.assertTrue(session.closed)
                self.assertIsNone(invoker._prepared_response)

    def test_writer_exception_is_generic_terminal_and_not_retried(self):
        _, _, _, session, handler = _parts()
        calls = 0
        def writer(data: bytes):
            nonlocal calls
            calls += 1
            raise RuntimeError("SECRET-WRITER-TEXT")
        invoker = BoundedInboundHttpResponseWriteInvoker(write_outcome_handler=handler, writer=writer)
        with self.assertRaises(InboundHttpResponseWriteInvocationError) as ctx:
            invoker.invoke_once()
        self.assertEqual(calls, 1)
        self.assertEqual(ctx.exception.code, "WRITE_INVOCATION_WRITER_FAILURE")
        self.assertNotIn("SECRET-WRITER-TEXT", str(ctx.exception))
        self.assertTrue(session.closed)
        self.assertIsNone(invoker._prepared_response)

    def test_non_exact_writer_result_is_terminal(self):
        _, _, _, session, handler = _parts()
        invoker = BoundedInboundHttpResponseWriteInvoker(write_outcome_handler=handler, writer=lambda data: 1)
        with self.assertRaises(InboundHttpResponseWriteInvocationError) as ctx:
            invoker.invoke_once()
        self.assertEqual(ctx.exception.code, "INVALID_WRITER_RESULT")
        self.assertTrue(session.closed)

    def test_oversized_already_returned_count_preserves_nested_codes(self):
        _, _, _, session, handler = _parts(max_write_bytes=2)
        invoker = BoundedInboundHttpResponseWriteInvoker(
            write_outcome_handler=handler,
            writer=lambda data: InboundHttpResponseWriteOutcome.progress(3),
        )
        with self.assertRaises(InboundHttpResponseWriteInvocationError) as ctx:
            invoker.invoke_once()
        self.assertEqual(ctx.exception.code, "WRITE_INVOCATION_OUTCOME_REJECTED")
        self.assertEqual(ctx.exception.outcome_code, "WRITE_OUTCOME_SESSION_REJECTED")
        self.assertEqual(ctx.exception.session_code, "WRITE_SESSION_TRANSITION_REJECTED")
        self.assertEqual(ctx.exception.transition_code, "WRITE_COUNT_EXCEEDS_PLAN")
        self.assertTrue(session.closed)

    def test_close_is_idempotent_and_releases_local_response_reference(self):
        _, _, _, session, handler = _parts()
        invoker = BoundedInboundHttpResponseWriteInvoker(
            write_outcome_handler=handler,
            writer=lambda data: InboundHttpResponseWriteOutcome.progress(1),
        )
        invoker.close()
        invoker.close()
        self.assertTrue(invoker.closed)
        self.assertTrue(session.closed)
        self.assertIsNone(invoker._prepared_response)


if __name__ == "__main__":
    unittest.main()
