from __future__ import annotations

import unittest

from marketplace.runtime.inbound_http import (
    BoundedInboundHttpApplicationAdapter,
    InboundHttpApplicationLimits,
)
from marketplace.runtime.inbound_http_read_driver import (
    DEFAULT_INBOUND_HTTP_READ_DRIVER_TIMEOUT_SECONDS,
    DEFAULT_MAX_INBOUND_HTTP_READ_DRIVER_STEPS,
    MAX_INBOUND_HTTP_READ_DRIVER_STEPS,
    MAX_INBOUND_HTTP_READ_DRIVER_TIMEOUT_SECONDS,
    BoundedInboundHttpReadDriver,
    InboundHttpReadDriverError,
    InboundHttpReadDriverLimits,
)
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
        raise AssertionError("M42 read driver MUST NOT reach disclosure")


class _Clock:
    def __init__(self, values):
        self.values = list(values)
        self.calls = 0

    def __call__(self):
        self.calls += 1
        if not self.values:
            raise AssertionError("clock called more often than expected")
        value = self.values.pop(0)
        if isinstance(value, BaseException):
            raise value
        return value


def _build(reader, *, max_read_calls=64):
    harness = _NoDisclosureHarness()
    wire = BoundedInboundHttpWireAdapter(
        application_adapter=harness.adapter,
        authority=AUTHORITY,
    )
    stream = BoundedInboundHttpStreamAssembler(wire_adapter=wire)
    planner = BoundedInboundHttpReadPlanner(
        stream_assembler=stream,
        limits=InboundHttpReadLimits(max_read_calls=max_read_calls),
    )
    transitioner = BoundedInboundHttpReadTransitioner(read_planner=planner)
    session = BoundedInboundHttpReadSession(read_transitioner=transitioner)
    handler = BoundedInboundHttpReadOutcomeHandler(read_session=session)
    invoker = BoundedInboundHttpReadInvoker(
        read_outcome_handler=handler,
        reader=reader,
    )
    raw = _get_request_bytes(f"/v1/records/{RECORD_ID}", AUTHORITY, 443)
    return harness, session, handler, invoker, raw


