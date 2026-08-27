from __future__ import annotations

import ast
import inspect
import types
import unittest
from dataclasses import replace
from unittest.mock import patch

import marketplace.runtime.inbound_http_response_write_session as m46
from marketplace.runtime.inbound_http_response_write_plan import (
    WRITE_ACTION_WRITE,
    BoundedInboundHttpResponseWritePlanner,
    InboundHttpResponseWriteLimits,
)
from marketplace.runtime.inbound_http_response_write_session import (
    BoundedInboundHttpResponseWriteSession,
    InboundHttpResponseWriteSessionError,
)
from marketplace.runtime.inbound_http_response_write_transition import (
    BoundedInboundHttpResponseWriteTransitioner,
    InboundHttpResponseWriteTransition,
)
from test_inbound_http_response_write_plan import _prepared


class InboundHttpResponseWriteSessionHardeningTests(unittest.TestCase):
    def _parts(self, *, calls: int = 8, size: int = 7):
        prepared = _prepared()
        planner = BoundedInboundHttpResponseWritePlanner(
            limits=InboundHttpResponseWriteLimits(
                max_write_calls=calls,
                max_write_bytes=size,
            )
        )
        transitioner = BoundedInboundHttpResponseWriteTransitioner(write_planner=planner)
        session = BoundedInboundHttpResponseWriteSession(
            write_transitioner=transitioner,
            prepared_response=prepared,
        )
        return prepared, planner, transitioner, session

    def test_private_counter_reset_is_detected_by_state_witness(self):
        _, _, _, session = self._parts()
        session.accept_write_count(1)
        session._bytes_written = 0
        with self.assertRaises(InboundHttpResponseWriteSessionError) as ctx:
            session.progress()
        self.assertEqual(ctx.exception.code, "WRITE_SESSION_STATE_DRIFT")

    def test_private_call_count_reset_is_detected_by_state_witness(self):
        _, _, _, session = self._parts()
        session.accept_write_count(1)
        session._write_calls_completed = 0
        with self.assertRaises(InboundHttpResponseWriteSessionError) as ctx:
            session.progress()
        self.assertEqual(ctx.exception.code, "WRITE_SESSION_STATE_DRIFT")

    def test_private_prepared_response_rebinding_is_detected(self):
        _, _, _, session = self._parts()
        session._prepared_response = _prepared()
        with self.assertRaises(InboundHttpResponseWriteSessionError) as ctx:
            session.progress()
        self.assertEqual(ctx.exception.code, "WRITE_SESSION_STATE_DRIFT")

    def test_private_current_plan_rebinding_is_detected(self):
        _, _, _, session = self._parts()
        session._current_plan = replace(
            session._current_plan,
            next_write_bytes=session._current_plan.next_write_bytes - 1,
            integrity_snapshot=None,
        )
        with self.assertRaises(InboundHttpResponseWriteSessionError) as ctx:
            session.progress()
        self.assertEqual(ctx.exception.code, "WRITE_SESSION_STATE_DRIFT")

    def test_m45_retained_m44_binding_drift_fails_even_on_progress(self):
        _, planner, transitioner, session = self._parts()

        def hostile(self, *args, **kwargs):
            raise AssertionError("must not run")

        transitioner._plan = types.MethodType(hostile, planner)
        with self.assertRaises(InboundHttpResponseWriteSessionError) as ctx:
            session.progress()
        self.assertEqual(ctx.exception.code, "WRITE_SESSION_CONFIGURATION_DRIFT")

    def test_public_m44_and_m45_method_replacement_cannot_substitute_captured_authority(self):
        _, planner, transitioner, session = self._parts()
        planner.plan = lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("public M44 substitution"))
        transitioner.transition = lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("public M45 substitution"))
        result = session.accept_write_count(1)
        self.assertEqual(result.bytes_written, 1)

    def test_coherent_private_m46_transition_rebind_is_blocked_by_witness(self):
        _, _, transitioner, session = self._parts()

        def hostile(self, *args, **kwargs):
            raise AssertionError("must not run")

        session._transition_function = hostile
        session._transition = types.MethodType(hostile, transitioner)
        with self.assertRaises(InboundHttpResponseWriteSessionError) as ctx:
            session.accept_write_count(1)
        self.assertEqual(ctx.exception.code, "WRITE_SESSION_STATE_DRIFT")

    def test_promoted_m45_transition_is_rejected_before_replace_normalization(self):
        original = BoundedInboundHttpResponseWriteTransitioner.transition

        def hostile(self, prepared_response, **kwargs):
            result = original(self, prepared_response, **kwargs)
            object.__setattr__(result, "transmitted", True)
            return result

        prepared = _prepared()
        planner = BoundedInboundHttpResponseWritePlanner(
            limits=InboundHttpResponseWriteLimits(max_write_calls=8, max_write_bytes=7)
        )
        transitioner = BoundedInboundHttpResponseWriteTransitioner(write_planner=planner)
        with patch.object(BoundedInboundHttpResponseWriteTransitioner, "transition", hostile):
            session = BoundedInboundHttpResponseWriteSession(
                write_transitioner=transitioner,
                prepared_response=prepared,
            )
            with self.assertRaises(InboundHttpResponseWriteSessionError) as ctx:
                session.accept_write_count(1)
        self.assertEqual(ctx.exception.code, "WRITE_SESSION_AUTHORITY_ESCALATION")
        self.assertEqual(session.progress().bytes_written, 0)

    def test_self_consistent_wrong_m45_next_plan_is_rejected_by_independent_m44_replay(self):
        original = BoundedInboundHttpResponseWriteTransitioner.transition

        def hostile(self, prepared_response, **kwargs):
            result = original(self, prepared_response, **kwargs)
            next_plan = result.next_plan
            if next_plan.action != WRITE_ACTION_WRITE:
                raise AssertionError("fixture must remain incomplete")
            forged_next = replace(
                next_plan,
                next_write_bytes=next_plan.next_write_bytes - 1,
                integrity_snapshot=None,
            )
            return InboundHttpResponseWriteTransition(
                write_calls_completed=result.write_calls_completed,
                bytes_written=result.bytes_written,
                accepted_write_bytes=result.accepted_write_bytes,
                prior_plan=result.prior_plan,
                next_plan=forged_next,
            )

        prepared = _prepared()
        planner = BoundedInboundHttpResponseWritePlanner(
            limits=InboundHttpResponseWriteLimits(max_write_calls=8, max_write_bytes=7)
        )
        transitioner = BoundedInboundHttpResponseWriteTransitioner(write_planner=planner)
        with patch.object(BoundedInboundHttpResponseWriteTransitioner, "transition", hostile):
            session = BoundedInboundHttpResponseWriteSession(
                write_transitioner=transitioner,
                prepared_response=prepared,
            )
            with self.assertRaises(InboundHttpResponseWriteSessionError) as ctx:
                session.accept_write_count(1)
        self.assertEqual(ctx.exception.code, "WRITE_SESSION_NEXT_PLAN_DRIFT")
        self.assertEqual(session.progress().bytes_written, 0)

    def test_self_consistent_wrong_m45_prior_plan_is_rejected(self):
        original = BoundedInboundHttpResponseWriteTransitioner.transition

        def hostile(self, prepared_response, **kwargs):
            result = original(self, prepared_response, **kwargs)
            forged_prior = replace(
                result.prior_plan,
                next_write_bytes=result.prior_plan.next_write_bytes - 1,
                integrity_snapshot=None,
            )
            return InboundHttpResponseWriteTransition(
                write_calls_completed=result.write_calls_completed,
                bytes_written=result.bytes_written,
                accepted_write_bytes=result.accepted_write_bytes,
                prior_plan=forged_prior,
                next_plan=result.next_plan,
            )

        prepared = _prepared()
        planner = BoundedInboundHttpResponseWritePlanner(
            limits=InboundHttpResponseWriteLimits(max_write_calls=8, max_write_bytes=7)
        )
        transitioner = BoundedInboundHttpResponseWriteTransitioner(write_planner=planner)
        with patch.object(BoundedInboundHttpResponseWriteTransitioner, "transition", hostile):
            session = BoundedInboundHttpResponseWriteSession(
                write_transitioner=transitioner,
                prepared_response=prepared,
            )
            with self.assertRaises(InboundHttpResponseWriteSessionError) as ctx:
                session.accept_write_count(1)
        self.assertEqual(ctx.exception.code, "WRITE_SESSION_PRIOR_PLAN_DRIFT")
        self.assertEqual(session.progress().bytes_written, 0)

    def test_public_progress_and_completion_contain_no_raw_response_copy(self):
        prepared, _, _, session = self._parts(size=1_000_000)
        raw = prepared.wire_exchange.response_bytes
        progress = session.progress()
        self.assertNotIn(raw, progress.integrity_snapshot)
        self.assertFalse(hasattr(progress, "response"))
        session.accept_write_count(prepared.response_bytes)
        completed = session.take_completed()
        self.assertNotIn(raw, completed.integrity_snapshot)
        self.assertFalse(hasattr(completed, "response"))

    def test_closed_state_witness_tampering_is_detected_and_close_recovers(self):
        _, _, _, session = self._parts()
        session.close()
        session._state_witness = ("wrong", True)
        with self.assertRaises(InboundHttpResponseWriteSessionError) as ctx:
            _ = session.closed
        self.assertEqual(ctx.exception.code, "WRITE_SESSION_STATE_DRIFT")
        session.close()
        self.assertTrue(session.closed)

    def test_source_has_no_writer_network_process_persistence_or_background_surface(self):
        source = inspect.getsource(m46)
        imports = {
            alias.name.split(".")[0]
            for node in ast.walk(ast.parse(source))
            if isinstance(node, (ast.Import, ast.ImportFrom))
            for alias in node.names
        }
        self.assertTrue(
            imports.isdisjoint(
                {
                    "socket",
                    "ssl",
                    "http",
                    "urllib",
                    "requests",
                    "subprocess",
                    "asyncio",
                    "threading",
                    "logging",
                    "pathlib",
                }
            )
        )
        accept_source = inspect.getsource(
            m46.BoundedInboundHttpResponseWriteSession.accept_write_count
        )
        self.assertNotIn("writer(", accept_source)
        self.assertNotIn("send(", accept_source)
        self.assertNotIn("while ", accept_source)


if __name__ == "__main__":
    unittest.main()
