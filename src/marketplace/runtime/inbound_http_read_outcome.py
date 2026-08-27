"""Transport-free semantic handling for already-returned inbound read outcomes.

M40 distinguishes DATA, EOF, and FAILURE without invoking a reader callback or
performing transport I/O. Non-empty DATA is delegated to one construction-bound
M39 session; terminal outcomes fail closed and clear that session.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from hashlib import sha256
from typing import Any, Final

from .inbound_http_read_plan import READ_ACTION_COMPLETE, READ_ACTION_READ
from .inbound_http_read_session import (
    BoundedInboundHttpReadSession,
    CompletedInboundHttpReadSession,
    InboundHttpReadSessionError,
    InboundHttpReadSessionProgress,
)

READ_OUTCOME_DATA: Final = "DATA"
READ_OUTCOME_EOF: Final = "EOF"
READ_OUTCOME_FAILURE: Final = "FAILURE"
_READ_OUTCOME_KINDS: Final = frozenset(
    (READ_OUTCOME_DATA, READ_OUTCOME_EOF, READ_OUTCOME_FAILURE)
)


class InboundHttpReadOutcomeError(RuntimeError):
    """Fail-closed M40 error with preserved M39-and-lower reason metadata."""

    def __init__(
        self,
        code: str,
        message: str,
        *,
        session_code: str | None = None,
        transition_code: str | None = None,
        plan_code: str | None = None,
        stream_code: str | None = None,
        wire_code: str | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.session_code = session_code
        self.transition_code = transition_code
        self.plan_code = plan_code
        self.stream_code = stream_code
        self.wire_code = wire_code


def _fail(
    code: str,
    message: str,
    *,
    session_code: str | None = None,
    transition_code: str | None = None,
    plan_code: str | None = None,
    stream_code: str | None = None,
    wire_code: str | None = None,
) -> None:
    raise InboundHttpReadOutcomeError(
        code,
        message,
        session_code=session_code,
        transition_code=transition_code,
        plan_code=plan_code,
        stream_code=stream_code,
        wire_code=wire_code,
    )


def _fail_from_session(exc: InboundHttpReadSessionError) -> None:
    _fail(
        "READ_SESSION_REJECTED",
        "M39 rejected the M40 read-outcome operation",
        session_code=exc.code,
        transition_code=exc.transition_code,
        plan_code=exc.plan_code,
        stream_code=exc.stream_code,
        wire_code=exc.wire_code,
    )


@dataclass(frozen=True)
class InboundHttpReadOutcome:
    """One immutable already-returned read outcome with no transport authority."""

    kind: str
    chunk: bytes = b""
    integrity_snapshot: tuple[Any, ...] | None = field(default=None, repr=False)
    reader_invoked: bool = field(default=False, init=False)
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
        if type(self.kind) is not str or self.kind not in _READ_OUTCOME_KINDS:
            raise ValueError("kind MUST be one canonical M40 read-outcome kind")
        if type(self.chunk) is not bytes:
            raise ValueError("chunk MUST be exact immutable bytes")
        if self.kind == READ_OUTCOME_DATA:
            if not self.chunk:
                raise ValueError("DATA outcome MUST contain non-empty bytes")
        elif self.chunk != b"":
            raise ValueError("EOF/FAILURE outcome MUST NOT contain payload bytes")

        for name in (
            "reader_invoked",
            "socket_accessed",
            "tls_terminated",
            "transmitted",
            "request_authenticated",
            "peer_identity_proven",
            "establishes_marketplace_truth",
            "establishes_trust",
            "establishes_authorization",
            "authorizes_protected_side_effects",
        ):
            if getattr(self, name, None) is not False:
                raise ValueError("M40 outcome promoted a forbidden authority fact")

        current = (
            "inbound-http-read-outcome-v1",
            self.kind,
            sha256(self.chunk).digest() if self.kind == READ_OUTCOME_DATA else None,
            len(self.chunk),
            self.reader_invoked,
            self.socket_accessed,
            self.tls_terminated,
            self.transmitted,
            self.request_authenticated,
            self.peer_identity_proven,
            self.establishes_marketplace_truth,
            self.establishes_trust,
            self.establishes_authorization,
            self.authorizes_protected_side_effects,
        )
        if self.integrity_snapshot is not None and self.integrity_snapshot != current:
            raise ValueError("M40 read-outcome integrity snapshot mismatch")
        if self.integrity_snapshot is None:
            object.__setattr__(self, "integrity_snapshot", current)

    @classmethod
    def data(cls, chunk: bytes) -> "InboundHttpReadOutcome":
        return cls(kind=READ_OUTCOME_DATA, chunk=chunk)

    @classmethod
    def eof(cls) -> "InboundHttpReadOutcome":
        return cls(kind=READ_OUTCOME_EOF)

    @classmethod
    def failure(cls) -> "InboundHttpReadOutcome":
        return cls(kind=READ_OUTCOME_FAILURE)


class BoundedInboundHttpReadOutcomeHandler:
    """Apply already-returned outcomes to one M39 session without reading."""

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
    )

    def __init__(self, *, read_session: BoundedInboundHttpReadSession) -> None:
        if type(read_session) is not BoundedInboundHttpReadSession:
            raise TypeError("read_session MUST be exact BoundedInboundHttpReadSession")

        closed_property = BoundedInboundHttpReadSession.closed
        closed_function = closed_property.fget
        if closed_function is None:
            raise ValueError("M39 closed property MUST retain an exact getter")

        self._session = read_session
        self._progress_function = BoundedInboundHttpReadSession.progress
        self._accept_function = BoundedInboundHttpReadSession.accept_chunk
        self._take_function = BoundedInboundHttpReadSession.take_completed
        self._close_function = BoundedInboundHttpReadSession.close
        self._closed_function = closed_function
        self._progress = self._progress_function.__get__(
            read_session,
            BoundedInboundHttpReadSession,
        )
        self._accept = self._accept_function.__get__(
            read_session,
            BoundedInboundHttpReadSession,
        )
        self._take = self._take_function.__get__(
            read_session,
            BoundedInboundHttpReadSession,
        )
        self._close = self._close_function.__get__(
            read_session,
            BoundedInboundHttpReadSession,
        )
        self._closed_getter = self._closed_function.__get__(
            read_session,
            BoundedInboundHttpReadSession,
        )
        self._validate_bindings()
        self._closed_value()

    def _validate_bound_method(self, bound: Any, function: Any, label: str) -> None:
        if (
            getattr(bound, "__self__", None) is not self._session
            or getattr(bound, "__func__", None) is not function
        ):
            _fail("READ_OUTCOME_BINDING_DRIFT", f"M40 captured M39 {label} binding changed")

    def _validate_bindings(self) -> None:
        if type(self._session) is not BoundedInboundHttpReadSession:
            _fail("READ_OUTCOME_BINDING_DRIFT", "M39 session changed type after M40 construction")
        self._validate_bound_method(self._progress, self._progress_function, "progress")
        self._validate_bound_method(self._accept, self._accept_function, "accept")
        self._validate_bound_method(self._take, self._take_function, "take-completed")
        self._validate_bound_method(self._close, self._close_function, "close")
        self._validate_bound_method(self._closed_getter, self._closed_function, "closed")

    def _closed_value(self) -> bool:
        self._validate_bindings()
        try:
            value = self._closed_getter()
        except InboundHttpReadSessionError as exc:
            _fail_from_session(exc)
        if type(value) is not bool:
            _fail("READ_OUTCOME_BINDING_DRIFT", "M39 closed getter returned a non-boolean value")
        self._validate_bindings()
        return value

    def _replay_progress(
        self,
        progress: InboundHttpReadSessionProgress,
    ) -> InboundHttpReadSessionProgress:
        if type(progress) is not InboundHttpReadSessionProgress:
            _fail("READ_OUTCOME_PROGRESS_DRIFT", "M39 returned an unexpected progress type")
        try:
            witnessed = replace(progress)
        except ValueError:
            _fail("READ_OUTCOME_PROGRESS_DRIFT", "M39 progress failed integrity replay")
        if witnessed.plan.action not in (READ_ACTION_READ, READ_ACTION_COMPLETE):
            _fail("READ_OUTCOME_PROGRESS_DRIFT", "M39 progress returned an unknown read action")
        return witnessed

    def _open_progress(self) -> InboundHttpReadSessionProgress:
        self._validate_bindings()
        if self._closed_value():
            _fail("READ_OUTCOME_SESSION_CLOSED", "M40 read-outcome handler session is closed")
        try:
            progress = self._progress()
        except InboundHttpReadSessionError as exc:
            self._validate_bindings()
            _fail_from_session(exc)
        self._validate_bindings()
        return self._replay_progress(progress)

    def _terminal_close(self) -> None:
        self._validate_bindings()
        self._close()
        self._validate_bindings()
        if not self._closed_value():
            _fail("READ_OUTCOME_CLOSE_DRIFT", "M39 did not close after terminal M40 outcome")

    @property
    def closed(self) -> bool:
        return self._closed_value()

    def progress(self) -> InboundHttpReadSessionProgress:
        """Return exact replayed M39 progress without exposing raw request bytes."""
        return self._open_progress()

    def accept_outcome(self, outcome: InboundHttpReadOutcome) -> InboundHttpReadSessionProgress:
        """Apply one already-returned DATA/EOF/FAILURE outcome without reading."""
        if type(outcome) is not InboundHttpReadOutcome:
            _fail("INVALID_READ_OUTCOME", "M40 outcome MUST be exact InboundHttpReadOutcome")
        try:
            witnessed_outcome = replace(outcome)
        except ValueError:
            _fail("READ_OUTCOME_DRIFT", "M40 outcome failed integrity replay")

        prior = self._open_progress()
        if prior.plan.action == READ_ACTION_COMPLETE:
            self._terminal_close()
            _fail(
                "READ_OUTCOME_AFTER_COMPLETE",
                "M40 rejects any supplied read outcome after request completion",
            )

        if witnessed_outcome.kind == READ_OUTCOME_DATA:
            try:
                progress = self._accept(witnessed_outcome.chunk)
            except InboundHttpReadSessionError as exc:
                self._validate_bindings()
                _fail_from_session(exc)
            self._validate_bindings()
            witnessed_progress = self._replay_progress(progress)
            if witnessed_progress.reads_completed != prior.reads_completed + 1:
                _fail(
                    "READ_OUTCOME_PROGRESS_DRIFT",
                    "M39 did not advance read accounting exactly once for M40 DATA",
                )
            if witnessed_progress.buffered_bytes != prior.buffered_bytes + len(
                witnessed_outcome.chunk
            ):
                _fail(
                    "READ_OUTCOME_PROGRESS_DRIFT",
                    "M39 buffered byte accounting does not match M40 DATA",
                )
            if witnessed_progress.last_accepted_chunk_bytes != len(witnessed_outcome.chunk):
                _fail(
                    "READ_OUTCOME_PROGRESS_DRIFT",
                    "M39 accepted chunk accounting does not match M40 DATA",
                )
            return witnessed_progress

        if witnessed_outcome.kind == READ_OUTCOME_EOF:
            self._terminal_close()
            _fail(
                "READ_EOF_BEFORE_COMPLETE",
                "M40 observed EOF before the bounded request reached COMPLETE",
            )

        if witnessed_outcome.kind == READ_OUTCOME_FAILURE:
            self._terminal_close()
            _fail(
                "READ_FAILURE_BEFORE_COMPLETE",
                "M40 observed a generic read failure before request completion",
            )

        _fail("READ_OUTCOME_DRIFT", "M40 outcome kind changed after integrity replay")

    def take_completed(self) -> CompletedInboundHttpReadSession:
        """Delegate one-shot completion transfer to the captured M39 session."""
        self._validate_bindings()
        if self._closed_value():
            _fail("READ_OUTCOME_SESSION_CLOSED", "M40 read-outcome handler session is closed")
        try:
            completed = self._take()
        except InboundHttpReadSessionError as exc:
            self._validate_bindings()
            _fail_from_session(exc)
        self._validate_bindings()
        if type(completed) is not CompletedInboundHttpReadSession:
            _fail("READ_OUTCOME_COMPLETION_DRIFT", "M39 returned an unexpected completion type")
        try:
            witnessed = replace(completed)
        except ValueError:
            _fail("READ_OUTCOME_COMPLETION_DRIFT", "M39 completion failed integrity replay")
        if not self._closed_value():
            _fail("READ_OUTCOME_COMPLETION_DRIFT", "M39 completion did not close the source session")
        return witnessed

    def close(self) -> None:
        """Idempotently close/clear the construction-bound M39 session."""
        self._validate_bindings()
        self._close()
        self._validate_bindings()
        if not self._closed_value():
            _fail("READ_OUTCOME_CLOSE_DRIFT", "M39 did not remain closed after M40 close")
