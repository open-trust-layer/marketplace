from __future__ import annotations

import unittest
from dataclasses import fields, replace

from marketplace.runtime.inbound_http_response_prepare import BoundedInboundHttpResponsePreparer
from marketplace.runtime.inbound_http_response_write_driver import InboundHttpResponseWriteDriverLimits
from marketplace.runtime.inbound_http_response_write_outcome import InboundHttpResponseWriteOutcome
from marketplace.runtime.inbound_http_response_write_plan import InboundHttpResponseWriteLimits
from marketplace.runtime.inbound_http_transaction import (
    BoundedInboundHttpRequestResponseTransaction,
    CompletedInboundHttpRequestResponseTransaction,
    InboundHttpRequestResponseTransactionError,
)
from test_inbound_http_response_prepare import _build


def _transaction(reader, writer, *, max_read_bytes=64 * 1024, max_read_calls=64,
                 write_limits=None, write_driver_limits=None, clock=lambda: 0.0):
    harness, _, _, read_session, read_driver, raw = _build(
        reader, max_read_bytes=max_read_bytes, max_read_calls=max_read_calls
    )
    preparer = BoundedInboundHttpResponsePreparer(read_driver=read_driver)
    transaction = BoundedInboundHttpRequestResponseTransaction(
        response_preparer=preparer,
        writer=writer,
        clock=clock,
        write_limits=write_limits,
        write_driver_limits=write_driver_limits,
    )
    return harness, read_session, preparer, transaction, raw


