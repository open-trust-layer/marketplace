"""One-shot bounded inbound HTTP request/response transaction composition.

M50 composes the already-reviewed M43 preparation boundary with M44-M49 local
write accounting. It owns no socket, TLS stack, listener, deployment, or concrete
transport. Injected reader/writer capabilities remain governed by their lower
boundaries; M50 never treats local accounting as transmission evidence.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from hashlib import sha256
from math import isfinite
from typing import Any, Callable, Final

from .inbound_http_read_session import BoundedInboundHttpReadSession
from .inbound_http_response_prepare import (
    BoundedInboundHttpResponsePreparer,
    InboundHttpResponsePreparationError,
    PreparedInboundHttpReadResponse,
)
from .inbound_http_response_write_driver import (
    BoundedInboundHttpResponseWriteDriver,
    CompletedInboundHttpResponseWriteDriverResult,
    InboundHttpResponseWriteDriverError,
    InboundHttpResponseWriteDriverLimits,
)
from .inbound_http_response_write_invoke import BoundedInboundHttpResponseWriteInvoker
from .inbound_http_response_write_outcome import (
    BoundedInboundHttpResponseWriteOutcomeHandler,
    InboundHttpResponseWriteOutcome,
)
from .inbound_http_response_write_plan import (
    BoundedInboundHttpResponseWritePlanner,
    InboundHttpResponseWriteLimits,
)
from .inbound_http_response_write_session import (
    BoundedInboundHttpResponseWriteSession,
)
from .inbound_http_response_write_transition import (
    BoundedInboundHttpResponseWriteTransitioner,
)

_BINDING_MARKER: Final = "inbound-http-transaction-binding-v1"
_RESULT_MARKER: Final = "completed-inbound-http-transaction-v1"
_MAX_DIGEST_DEPTH: Final = 32
_MAX_DIGEST_ITEMS: Final = 8_192
_AUTHORITY_NEGATIVE_FIELDS: Final = (
    "socket_access_proven",
    "network_origin_proven",
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
    "BoundedInboundHttpRequestResponseTransaction",
    "CompletedInboundHttpRequestResponseTransaction",
    "InboundHttpRequestResponseTransactionError",
]


def _current_write_class_witness() -> tuple[Any, ...]:
    return (
        BoundedInboundHttpResponseWritePlanner.__init__,
        BoundedInboundHttpResponseWritePlanner.plan,
        BoundedInboundHttpResponseWriteTransitioner.__init__,
        BoundedInboundHttpResponseWriteTransitioner.transition,
        BoundedInboundHttpResponseWriteSession.__init__,
        BoundedInboundHttpResponseWriteSession.progress,
        BoundedInboundHttpResponseWriteSession.accept_write_count,
        BoundedInboundHttpResponseWriteSession.take_completed,
        BoundedInboundHttpResponseWriteSession.close,
        BoundedInboundHttpResponseWriteOutcomeHandler.__init__,
        BoundedInboundHttpResponseWriteOutcomeHandler.progress,
        BoundedInboundHttpResponseWriteOutcomeHandler.accept_outcome,
        BoundedInboundHttpResponseWriteOutcomeHandler.take_completed,
        BoundedInboundHttpResponseWriteOutcomeHandler.close,
        BoundedInboundHttpResponseWriteInvoker.__init__,
        BoundedInboundHttpResponseWriteInvoker.invoke_once,
        BoundedInboundHttpResponseWriteInvoker.close,
        BoundedInboundHttpResponseWriteDriver.__init__,
        BoundedInboundHttpResponseWriteDriver.run_to_completion,
        BoundedInboundHttpResponseWriteDriver.close,
    )


class InboundHttpRequestResponseTransactionError(RuntimeError):
    """Fail-closed M50 error preserving read-side and write-side reason metadata."""

    def __init__(
        self,
        code: str,
        message: str,
        *,
        preparation_code: str | None = None,
        read_driver_code: str | None = None,
        read_invocation_code: str | None = None,
        read_outcome_code: str | None = None,
        read_session_code: str | None = None,
        read_transition_code: str | None = None,
        read_plan_code: str | None = None,
        stream_code: str | None = None,
        wire_code: str | None = None,
        write_driver_code: str | None = None,
        write_invocation_code: str | None = None,
        write_outcome_code: str | None = None,
        write_session_code: str | None = None,
        write_transition_code: str | None = None,
        write_plan_code: str | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.preparation_code = preparation_code
        self.read_driver_code = read_driver_code
        self.read_invocation_code = read_invocation_code
        self.read_outcome_code = read_outcome_code
        self.read_session_code = read_session_code
        self.read_transition_code = read_transition_code
        self.read_plan_code = read_plan_code
        self.stream_code = stream_code
        self.wire_code = wire_code
        self.write_driver_code = write_driver_code
        self.write_invocation_code = write_invocation_code
        self.write_outcome_code = write_outcome_code
        self.write_session_code = write_session_code
        self.write_transition_code = write_transition_code
        self.write_plan_code = write_plan_code


def _fail(code: str, message: str, **metadata: str | None) -> None:
    raise InboundHttpRequestResponseTransactionError(code, message, **metadata)


def _fail_from_preparation(exc: InboundHttpResponsePreparationError) -> None:
    _fail(
        "TRANSACTION_PREPARATION_REJECTED",
        "M43 rejected request/response preparation",
        preparation_code=exc.code,
        read_driver_code=exc.driver_code,
        read_invocation_code=exc.invocation_code,
        read_outcome_code=exc.outcome_code,
        read_session_code=exc.session_code,
        read_transition_code=exc.transition_code,
        read_plan_code=exc.plan_code,
        stream_code=exc.stream_code,
        wire_code=exc.wire_code,
    )


def _fail_from_write(exc: InboundHttpResponseWriteDriverError) -> None:
    _fail(
        "TRANSACTION_WRITE_REJECTED",
        "M49 rejected response write accounting",
        write_driver_code=exc.code,
        write_invocation_code=exc.invocation_code,
        write_outcome_code=exc.outcome_code,
        write_session_code=exc.session_code,
        write_transition_code=exc.transition_code,
        write_plan_code=exc.write_plan_code,
    )


def _require_negative(value: object, names: tuple[str, ...], *, code: str) -> None:
    for name in names:
        if getattr(value, name, None) is not False:
            _fail(code, "M50 observed promoted authority on an original object")


def _digest_integrity_snapshot(value: tuple[Any, ...]) -> str:
    """Hash an integrity witness without retaining a second raw-byte representation."""
    if type(value) is not tuple:
        _fail("TRANSACTION_INTEGRITY_DRIFT", "integrity witness MUST be exact tuple")
    digest = sha256()
    item_count = 0

    def visit(item: Any, depth: int) -> None:
        nonlocal item_count
        item_count += 1
        if depth > _MAX_DIGEST_DEPTH or item_count > _MAX_DIGEST_ITEMS:
            _fail("TRANSACTION_INTEGRITY_DRIFT", "integrity witness exceeds M50 digest bounds")
        t = type(item)
        if t is tuple:
            digest.update(b"T")
            digest.update(len(item).to_bytes(4, "big"))
            for child in item:
                visit(child, depth + 1)
            return
        if t is bytes:
            digest.update(b"B")
            digest.update(len(item).to_bytes(8, "big"))
            digest.update(item)
            return
        if t is str:
            encoded = item.encode("utf-8")
            digest.update(b"S")
            digest.update(len(encoded).to_bytes(4, "big"))
            digest.update(encoded)
            return
        if t is int:
            encoded = str(item).encode("ascii")
            digest.update(b"I")
            digest.update(len(encoded).to_bytes(2, "big"))
            digest.update(encoded)
            return
        if t is float:
            encoded = item.hex().encode("ascii")
            digest.update(b"F")
            digest.update(len(encoded).to_bytes(2, "big"))
            digest.update(encoded)
            return
        if t is bool:
            digest.update(b"1" if item else b"0")
            return
        if item is None:
            digest.update(b"N")
            return
        _fail("TRANSACTION_INTEGRITY_DRIFT", "integrity witness contains unsupported type")

    visit(value, 0)
    return digest.hexdigest()


@dataclass(frozen=True)
class CompletedInboundHttpRequestResponseTransaction:
    """Detached M50 accounting result containing no raw request or response bytes."""

    host_authority: str
    route_kind: str
    route_operation: str
    status_code: int
    olp_message_type: str
    request_bytes: int
    response_bytes: int
    response_body_bytes: int
    read_driver_steps: int
    reader_invocations: int
    reads_completed: int
    write_driver_steps: int
    writer_invocations: int
    write_calls_completed: int
    bytes_written: int
    write_elapsed_seconds: float
    preparation_integrity_sha256: str
    write_completion_integrity_sha256: str
    integrity_snapshot: tuple[Any, ...] | None = field(default=None, repr=False)
    transaction_completed: bool = field(default=True, init=False)
    response_prepared: bool = field(default=True, init=False)
    local_write_accounting_complete: bool = field(default=True, init=False)
    socket_access_proven: bool = field(default=False, init=False)
    network_origin_proven: bool = field(default=False, init=False)
    tls_terminated: bool = field(default=False, init=False)
    transmitted: bool = field(default=False, init=False)
    request_authenticated: bool = field(default=False, init=False)
    peer_identity_proven: bool = field(default=False, init=False)
    establishes_marketplace_truth: bool = field(default=False, init=False)
    establishes_trust: bool = field(default=False, init=False)
    establishes_authorization: bool = field(default=False, init=False)
    authorizes_protected_side_effects: bool = field(default=False, init=False)

    def __post_init__(self) -> None:
        for name in ("host_authority", "route_kind", "route_operation", "olp_message_type"):
            value = getattr(self, name)
            if type(value) is not str or not value:
                raise ValueError(f"{name} MUST be non-empty exact text")
        if type(self.status_code) is not int or self.status_code != 200:
            raise ValueError("status_code MUST be exact success status 200")
        for name in (
            "request_bytes", "response_bytes", "response_body_bytes", "read_driver_steps",
            "reads_completed", "write_driver_steps", "write_calls_completed", "bytes_written",
        ):
            value = getattr(self, name)
            if type(value) is not int or value <= 0:
                raise ValueError(f"{name} MUST be a positive exact integer")
        for name in ("reader_invocations", "writer_invocations"):
            value = getattr(self, name)
            if type(value) is not int or value < 0:
                raise ValueError(f"{name} MUST be a non-negative exact integer")
        if self.reader_invocations > self.read_driver_steps or self.reader_invocations > self.reads_completed:
            raise ValueError("M50 read accounting is inconsistent")
        if self.writer_invocations != self.write_calls_completed:
            raise ValueError("fresh M50 write session requires exact invocation/call equality")
        if self.writer_invocations > self.write_driver_steps:
            raise ValueError("M50 writer invocations exceed driver steps")
        if self.bytes_written != self.response_bytes:
            raise ValueError("M50 local write accounting MUST cover exact prepared response length")
        if self.response_body_bytes > self.response_bytes:
            raise ValueError("response body length exceeds wire response length")
        if type(self.write_elapsed_seconds) is not float or not isfinite(self.write_elapsed_seconds):
            raise ValueError("write_elapsed_seconds MUST be one finite float")
        if self.write_elapsed_seconds < 0.0:
            raise ValueError("write_elapsed_seconds MUST NOT be negative")
        for name in ("preparation_integrity_sha256", "write_completion_integrity_sha256"):
            value = getattr(self, name)
            if type(value) is not str or len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
                raise ValueError(f"{name} MUST be lowercase SHA-256 hex")
        if self.transaction_completed is not True or self.response_prepared is not True:
            raise ValueError("M50 completion state is invalid")
        if self.local_write_accounting_complete is not True:
            raise ValueError("M50 local write accounting MUST be complete")
        for name in _AUTHORITY_NEGATIVE_FIELDS:
            if getattr(self, name, None) is not False:
                raise ValueError("M50 result promoted a forbidden authority fact")
        current = (
            _RESULT_MARKER, self.host_authority, self.route_kind, self.route_operation,
            self.status_code, self.olp_message_type, self.request_bytes, self.response_bytes,
            self.response_body_bytes, self.read_driver_steps, self.reader_invocations,
            self.reads_completed, self.write_driver_steps, self.writer_invocations,
            self.write_calls_completed, self.bytes_written, self.write_elapsed_seconds,
            self.preparation_integrity_sha256, self.write_completion_integrity_sha256,
            self.transaction_completed, self.response_prepared, self.local_write_accounting_complete,
            *(getattr(self, name) for name in _AUTHORITY_NEGATIVE_FIELDS),
        )
        if self.integrity_snapshot is not None and self.integrity_snapshot != current:
            raise ValueError("M50 transaction-result integrity snapshot mismatch")
        if self.integrity_snapshot is None:
            object.__setattr__(self, "integrity_snapshot", current)


class BoundedInboundHttpRequestResponseTransaction:
    """Compose exactly one M43 preparation with one bounded M49 write drive."""

    __slots__ = (
        "_preparer", "_read_session", "_writer", "_clock", "_write_limits",
        "_write_driver_limits", "_prepare_function", "_preparer_close_function",
        "_used_function", "_write_class_witness", "_write_run_function",
        "_session_close_function", "_prepare", "_preparer_close", "_used_getter",
        "_binding_witness", "_used",
    )

    def __init__(
        self,
        *,
        response_preparer: BoundedInboundHttpResponsePreparer,
        writer: Callable[[bytes], InboundHttpResponseWriteOutcome],
        clock: Callable[[], float],
        write_limits: InboundHttpResponseWriteLimits | None = None,
        write_driver_limits: InboundHttpResponseWriteDriverLimits | None = None,
    ) -> None:
        if type(response_preparer) is not BoundedInboundHttpResponsePreparer:
            raise TypeError("response_preparer MUST be exact M43 preparer")
        if not callable(writer) or not callable(clock):
            raise TypeError("writer and clock MUST be callable")
        read_session = getattr(response_preparer, "_session", None)
        if type(read_session) is not BoundedInboundHttpReadSession:
            raise ValueError("M43 MUST retain one exact M39 read session")
        if write_limits is None:
            detached_write_limits = InboundHttpResponseWriteLimits()
        else:
            if type(write_limits) is not InboundHttpResponseWriteLimits:
                raise TypeError("write_limits MUST be exact InboundHttpResponseWriteLimits")
            detached_write_limits = InboundHttpResponseWriteLimits(
                max_write_calls=write_limits.max_write_calls,
                max_write_bytes=write_limits.max_write_bytes,
            )
        detached_driver_limits = None
        if write_driver_limits is not None:
            if type(write_driver_limits) is not InboundHttpResponseWriteDriverLimits:
                raise TypeError("write_driver_limits MUST be exact M49 limits")
            detached_driver_limits = InboundHttpResponseWriteDriverLimits(
                max_steps=write_driver_limits.max_steps,
                max_elapsed_seconds=write_driver_limits.max_elapsed_seconds,
            )
            if detached_driver_limits.max_steps > detached_write_limits.max_write_calls + 1:
                raise ValueError("M50 write-driver steps exceed M44 call ceiling plus completion transfer")
        used_function = BoundedInboundHttpResponsePreparer.used.fget
        if used_function is None:
            raise ValueError("M43 used property MUST retain exact getter")
        self._preparer = response_preparer
        self._read_session = read_session
        self._writer = writer
        self._clock = clock
        self._write_limits = detached_write_limits
        self._write_driver_limits = detached_driver_limits
        self._prepare_function = BoundedInboundHttpResponsePreparer.prepare
        self._preparer_close_function = BoundedInboundHttpResponsePreparer.close
        self._used_function = used_function
        self._write_class_witness = _current_write_class_witness()
        self._write_run_function = BoundedInboundHttpResponseWriteDriver.run_to_completion
        self._session_close_function = BoundedInboundHttpResponseWriteSession.close
        self._prepare = self._prepare_function.__get__(response_preparer, BoundedInboundHttpResponsePreparer)
        self._preparer_close = self._preparer_close_function.__get__(response_preparer, BoundedInboundHttpResponsePreparer)
        self._used_getter = self._used_function.__get__(response_preparer, BoundedInboundHttpResponsePreparer)
        self._used = False
        self._binding_witness = self._binding_snapshot()
        self._validate_bindings()

    def _binding_snapshot(self) -> tuple[Any, ...]:
        driver_limits = None if self._write_driver_limits is None else (
            self._write_driver_limits.max_steps, self._write_driver_limits.max_elapsed_seconds
        )
        return (
            _BINDING_MARKER, self._preparer, self._read_session, self._writer, self._clock,
            self._write_limits.max_write_calls, self._write_limits.max_write_bytes, driver_limits,
            self._prepare_function, self._preparer_close_function, self._used_function,
            self._write_class_witness, self._write_run_function, self._session_close_function,
        )

    def _validate_bound(self, bound: Any, function: Any, label: str) -> None:
        if getattr(bound, "__self__", None) is not self._preparer or getattr(bound, "__func__", None) is not function:
            _fail("TRANSACTION_BINDING_DRIFT", f"captured M43 {label} binding changed")

    def _validate_bindings(self) -> None:
        if type(self._preparer) is not BoundedInboundHttpResponsePreparer:
            _fail("TRANSACTION_BINDING_DRIFT", "M43 preparer changed type")
        if getattr(self._preparer, "_session", None) is not self._read_session:
            _fail("TRANSACTION_BINDING_DRIFT", "M43 retained read session changed")
        if type(self._read_session) is not BoundedInboundHttpReadSession:
            _fail("TRANSACTION_BINDING_DRIFT", "M39 read session changed type")
        if not callable(self._writer) or not callable(self._clock):
            _fail("TRANSACTION_BINDING_DRIFT", "writer or clock binding is no longer callable")
        if _current_write_class_witness() != self._write_class_witness:
            _fail("TRANSACTION_BINDING_DRIFT", "M44-M49 public class-method graph changed")
        if self._binding_witness != self._binding_snapshot():
            _fail("TRANSACTION_BINDING_DRIFT", "M50 construction witness changed")
        self._validate_bound(self._prepare, self._prepare_function, "prepare")
        self._validate_bound(self._preparer_close, self._preparer_close_function, "close")
        self._validate_bound(self._used_getter, self._used_function, "used")

    def _cleanup_preparer(self) -> None:
        witness = self._binding_witness
        if (
            type(witness) is not tuple or len(witness) != 14 or witness[0] != _BINDING_MARKER
            or witness[1] is not self._preparer or witness[2] is not self._read_session
        ):
            _fail("TRANSACTION_CLEANUP_UNCERTAIN", "M50 cleanup witness is unavailable")
        expected_close = witness[9]
        expected_used = witness[10]
        if (
            self._preparer_close_function is not expected_close
            or self._used_function is not expected_used
            or getattr(self._preparer_close, "__self__", None) is not self._preparer
            or getattr(self._preparer_close, "__func__", None) is not expected_close
            or getattr(self._used_getter, "__self__", None) is not self._preparer
            or getattr(self._used_getter, "__func__", None) is not expected_used
        ):
            _fail("TRANSACTION_CLEANUP_UNCERTAIN", "captured M43 cleanup authority changed")
        try:
            self._preparer_close()
            used = self._used_getter()
        except Exception:
            _fail("TRANSACTION_CLEANUP_UNCERTAIN", "M50 could not verify M43 cleanup")
        if used is not True or getattr(self._read_session, "_closed", None) is not True:
            _fail("TRANSACTION_CLEANUP_UNCERTAIN", "M43 cleanup did not verify closed read state")
        if getattr(self._read_session, "_prefix", None) != b"":
            _fail("TRANSACTION_CLEANUP_UNCERTAIN", "M43 cleanup did not verify cleared request bytes")

    def _cleanup_write_session(self, session: BoundedInboundHttpResponseWriteSession) -> None:
        witness = self._binding_witness
        if type(witness) is not tuple or len(witness) != 14 or witness[0] != _BINDING_MARKER:
            _fail("TRANSACTION_CLEANUP_UNCERTAIN", "M50 cleanup witness is unavailable")
        expected_close = witness[13]
        if self._session_close_function is not expected_close:
            _fail("TRANSACTION_CLEANUP_UNCERTAIN", "captured M46 cleanup authority changed")
        close = expected_close.__get__(session, BoundedInboundHttpResponseWriteSession)
        if getattr(close, "__self__", None) is not session or getattr(close, "__func__", None) is not expected_close:
            _fail("TRANSACTION_CLEANUP_UNCERTAIN", "captured M46 cleanup authority changed")
        try:
            close()
        except Exception:
            _fail("TRANSACTION_CLEANUP_UNCERTAIN", "M50 could not close M46 response state")
        if getattr(session, "_closed", None) is not True or getattr(session, "_prepared_response", None) is not None:
            _fail("TRANSACTION_CLEANUP_UNCERTAIN", "M46 cleanup did not release prepared response")

    @property
    def used(self) -> bool:
        return self._used

    def _replay_prepared(self, value: PreparedInboundHttpReadResponse) -> PreparedInboundHttpReadResponse:
        if type(value) is not PreparedInboundHttpReadResponse:
            _fail("TRANSACTION_PREPARATION_DRIFT", "M43 returned unexpected prepared-response type")
        _require_negative(
            value,
            ("transmitted", "socket_access_proven", "network_origin_proven", "request_authenticated",
             "peer_identity_proven", "establishes_marketplace_truth", "establishes_trust",
             "establishes_authorization", "authorizes_protected_side_effects"),
            code="TRANSACTION_PREPARATION_AUTHORITY",
        )
        try:
            witnessed = replace(value)
        except ValueError:
            _fail("TRANSACTION_PREPARATION_DRIFT", "M43 result failed integrity replay")
        return witnessed

    def _replay_write_result(
        self, value: CompletedInboundHttpResponseWriteDriverResult
    ) -> CompletedInboundHttpResponseWriteDriverResult:
        if type(value) is not CompletedInboundHttpResponseWriteDriverResult:
            _fail("TRANSACTION_WRITE_DRIFT", "M49 returned unexpected completion type")
        _require_negative(
            value,
            ("socket_access_proven", "tls_terminated", "transmitted", "request_authenticated",
             "peer_identity_proven", "establishes_marketplace_truth", "establishes_trust",
             "establishes_authorization", "authorizes_protected_side_effects"),
            code="TRANSACTION_WRITE_AUTHORITY",
        )
        try:
            witnessed = replace(value)
        except ValueError:
            _fail("TRANSACTION_WRITE_DRIFT", "M49 result failed integrity replay")
        return witnessed

    def run(self) -> CompletedInboundHttpRequestResponseTransaction:
        """Perform one bounded composition; M49 owns the only orchestration loop."""
        if self._used:
            _fail("TRANSACTION_USED", "M50 transaction is one-shot")
        try:
            self._validate_bindings()
        except InboundHttpRequestResponseTransactionError:
            self._used = True
            self._cleanup_preparer()
            raise
        self._used = True

        try:
            prepared_raw = self._prepare()
        except InboundHttpResponsePreparationError as exc:
            self._cleanup_preparer()
            _fail_from_preparation(exc)
        except Exception:
            self._cleanup_preparer()
            _fail("TRANSACTION_PREPARATION_FAILED", "M43 preparation failed unexpectedly")
        try:
            self._validate_bindings()
            prepared = self._replay_prepared(prepared_raw)
        except InboundHttpRequestResponseTransactionError:
            self._cleanup_preparer()
            raise

        wire = prepared.wire_exchange
        preparation_digest = _digest_integrity_snapshot(prepared.integrity_snapshot)
        session = None
        driver = None
        try:
            planner = BoundedInboundHttpResponseWritePlanner(limits=self._write_limits)
            transitioner = BoundedInboundHttpResponseWriteTransitioner(write_planner=planner)
            session = BoundedInboundHttpResponseWriteSession(
                write_transitioner=transitioner, prepared_response=prepared_raw
            )
            handler = BoundedInboundHttpResponseWriteOutcomeHandler(write_session=session)
            invoker = BoundedInboundHttpResponseWriteInvoker(
                write_outcome_handler=handler, writer=self._writer
            )
            driver = BoundedInboundHttpResponseWriteDriver(
                write_invoker=invoker, clock=self._clock, limits=self._write_driver_limits
            )
            write_raw = self._write_run_function(driver)
        except InboundHttpResponseWriteDriverError as exc:
            if session is not None:
                self._cleanup_write_session(session)
            self._cleanup_preparer()
            _fail_from_write(exc)
        except InboundHttpRequestResponseTransactionError:
            if session is not None:
                self._cleanup_write_session(session)
            self._cleanup_preparer()
            raise
        except Exception:
            if session is not None:
                self._cleanup_write_session(session)
            self._cleanup_preparer()
            _fail("TRANSACTION_WRITE_FAILED", "response write composition failed unexpectedly")

        try:
            self._validate_bindings()
            write_result = self._replay_write_result(write_raw)
            if write_result.completed.response_bytes != prepared.response_bytes:
                _fail("TRANSACTION_WRITE_DRIFT", "M49 response length differs from M43 preparation")
            if write_result.completed.bytes_written != prepared.response_bytes:
                _fail("TRANSACTION_WRITE_DRIFT", "M49 local byte accounting is incomplete")
            if write_result.completed.prepared_response_integrity != prepared.integrity_snapshot:
                _fail("TRANSACTION_WRITE_DRIFT", "M49 completion is not bound to exact M43 response")
            if write_result.writer_invocations != write_result.write_calls_completed:
                _fail("TRANSACTION_WRITE_DRIFT", "fresh M50 write-call accounting drifted")
            if session is None or getattr(session, "_closed", None) is not True:
                _fail("TRANSACTION_WRITE_DRIFT", "M46 source did not close after M49 completion")
            if getattr(session, "_prepared_response", None) is not None:
                _fail("TRANSACTION_WRITE_DRIFT", "M46 retained prepared response after completion")
            write_digest = _digest_integrity_snapshot(write_result.integrity_snapshot)
            self._cleanup_preparer()
            return CompletedInboundHttpRequestResponseTransaction(
                host_authority=wire.host_authority,
                route_kind=wire.route_kind,
                route_operation=wire.route_operation,
                status_code=wire.status_code,
                olp_message_type=wire.olp_message_type,
                request_bytes=prepared.request_bytes,
                response_bytes=prepared.response_bytes,
                response_body_bytes=wire.response_body_bytes,
                read_driver_steps=prepared.driver_steps,
                reader_invocations=prepared.reader_invocations,
                reads_completed=prepared.reads_completed,
                write_driver_steps=write_result.driver_steps,
                writer_invocations=write_result.writer_invocations,
                write_calls_completed=write_result.write_calls_completed,
                bytes_written=write_result.completed.bytes_written,
                write_elapsed_seconds=write_result.elapsed_seconds,
                preparation_integrity_sha256=preparation_digest,
                write_completion_integrity_sha256=write_digest,
            )
        except InboundHttpRequestResponseTransactionError:
            if session is not None:
                self._cleanup_write_session(session)
            self._cleanup_preparer()
            raise
        except Exception:
            if session is not None:
                self._cleanup_write_session(session)
            self._cleanup_preparer()
            _fail("TRANSACTION_RESULT_DRIFT", "M50 could not construct detached completion result")

    def close(self) -> None:
        """Idempotently make an unused transaction terminal and clear read-side state."""
        self._used = True
        self._cleanup_preparer()
