"""Transport-free semantics for already-returned response-write outcomes.

M47 distinguishes positive progress, zero progress/closed, and generic failure
without invoking a writer. Positive progress is delegated to one
construction-bound M46 session; terminal outcomes close that session.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any, Final

from .inbound_http_response_write_plan import WRITE_ACTION_COMPLETE, WRITE_ACTION_WRITE
from .inbound_http_response_write_session import (
    BoundedInboundHttpResponseWriteSession,
    CompletedInboundHttpResponseWriteSession,
    InboundHttpResponseWriteSessionError,
    InboundHttpResponseWriteSessionProgress,
)

WRITE_OUTCOME_PROGRESS: Final = "PROGRESS"
WRITE_OUTCOME_ZERO: Final = "ZERO"
WRITE_OUTCOME_FAILURE: Final = "FAILURE"
_WRITE_OUTCOME_KINDS: Final = frozenset(
    (WRITE_OUTCOME_PROGRESS, WRITE_OUTCOME_ZERO, WRITE_OUTCOME_FAILURE)
)
_NEGATIVE_FIELDS: Final = (
    "writer_invoked",
    "socket_accessed",
    "tls_terminated",
    "transmitted",
    "request_authenticated",
    "peer_identity_proven",
    "establishes_marketplace_truth",
    "establishes_trust",
    "establishes_authorization",
    "authorizes_protected_side_effects",
)

__all__ = [
    "WRITE_OUTCOME_FAILURE",
    "WRITE_OUTCOME_PROGRESS",
    "WRITE_OUTCOME_ZERO",
    "BoundedInboundHttpResponseWriteOutcomeHandler",
    "InboundHttpResponseWriteOutcome",
    "InboundHttpResponseWriteOutcomeError",
]


class InboundHttpResponseWriteOutcomeError(RuntimeError):
    """Fail-closed M47 error preserving M46/M45/M44 reason metadata."""

    def __init__(
        self,
        code: str,
        message: str,
        *,
        session_code: str | None = None,
        transition_code: str | None = None,
        write_plan_code: str | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.session_code = session_code
        self.transition_code = transition_code
        self.write_plan_code = write_plan_code


def _fail(
    code: str,
    message: str,
    *,
    session_code: str | None = None,
    transition_code: str | None = None,
    write_plan_code: str | None = None,
) -> None:
    raise InboundHttpResponseWriteOutcomeError(
        code,
        message,
        session_code=session_code,
        transition_code=transition_code,
        write_plan_code=write_plan_code,
    )


def _require_negative(value: object, *, code: str) -> None:
    for name in _NEGATIVE_FIELDS:
        if getattr(value, name, None) is not False:
            _fail(code, "M47 observed promoted authority on an original object")


def _fail_from_session(exc: InboundHttpResponseWriteSessionError) -> None:
    _fail(
        "WRITE_OUTCOME_SESSION_REJECTED",
        "M46 rejected the M47 operation",
        session_code=exc.code,
        transition_code=exc.transition_code,
        write_plan_code=exc.write_plan_code,
    )


@dataclass(frozen=True)
class InboundHttpResponseWriteOutcome:
    """One immutable already-returned write outcome with no transport authority."""

    kind: str
    accepted_write_bytes: int = 0
    integrity_snapshot: tuple[Any, ...] | None = field(default=None, repr=False)
    writer_invoked: bool = field(default=False, init=False)
    socket_accessed: bool = field(default=False, init=False)
    tls_terminated: bool = field(default=False, init=False)
    transmitted: bool = field(default=False, init=False)
    request_authenticated: bool = field(default=False, init=False)
    peer_identity_proven: bool = field(default=False, init=False)
    establishes_marketplace_truth: bool = field(default=False, init=False)
    establishes_trust: bool = field(default=False, init=False)
    establishes_authorization: bool = field(default=False, init=False)
    authorizes_protected_side_effects: bool = field(default=False, init=False)

    def __post_init__(self) -> None:
        if type(self.kind) is not str or self.kind not in _WRITE_OUTCOME_KINDS:
            raise ValueError("kind MUST be one canonical M47 write-outcome kind")
        if type(self.accepted_write_bytes) is not int:
            raise ValueError("accepted_write_bytes MUST be an exact integer")
        if self.kind == WRITE_OUTCOME_PROGRESS:
            if self.accepted_write_bytes <= 0:
                raise ValueError("PROGRESS outcome MUST contain a positive write count")
        elif self.accepted_write_bytes != 0:
            raise ValueError("ZERO/FAILURE outcome MUST carry a zero write count")
        for name in _NEGATIVE_FIELDS:
            if getattr(self, name, None) is not False:
                raise ValueError("M47 outcome promoted forbidden authority")
        current = (
            "inbound-http-response-write-outcome-v1",
            self.kind,
            self.accepted_write_bytes,
            *(getattr(self, name) for name in _NEGATIVE_FIELDS),
        )
        if self.integrity_snapshot is not None and self.integrity_snapshot != current:
            raise ValueError("M47 write-outcome integrity snapshot mismatch")
        if self.integrity_snapshot is None:
            object.__setattr__(self, "integrity_snapshot", current)

    @classmethod
    def progress(cls, accepted_write_bytes: int) -> "InboundHttpResponseWriteOutcome":
        return cls(kind=WRITE_OUTCOME_PROGRESS, accepted_write_bytes=accepted_write_bytes)

    @classmethod
    def zero(cls) -> "InboundHttpResponseWriteOutcome":
        return cls(kind=WRITE_OUTCOME_ZERO)

    @classmethod
    def failure(cls) -> "InboundHttpResponseWriteOutcome":
        return cls(kind=WRITE_OUTCOME_FAILURE)


class BoundedInboundHttpResponseWriteOutcomeHandler:
    """Apply already-returned write outcomes to one exact M46 session."""

    __slots__ = (
        "_session",
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

    def __init__(self, *, write_session: BoundedInboundHttpResponseWriteSession) -> None:
        if type(write_session) is not BoundedInboundHttpResponseWriteSession:
            raise TypeError("write_session MUST be exact BoundedInboundHttpResponseWriteSession")
        closed_function = BoundedInboundHttpResponseWriteSession.closed.fget
        if closed_function is None:
            raise ValueError("M46 closed property MUST retain an exact getter")
        self._session = write_session
        self._progress_function = BoundedInboundHttpResponseWriteSession.progress
        self._accept_function = BoundedInboundHttpResponseWriteSession.accept_write_count
        self._take_function = BoundedInboundHttpResponseWriteSession.take_completed
        self._close_function = BoundedInboundHttpResponseWriteSession.close
        self._closed_function = closed_function
        self._progress = self._progress_function.__get__(
            write_session, BoundedInboundHttpResponseWriteSession
        )
        self._accept = self._accept_function.__get__(
            write_session, BoundedInboundHttpResponseWriteSession
        )
        self._take = self._take_function.__get__(
            write_session, BoundedInboundHttpResponseWriteSession
        )
        self._close = self._close_function.__get__(
            write_session, BoundedInboundHttpResponseWriteSession
        )
        self._closed_getter = self._closed_function.__get__(
            write_session, BoundedInboundHttpResponseWriteSession
        )
        self._binding_witness = self._binding_snapshot()
        self._validate_bindings()
        self._closed_value()

    def _binding_snapshot(self) -> tuple[Any, ...]:
        return (
            "inbound-http-response-write-outcome-binding-v1",
            self._session,
            self._progress_function,
            self._accept_function,
            self._take_function,
            self._close_function,
            self._closed_function,
        )

    def _validate_bound_method(self, bound: Any, function: Any, label: str) -> None:
        if (
            getattr(bound, "__self__", None) is not self._session
            or getattr(bound, "__func__", None) is not function
        ):
            _fail("WRITE_OUTCOME_BINDING_DRIFT", f"M47 captured M46 {label} binding changed")

    def _validate_bindings(self) -> None:
        if type(self._session) is not BoundedInboundHttpResponseWriteSession:
            _fail("WRITE_OUTCOME_BINDING_DRIFT", "M46 session changed type")
        if self._binding_witness != self._binding_snapshot():
            _fail("WRITE_OUTCOME_BINDING_DRIFT", "M47 binding witness changed")
        self._validate_bound_method(self._progress, self._progress_function, "progress")
        self._validate_bound_method(self._accept, self._accept_function, "accept")
        self._validate_bound_method(self._take, self._take_function, "take")
        self._validate_bound_method(self._close, self._close_function, "close")
        self._validate_bound_method(self._closed_getter, self._closed_function, "closed")

    def _closed_value(self) -> bool:
        self._validate_bindings()
        try:
            value = self._closed_getter()
        except InboundHttpResponseWriteSessionError as exc:
            self._validate_bindings()
            _fail_from_session(exc)
        if type(value) is not bool:
            _fail("WRITE_OUTCOME_BINDING_DRIFT", "M46 closed getter returned non-boolean")
        self._validate_bindings()
        return value

    def _replay_progress(
        self, value: InboundHttpResponseWriteSessionProgress
    ) -> InboundHttpResponseWriteSessionProgress:
        if type(value) is not InboundHttpResponseWriteSessionProgress:
            _fail("WRITE_OUTCOME_PROGRESS_DRIFT", "M46 returned unexpected progress type")
        # Required by M46: inspect original init=False authority facts before replay.
        _require_negative(value, code="WRITE_OUTCOME_PROGRESS_AUTHORITY")
        try:
            replayed = replace(value)
        except ValueError:
            _fail("WRITE_OUTCOME_PROGRESS_DRIFT", "M46 progress failed integrity replay")
        _require_negative(replayed, code="WRITE_OUTCOME_PROGRESS_AUTHORITY")
        if replayed.plan.action not in (WRITE_ACTION_WRITE, WRITE_ACTION_COMPLETE):
            _fail("WRITE_OUTCOME_PROGRESS_DRIFT", "M46 progress returned unknown write action")
        return replayed

    def _replay_completion(
        self, value: CompletedInboundHttpResponseWriteSession
    ) -> CompletedInboundHttpResponseWriteSession:
        if type(value) is not CompletedInboundHttpResponseWriteSession:
            _fail("WRITE_OUTCOME_COMPLETION_DRIFT", "M46 returned unexpected completion type")
        _require_negative(value, code="WRITE_OUTCOME_COMPLETION_AUTHORITY")
        try:
            replayed = replace(value)
        except ValueError:
            _fail("WRITE_OUTCOME_COMPLETION_DRIFT", "M46 completion failed integrity replay")
        _require_negative(replayed, code="WRITE_OUTCOME_COMPLETION_AUTHORITY")
        if replayed.plan.action != WRITE_ACTION_COMPLETE:
            _fail("WRITE_OUTCOME_COMPLETION_DRIFT", "M46 completion lost COMPLETE plan")
        return replayed

    def _replay_outcome(self, value: InboundHttpResponseWriteOutcome) -> InboundHttpResponseWriteOutcome:
        if type(value) is not InboundHttpResponseWriteOutcome:
            _fail("INVALID_WRITE_OUTCOME", "M47 outcome MUST be exact InboundHttpResponseWriteOutcome")
        _require_negative(value, code="WRITE_OUTCOME_AUTHORITY")
        try:
            replayed = replace(value)
        except ValueError:
            _fail("WRITE_OUTCOME_DRIFT", "M47 outcome failed integrity replay")
        _require_negative(replayed, code="WRITE_OUTCOME_AUTHORITY")
        return replayed

    def _open_progress(self) -> InboundHttpResponseWriteSessionProgress:
        if self._closed_value():
            _fail("WRITE_OUTCOME_SESSION_CLOSED", "M47 source M46 session is closed")
        try:
            progress = self._progress()
        except InboundHttpResponseWriteSessionError as exc:
            self._validate_bindings()
            _fail_from_session(exc)
        self._validate_bindings()
        return self._replay_progress(progress)

    def _terminal_close(self) -> None:
        self._validate_bindings()
        self._close()
        self._validate_bindings()
        if not self._closed_value():
            _fail("WRITE_OUTCOME_CLOSE_DRIFT", "M46 did not close after terminal M47 path")

    def _terminal_fail(
        self,
        code: str,
        message: str,
        *,
        session_code: str | None = None,
        transition_code: str | None = None,
        write_plan_code: str | None = None,
    ) -> None:
        self._terminal_close()
        _fail(
            code,
            message,
            session_code=session_code,
            transition_code=transition_code,
            write_plan_code=write_plan_code,
        )

    @property
    def closed(self) -> bool:
        return self._closed_value()

    def progress(self) -> InboundHttpResponseWriteSessionProgress:
        return self._open_progress()

    def accept_outcome(
        self, outcome: InboundHttpResponseWriteOutcome
    ) -> InboundHttpResponseWriteSessionProgress:
        """Apply one already-returned outcome without invoking a writer."""
        witnessed_outcome = self._replay_outcome(outcome)
        prior = self._open_progress()
        if prior.plan.action == WRITE_ACTION_COMPLETE:
            self._terminal_fail(
                "WRITE_OUTCOME_AFTER_COMPLETE",
                "M47 rejects supplied outcomes after local write completion",
            )

        if witnessed_outcome.kind == WRITE_OUTCOME_PROGRESS:
            try:
                returned = self._accept(witnessed_outcome.accepted_write_bytes)
            except InboundHttpResponseWriteSessionError as exc:
                self._validate_bindings()
                self._terminal_fail(
                    "WRITE_OUTCOME_SESSION_REJECTED",
                    "M46 rejected already-returned M47 progress; session was closed",
                    session_code=exc.code,
                    transition_code=exc.transition_code,
                    write_plan_code=exc.write_plan_code,
                )
            self._validate_bindings()
            try:
                progress = self._replay_progress(returned)
            except InboundHttpResponseWriteOutcomeError:
                self._terminal_close()
                raise
            if progress.write_calls_completed != prior.write_calls_completed + 1:
                self._terminal_fail(
                    "WRITE_OUTCOME_PROGRESS_DRIFT",
                    "M46 did not advance write-call accounting exactly once",
                )
            if progress.bytes_written != prior.bytes_written + witnessed_outcome.accepted_write_bytes:
                self._terminal_fail(
                    "WRITE_OUTCOME_PROGRESS_DRIFT",
                    "M46 byte accounting does not match M47 progress",
                )
            if progress.last_accepted_write_bytes != witnessed_outcome.accepted_write_bytes:
                self._terminal_fail(
                    "WRITE_OUTCOME_PROGRESS_DRIFT",
                    "M46 accepted-count metadata does not match M47 progress",
                )
            try:
                current = self._open_progress()
            except InboundHttpResponseWriteOutcomeError:
                self._terminal_close()
                raise
            if (
                current.write_calls_completed != progress.write_calls_completed
                or current.bytes_written != progress.bytes_written
                or current.plan.integrity_snapshot != progress.plan.integrity_snapshot
            ):
                self._terminal_fail(
                    "WRITE_OUTCOME_PROGRESS_DRIFT",
                    "M46 current state differs from returned progress",
                )
            return progress

        if witnessed_outcome.kind == WRITE_OUTCOME_ZERO:
            self._terminal_fail(
                "WRITE_ZERO_BEFORE_COMPLETE",
                "M47 observed zero write progress before local completion",
            )
        if witnessed_outcome.kind == WRITE_OUTCOME_FAILURE:
            self._terminal_fail(
                "WRITE_FAILURE_BEFORE_COMPLETE",
                "M47 observed a generic write failure before local completion",
            )
        self._terminal_fail("WRITE_OUTCOME_DRIFT", "M47 outcome kind changed after replay")

    def take_completed(self) -> CompletedInboundHttpResponseWriteSession:
        """Transfer one exact M46 completion without requiring another outcome."""
        self._validate_bindings()
        if self._closed_value():
            _fail("WRITE_OUTCOME_SESSION_CLOSED", "M47 source M46 session is closed")
        try:
            completed = self._take()
        except InboundHttpResponseWriteSessionError as exc:
            self._validate_bindings()
            _fail_from_session(exc)
        self._validate_bindings()
        witnessed = self._replay_completion(completed)
        if not self._closed_value():
            _fail("WRITE_OUTCOME_COMPLETION_DRIFT", "M46 completion did not close source session")
        return witnessed

    def close(self) -> None:
        """Idempotently close the construction-bound M46 source session."""
        if self._closed_value():
            return
        self._terminal_close()
