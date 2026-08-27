from __future__ import annotations

import unittest
from dataclasses import replace

from marketplace.runtime.inbound_http_response_write_outcome import (
    WRITE_OUTCOME_FAILURE,
    WRITE_OUTCOME_PROGRESS,
    WRITE_OUTCOME_ZERO,
    BoundedInboundHttpResponseWriteOutcomeHandler,
    InboundHttpResponseWriteOutcome,
    InboundHttpResponseWriteOutcomeError,
)
from marketplace.runtime.inbound_http_response_write_plan import (
    WRITE_ACTION_COMPLETE,
    BoundedInboundHttpResponseWritePlanner,
    InboundHttpResponseWriteLimits,
)
from marketplace.runtime.inbound_http_response_write_session import (
    BoundedInboundHttpResponseWriteSession,
)
from marketplace.runtime.inbound_http_response_write_transition import (
    BoundedInboundHttpResponseWriteTransitioner,
)
from test_inbound_http_response_write_plan import _prepared


def _parts(*, max_write_bytes: int = 7, max_write_calls: int = 8):
    prepared = _prepared()
    planner = BoundedInboundHttpResponseWritePlanner(
        limits=InboundHttpResponseWriteLimits(
            max_write_calls=max_write_calls,
            max_write_bytes=max_write_bytes,
        )
    )
    transitioner = BoundedInboundHttpResponseWriteTransitioner(write_planner=planner)
    session = BoundedInboundHttpResponseWriteSession(
        write_transitioner=transitioner,
        prepared_response=prepared,
    )
    handler = BoundedInboundHttpResponseWriteOutcomeHandler(write_session=session)
    return prepared, planner, transitioner, session, handler


