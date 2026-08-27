"""One-step bounded invocation of one injected inbound HTTP response writer.

M48 invokes at most one construction-bound writer per public call. It owns no
socket, TLS stack, listener, deployment, or concrete transport and never retries.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any, Callable, Final

from .inbound_http_response_prepare import PreparedInboundHttpReadResponse
from .inbound_http_response_write_outcome import (
    WRITE_OUTCOME_PROGRESS,
    BoundedInboundHttpResponseWriteOutcomeHandler,
    InboundHttpResponseWriteOutcome,
    InboundHttpResponseWriteOutcomeError,
)
from .inbound_http_response_write_plan import WRITE_ACTION_COMPLETE, WRITE_ACTION_WRITE
from .inbound_http_response_write_session import (
    BoundedInboundHttpResponseWriteSession,
    CompletedInboundHttpResponseWriteSession,
    InboundHttpResponseWriteSessionProgress,
)

WRITE_INVOCATION_PROGRESS: Final = "PROGRESS"
WRITE_INVOCATION_COMPLETED: Final = "COMPLETED"
_INVOCATION_STATES: Final = frozenset((WRITE_INVOCATION_PROGRESS, WRITE_INVOCATION_COMPLETED))
_BINDING_MARKER: Final = "inbound-http-response-write-invoker-binding-v1"
_M46_NEGATIVE_FIELDS: Final = (
    "writer_invoked", "socket_accessed", "tls_terminated", "transmitted",
    "request_authenticated", "peer_identity_proven", "establishes_marketplace_truth",
    "establishes_trust", "establishes_authorization", "authorizes_protected_side_effects",
)
_M43_NEGATIVE_FIELDS: Final = (
    "transmitted", "socket_access_proven", "network_origin_proven",
    "request_authenticated", "peer_identity_proven", "establishes_marketplace_truth",
    "establishes_trust", "establishes_authorization", "authorizes_protected_side_effects",
)
_M47_NEGATIVE_FIELDS: Final = _M46_NEGATIVE_FIELDS

__all__ = [
    "WRITE_INVOCATION_COMPLETED", "WRITE_INVOCATION_PROGRESS",
    "BoundedInboundHttpResponseWriteInvoker", "InboundHttpResponseWriteInvocationError",
    "InboundHttpResponseWriteInvocationResult",
]


class InboundHttpResponseWriteInvocationError(RuntimeError):
    """Fail-closed M48 error preserving M47-and-lower reason metadata."""
    def __init__(self, code: str, message: str, *, outcome_code: str | None = None,
                 session_code: str | None = None, transition_code: str | None = None,
                 write_plan_code: str | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.outcome_code = outcome_code
        self.session_code = session_code
        self.transition_code = transition_code
        self.write_plan_code = write_plan_code


def _fail(code: str, message: str, *, outcome_code: str | None = None,
          session_code: str | None = None, transition_code: str | None = None,
          write_plan_code: str | None = None) -> None:
    raise InboundHttpResponseWriteInvocationError(
        code, message, outcome_code=outcome_code, session_code=session_code,
        transition_code=transition_code, write_plan_code=write_plan_code,
    )


def _fail_from_outcome(code: str, message: str, exc: InboundHttpResponseWriteOutcomeError) -> None:
    _fail(code, message, outcome_code=exc.code, session_code=exc.session_code,
          transition_code=exc.transition_code, write_plan_code=exc.write_plan_code)


def _require_negative(value: object, names: tuple[str, ...], *, code: str) -> None:
    for name in names:
        if getattr(value, name, None) is not False:
            _fail(code, "M48 observed promoted authority on an original object")


def _replay_m46_progress(value: InboundHttpResponseWriteSessionProgress) -> InboundHttpResponseWriteSessionProgress:
    if type(value) is not InboundHttpResponseWriteSessionProgress:
        _fail("WRITE_INVOCATION_PROGRESS_DRIFT", "M47 returned unexpected progress type")
    _require_negative(value, _M46_NEGATIVE_FIELDS, code="WRITE_INVOCATION_PROGRESS_AUTHORITY")
    try:
        replayed = replace(value)
    except ValueError:
        _fail("WRITE_INVOCATION_PROGRESS_DRIFT", "M46 progress failed integrity replay")
    _require_negative(replayed, _M46_NEGATIVE_FIELDS, code="WRITE_INVOCATION_PROGRESS_AUTHORITY")
    if replayed.plan.action not in (WRITE_ACTION_WRITE, WRITE_ACTION_COMPLETE):
        _fail("WRITE_INVOCATION_PROGRESS_DRIFT", "M46 progress contains unknown write action")
    return replayed


def _replay_m46_completion(value: CompletedInboundHttpResponseWriteSession) -> CompletedInboundHttpResponseWriteSession:
    if type(value) is not CompletedInboundHttpResponseWriteSession:
        _fail("WRITE_INVOCATION_COMPLETION_DRIFT", "M47 returned unexpected completion type")
    _require_negative(value, _M46_NEGATIVE_FIELDS, code="WRITE_INVOCATION_COMPLETION_AUTHORITY")
    try:
        replayed = replace(value)
    except ValueError:
        _fail("WRITE_INVOCATION_COMPLETION_DRIFT", "M46 completion failed integrity replay")
    _require_negative(replayed, _M46_NEGATIVE_FIELDS, code="WRITE_INVOCATION_COMPLETION_AUTHORITY")
    if replayed.plan.action != WRITE_ACTION_COMPLETE:
        _fail("WRITE_INVOCATION_COMPLETION_DRIFT", "M46 completion lost COMPLETE plan")
    return replayed


@dataclass(frozen=True)
class InboundHttpResponseWriteInvocationResult:
    """One M48 step result; never proof that offered bytes reached a peer."""
    state: str
    writer_invoked: bool
    offered_bytes: int
    outcome_kind: str | None
    progress: InboundHttpResponseWriteSessionProgress | None = None
    completed: CompletedInboundHttpResponseWriteSession | None = None
    integrity_snapshot: tuple[Any, ...] | None = field(default=None, repr=False)
    socket_access_proven: bool = field(default=False, init=False)
    tls_terminated: bool = field(default=False, init=False)
    transmitted: bool = field(default=False, init=False)
    request_authenticated: bool = field(default=False, init=False)
    peer_identity_proven: bool = field(default=False, init=False)
    establishes_marketplace_truth: bool = field(default=False, init=False)
    establishes_trust: bool = field(default=False, init=False)
    establishes_authorization: bool = field(default=False, init=False)
    authorizes_protected_side_effects: bool = field(default=False, init=False)

    def __post_init__(self) -> None:
        if type(self.state) is not str or self.state not in _INVOCATION_STATES:
            raise ValueError("state MUST be one canonical M48 state")
        if type(self.writer_invoked) is not bool:
            raise ValueError("writer_invoked MUST be exact bool")
        if type(self.offered_bytes) is not int or self.offered_bytes < 0:
            raise ValueError("offered_bytes MUST be non-negative exact int")
        if self.outcome_kind is not None and type(self.outcome_kind) is not str:
            raise ValueError("outcome_kind MUST be exact str or None")
        progress_snapshot = None
        completion_snapshot = None
        if self.state == WRITE_INVOCATION_PROGRESS:
            if self.writer_invoked is not True or self.offered_bytes <= 0:
                raise ValueError("PROGRESS MUST represent one positive writer invocation")
            if self.outcome_kind != WRITE_OUTCOME_PROGRESS:
                raise ValueError("successful M48 PROGRESS MUST arise from exact PROGRESS outcome")
            witnessed = _replay_m46_progress(self.progress)  # type: ignore[arg-type]
            if self.completed is not None:
                raise ValueError("PROGRESS MUST NOT carry completion")
            object.__setattr__(self, "progress", witnessed)
            progress_snapshot = witnessed.integrity_snapshot
        else:
            if self.writer_invoked is not False or self.offered_bytes != 0:
                raise ValueError("COMPLETED MUST NOT claim a writer invocation")
            if self.outcome_kind is not None or self.progress is not None:
                raise ValueError("COMPLETED MUST NOT carry outcome/progress")
            witnessed_completed = _replay_m46_completion(self.completed)  # type: ignore[arg-type]
            object.__setattr__(self, "completed", witnessed_completed)
            completion_snapshot = witnessed_completed.integrity_snapshot
        authority = (
            self.socket_access_proven, self.tls_terminated, self.transmitted,
            self.request_authenticated, self.peer_identity_proven,
            self.establishes_marketplace_truth, self.establishes_trust,
            self.establishes_authorization, self.authorizes_protected_side_effects,
        )
        if any(value is not False for value in authority):
            raise ValueError("M48 result promoted forbidden authority")
        current = (
            "inbound-http-response-write-invocation-result-v1", self.state,
            self.writer_invoked, self.offered_bytes, self.outcome_kind,
            progress_snapshot, completion_snapshot, *authority,
        )
        if self.integrity_snapshot is not None and self.integrity_snapshot != current:
            raise ValueError("M48 invocation-result integrity mismatch")
        if self.integrity_snapshot is None:
            object.__setattr__(self, "integrity_snapshot", current)


class BoundedInboundHttpResponseWriteInvoker:
    """Invoke one construction-bound writer at most once per public call."""
    __slots__ = (
        "_handler", "_session", "_writer", "_prepared_response", "_response_identity", "_response_integrity",
        "_progress_function", "_accept_function", "_take_function", "_close_function",
        "_closed_function", "_session_close_function", "_session_closed_function",
        "_progress", "_accept", "_take", "_close", "_closed_getter",
        "_session_close", "_session_closed_getter", "_binding_witness",
    )

    def __init__(self, *, write_outcome_handler: BoundedInboundHttpResponseWriteOutcomeHandler,
                 writer: Callable[[bytes], InboundHttpResponseWriteOutcome]) -> None:
        if type(write_outcome_handler) is not BoundedInboundHttpResponseWriteOutcomeHandler:
            raise TypeError("write_outcome_handler MUST be exact M47 handler")
        if not callable(writer):
            raise TypeError("writer MUST be callable")
        session = getattr(write_outcome_handler, "_session", None)
        if type(session) is not BoundedInboundHttpResponseWriteSession:
            raise ValueError("M47 MUST retain one exact M46 session")
        prepared = getattr(session, "_prepared_response", None)
        if type(prepared) is not PreparedInboundHttpReadResponse:
            raise ValueError("M46 MUST retain one exact M43 prepared response")
        _require_negative(prepared, _M43_NEGATIVE_FIELDS, code="WRITE_INVOCATION_PREPARED_AUTHORITY")
        try:
            replayed_prepared = replace(prepared)
        except ValueError as exc:
            raise ValueError("M43 prepared response failed integrity replay") from exc
        _require_negative(replayed_prepared, _M43_NEGATIVE_FIELDS, code="WRITE_INVOCATION_PREPARED_AUTHORITY")
        closed_function = BoundedInboundHttpResponseWriteOutcomeHandler.closed.fget
        session_closed_function = BoundedInboundHttpResponseWriteSession.closed.fget
        if closed_function is None or session_closed_function is None:
            raise ValueError("M47/M46 closed properties MUST retain exact getters")
        self._handler = write_outcome_handler
        self._session = session
        self._writer = writer
        self._prepared_response = prepared
        self._response_identity = id(prepared)
        self._response_integrity = replayed_prepared.integrity_snapshot
        self._progress_function = BoundedInboundHttpResponseWriteOutcomeHandler.progress
        self._accept_function = BoundedInboundHttpResponseWriteOutcomeHandler.accept_outcome
        self._take_function = BoundedInboundHttpResponseWriteOutcomeHandler.take_completed
        self._close_function = BoundedInboundHttpResponseWriteOutcomeHandler.close
        self._closed_function = closed_function
        self._session_close_function = BoundedInboundHttpResponseWriteSession.close
        self._session_closed_function = session_closed_function
        self._progress = self._progress_function.__get__(write_outcome_handler, BoundedInboundHttpResponseWriteOutcomeHandler)
        self._accept = self._accept_function.__get__(write_outcome_handler, BoundedInboundHttpResponseWriteOutcomeHandler)
        self._take = self._take_function.__get__(write_outcome_handler, BoundedInboundHttpResponseWriteOutcomeHandler)
        self._close = self._close_function.__get__(write_outcome_handler, BoundedInboundHttpResponseWriteOutcomeHandler)
        self._closed_getter = self._closed_function.__get__(write_outcome_handler, BoundedInboundHttpResponseWriteOutcomeHandler)
        self._session_close = self._session_close_function.__get__(session, BoundedInboundHttpResponseWriteSession)
        self._session_closed_getter = self._session_closed_function.__get__(session, BoundedInboundHttpResponseWriteSession)
        self._binding_witness = self._binding_snapshot()
        self._validate_bindings()
        self._closed_value()

    def _binding_snapshot(self) -> tuple[Any, ...]:
        return (_BINDING_MARKER, self._handler, self._session, self._writer,
                self._response_identity, self._response_integrity, self._progress_function,
                self._accept_function, self._take_function, self._close_function,
                self._closed_function, self._session_close_function, self._session_closed_function)

    def _validate_bound(self, bound: Any, owner: object, function: Any, label: str) -> None:
        if getattr(bound, "__self__", None) is not owner or getattr(bound, "__func__", None) is not function:
            _fail("WRITE_INVOCATION_BINDING_DRIFT", f"captured {label} binding changed")

    def _validate_prepared(self) -> PreparedInboundHttpReadResponse:
        if self._prepared_response is None or id(self._prepared_response) != self._response_identity:
            _fail("WRITE_INVOCATION_PREPARED_DRIFT", "M48 released or rebound its prepared response")
        if getattr(self._session, "_prepared_response", None) is not self._prepared_response:
            _fail("WRITE_INVOCATION_PREPARED_DRIFT", "M46 prepared-response binding changed")
        _require_negative(self._prepared_response, _M43_NEGATIVE_FIELDS, code="WRITE_INVOCATION_PREPARED_AUTHORITY")
        try:
            replayed = replace(self._prepared_response)
        except ValueError:
            _fail("WRITE_INVOCATION_PREPARED_DRIFT", "M43 prepared response failed integrity replay")
        if replayed.integrity_snapshot != self._response_integrity:
            _fail("WRITE_INVOCATION_PREPARED_DRIFT", "M43 prepared response integrity changed")
        return replayed

    def _validate_bindings(self) -> None:
        if type(self._handler) is not BoundedInboundHttpResponseWriteOutcomeHandler:
            _fail("WRITE_INVOCATION_BINDING_DRIFT", "M47 handler changed type")
        if getattr(self._handler, "_session", None) is not self._session:
            _fail("WRITE_INVOCATION_BINDING_DRIFT", "M47 to M46 binding changed")
        if type(self._session) is not BoundedInboundHttpResponseWriteSession:
            _fail("WRITE_INVOCATION_BINDING_DRIFT", "M46 session changed type")
        if self._binding_witness != self._binding_snapshot():
            _fail("WRITE_INVOCATION_BINDING_DRIFT", "M48 binding witness changed")
        if not callable(self._writer):
            _fail("WRITE_INVOCATION_BINDING_DRIFT", "construction-bound writer is not callable")
        self._validate_bound(self._progress, self._handler, self._progress_function, "M47 progress")
        self._validate_bound(self._accept, self._handler, self._accept_function, "M47 accept")
        self._validate_bound(self._take, self._handler, self._take_function, "M47 take")
        self._validate_bound(self._close, self._handler, self._close_function, "M47 close")
        self._validate_bound(self._closed_getter, self._handler, self._closed_function, "M47 closed")
        self._validate_bound(self._session_close, self._session, self._session_close_function, "M46 close")
        self._validate_bound(self._session_closed_getter, self._session, self._session_closed_function, "M46 closed")

    def _closed_value(self) -> bool:
        self._validate_bindings()
        try:
            value = self._closed_getter()
        except InboundHttpResponseWriteOutcomeError as exc:
            _fail_from_outcome("WRITE_INVOCATION_OUTCOME_REJECTED", "M47 rejected closed-state inspection", exc)
        if type(value) is not bool:
            _fail("WRITE_INVOCATION_BINDING_DRIFT", "M47 closed getter returned non-boolean")
        self._validate_bindings()
        if value is True:
            self._prepared_response = None
        return value

    def _current_progress(self) -> InboundHttpResponseWriteSessionProgress:
        if self._closed_value():
            _fail("WRITE_INVOCATION_SESSION_CLOSED", "M48 source session is closed")
        try:
            progress = self._progress()
        except InboundHttpResponseWriteOutcomeError as exc:
            self._validate_bindings()
            _fail_from_outcome("WRITE_INVOCATION_OUTCOME_REJECTED", "M47 rejected progress inspection", exc)
        self._validate_bindings()
        return _replay_m46_progress(progress)

    def _best_effort_close_after_writer(self) -> None:
        """Clear M46 directly after consumed writer capability, or report uncertainty."""
        witness = self._binding_witness
        if type(witness) is not tuple or len(witness) != 13 or witness[0] != _BINDING_MARKER or witness[2] is not self._session:
            _fail("WRITE_INVOCATION_CLEANUP_UNCERTAIN", "post-writer cleanup witness unavailable")
        expected_close = witness[11]
        expected_closed = witness[12]
        if (getattr(self._session_close, "__self__", None) is not self._session or
            getattr(self._session_close, "__func__", None) is not expected_close or
            getattr(self._session_closed_getter, "__self__", None) is not self._session or
            getattr(self._session_closed_getter, "__func__", None) is not expected_closed):
            _fail("WRITE_INVOCATION_CLEANUP_UNCERTAIN", "captured M46 cleanup authority changed")
        try:
            self._session_close()
            closed = self._session_closed_getter()
        except Exception:
            _fail("WRITE_INVOCATION_CLEANUP_UNCERTAIN", "post-writer cleanup could not be verified")
        if closed is not True:
            _fail("WRITE_INVOCATION_CLEANUP_UNCERTAIN", "post-writer cleanup did not verify closed state")
        self._prepared_response = None

    def _post_writer_validate(self) -> None:
        try:
            self._validate_bindings()
        except InboundHttpResponseWriteInvocationError:
            self._best_effort_close_after_writer()
            raise

    @property
    def closed(self) -> bool:
        return self._closed_value()

    def invoke_once(self) -> InboundHttpResponseWriteInvocationResult:
        """Perform zero or one writer invocations and never retry."""
        prior = self._current_progress()
        if prior.plan.action == WRITE_ACTION_COMPLETE:
            try:
                completed = self._take()
            except InboundHttpResponseWriteOutcomeError as exc:
                self._validate_bindings()
                _fail_from_outcome("WRITE_INVOCATION_OUTCOME_REJECTED", "M47 rejected completion transfer", exc)
            self._validate_bindings()
            witnessed_completed = _replay_m46_completion(completed)
            self._prepared_response = None
            if not self._closed_value():
                _fail("WRITE_INVOCATION_COMPLETION_DRIFT", "completion did not close M47/M46")
            return InboundHttpResponseWriteInvocationResult(
                state=WRITE_INVOCATION_COMPLETED, writer_invoked=False,
                offered_bytes=0, outcome_kind=None, completed=witnessed_completed,
            )
        if prior.plan.action != WRITE_ACTION_WRITE:
            _fail("WRITE_INVOCATION_PROGRESS_DRIFT", "M47 returned unknown planning state")
        budget = prior.plan.next_write_bytes
        if type(budget) is not int or budget <= 0:
            _fail("WRITE_INVOCATION_PROGRESS_DRIFT", "WRITE plan MUST carry positive exact budget")
        prepared = self._validate_prepared()
        raw = prepared.wire_exchange.response_bytes
        start = prior.bytes_written
        stop = start + budget
        if type(raw) is not bytes or stop > len(raw) or len(raw) != prior.plan.response_bytes:
            _fail("WRITE_INVOCATION_PREPARED_DRIFT", "M43 response bytes do not match M46 plan")
        offered = raw[start:stop]
        if type(offered) is not bytes or len(offered) != budget:
            _fail("WRITE_INVOCATION_PREPARED_DRIFT", "M48 failed exact bounded response slice")
        self._validate_bindings()
        try:
            outcome = self._writer(offered)
        except Exception:
            self._post_writer_validate()
            try:
                self._accept(InboundHttpResponseWriteOutcome.failure())
            except InboundHttpResponseWriteOutcomeError as exc:
                self._best_effort_close_after_writer()
                _fail_from_outcome("WRITE_INVOCATION_WRITER_FAILURE", "injected writer failed; session closed", exc)
            self._best_effort_close_after_writer()
            _fail("WRITE_INVOCATION_WRITER_FAILURE", "injected writer failed")
        self._post_writer_validate()
        if type(outcome) is not InboundHttpResponseWriteOutcome:
            self._best_effort_close_after_writer()
            _fail("INVALID_WRITER_RESULT", "writer MUST return exact M47 outcome; session closed")
        try:
            _require_negative(outcome, _M47_NEGATIVE_FIELDS, code="WRITE_INVOCATION_OUTCOME_AUTHORITY")
            witnessed_outcome = replace(outcome)
            _require_negative(witnessed_outcome, _M47_NEGATIVE_FIELDS, code="WRITE_INVOCATION_OUTCOME_AUTHORITY")
        except InboundHttpResponseWriteInvocationError:
            self._best_effort_close_after_writer()
            raise
        except ValueError:
            self._best_effort_close_after_writer()
            _fail("WRITE_INVOCATION_OUTCOME_DRIFT", "writer outcome failed integrity replay")
        try:
            returned = self._accept(witnessed_outcome)
        except InboundHttpResponseWriteOutcomeError as exc:
            self._best_effort_close_after_writer()
            _fail_from_outcome("WRITE_INVOCATION_OUTCOME_REJECTED", "M47 rejected already-returned writer outcome", exc)
        self._post_writer_validate()
        try:
            progress = _replay_m46_progress(returned)
        except InboundHttpResponseWriteInvocationError:
            self._best_effort_close_after_writer()
            raise
        if witnessed_outcome.kind != WRITE_OUTCOME_PROGRESS:
            self._best_effort_close_after_writer()
            _fail("WRITE_INVOCATION_OUTCOME_DRIFT", "non-PROGRESS outcome unexpectedly returned progress")
        accepted = witnessed_outcome.accepted_write_bytes
        if accepted > budget or progress.write_calls_completed != prior.write_calls_completed + 1:
            self._best_effort_close_after_writer()
            _fail("WRITE_INVOCATION_PROGRESS_DRIFT", "writer progress exceeded offer or call accounting drifted")
        if progress.bytes_written != prior.bytes_written + accepted or progress.last_accepted_write_bytes != accepted:
            self._best_effort_close_after_writer()
            _fail("WRITE_INVOCATION_PROGRESS_DRIFT", "M46 accounting does not match writer outcome")
        return InboundHttpResponseWriteInvocationResult(
            state=WRITE_INVOCATION_PROGRESS, writer_invoked=True,
            offered_bytes=budget, outcome_kind=WRITE_OUTCOME_PROGRESS, progress=progress,
        )

    def close(self) -> None:
        """Idempotently release M46 retained response state."""
        try:
            if self._closed_value():
                return
            self._close()
            self._prepared_response = None
            if not self._closed_value():
                _fail("WRITE_INVOCATION_CLOSE_FAILED", "M47/M46 did not close")
        except InboundHttpResponseWriteInvocationError:
            self._best_effort_close_after_writer()
            raise
