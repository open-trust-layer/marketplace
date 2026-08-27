from __future__ import annotations

import math
import unittest

from marketplace.runtime.inbound_http_response_write_driver import (
    BoundedInboundHttpResponseWriteDriver,
    InboundHttpResponseWriteDriverError,
    InboundHttpResponseWriteDriverLimits,
)
from marketplace.runtime.inbound_http_response_write_invoke import (
    BoundedInboundHttpResponseWriteInvoker,
)
from marketplace.runtime.inbound_http_response_write_outcome import (
    InboundHttpResponseWriteOutcome,
)
from test_inbound_http_response_write_outcome import _parts


def _driver(*, writer, max_write_bytes=1_000_000, max_write_calls=8, clock=lambda: 0.0, limits=None):
    prepared, _, _, session, handler = _parts(
        max_write_bytes=max_write_bytes,
        max_write_calls=max_write_calls,
    )
    invoker = BoundedInboundHttpResponseWriteInvoker(
        write_outcome_handler=handler,
        writer=writer,
    )
    driver = BoundedInboundHttpResponseWriteDriver(
        write_invoker=invoker,
        clock=clock,
        limits=limits,
    )
    return prepared, session, invoker, driver


class InboundHttpResponseWriteDriverTests(unittest.TestCase):
    def test_one_writer_call_plus_zero_writer_completion_transfer(self):
        calls: list[bytes] = []
        def writer(data: bytes):
            calls.append(data)
            return InboundHttpResponseWriteOutcome.progress(len(data))
        prepared, session, _, driver = _driver(writer=writer, max_write_calls=1)
        result = driver.run_to_completion()
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0], prepared.wire_exchange.response_bytes)
        self.assertEqual(result.driver_steps, 2)
        self.assertEqual(result.writer_invocations, 1)
        self.assertEqual(result.write_calls_completed, 1)
        self.assertEqual(result.completed.bytes_written, prepared.response_bytes)
        self.assertTrue(session.closed)
        self.assertFalse(result.transmitted)
        self.assertFalse(result.tls_terminated)

    def test_default_64_writes_reserve_step_65_for_zero_writer_completion(self):
        calls = 0

        def writer(data: bytes):
            nonlocal calls
            calls += 1
            accepted = 1 if calls < 64 else len(data)
            return InboundHttpResponseWriteOutcome.progress(accepted)

        prepared, session, _, driver = _driver(writer=writer, max_write_calls=64)
        self.assertGreater(prepared.response_bytes, 64)

        result = driver.run_to_completion()

        self.assertEqual(driver.limits.max_steps, 65)
        self.assertEqual(result.driver_steps, 65)
        self.assertEqual(result.writer_invocations, 64)
        self.assertEqual(calls, 64)
        self.assertEqual(result.completed.bytes_written, prepared.response_bytes)
        self.assertTrue(session.closed)

    def test_default_step_limit_includes_completion_transfer(self):
        _, _, _, driver = _driver(
            writer=lambda data: InboundHttpResponseWriteOutcome.progress(len(data)),
            max_write_calls=3,
        )
        self.assertEqual(driver.limits.max_steps, 4)
        self.assertEqual(driver.m44_max_write_calls, 3)

    def test_explicit_step_limit_cannot_exceed_lower_ceiling_plus_transfer(self):
        _, _, _, _, handler = _parts(max_write_calls=2)
        invoker = BoundedInboundHttpResponseWriteInvoker(
            write_outcome_handler=handler,
            writer=lambda data: InboundHttpResponseWriteOutcome.progress(len(data)),
        )
        with self.assertRaises(ValueError):
            BoundedInboundHttpResponseWriteDriver(
                write_invoker=invoker,
                clock=lambda: 0.0,
                limits=InboundHttpResponseWriteDriverLimits(max_steps=4),
            )

    def test_step_exhaustion_is_terminal_and_clears(self):
        calls = 0
        def writer(data: bytes):
            nonlocal calls
            calls += 1
            return InboundHttpResponseWriteOutcome.progress(len(data))
        _, session, _, driver = _driver(
            writer=writer,
            max_write_calls=2,
            limits=InboundHttpResponseWriteDriverLimits(max_steps=1),
        )
        with self.assertRaises(InboundHttpResponseWriteDriverError) as ctx:
            driver.run_to_completion()
        self.assertEqual(ctx.exception.code, "WRITE_DRIVER_STEP_LIMIT_EXHAUSTED")
        self.assertEqual(calls, 1)
        self.assertTrue(session.closed)

    def test_time_limit_before_next_step_prevents_second_writer_call(self):
        values = iter((0.0, 0.0, 0.1, 2.0))
        calls = 0
        def writer(data: bytes):
            nonlocal calls
            calls += 1
            return InboundHttpResponseWriteOutcome.progress(min(1, len(data)))
        _, session, _, driver = _driver(
            writer=writer,
            max_write_calls=8,
            clock=lambda: next(values),
            limits=InboundHttpResponseWriteDriverLimits(max_steps=8, max_elapsed_seconds=1.0),
        )
        with self.assertRaises(InboundHttpResponseWriteDriverError) as ctx:
            driver.run_to_completion()
        self.assertEqual(ctx.exception.code, "WRITE_DRIVER_TIME_LIMIT_EXHAUSTED")
        self.assertEqual(calls, 1)
        self.assertTrue(session.closed)

    def test_clock_regression_after_consumption_is_terminal(self):
        values = iter((1.0, 1.0, 0.5))
        calls = 0
        def writer(data: bytes):
            nonlocal calls
            calls += 1
            return InboundHttpResponseWriteOutcome.progress(min(1, len(data)))
        _, session, _, driver = _driver(
            writer=writer,
            clock=lambda: next(values),
        )
        with self.assertRaises(InboundHttpResponseWriteDriverError) as ctx:
            driver.run_to_completion()
        self.assertEqual(ctx.exception.code, "WRITE_DRIVER_CLOCK_REGRESSION")
        self.assertEqual(calls, 1)
        self.assertTrue(session.closed)

    def test_clock_failure_after_consumption_is_generic_and_terminal(self):
        calls = 0
        ticks = 0
        def clock():
            nonlocal ticks
            ticks += 1
            if ticks == 3:
                raise RuntimeError("SECRET-CLOCK")
            return 0.0
        def writer(data: bytes):
            nonlocal calls
            calls += 1
            return InboundHttpResponseWriteOutcome.progress(min(1, len(data)))
        _, session, _, driver = _driver(writer=writer, clock=clock)
        with self.assertRaises(InboundHttpResponseWriteDriverError) as ctx:
            driver.run_to_completion()
        self.assertEqual(ctx.exception.code, "WRITE_DRIVER_CLOCK_FAILURE")
        self.assertNotIn("SECRET-CLOCK", str(ctx.exception))
        self.assertEqual(calls, 1)
        self.assertTrue(session.closed)

    def test_m48_rejection_is_not_retried_and_preserves_nested_codes(self):
        calls = 0
        def writer(data: bytes):
            nonlocal calls
            calls += 1
            return InboundHttpResponseWriteOutcome.zero()
        _, session, _, driver = _driver(writer=writer)
        with self.assertRaises(InboundHttpResponseWriteDriverError) as ctx:
            driver.run_to_completion()
        self.assertEqual(calls, 1)
        self.assertEqual(ctx.exception.code, "WRITE_DRIVER_INVOCATION_REJECTED")
        self.assertEqual(ctx.exception.invocation_code, "WRITE_INVOCATION_OUTCOME_REJECTED")
        self.assertEqual(ctx.exception.outcome_code, "WRITE_ZERO_BEFORE_COMPLETE")
        self.assertTrue(session.closed)

    def test_limits_reject_invalid_and_nonfinite_values(self):
        for kwargs in (
            {"max_steps": True},
            {"max_steps": 0},
            {"max_steps": 1026},
            {"max_elapsed_seconds": True},
            {"max_elapsed_seconds": 0.0},
            {"max_elapsed_seconds": math.inf},
            {"max_elapsed_seconds": math.nan},
        ):
            with self.subTest(kwargs=kwargs):
                with self.assertRaises(ValueError):
                    InboundHttpResponseWriteDriverLimits(**kwargs)

    def test_close_is_idempotent_and_blocks_future_run(self):
        _, session, _, driver = _driver(
            writer=lambda data: InboundHttpResponseWriteOutcome.progress(len(data))
        )
        driver.close()
        driver.close()
        self.assertTrue(driver.closed)
        self.assertTrue(session.closed)
        with self.assertRaises(InboundHttpResponseWriteDriverError) as ctx:
            driver.run_to_completion()
        self.assertEqual(ctx.exception.code, "WRITE_DRIVER_SESSION_CLOSED")


if __name__ == "__main__":
    unittest.main()
