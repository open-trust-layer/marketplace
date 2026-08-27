from __future__ import annotations

import ast
import inspect
import types
import unittest
from dataclasses import replace

import marketplace.runtime.inbound_http_response_write_transition as m45
from marketplace.runtime.inbound_http_response_write_plan import (
    WRITE_ACTION_COMPLETE,
    WRITE_ACTION_WRITE,
    BoundedInboundHttpResponseWritePlanner,
    InboundHttpResponseWriteLimits,
)
from marketplace.runtime.inbound_http_response_write_transition import (
    BoundedInboundHttpResponseWriteTransitioner,
    InboundHttpResponseWriteTransition,
    InboundHttpResponseWriteTransitionError,
)
from test_inbound_http_response_write_plan import _prepared


class InboundHttpResponseWriteTransitionTests(unittest.TestCase):
    def _transitioner(self, *, calls=8, size=7):
        planner = BoundedInboundHttpResponseWritePlanner(
            limits=InboundHttpResponseWriteLimits(max_write_calls=calls, max_write_bytes=size)
        )
        return planner, BoundedInboundHttpResponseWriteTransitioner(write_planner=planner)

    def test_one_partial_write_advances_exactly_once(self):
        prepared = _prepared()
        _, transitioner = self._transitioner(size=7)
        result = transitioner.transition(
            prepared, write_calls_completed=0, bytes_written=0, accepted_write_bytes=3
        )
        self.assertEqual(result.write_calls_completed, 1)
        self.assertEqual(result.bytes_written, 3)
        self.assertEqual(result.accepted_write_bytes, 3)
        self.assertEqual(result.prior_plan.action, WRITE_ACTION_WRITE)
        self.assertEqual(result.next_plan.bytes_written, 3)
        self.assertFalse(result.writer_invoked)
        self.assertFalse(result.transmitted)

    def test_exact_remaining_write_yields_complete_next_plan(self):
        prepared = _prepared()
        _, transitioner = self._transitioner(size=1_000_000)
        result = transitioner.transition(
            prepared,
            write_calls_completed=0,
            bytes_written=0,
            accepted_write_bytes=prepared.response_bytes,
        )
        self.assertEqual(result.next_plan.action, WRITE_ACTION_COMPLETE)
        self.assertEqual(result.next_plan.remaining_bytes, 0)
        self.assertFalse(result.transmitted)

    def test_zero_negative_boolean_and_noninteger_write_counts_fail(self):
        prepared = _prepared()
        _, transitioner = self._transitioner()
        for value in (0, -1, True, 1.0):
            with self.assertRaises(InboundHttpResponseWriteTransitionError) as ctx:
                transitioner.transition(
                    prepared, write_calls_completed=0, bytes_written=0, accepted_write_bytes=value
                )
            self.assertEqual(ctx.exception.code, "INVALID_ACCEPTED_WRITE_COUNT")

    def test_count_above_exact_prior_budget_fails(self):
        prepared = _prepared()
        _, transitioner = self._transitioner(size=5)
        with self.assertRaises(InboundHttpResponseWriteTransitionError) as ctx:
            transitioner.transition(
                prepared, write_calls_completed=0, bytes_written=0, accepted_write_bytes=6
            )
        self.assertEqual(ctx.exception.code, "WRITE_COUNT_EXCEEDS_PLAN")

    def test_write_after_complete_fails_without_new_authority(self):
        prepared = _prepared()
        _, transitioner = self._transitioner()
        with self.assertRaises(InboundHttpResponseWriteTransitionError) as ctx:
            transitioner.transition(
                prepared,
                write_calls_completed=1,
                bytes_written=prepared.response_bytes,
                accepted_write_bytes=1,
            )
        self.assertEqual(ctx.exception.code, "WRITE_AFTER_COMPLETE")

    def test_m44_rejection_preserves_nested_code(self):
        prepared = _prepared()
        object.__setattr__(prepared, "request_authenticated", True)
        _, transitioner = self._transitioner()
        with self.assertRaises(InboundHttpResponseWriteTransitionError) as ctx:
            transitioner.transition(
                prepared, write_calls_completed=0, bytes_written=0, accepted_write_bytes=1
            )
        self.assertEqual(ctx.exception.code, "WRITE_PLAN_REJECTED")
        self.assertEqual(ctx.exception.write_plan_code, "WRITE_AUTHORITY_ESCALATION")

    def test_m44_limit_drift_is_detected_before_transition(self):
        prepared = _prepared()
        planner, transitioner = self._transitioner(size=7)
        planner._limits = InboundHttpResponseWriteLimits(max_write_calls=8, max_write_bytes=8)
        with self.assertRaises(InboundHttpResponseWriteTransitionError) as ctx:
            transitioner.transition(
                prepared, write_calls_completed=0, bytes_written=0, accepted_write_bytes=1
            )
        self.assertEqual(ctx.exception.code, "WRITE_CONFIGURATION_DRIFT")

    def test_public_m44_plan_replacement_cannot_substitute_captured_authority(self):
        prepared = _prepared()
        planner, transitioner = self._transitioner(size=7)
        planner.plan = lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("substituted"))
        result = transitioner.transition(
            prepared, write_calls_completed=0, bytes_written=0, accepted_write_bytes=1
        )
        self.assertEqual(result.bytes_written, 1)

    def test_private_captured_plan_rebinding_is_detected(self):
        prepared = _prepared()
        planner, transitioner = self._transitioner()
        def hostile(self, *args, **kwargs):
            raise AssertionError("must not run")
        transitioner._plan = types.MethodType(hostile, planner)
        with self.assertRaises(InboundHttpResponseWriteTransitionError) as ctx:
            transitioner.transition(
                prepared, write_calls_completed=0, bytes_written=0, accepted_write_bytes=1
            )
        self.assertEqual(ctx.exception.code, "WRITE_CONFIGURATION_DRIFT")

    def test_transition_integrity_and_nested_authority_promotion_fail(self):
        prepared = _prepared()
        _, transitioner = self._transitioner()
        result = transitioner.transition(
            prepared, write_calls_completed=0, bytes_written=0, accepted_write_bytes=1
        )
        with self.assertRaises(ValueError):
            replace(result, bytes_written=2)
        object.__setattr__(result.prior_plan, "transmitted", True)
        with self.assertRaises(ValueError):
            replace(result)

    def test_transition_witness_contains_no_raw_response_bytes(self):
        prepared = _prepared()
        _, transitioner = self._transitioner()
        result = transitioner.transition(
            prepared, write_calls_completed=0, bytes_written=0, accepted_write_bytes=1
        )
        self.assertNotIn(prepared.wire_exchange.response_bytes, result.integrity_snapshot)

    def test_source_has_no_writer_network_or_background_surface(self):
        source = inspect.getsource(m45)
        imports = {
            alias.name.split(".")[0]
            for node in ast.walk(ast.parse(source))
            if isinstance(node, (ast.Import, ast.ImportFrom))
            for alias in node.names
        }
        self.assertTrue(imports.isdisjoint({"socket", "ssl", "http", "urllib", "requests", "subprocess", "asyncio", "threading", "logging", "pathlib"}))
        transition_source = inspect.getsource(m45.BoundedInboundHttpResponseWriteTransitioner.transition)
        self.assertNotIn("writer(", transition_source)
        self.assertNotIn("send(", transition_source)


if __name__ == "__main__":
    unittest.main()
