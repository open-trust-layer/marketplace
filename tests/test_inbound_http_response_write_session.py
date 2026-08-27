from __future__ import annotations

import inspect
import unittest
from dataclasses import replace

import marketplace.runtime.inbound_http_response_write_session as m46
from marketplace.runtime.inbound_http_response_write_plan import (
    WRITE_ACTION_COMPLETE,
    WRITE_ACTION_WRITE,
    BoundedInboundHttpResponseWritePlanner,
    InboundHttpResponseWriteLimits,
)
from marketplace.runtime.inbound_http_response_write_session import (
    BoundedInboundHttpResponseWriteSession,
    CompletedInboundHttpResponseWriteSession,
    InboundHttpResponseWriteSessionError,
)
from marketplace.runtime.inbound_http_response_write_transition import (
    BoundedInboundHttpResponseWriteTransitioner,
)
from test_inbound_http_response_write_plan import _prepared


class InboundHttpResponseWriteSessionTests(unittest.TestCase):
    def _session(self, *, calls: int = 8, size: int = 7):
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

    def test_session_starts_at_canonical_zero_zero_state(self):
        prepared, _, _, session = self._session()
        progress = session.progress()
        self.assertEqual(progress.response_bytes, prepared.response_bytes)
        self.assertEqual(progress.bytes_written, 0)
        self.assertEqual(progress.write_calls_completed, 0)
        self.assertEqual(progress.last_accepted_write_bytes, 0)
        self.assertEqual(progress.plan.action, WRITE_ACTION_WRITE)
        self.assertFalse(progress.writer_invoked)
        self.assertFalse(progress.transmitted)

    def test_accept_api_has_no_external_offset_or_call_count(self):
        parameters = inspect.signature(
            BoundedInboundHttpResponseWriteSession.accept_write_count
        ).parameters
        self.assertEqual(tuple(parameters), ("self", "accepted_write_bytes"))
        constructor = inspect.signature(BoundedInboundHttpResponseWriteSession).parameters
        self.assertNotIn("bytes_written", constructor)
        self.assertNotIn("write_calls_completed", constructor)

    def test_sequential_counts_advance_owned_state_exactly_once(self):
        _, _, _, session = self._session(size=7)
        first = session.accept_write_count(3)
        second = session.accept_write_count(4)
        self.assertEqual((first.write_calls_completed, first.bytes_written), (1, 3))
        self.assertEqual((second.write_calls_completed, second.bytes_written), (2, 7))
        self.assertEqual(second.last_accepted_write_bytes, 4)

    def test_rejected_count_does_not_advance_state(self):
        _, _, _, session = self._session(size=5)
        before = session.progress().integrity_snapshot
        with self.assertRaises(InboundHttpResponseWriteSessionError) as ctx:
            session.accept_write_count(6)
        self.assertEqual(ctx.exception.code, "WRITE_SESSION_TRANSITION_REJECTED")
        self.assertEqual(ctx.exception.transition_code, "WRITE_COUNT_EXCEEDS_PLAN")
        after = session.progress()
        self.assertEqual(after.integrity_snapshot, before)
        self.assertEqual((after.write_calls_completed, after.bytes_written), (0, 0))

    def test_zero_boolean_negative_and_noninteger_counts_fail_without_state_change(self):
        for value in (0, True, -1, 1.0):
            with self.subTest(value=value):
                _, _, _, session = self._session()
                with self.assertRaises(InboundHttpResponseWriteSessionError) as ctx:
                    session.accept_write_count(value)
                self.assertEqual(ctx.exception.code, "WRITE_SESSION_TRANSITION_REJECTED")
                self.assertEqual(ctx.exception.transition_code, "INVALID_ACCEPTED_WRITE_COUNT")
                self.assertEqual(session.progress().bytes_written, 0)

    def test_exact_response_count_completes_then_transfers_once(self):
        prepared, _, _, session = self._session(size=1_000_000)
        progress = session.accept_write_count(prepared.response_bytes)
        self.assertEqual(progress.plan.action, WRITE_ACTION_COMPLETE)
        completed = session.take_completed()
        self.assertIs(type(completed), CompletedInboundHttpResponseWriteSession)
        self.assertEqual(completed.bytes_written, prepared.response_bytes)
        self.assertEqual(completed.response_bytes, prepared.response_bytes)
        self.assertTrue(session.closed)
        self.assertFalse(completed.writer_invoked)
        self.assertFalse(completed.transmitted)
        with self.assertRaises(InboundHttpResponseWriteSessionError) as ctx:
            session.take_completed()
        self.assertEqual(ctx.exception.code, "WRITE_SESSION_CLOSED")

    def test_incomplete_take_fails_without_closing(self):
        _, _, _, session = self._session()
        with self.assertRaises(InboundHttpResponseWriteSessionError) as ctx:
            session.take_completed()
        self.assertEqual(ctx.exception.code, "WRITE_SESSION_INCOMPLETE")
        self.assertFalse(session.closed)

    def test_close_is_idempotent_and_blocks_reuse(self):
        _, _, _, session = self._session()
        session.accept_write_count(1)
        session.close()
        session.close()
        self.assertTrue(session.closed)
        self.assertIsNone(session._prepared_response)
        for method in (session.progress, lambda: session.accept_write_count(1), session.take_completed):
            with self.assertRaises(InboundHttpResponseWriteSessionError) as ctx:
                method()
            self.assertEqual(ctx.exception.code, "WRITE_SESSION_CLOSED")

    def test_completion_integrity_blocks_rebinding_and_original_authority_promotion(self):
        prepared, _, _, session = self._session(size=1_000_000)
        session.accept_write_count(prepared.response_bytes)
        completed = session.take_completed()
        with self.assertRaises(ValueError):
            replace(completed, bytes_written=completed.bytes_written - 1)

        # init=False fields are reset to defaults by dataclasses.replace(). Consumers
        # must inspect the original object before replay rather than treating replace()
        # as proof that the source object carried no authority promotion.
        object.__setattr__(completed, "transmitted", True)
        with self.assertRaises(InboundHttpResponseWriteSessionError) as ctx:
            m46._require_negative(completed)
        self.assertEqual(ctx.exception.code, "WRITE_SESSION_AUTHORITY_ESCALATION")
        replayed = replace(completed)
        self.assertFalse(replayed.transmitted)


if __name__ == "__main__":
    unittest.main()