class InboundHttpReadDriverTests(unittest.TestCase):
    def test_default_and_hard_limits_are_explicit(self):
        limits = InboundHttpReadDriverLimits()
        self.assertEqual(limits.max_steps, DEFAULT_MAX_INBOUND_HTTP_READ_DRIVER_STEPS)
        self.assertEqual(
            limits.max_elapsed_seconds,
            DEFAULT_INBOUND_HTTP_READ_DRIVER_TIMEOUT_SECONDS,
        )
        self.assertEqual(MAX_INBOUND_HTTP_READ_DRIVER_STEPS, 1025)
        self.assertEqual(MAX_INBOUND_HTTP_READ_DRIVER_TIMEOUT_SECONDS, 120.0)

    def test_limit_types_bounds_and_nonfinite_values_fail_closed(self):
        for value in (True, 0, -1, 1026, 1.5, "1"):
            with self.subTest(max_steps=value):
                with self.assertRaises(ValueError):
                    InboundHttpReadDriverLimits(max_steps=value)
        for value in (True, 0, -1, float("nan"), float("inf"), -float("inf"), 120.1, "1"):
            with self.subTest(max_elapsed_seconds=value):
                with self.assertRaises(ValueError):
                    InboundHttpReadDriverLimits(max_elapsed_seconds=value)

    def test_default_step_limit_includes_completion_transfer(self):
        _, _, _, invoker, _ = _build(lambda _: InboundHttpReadOutcome.eof(), max_read_calls=3)
        driver = BoundedInboundHttpReadDriver(read_invoker=invoker, clock=lambda: 0.0)
        self.assertEqual(driver.limits.max_steps, 4)
        self.assertEqual(driver.m37_max_read_calls, 3)

    def test_explicit_step_limit_cannot_exceed_lower_ceiling_plus_transfer(self):
        _, _, _, invoker, _ = _build(lambda _: InboundHttpReadOutcome.eof(), max_read_calls=3)
        allowed = BoundedInboundHttpReadDriver(
            read_invoker=invoker,
            clock=lambda: 0.0,
            limits=InboundHttpReadDriverLimits(max_steps=4),
        )
        self.assertEqual(allowed.limits.max_steps, 4)

        _, _, _, invoker2, _ = _build(lambda _: InboundHttpReadOutcome.eof(), max_read_calls=3)
        with self.assertRaises(ValueError):
            BoundedInboundHttpReadDriver(
                read_invoker=invoker2,
                clock=lambda: 0.0,
                limits=InboundHttpReadDriverLimits(max_steps=5),
            )

    def test_default_64_reads_reserve_step_65_for_zero_reader_completion(self):
        calls = []
        holder = {"offset": 0}

        def reader(max_bytes):
            calls.append(max_bytes)
            raw = holder["raw"]
            start = holder["offset"]
            end = start + 1 if len(calls) < 64 else len(raw)
            holder["offset"] = end
            return InboundHttpReadOutcome.data(raw[start:end])

        _, session, _, invoker, raw = _build(reader, max_read_calls=64)
        self.assertGreater(len(raw), 64)
        holder["raw"] = raw
        driver = BoundedInboundHttpReadDriver(read_invoker=invoker, clock=lambda: 0.0)

        result = driver.run_to_completion()

        self.assertEqual(driver.limits.max_steps, 65)
        self.assertEqual(result.driver_steps, 65)
        self.assertEqual(result.reader_invocations, 64)
        self.assertEqual(len(calls), 64)
        self.assertEqual(result.completed.prefix, raw)
        self.assertTrue(session.closed)

    def test_one_data_read_plus_completion_transfer_finishes(self):
        calls = []
        holder = {}

        def reader(max_bytes):
            calls.append(max_bytes)
            return InboundHttpReadOutcome.data(holder["raw"])

        harness, session, _, invoker, raw = _build(reader)
        holder["raw"] = raw
        clock = _Clock([0.0, 0.0, 0.1, 0.1, 0.2])
        driver = BoundedInboundHttpReadDriver(read_invoker=invoker, clock=clock)

        result = driver.run_to_completion()

        self.assertEqual(result.completed.prefix, raw)
        self.assertEqual(result.driver_steps, 2)
        self.assertEqual(result.reader_invocations, 1)
        self.assertEqual(result.elapsed_seconds, 0.2)
        self.assertEqual(len(calls), 1)
        self.assertTrue(driver.closed)
        self.assertTrue(session.closed)
        self.assertEqual(session._prefix, b"")
        self.assertEqual(harness.calls, [])

    def test_multiple_data_reads_then_zero_reader_completion_transfer(self):
        holder = {}
        calls = []
        chunks = []

        def reader(max_bytes):
            calls.append(max_bytes)
            return InboundHttpReadOutcome.data(chunks.pop(0))

        _, _, _, invoker, raw = _build(reader)
        holder["raw"] = raw
        chunks.extend((raw[:4], raw[4:]))
        clock = _Clock([0, 0, 1, 1, 2, 2, 3])
        driver = BoundedInboundHttpReadDriver(read_invoker=invoker, clock=clock)

        result = driver.run_to_completion()

        self.assertEqual(result.completed.prefix, raw)
        self.assertEqual(result.driver_steps, 3)
        self.assertEqual(result.reader_invocations, 2)
        self.assertEqual(len(calls), 2)
        self.assertTrue(driver.closed)

    def test_step_exhaustion_clears_partial_or_complete_source_state(self):
        holder = {}
        calls = []

        def reader(max_bytes):
            calls.append(max_bytes)
            return InboundHttpReadOutcome.data(holder["raw"])

        _, session, _, invoker, raw = _build(reader)
        holder["raw"] = raw
        driver = BoundedInboundHttpReadDriver(
            read_invoker=invoker,
            clock=_Clock([0, 0, 0.1]),
            limits=InboundHttpReadDriverLimits(max_steps=1),
        )

        with self.assertRaises(InboundHttpReadDriverError) as caught:
            driver.run_to_completion()
        self.assertEqual(caught.exception.code, "READ_DRIVER_STEP_LIMIT_EXHAUSTED")
        self.assertEqual(len(calls), 1)
        self.assertTrue(driver.closed)
        self.assertEqual(session._prefix, b"")

    def test_time_exhaustion_before_next_step_closes_without_next_reader_call(self):
        calls = []

        def reader(max_bytes):
            calls.append(max_bytes)
            return InboundHttpReadOutcome.data(b"GET ")

        _, session, _, invoker, _ = _build(reader)
        driver = BoundedInboundHttpReadDriver(
            read_invoker=invoker,
            clock=_Clock([0.0, 0.0, 0.1, 31.0]),
        )

        with self.assertRaises(InboundHttpReadDriverError) as caught:
            driver.run_to_completion()
        self.assertEqual(caught.exception.code, "READ_DRIVER_TIME_LIMIT_EXHAUSTED")
        self.assertEqual(len(calls), 1)
        self.assertTrue(driver.closed)
        self.assertEqual(session._prefix, b"")

    def test_time_exhaustion_after_step_closes_consumed_state(self):
        calls = []

        def reader(max_bytes):
            calls.append(max_bytes)
            return InboundHttpReadOutcome.data(b"GET ")

        _, session, _, invoker, _ = _build(reader)
        driver = BoundedInboundHttpReadDriver(
            read_invoker=invoker,
            clock=_Clock([0.0, 0.0, 31.0]),
        )
        with self.assertRaises(InboundHttpReadDriverError) as caught:
            driver.run_to_completion()
        self.assertEqual(caught.exception.code, "READ_DRIVER_TIME_LIMIT_EXHAUSTED")
        self.assertEqual(len(calls), 1)
        self.assertTrue(driver.closed)
        self.assertEqual(session._prefix, b"")

    def test_clock_regression_and_nonfinite_after_consumption_are_terminal(self):
        for bad_after, code in (
            (-1.0, "READ_DRIVER_CLOCK_REGRESSION"),
            (float("inf"), "READ_DRIVER_CLOCK_DRIFT"),
        ):
            with self.subTest(bad_after=bad_after):
                _, session, _, invoker, _ = _build(
                    lambda _: InboundHttpReadOutcome.data(b"GET ")
                )
                driver = BoundedInboundHttpReadDriver(
                    read_invoker=invoker,
                    clock=_Clock([0.0, 0.0, bad_after]),
                )
                with self.assertRaises(InboundHttpReadDriverError) as caught:
                    driver.run_to_completion()
                self.assertEqual(caught.exception.code, code)
                self.assertTrue(driver.closed)
                self.assertEqual(session._prefix, b"")

    def test_clock_exception_after_consumption_is_generic_and_terminal(self):
        _, session, _, invoker, _ = _build(
            lambda _: InboundHttpReadOutcome.data(b"GET ")
        )
        driver = BoundedInboundHttpReadDriver(
            read_invoker=invoker,
            clock=_Clock([0.0, 0.0, RuntimeError("SECRET clock token")]),
        )
        with self.assertRaises(InboundHttpReadDriverError) as caught:
            driver.run_to_completion()
        self.assertEqual(caught.exception.code, "READ_DRIVER_CLOCK_FAILURE")
        self.assertNotIn("SECRET", str(caught.exception))
        self.assertTrue(driver.closed)
        self.assertEqual(session._prefix, b"")

    def test_m41_error_is_not_retried_and_preserves_nested_codes(self):
        calls = []

        def reader(max_bytes):
            calls.append(max_bytes)
            return InboundHttpReadOutcome.eof()

        _, session, _, invoker, _ = _build(reader)
        driver = BoundedInboundHttpReadDriver(
            read_invoker=invoker,
            clock=_Clock([0.0, 0.0]),
        )
        with self.assertRaises(InboundHttpReadDriverError) as caught:
            driver.run_to_completion()
        self.assertEqual(caught.exception.code, "READ_DRIVER_INVOCATION_REJECTED")
        self.assertEqual(caught.exception.invocation_code, "READ_INVOCATION_OUTCOME_REJECTED")
        self.assertEqual(caught.exception.outcome_code, "READ_EOF_BEFORE_COMPLETE")
        self.assertEqual(len(calls), 1)
        self.assertTrue(driver.closed)
        self.assertEqual(session._prefix, b"")

    def test_close_is_idempotent_and_blocks_future_run(self):
        _, session, _, invoker, _ = _build(lambda _: InboundHttpReadOutcome.eof())
        driver = BoundedInboundHttpReadDriver(read_invoker=invoker, clock=lambda: 0.0)
        driver.close()
        driver.close()
        self.assertTrue(driver.closed)
        self.assertTrue(session.closed)
        with self.assertRaises(InboundHttpReadDriverError) as caught:
            driver.run_to_completion()
        self.assertEqual(caught.exception.code, "READ_DRIVER_SESSION_CLOSED")


if __name__ == "__main__":
    unittest.main()
