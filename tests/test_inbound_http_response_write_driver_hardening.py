from __future__ import annotations

import ast
import inspect
import pathlib
import unittest

from marketplace.runtime.inbound_http_response_write_driver import (
    BoundedInboundHttpResponseWriteDriver,
    InboundHttpResponseWriteDriverError,
)
from marketplace.runtime.inbound_http_response_write_invoke import (
    BoundedInboundHttpResponseWriteInvoker,
)
from marketplace.runtime.inbound_http_response_write_outcome import (
    InboundHttpResponseWriteOutcome,
)
from test_inbound_http_response_write_driver import _driver

ROOT = pathlib.Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src/marketplace/runtime/inbound_http_response_write_driver.py"


class InboundHttpResponseWriteDriverHardeningTests(unittest.TestCase):
    def test_constructor_has_no_writer_or_transport_parameter(self):
        params = inspect.signature(BoundedInboundHttpResponseWriteDriver).parameters
        self.assertEqual(set(params), {"write_invoker", "clock", "limits"})
    def test_run_to_completion_contains_exactly_one_bounded_loop(self):
        tree = ast.parse(SOURCE.read_text(encoding="utf-8-sig"))
        target = None
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == "run_to_completion":
                target = node
                break
        self.assertIsNotNone(target)
        loops = [node for node in ast.walk(target) if isinstance(node, (ast.For, ast.While))]
        self.assertEqual(len(loops), 1)
        self.assertIsInstance(loops[0], ast.For)

    def test_public_m48_method_replacement_cannot_substitute_captured_authority(self):
        _, _, _, driver = _driver(
            writer=lambda data: InboundHttpResponseWriteOutcome.progress(len(data)),
            max_write_calls=1,
        )
        original = BoundedInboundHttpResponseWriteInvoker.invoke_once
        try:
            BoundedInboundHttpResponseWriteInvoker.invoke_once = lambda self: (_ for _ in ()).throw(RuntimeError("replacement"))
            result = driver.run_to_completion()
        finally:
            BoundedInboundHttpResponseWriteInvoker.invoke_once = original
        self.assertEqual(result.writer_invocations, 1)
    def test_private_captured_invoke_rebind_fails_before_writer_consumption(self):
        calls = 0
        def writer(data: bytes):
            nonlocal calls
            calls += 1
            return InboundHttpResponseWriteOutcome.progress(len(data))
        _, session, _, driver = _driver(writer=writer)
        driver._invoke = lambda: None
        with self.assertRaises(InboundHttpResponseWriteDriverError) as ctx:
            driver.run_to_completion()
        self.assertEqual(ctx.exception.code, "WRITE_DRIVER_BINDING_DRIFT")
        self.assertEqual(calls, 0)
        self.assertTrue(session.closed)

    def test_retained_m44_limit_drift_after_consumption_closes_before_error(self):
        calls = 0
        holder = {}
        def writer(data: bytes):
            nonlocal calls
            calls += 1
            holder["session"]._max_write_calls += 1
            return InboundHttpResponseWriteOutcome.progress(min(1, len(data)))
        _, session, _, driver = _driver(writer=writer, max_write_calls=8)
        holder["session"] = session
        with self.assertRaises(InboundHttpResponseWriteDriverError) as ctx:
            driver.run_to_completion()
        self.assertEqual(ctx.exception.code, "WRITE_DRIVER_INVOCATION_REJECTED")
        self.assertEqual(ctx.exception.invocation_code, "WRITE_INVOCATION_OUTCOME_REJECTED")
        self.assertEqual(ctx.exception.outcome_code, "WRITE_OUTCOME_SESSION_REJECTED")
        self.assertEqual(ctx.exception.session_code, "WRITE_SESSION_CONFIGURATION_DRIFT")
        self.assertEqual(calls, 1)
        self.assertTrue(session.closed)

    def test_drifted_cleanup_binding_reports_uncertain(self):
        _, session, _, driver = _driver(
            writer=lambda data: InboundHttpResponseWriteOutcome.progress(len(data))
        )
        original = driver._close
        driver._close = lambda: None
        with self.assertRaises(InboundHttpResponseWriteDriverError) as ctx:
            driver.close()
        self.assertEqual(ctx.exception.code, "WRITE_DRIVER_CLEANUP_UNCERTAIN")
        driver._close = original
        driver.close()
        self.assertTrue(session.closed)

    def test_completion_result_contains_no_raw_response_bytes(self):
        _, _, _, driver = _driver(
            writer=lambda data: InboundHttpResponseWriteOutcome.progress(len(data)),
            max_write_calls=1,
        )
        result = driver.run_to_completion()
        self.assertFalse(any(type(value) is bytes for value in vars(result).values()))
        self.assertFalse(any(type(value) is bytes for value in vars(result.completed).values()))
        self.assertFalse(result.transmitted)
        self.assertFalse(result.tls_terminated)


if __name__ == "__main__":
    unittest.main()
