from __future__ import annotations

import ast
import inspect
import pathlib
import unittest

from marketplace.runtime.inbound_http_read_outcome import InboundHttpReadOutcome
from marketplace.runtime.inbound_http_response_prepare import (
    BoundedInboundHttpResponsePreparer,
    PreparedInboundHttpReadResponse,
)
from marketplace.runtime.inbound_http_response_write_driver import (
    BoundedInboundHttpResponseWriteDriver,
    CompletedInboundHttpResponseWriteDriverResult,
    InboundHttpResponseWriteDriverLimits,
)
from marketplace.runtime.inbound_http_response_write_outcome import InboundHttpResponseWriteOutcome
from marketplace.runtime.inbound_http_response_write_plan import InboundHttpResponseWriteLimits
from marketplace.runtime.inbound_http_transaction import (
    BoundedInboundHttpRequestResponseTransaction,
    CompletedInboundHttpRequestResponseTransaction,
    InboundHttpRequestResponseTransactionError,
)
from test_inbound_http_transaction import _transaction

ROOT = pathlib.Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src/marketplace/runtime/inbound_http_transaction.py"


def _contains_raw_bytes(value, *, seen=None):
    if type(value) in (bytes, bytearray, memoryview):
        return True
    if seen is None:
        seen = set()
    marker = id(value)
    if marker in seen:
        return False
    seen.add(marker)
    if isinstance(value, tuple):
        return any(_contains_raw_bytes(item, seen=seen) for item in value)
    if hasattr(value, "__dict__"):
        return any(_contains_raw_bytes(item, seen=seen) for item in vars(value).values())
    return False