class InboundHttpTransactionTests(unittest.TestCase):
    def test_one_read_one_write_completes_detached_accounting_only(self):
        holder = {}
        reads = []
        writes = []

        def reader(max_bytes):
            reads.append(max_bytes)
            return holder["outcome"]

        def writer(data: bytes):
            writes.append(bytes(data))
            return InboundHttpResponseWriteOutcome.progress(len(data))

        harness, read_session, preparer, transaction, raw = _transaction(reader, writer)
        from marketplace.runtime.inbound_http_read_outcome import InboundHttpReadOutcome
        holder["outcome"] = InboundHttpReadOutcome.data(raw)

        result = transaction.run()

        self.assertIs(type(result), CompletedInboundHttpRequestResponseTransaction)
        self.assertEqual(len(reads), 1)
        self.assertEqual(len(writes), 1)
        self.assertEqual(len(harness.calls), 1)
        self.assertTrue(read_session.closed)
        self.assertTrue(preparer.used)
        self.assertTrue(transaction.used)
        self.assertEqual(result.reader_invocations, 1)
        self.assertEqual(result.read_driver_steps, 2)
        self.assertEqual(result.writer_invocations, 1)
        self.assertEqual(result.write_calls_completed, 1)
        self.assertEqual(result.write_driver_steps, 2)
        self.assertEqual(result.bytes_written, result.response_bytes)
        self.assertEqual(sum(map(len, writes)), result.response_bytes)
        self.assertTrue(result.transaction_completed)
        self.assertTrue(result.local_write_accounting_complete)
        self.assertFalse(result.transmitted)
        self.assertFalse(result.network_origin_proven)
        self.assertFalse(result.tls_terminated)
        self.assertEqual(len(result.preparation_integrity_sha256), 64)
        self.assertEqual(len(result.write_completion_integrity_sha256), 64)

    def test_multi_read_and_partial_writes_preserve_bounded_accounting(self):
        from marketplace.runtime.inbound_http_read_outcome import InboundHttpReadOutcome
        holder = {"raw": b"", "offset": 0}
        writer_calls = []

        def reader(max_bytes):
            start = holder["offset"]
            end = min(start + max_bytes, len(holder["raw"]))
            holder["offset"] = end
            return InboundHttpReadOutcome.data(holder["raw"][start:end])

        def writer(data: bytes):
            accepted = min(8, len(data))
            writer_calls.append(accepted)
            return InboundHttpResponseWriteOutcome.progress(accepted)

        _, _, _, transaction, raw = _transaction(
            reader, writer, max_read_bytes=8, max_read_calls=64,
            write_limits=InboundHttpResponseWriteLimits(max_write_calls=64, max_write_bytes=16),
        )
        holder["raw"] = raw
        result = transaction.run()
        self.assertGreater(result.reader_invocations, 1)
        self.assertGreater(result.writer_invocations, 1)
        self.assertEqual(result.writer_invocations, len(writer_calls))
        self.assertEqual(result.write_calls_completed, len(writer_calls))
        self.assertEqual(sum(writer_calls), result.response_bytes)
        self.assertEqual(result.write_driver_steps, result.writer_invocations + 1)

    def test_preparation_failure_never_calls_writer_and_preserves_read_codes(self):
        from marketplace.runtime.inbound_http_read_outcome import InboundHttpReadOutcome
        writer_calls = 0

        def writer(data: bytes):
            nonlocal writer_calls
            writer_calls += 1
            return InboundHttpResponseWriteOutcome.progress(len(data))

        _, read_session, _, transaction, _ = _transaction(
            lambda _: InboundHttpReadOutcome.eof(), writer
        )
        with self.assertRaises(InboundHttpRequestResponseTransactionError) as caught:
            transaction.run()
        self.assertEqual(caught.exception.code, "TRANSACTION_PREPARATION_REJECTED")
        self.assertEqual(caught.exception.preparation_code, "RESPONSE_PREPARATION_READ_REJECTED")
        self.assertEqual(caught.exception.read_driver_code, "READ_DRIVER_INVOCATION_REJECTED")
        self.assertEqual(writer_calls, 0)
        self.assertTrue(read_session.closed)
        self.assertTrue(transaction.used)

    def test_writer_failure_is_terminal_redacted_and_preserves_write_codes(self):
        from marketplace.runtime.inbound_http_read_outcome import InboundHttpReadOutcome
        holder = {}
        writer_calls = 0

        def reader(_):
            return InboundHttpReadOutcome.data(holder["raw"])

        def writer(_):
            nonlocal writer_calls
            writer_calls += 1
            raise RuntimeError("TOP-SECRET-WRITER-TEXT")

        _, read_session, _, transaction, raw = _transaction(reader, writer)
        holder["raw"] = raw
        with self.assertRaises(InboundHttpRequestResponseTransactionError) as caught:
            transaction.run()
        self.assertEqual(caught.exception.code, "TRANSACTION_WRITE_REJECTED")
        self.assertEqual(caught.exception.write_driver_code, "WRITE_DRIVER_INVOCATION_REJECTED")
        self.assertEqual(caught.exception.write_invocation_code, "WRITE_INVOCATION_WRITER_FAILURE")
        self.assertNotIn("TOP-SECRET", str(caught.exception))
        self.assertEqual(writer_calls, 1)
        self.assertTrue(read_session.closed)
        with self.assertRaises(InboundHttpRequestResponseTransactionError) as second:
            transaction.run()
        self.assertEqual(second.exception.code, "TRANSACTION_USED")
        self.assertEqual(writer_calls, 1)

    def test_explicit_limits_are_detached_and_checked_before_read(self):
        from marketplace.runtime.inbound_http_read_outcome import InboundHttpReadOutcome
        reads = 0
        def reader(_):
            nonlocal reads
            reads += 1
            return InboundHttpReadOutcome.eof()
        write_limits = InboundHttpResponseWriteLimits(max_write_calls=2, max_write_bytes=8)
        driver_limits = InboundHttpResponseWriteDriverLimits(max_steps=3, max_elapsed_seconds=1.0)
        _, _, _, transaction, _ = _transaction(
            reader, lambda data: InboundHttpResponseWriteOutcome.progress(len(data)),
            write_limits=write_limits, write_driver_limits=driver_limits,
        )
        object.__setattr__(write_limits, "max_write_calls", 3)
        object.__setattr__(driver_limits, "max_steps", 4)
        self.assertEqual(transaction._write_limits.max_write_calls, 2)
        self.assertEqual(transaction._write_driver_limits.max_steps, 3)
        self.assertEqual(reads, 0)

    def test_result_integrity_blocks_rebinding(self):
        from marketplace.runtime.inbound_http_read_outcome import InboundHttpReadOutcome
        holder = {}
        def reader(_):
            return InboundHttpReadOutcome.data(holder["raw"])
        _, _, _, transaction, raw = _transaction(
            reader, lambda data: InboundHttpResponseWriteOutcome.progress(len(data))
        )
        holder["raw"] = raw
        result = transaction.run()
        with self.assertRaises(ValueError):
            replace(result, route_kind=result.route_kind + "-drift")

    def test_close_before_run_is_terminal_without_reader_or_writer(self):
        from marketplace.runtime.inbound_http_read_outcome import InboundHttpReadOutcome
        calls = {"read": 0, "write": 0}
        def reader(_):
            calls["read"] += 1
            return InboundHttpReadOutcome.eof()
        def writer(data):
            calls["write"] += 1
            return InboundHttpResponseWriteOutcome.progress(len(data))
        _, read_session, _, transaction, _ = _transaction(reader, writer)
        transaction.close()
        transaction.close()
        self.assertTrue(read_session.closed)
        self.assertEqual(calls, {"read": 0, "write": 0})
        with self.assertRaises(InboundHttpRequestResponseTransactionError) as caught:
            transaction.run()
        self.assertEqual(caught.exception.code, "TRANSACTION_USED")


if __name__ == "__main__":
    unittest.main()
