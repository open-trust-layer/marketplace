"""One-step bounded inbound reader invocation above M37-M40.

M41 intentionally invokes one injected read capability, but never discovers or
implements a concrete socket/reader itself. One public invocation performs zero
or one reader calls, never retries, and never loops.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any, Callable, Final

from .inbound_http_read_outcome import (
    READ_OUTCOME_DATA,
    BoundedInboundHttpReadOutcomeHandler,
    InboundHttpReadOutcome,
    InboundHttpReadOutcomeError,
)
from .inbound_http_read_plan import READ_ACTION_COMPLETE, READ_ACTION_READ
from .inbound_http_read_session import (
    CompletedInboundHttpReadSession,
    InboundHttpReadSessionProgress,
)

READ_INVOCATION_PROGRESS: Final = "PROGRESS"
READ_INVOCATION_COMPLETED: Final = "COMPLETED"
_READ_INVOCATION_STATES: Final = frozenset(
    (READ_INVOCATION_PROGRESS, READ_INVOCATION_COMPLETED)
)
_BINDING_MARKER: Final = "inbound-http-read-invoker-binding-v1"


class InboundHttpReadInvocationError(RuntimeError):
    """Fail-closed M41 error with preserved M40-and-lower reason metadata."""

    def __init__(
        self,
        code: str,
        message: str,
        *,
        outcome_code: str | None = None,
        session_code: str | None = None,
        transition_code: str | None = None,
        plan_code: str | None = None,
        stream_code: str | None = None,
        wire_code: str | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.outcome_code = outcome_code
        self.session_code = session_code
        self.transition_code = transition_code
        self.plan_code = plan_code
        self.stream_code = stream_code
        self.wire_code = wire_code


def _fail(
    code: str,
    message: str,
    *,
    outcome_code: str | None = None,
    session_code: str | None = None,
    transition_code: str | None = None,
    plan_code: str | None = None,
    stream_code: str | None = None,
    wire_code: str | None = None,
) -> None:
    raise InboundHttpReadInvocationError(
        code,
        message,
        outcome_code=outcome_code,
        session_code=session_code,
        transition_code=transition_code,
        plan_code=plan_code,
        stream_code=stream_code,
        wire_code=wire_code,
    )


def _fail_from_outcome(
    code: str,
    message: str,
    exc: InboundHttpReadOutcomeError,
) -> None:
    _fail(
        code,
        message,
        outcome_code=exc.code,
        session_code=exc.session_code,
        transition_code=exc.transition_code,
        plan_code=exc.plan_code,
        stream_code=exc.stream_code,
        wire_code=exc.wire_code,
    )


@dataclass(frozen=True)
class InboundHttpReadInvocationResult:
    """Integrity-bound result containing no M41-owned raw request field."""

    state: str
    reader_invoked: bool
    requested_bytes: int
    outcome_kind: str | None
    progress: InboundHttpReadSessionProgress | None = None
    completed: CompletedInboundHttpReadSession | None = None
    integrity_snapshot: tuple[Any, ...] | None = field(default=None, repr=False)
    socket_access_proven: bool = field(default=False, init=False)
    network_origin_proven: bool = field(default=False, init=False)
    request_authenticated: bool = field(default=False, init=False)
    peer_identity_proven: bool = field(default=False, init=False)
    establishes_marketplace_truth: bool = field(default=False, init=False)
    establishes_trust: bool = field(default=False, init=False)
    establishes_authorization: bool = field(default=False, init=False)
    authorizes_protected_side_effects: bool = field(default=False, init=False)

    def __post_init__(self) -> None:
        if type(self.state) is not str or self.state not in _READ_INVOCATION_STATES:
            raise ValueError("state MUST be one canonical M41 invocation state")
        if type(self.reader_invoked) is not bool:
            raise ValueError("reader_invoked MUST be exact bool")
        if type(self.requested_bytes) is not int or self.requested_bytes < 0:
            raise ValueError("requested_bytes MUST be an exact non-negative integer")
        if self.outcome_kind is not None and type(self.outcome_kind) is not str:
            raise ValueError("outcome_kind MUST be exact str or None")

        progress_snapshot: tuple[Any, ...] | None = None
        completed_snapshot: tuple[Any, ...] | None = None
        if self.state == READ_INVOCATION_PROGRESS:
            if self.reader_invoked is not True or self.requested_bytes <= 0:
                raise ValueError("PROGRESS MUST represent one positive reader invocation")
            if self.outcome_kind != READ_OUTCOME_DATA:
                raise ValueError("successful M41 PROGRESS MUST arise from exact DATA")
            if type(self.progress) is not InboundHttpReadSessionProgress:
                raise ValueError("PROGRESS MUST carry exact M39 progress")
            if self.completed is not None:
                raise ValueError("PROGRESS MUST NOT carry completion bytes")
            witnessed_progress = replace(self.progress)
            object.__setattr__(self, "progress", witnessed_progress)
            progress_snapshot = witnessed_progress.integrity_snapshot
        else:
            if self.reader_invoked is not False or self.requested_bytes != 0:
                raise ValueError("COMPLETED MUST NOT claim a reader invocation")
            if self.outcome_kind is not None or self.progress is not None:
                raise ValueError("COMPLETED MUST NOT carry outcome/progress metadata")
            if type(self.completed) is not CompletedInboundHttpReadSession:
                raise ValueError("COMPLETED MUST carry exact M39 completion handoff")
            witnessed_completed = replace(self.completed)
            object.__setattr__(self, "completed", witnessed_completed)
            completed_snapshot = witnessed_completed.integrity_snapshot

        authority_facts = (
            self.socket_access_proven,
            self.network_origin_proven,
            self.request_authenticated,
            self.peer_identity_proven,
            self.establishes_marketplace_truth,
            self.establishes_trust,
            self.establishes_authorization,
            self.authorizes_protected_side_effects,
        )
        if any(value is not False for value in authority_facts):
            raise ValueError("M41 result promoted a forbidden authority fact")

        current = (
            "inbound-http-read-invocation-result-v1",
            self.state,
            self.reader_invoked,
            self.requested_bytes,
            self.outcome_kind,
            progress_snapshot,
            completed_snapshot,
            *authority_facts,
        )
        if self.integrity_snapshot is not None and self.integrity_snapshot != current:
            raise ValueError("M41 invocation-result integrity snapshot mismatch")
        if self.integrity_snapshot is None:
            object.__setattr__(self, "integrity_snapshot", current)


class BoundedInboundHttpReadInvoker:
    """Invoke one construction-bound reader at most once per public call."""

    __slots__ = (
        "_handler",
        "_reader",
        "_progress_function",
        "_accept_function",
        "_take_function",
        "_close_function",
        "_closed_function",
        "_progress",
        "_accept",
        "_take",
        "_close",
        "_closed_getter",
        "_binding_witness",
    )

    def __init__(
        self,
        *,
        read_outcome_handler: BoundedInboundHttpReadOutcomeHandler,
        reader: Callable[[int], InboundHttpReadOutcome],
    ) -> None:
        if type(read_outcome_handler) is not BoundedInboundHttpReadOutcomeHandler:
            raise TypeError(
                "read_outcome_handler MUST be exact BoundedInboundHttpReadOutcomeHandler"
            )
        if not callable(reader):
            raise TypeError("reader MUST be callable")

        closed_function = BoundedInboundHttpReadOutcomeHandler.closed.fget
        if closed_function is None:
            raise ValueError("M40 closed property MUST retain an exact getter")

        self._handler = read_outcome_handler
        self._reader = reader
        self._progress_function = BoundedInboundHttpReadOutcomeHandler.progress
        self._accept_function = BoundedInboundHttpReadOutcomeHandler.accept_outcome
        self._take_function = BoundedInboundHttpReadOutcomeHandler.take_completed
        self._close_function = BoundedInboundHttpReadOutcomeHandler.close
        self._closed_function = closed_function
        self._progress = self._progress_function.__get__(
            read_outcome_handler, BoundedInboundHttpReadOutcomeHandler
        )
        self._accept = self._accept_function.__get__(
            read_outcome_handler, BoundedInboundHttpReadOutcomeHandler
        )
        self._take = self._take_function.__get__(
            read_outcome_handler, BoundedInboundHttpReadOutcomeHandler
        )
        self._close = self._close_function.__get__(
            read_outcome_handler, BoundedInboundHttpReadOutcomeHandler
        )
        self._closed_getter = self._closed_function.__get__(
            read_outcome_handler, BoundedInboundHttpReadOutcomeHandler
        )
        self._binding_witness = self._binding_snapshot()
        self._validate_bindings()
        self._closed_value()

    def _binding_snapshot(self) -> tuple[Any, ...]:
        return (
            _BINDING_MARKER,
            self._handler,
            self._reader,
            self._progress_function,
            self._accept_function,
            self._take_function,
            self._close_function,
            self._closed_function,
        )

    def _validate_bound_method(self, bound: Any, function: Any, label: str) -> None:
        if (
            getattr(bound, "__self__", None) is not self._handler
            or getattr(bound, "__func__", None) is not function
        ):
            _fail("READ_INVOCATION_BINDING_DRIFT", f"captured M40 {label} binding changed")

    def _validate_bindings(self) -> None:
        if type(self._handler) is not BoundedInboundHttpReadOutcomeHandler:
            _fail("READ_INVOCATION_BINDING_DRIFT", "M40 handler changed type")
        if self._binding_witness != self._binding_snapshot():
            _fail("READ_INVOCATION_BINDING_DRIFT", "M41 binding witness changed")
        if not callable(self._reader):
            _fail("READ_INVOCATION_BINDING_DRIFT", "construction-bound reader is no longer callable")
        self._validate_bound_method(self._progress, self._progress_function, "progress")
        self._validate_bound_method(self._accept, self._accept_function, "accept-outcome")
        self._validate_bound_method(self._take, self._take_function, "take-completed")
        self._validate_bound_method(self._close, self._close_function, "close")
        self._validate_bound_method(self._closed_getter, self._closed_function, "closed")

    def _closed_value(self) -> bool:
        self._validate_bindings()
        try:
            value = self._closed_getter()
        except InboundHttpReadOutcomeError as exc:
            _fail_from_outcome(
                "READ_INVOCATION_OUTCOME_REJECTED",
                "M40 rejected M41 closed-state inspection",
                exc,
            )
        if type(value) is not bool:
            _fail("READ_INVOCATION_BINDING_DRIFT", "M40 closed getter returned non-boolean")
        self._validate_bindings()
        return value

    def _replay_progress(
        self, progress: InboundHttpReadSessionProgress
    ) -> InboundHttpReadSessionProgress:
        if type(progress) is not InboundHttpReadSessionProgress:
            _fail("READ_INVOCATION_PROGRESS_DRIFT", "M40 returned unexpected progress type")
        try:
            witnessed = replace(progress)
        except ValueError:
            _fail("READ_INVOCATION_PROGRESS_DRIFT", "M40 progress failed integrity replay")
        if witnessed.plan.action not in (READ_ACTION_READ, READ_ACTION_COMPLETE):
            _fail("READ_INVOCATION_PROGRESS_DRIFT", "M40 progress has unknown plan action")
        return witnessed

    def _current_progress(self) -> InboundHttpReadSessionProgress:
        self._validate_bindings()
        if self._closed_value():
            _fail("READ_INVOCATION_SESSION_CLOSED", "M41 source session is closed")
        try:
            progress = self._progress()
        except InboundHttpReadOutcomeError as exc:
            self._validate_bindings()
            _fail_from_outcome(
                "READ_INVOCATION_OUTCOME_REJECTED",
                "M40 rejected M41 progress inspection",
                exc,
            )
        self._validate_bindings()
        return self._replay_progress(progress)

    def _terminal_close(self) -> None:
        """Close on a pre-reader path where the complete M41 binding is intact."""
        self._validate_bindings()
        try:
            self._close()
        except InboundHttpReadOutcomeError as exc:
            self._validate_bindings()
            _fail_from_outcome(
                "READ_INVOCATION_CLOSE_FAILED",
                "M40 rejected terminal M41 close",
                exc,
            )
        self._validate_bindings()
        if not self._closed_value():
            _fail("READ_INVOCATION_CLOSE_FAILED", "M40 did not close after terminal M41 path")

    def _best_effort_close_after_reader(self) -> None:
        """Clear M40/M39 without trusting reader-sensitive M41 bindings.

        Once the reader has been invoked, an M41 binding drift must not strand
        consumed external input in a reusable partial session. This cleanup uses
        only the construction-witnessed M40 close/closed bound methods. It cannot
        sandbox arbitrary same-process memory corruption; if even those captured
        cleanup bindings drift, cleanup is reported as uncertain and fails closed.
        """
        witness = self._binding_witness
        if (
            type(witness) is not tuple
            or len(witness) != 8
            or witness[0] != _BINDING_MARKER
            or witness[1] is not self._handler
            or type(self._handler) is not BoundedInboundHttpReadOutcomeHandler
        ):
            _fail(
                "READ_INVOCATION_CLEANUP_UNCERTAIN",
                "post-reader cleanup binding witness is unavailable",
            )
        expected_close = witness[6]
        expected_closed = witness[7]
        if (
            getattr(self._close, "__self__", None) is not self._handler
            or getattr(self._close, "__func__", None) is not expected_close
            or getattr(self._closed_getter, "__self__", None) is not self._handler
            or getattr(self._closed_getter, "__func__", None) is not expected_closed
        ):
            _fail(
                "READ_INVOCATION_CLEANUP_UNCERTAIN",
                "captured post-reader cleanup authority changed",
            )
        try:
            self._close()
            closed = self._closed_getter()
        except Exception:
            _fail(
                "READ_INVOCATION_CLEANUP_UNCERTAIN",
                "post-reader cleanup could not be verified",
            )
        if closed is not True:
            _fail(
                "READ_INVOCATION_CLEANUP_UNCERTAIN",
                "post-reader cleanup did not verify a closed session",
            )

    def _post_reader_validate_bindings(self) -> None:
        try:
            self._validate_bindings()
        except InboundHttpReadInvocationError:
            self._best_effort_close_after_reader()
            raise

    def _post_reader_replay_progress(
        self, progress: InboundHttpReadSessionProgress
    ) -> InboundHttpReadSessionProgress:
        try:
            return self._replay_progress(progress)
        except InboundHttpReadInvocationError:
            self._best_effort_close_after_reader()
            raise

    @property
    def closed(self) -> bool:
        return self._closed_value()

    def invoke_once(self) -> InboundHttpReadInvocationResult:
        """Perform zero or one construction-bound reader invocation."""
        prior = self._current_progress()

        if prior.plan.action == READ_ACTION_COMPLETE:
            self._validate_bindings()
            try:
                completed = self._take()
            except InboundHttpReadOutcomeError as exc:
                self._validate_bindings()
                _fail_from_outcome(
                    "READ_INVOCATION_OUTCOME_REJECTED",
                    "M40 rejected M41 completion transfer",
                    exc,
                )
            self._validate_bindings()
            if type(completed) is not CompletedInboundHttpReadSession:
                _fail("READ_INVOCATION_COMPLETION_DRIFT", "M40 returned unexpected completion type")
            try:
                witnessed_completed = replace(completed)
            except ValueError:
                _fail("READ_INVOCATION_COMPLETION_DRIFT", "M40 completion failed integrity replay")
            if not self._closed_value():
                _fail("READ_INVOCATION_COMPLETION_DRIFT", "completion transfer did not close M40")
            return InboundHttpReadInvocationResult(
                state=READ_INVOCATION_COMPLETED,
                reader_invoked=False,
                requested_bytes=0,
                outcome_kind=None,
                completed=witnessed_completed,
            )

        if prior.plan.action != READ_ACTION_READ:
            _fail("READ_INVOCATION_PROGRESS_DRIFT", "M40 returned unknown planning state")
        budget = prior.plan.next_read_bytes
        if type(budget) is not int or budget <= 0:
            _fail("READ_INVOCATION_PROGRESS_DRIFT", "READ plan MUST carry positive exact byte budget")

        self._validate_bindings()
        try:
            outcome = self._reader(budget)
        except Exception:
            self._post_reader_validate_bindings()
            try:
                self._accept(InboundHttpReadOutcome.failure())
            except InboundHttpReadOutcomeError as exc:
                self._best_effort_close_after_reader()
                _fail_from_outcome(
                    "READ_INVOCATION_READER_FAILURE",
                    "injected reader failed; M40 closed the session",
                    exc,
                )
            self._best_effort_close_after_reader()
            _fail("READ_INVOCATION_READER_FAILURE", "injected reader failed")

        self._post_reader_validate_bindings()
        if type(outcome) is not InboundHttpReadOutcome:
            self._best_effort_close_after_reader()
            _fail(
                "INVALID_READER_RESULT",
                "reader MUST return exact InboundHttpReadOutcome; session was closed",
            )
        try:
            witnessed_outcome = replace(outcome)
        except ValueError:
            self._best_effort_close_after_reader()
            _fail("READ_INVOCATION_OUTCOME_DRIFT", "reader outcome failed integrity replay")

        try:
            progress = self._accept(witnessed_outcome)
        except InboundHttpReadOutcomeError as exc:
            self._best_effort_close_after_reader()
            _fail_from_outcome(
                "READ_INVOCATION_OUTCOME_REJECTED",
                "M40 rejected the already-returned reader outcome",
                exc,
            )
        self._post_reader_validate_bindings()
        witnessed_progress = self._post_reader_replay_progress(progress)

        if witnessed_outcome.kind != READ_OUTCOME_DATA:
            self._best_effort_close_after_reader()
            _fail("READ_INVOCATION_OUTCOME_DRIFT", "non-DATA outcome unexpectedly returned progress")
        if witnessed_progress.reads_completed != prior.reads_completed + 1:
            self._best_effort_close_after_reader()
            _fail("READ_INVOCATION_PROGRESS_DRIFT", "read accounting did not advance exactly once")
        if witnessed_progress.buffered_bytes != prior.buffered_bytes + len(witnessed_outcome.chunk):
            self._best_effort_close_after_reader()
            _fail("READ_INVOCATION_PROGRESS_DRIFT", "buffer accounting does not match DATA outcome")
        if witnessed_progress.last_accepted_chunk_bytes != len(witnessed_outcome.chunk):
            self._best_effort_close_after_reader()
            _fail("READ_INVOCATION_PROGRESS_DRIFT", "accepted chunk count does not match DATA outcome")

        return InboundHttpReadInvocationResult(
            state=READ_INVOCATION_PROGRESS,
            reader_invoked=True,
            requested_bytes=budget,
            outcome_kind=READ_OUTCOME_DATA,
            progress=witnessed_progress,
        )

    def close(self) -> None:
        """Idempotently clear/close the construction-bound M40/M39 session."""
        self._validate_bindings()
        if self._closed_value():
            return
        self._terminal_close()