class InboundHttpTransactionHardeningTests(unittest.TestCase):
    def test_constructor_surface_is_exact_and_contains_no_transport_endpoint(self):
        params = inspect.signature(BoundedInboundHttpRequestResponseTransaction).parameters
        self.assertEqual(
            set(params),
            {"response_preparer", "writer", "clock", "write_limits", "write_driver_limits"},
        )
        self.assertTrue({"socket", "host", "port", "address", "credentials"}.isdisjoint(params))

    def test_run_contains_no_loop(self):
        tree = ast.parse(SOURCE.read_text(encoding="utf-8-sig"))
        target = next(
            node for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef) and node.name == "run"
        )
        self.assertEqual(
            [node for node in ast.walk(target) if isinstance(node, (ast.For, ast.While))], []
        )

    def test_source_has_no_concrete_network_process_filesystem_or_concurrency_import(self):
        tree = ast.parse(SOURCE.read_text(encoding="utf-8-sig"))
        roots = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                roots.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                roots.add(node.module.split(".")[0])
        self.assertTrue(
            {"socket", "ssl", "http", "urllib", "requests", "subprocess", "os", "pathlib",
             "logging", "threading", "asyncio", "multiprocessing"}.isdisjoint(roots)
        )

    def test_public_m43_prepare_replacement_after_construction_cannot_substitute_authority(self):
        holder = {}
        def reader(_):
            return InboundHttpReadOutcome.data(holder["raw"])
        _, _, _, transaction, raw = _transaction(
            reader, lambda data: InboundHttpResponseWriteOutcome.progress(len(data))
        )
        holder["raw"] = raw
        original = BoundedInboundHttpResponsePreparer.prepare
        try:
            BoundedInboundHttpResponsePreparer.prepare = lambda self: (_ for _ in ()).throw(
                AssertionError("replacement M43 prepare MUST NOT run")
            )
            result = transaction.run()
        finally:
            BoundedInboundHttpResponsePreparer.prepare = original
        self.assertTrue(result.transaction_completed)

    def test_private_captured_prepare_rebind_fails_before_reader_or_writer(self):
        calls = {"read": 0, "write": 0}
        def reader(_):
            calls["read"] += 1
            return InboundHttpReadOutcome.eof()
        def writer(data):
            calls["write"] += 1
            return InboundHttpResponseWriteOutcome.progress(len(data))
        _, read_session, _, transaction, _ = _transaction(reader, writer)
        transaction._prepare = lambda: None
        with self.assertRaises(InboundHttpRequestResponseTransactionError) as caught:
            transaction.run()
        self.assertEqual(caught.exception.code, "TRANSACTION_BINDING_DRIFT")
        self.assertEqual(calls, {"read": 0, "write": 0})
        self.assertTrue(read_session.closed)

    def test_reader_cannot_swap_write_class_graph_before_write_construction(self):
        holder = {}
        writer_calls = 0
        original = BoundedInboundHttpResponseWriteDriver.run_to_completion
        def reader(_):
            BoundedInboundHttpResponseWriteDriver.run_to_completion = lambda self: None
            return InboundHttpReadOutcome.data(holder["raw"])
        def writer(data):
            nonlocal writer_calls
            writer_calls += 1
            return InboundHttpResponseWriteOutcome.progress(len(data))
        _, read_session, _, transaction, raw = _transaction(reader, writer)
        holder["raw"] = raw
        try:
            with self.assertRaises(InboundHttpRequestResponseTransactionError) as caught:
                transaction.run()
        finally:
            BoundedInboundHttpResponseWriteDriver.run_to_completion = original
        self.assertEqual(caught.exception.code, "TRANSACTION_BINDING_DRIFT")
        self.assertEqual(writer_calls, 0)
        self.assertTrue(read_session.closed)

    def test_writer_class_graph_swap_is_detected_after_consumption_and_cleanup_uses_captured_close(self):
        holder = {}
        calls = 0
        original = BoundedInboundHttpResponseWriteDriver.close
        def reader(_):
            return InboundHttpReadOutcome.data(holder["raw"])
        def writer(data):
            nonlocal calls
            calls += 1
            BoundedInboundHttpResponseWriteDriver.close = lambda self: None
            return InboundHttpResponseWriteOutcome.progress(len(data))
        _, read_session, _, transaction, raw = _transaction(reader, writer)
        holder["raw"] = raw
        try:
            with self.assertRaises(InboundHttpRequestResponseTransactionError) as caught:
                transaction.run()
        finally:
            BoundedInboundHttpResponseWriteDriver.close = original
        self.assertEqual(caught.exception.code, "TRANSACTION_BINDING_DRIFT")
        self.assertEqual(calls, 1)
        self.assertTrue(read_session.closed)

    def test_drifted_m46_cleanup_function_reports_uncertain_after_consumption(self):
        holder = {}
        transaction_holder = {}
        def reader(_):
            return InboundHttpReadOutcome.data(holder["raw"])
        def writer(_):
            transaction_holder["transaction"]._session_close_function = lambda self: None
            raise RuntimeError("consumed")
        _, _, _, transaction, raw = _transaction(reader, writer)
        transaction_holder["transaction"] = transaction
        holder["raw"] = raw
        with self.assertRaises(InboundHttpRequestResponseTransactionError) as caught:
            transaction.run()
        self.assertEqual(caught.exception.code, "TRANSACTION_CLEANUP_UNCERTAIN")

    def test_clock_failure_is_redacted_terminal_and_preserves_m49_code(self):
        holder = {}
        clock_calls = 0
        def reader(_):
            return InboundHttpReadOutcome.data(holder["raw"])
        def clock():
            nonlocal clock_calls
            clock_calls += 1
            raise RuntimeError("TOP-SECRET-CLOCK-TEXT")
        _, read_session, _, transaction, raw = _transaction(
            reader,
            lambda data: InboundHttpResponseWriteOutcome.progress(len(data)),
            clock=clock,
        )
        holder["raw"] = raw
        with self.assertRaises(InboundHttpRequestResponseTransactionError) as caught:
            transaction.run()
        self.assertEqual(caught.exception.code, "TRANSACTION_WRITE_REJECTED")
        self.assertEqual(caught.exception.write_driver_code, "WRITE_DRIVER_CLOCK_FAILURE")
        self.assertNotIn("TOP-SECRET", str(caught.exception))
        self.assertEqual(clock_calls, 1)
        self.assertTrue(read_session.closed)

    def test_public_result_recursively_contains_no_raw_bytes_or_nested_m43_m49_objects(self):
        holder = {}
        def reader(_):
            return InboundHttpReadOutcome.data(holder["raw"])
        _, _, _, transaction, raw = _transaction(
            reader, lambda data: InboundHttpResponseWriteOutcome.progress(len(data))
        )
        holder["raw"] = raw
        result = transaction.run()
        self.assertFalse(_contains_raw_bytes(result))
        self.assertNotIsInstance(result, PreparedInboundHttpReadResponse)
        self.assertNotIsInstance(result, CompletedInboundHttpResponseWriteDriverResult)
        for value in vars(result).values():
            self.assertNotIsInstance(value, PreparedInboundHttpReadResponse)
            self.assertNotIsInstance(value, CompletedInboundHttpResponseWriteDriverResult)

    def test_invalid_explicit_driver_steps_fail_before_read(self):
        calls = 0
        def reader(_):
            nonlocal calls
            calls += 1
            return InboundHttpReadOutcome.eof()
        write_limits = InboundHttpResponseWriteLimits(max_write_calls=2, max_write_bytes=8)
        bad_driver_limits = InboundHttpResponseWriteDriverLimits(max_steps=4, max_elapsed_seconds=1.0)
        from test_inbound_http_response_prepare import _build
        _, _, _, _, read_driver, _ = _build(reader)
        preparer = BoundedInboundHttpResponsePreparer(read_driver=read_driver)
        with self.assertRaises(ValueError):
            BoundedInboundHttpRequestResponseTransaction(
                response_preparer=preparer,
                writer=lambda data: InboundHttpResponseWriteOutcome.progress(len(data)),
                clock=lambda: 0.0,
                write_limits=write_limits,
                write_driver_limits=bad_driver_limits,
            )
        self.assertEqual(calls, 0)


if __name__ == "__main__":
    unittest.main()