class InboundHttpResponseWriteOutcomeTests(unittest.TestCase):
    def test_canonical_factories_are_exact_and_authority_negative(self):
        progress = InboundHttpResponseWriteOutcome.progress(3)
        zero = InboundHttpResponseWriteOutcome.zero()
        failure = InboundHttpResponseWriteOutcome.failure()
        self.assertEqual((progress.kind, progress.accepted_write_bytes), (WRITE_OUTCOME_PROGRESS, 3))
        self.assertEqual((zero.kind, zero.accepted_write_bytes), (WRITE_OUTCOME_ZERO, 0))
        self.assertEqual((failure.kind, failure.accepted_write_bytes), (WRITE_OUTCOME_FAILURE, 0))
        for value in (progress, zero, failure):
            self.assertFalse(value.writer_invoked)
            self.assertFalse(value.socket_accessed)
            self.assertFalse(value.transmitted)

    def test_invalid_outcome_shapes_fail_before_session_change(self):
        _, _, _, _, handler = _parts()
        before = handler.progress().integrity_snapshot
        invalid = (
            lambda: InboundHttpResponseWriteOutcome(kind="OTHER"),
            lambda: InboundHttpResponseWriteOutcome.progress(0),
            lambda: InboundHttpResponseWriteOutcome.progress(True),
            lambda: InboundHttpResponseWriteOutcome(kind=WRITE_OUTCOME_ZERO, accepted_write_bytes=1),
        )
        for factory in invalid:
            with self.subTest(factory=factory):
                with self.assertRaises(ValueError):
                    factory()
        self.assertEqual(handler.progress().integrity_snapshot, before)

    def test_progress_advances_m46_exactly_once(self):
        _, _, _, _, handler = _parts()
        prior = handler.progress()
        current = handler.accept_outcome(InboundHttpResponseWriteOutcome.progress(3))
        self.assertEqual(current.write_calls_completed, prior.write_calls_completed + 1)
        self.assertEqual(current.bytes_written, prior.bytes_written + 3)
        self.assertEqual(current.last_accepted_write_bytes, 3)
        self.assertEqual(handler.progress().bytes_written, 3)

    def test_rejected_already_returned_progress_is_terminal_and_preserves_codes(self):
        _, _, _, session, handler = _parts(max_write_bytes=2)
        with self.assertRaises(InboundHttpResponseWriteOutcomeError) as ctx:
            handler.accept_outcome(InboundHttpResponseWriteOutcome.progress(3))
        self.assertEqual(ctx.exception.code, "WRITE_OUTCOME_SESSION_REJECTED")
        self.assertEqual(ctx.exception.session_code, "WRITE_SESSION_TRANSITION_REJECTED")
        self.assertEqual(ctx.exception.transition_code, "WRITE_COUNT_EXCEEDS_PLAN")
        self.assertTrue(session.closed)
        self.assertIsNone(session._prepared_response)

    def test_zero_before_complete_is_terminal_and_clears(self):
        _, _, _, session, handler = _parts()
        with self.assertRaises(InboundHttpResponseWriteOutcomeError) as ctx:
            handler.accept_outcome(InboundHttpResponseWriteOutcome.zero())
        self.assertEqual(ctx.exception.code, "WRITE_ZERO_BEFORE_COMPLETE")
        self.assertTrue(session.closed)
        self.assertIsNone(session._prepared_response)

    def test_failure_before_complete_is_generic_terminal_and_clears(self):
        _, _, _, session, handler = _parts()
        with self.assertRaises(InboundHttpResponseWriteOutcomeError) as ctx:
            handler.accept_outcome(InboundHttpResponseWriteOutcome.failure())
        self.assertEqual(ctx.exception.code, "WRITE_FAILURE_BEFORE_COMPLETE")
        self.assertNotIn("exception", str(ctx.exception).lower())
        self.assertTrue(session.closed)

    def test_complete_progress_then_explicit_one_shot_transfer(self):
        prepared, _, _, session, handler = _parts(max_write_bytes=1_000_000)
        progress = handler.accept_outcome(
            InboundHttpResponseWriteOutcome.progress(prepared.response_bytes)
        )
        self.assertEqual(progress.plan.action, WRITE_ACTION_COMPLETE)
        completed = handler.take_completed()
        self.assertEqual(completed.response_bytes, prepared.response_bytes)
        self.assertEqual(completed.bytes_written, prepared.response_bytes)
        self.assertFalse(completed.writer_invoked)
        self.assertFalse(completed.transmitted)
        self.assertTrue(session.closed)
        with self.assertRaises(InboundHttpResponseWriteOutcomeError) as ctx:
            handler.take_completed()
        self.assertEqual(ctx.exception.code, "WRITE_OUTCOME_SESSION_CLOSED")

    def test_supplied_outcome_after_complete_is_rejected_and_closes(self):
        prepared, _, _, session, handler = _parts(max_write_bytes=1_000_000)
        handler.accept_outcome(InboundHttpResponseWriteOutcome.progress(prepared.response_bytes))
        with self.assertRaises(InboundHttpResponseWriteOutcomeError) as ctx:
            handler.accept_outcome(InboundHttpResponseWriteOutcome.progress(1))
        self.assertEqual(ctx.exception.code, "WRITE_OUTCOME_AFTER_COMPLETE")
        self.assertTrue(session.closed)
        self.assertIsNone(session._prepared_response)

    def test_incomplete_take_preserves_m46_reason_and_keeps_session_open(self):
        _, _, _, session, handler = _parts()
        with self.assertRaises(InboundHttpResponseWriteOutcomeError) as ctx:
            handler.take_completed()
        self.assertEqual(ctx.exception.code, "WRITE_OUTCOME_SESSION_REJECTED")
        self.assertEqual(ctx.exception.session_code, "WRITE_SESSION_INCOMPLETE")
        self.assertFalse(session.closed)

    def test_outcome_integrity_blocks_rebinding_and_original_authority_is_checked(self):
        outcome = InboundHttpResponseWriteOutcome.progress(1)
        with self.assertRaises(ValueError):
            replace(outcome, accepted_write_bytes=2)
        object.__setattr__(outcome, "transmitted", True)
        _, _, _, _, handler = _parts()
        with self.assertRaises(InboundHttpResponseWriteOutcomeError) as ctx:
            handler.accept_outcome(outcome)
        self.assertEqual(ctx.exception.code, "WRITE_OUTCOME_AUTHORITY")
        self.assertEqual(handler.progress().bytes_written, 0)

    def test_close_is_idempotent(self):
        _, _, _, session, handler = _parts()
        handler.close()
        handler.close()
        self.assertTrue(session.closed)
        self.assertIsNone(session._prepared_response)


if __name__ == "__main__":
    unittest.main()
