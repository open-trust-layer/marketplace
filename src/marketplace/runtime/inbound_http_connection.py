"""Bounded adapter for one already-established inbound HTTP byte-stream connection.

M51 does not create, bind, listen, accept, connect, resolve, or negotiate TLS.
It adapts one caller-supplied connection into the already-reviewed M41/M48
reader/writer contracts and composes exactly one M50 transaction.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any, Callable, Final, Protocol

from .inbound_http_read_driver import BoundedInboundHttpReadDriver
from .inbound_http_read_invoke import BoundedInboundHttpReadInvoker
from .inbound_http_read_outcome import InboundHttpReadOutcome
from .inbound_http_response_prepare import BoundedInboundHttpResponsePreparer
from .inbound_http_response_write_driver import InboundHttpResponseWriteDriverLimits
from .inbound_http_response_write_outcome import InboundHttpResponseWriteOutcome
from .inbound_http_response_write_plan import InboundHttpResponseWriteLimits
from .inbound_http_transaction import (
    BoundedInboundHttpRequestResponseTransaction,
    CompletedInboundHttpRequestResponseTransaction,
    InboundHttpRequestResponseTransactionError,
)

_RESULT_MARKER: Final = "completed-inbound-http-single-connection-transport-v1"
_M50_ERROR_FIELDS: Final = (
    "preparation_code",
    "read_driver_code",
    "read_invocation_code",
    "read_outcome_code",
    "read_session_code",
    "read_transition_code",
    "read_plan_code",
    "stream_code",
    "wire_code",
    "write_driver_code",
    "write_invocation_code",
    "write_outcome_code",
    "write_session_code",
    "write_transition_code",
    "write_plan_code",
)
_AUTHORITY_NEGATIVE_FIELDS: Final = (
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
    "BoundedInboundHttpSingleConnectionIO",
    "BoundedInboundHttpSingleConnectionTransport",
    "CompletedInboundHttpSingleConnectionTransport",
    "InboundHttpSingleConnection",
    "InboundHttpSingleConnectionTransportError",
]


class InboundHttpSingleConnection(Protocol):
    """Already-established byte-stream capability supplied by a caller."""

    def recv(self, max_bytes: int) -> bytes: ...
    def send(self, data: bytes) -> int: ...
    def close(self) -> None: ...


class InboundHttpSingleConnectionTransportError(RuntimeError):
    """Stable M51 failure without reflecting arbitrary connection exception text."""

    def __init__(
        self,
        code: str,
        message: str,
        *,
        transaction_code: str | None = None,
        **metadata: str | None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.transaction_code = transaction_code
        for name in _M50_ERROR_FIELDS:
            setattr(self, name, metadata.get(name))


def _fail(
    code: str,
    message: str,
    *,
    transaction_code: str | None = None,
    **metadata: str | None,
) -> None:
    raise InboundHttpSingleConnectionTransportError(
        code,
        message,
        transaction_code=transaction_code,
        **metadata,
    )


def _same_callable(current: object, captured: object) -> bool:
    current_self = getattr(current, "__self__", None)
    captured_self = getattr(captured, "__self__", None)
    current_func = getattr(current, "__func__", None)
    captured_func = getattr(captured, "__func__", None)
    if current_func is not None or captured_func is not None:
        return current_self is captured_self and current_func is captured_func
    return current is captured


class BoundedInboundHttpSingleConnectionIO:
    """Translate one captured connection into exact M41/M48 outcome callables."""

    __slots__ = (
        "_connection",
        "_recv",
        "_send",
        "_connection_close",
        "_validate_function",
        "_ensure_open_function",
        "_read_function",
        "_write_function",
        "_close_function",
        "_reader",
        "_writer",
        "_closer",
        "_read_calls",
        "_write_calls",
        "_read_bytes",
        "_write_bytes",
        "_close_attempted",
        "_closed",
    )

    def __init__(self, *, connection: InboundHttpSingleConnection) -> None:
        recv = getattr(connection, "recv", None)
        send = getattr(connection, "send", None)
        close = getattr(connection, "close", None)
        if not callable(recv) or not callable(send) or not callable(close):
            raise TypeError("connection MUST expose callable recv, send, and close")

        self._connection = connection
        self._recv = recv
        self._send = send
        self._connection_close = close
        self._validate_function = BoundedInboundHttpSingleConnectionIO._validate_bindings
        self._ensure_open_function = BoundedInboundHttpSingleConnectionIO._ensure_open
        self._read_function = BoundedInboundHttpSingleConnectionIO._read_once
        self._write_function = BoundedInboundHttpSingleConnectionIO._write_once
        self._close_function = BoundedInboundHttpSingleConnectionIO._close_once
        self._reader = self._read_function.__get__(
            self, BoundedInboundHttpSingleConnectionIO
        )
        self._writer = self._write_function.__get__(
            self, BoundedInboundHttpSingleConnectionIO
        )
        self._closer = self._close_function.__get__(
            self, BoundedInboundHttpSingleConnectionIO
        )
        self._read_calls = 0
        self._write_calls = 0
        self._read_bytes = 0
        self._write_bytes = 0
        self._close_attempted = False
        self._closed = False
        self._validate_function(self)

    @property
    def reader(self) -> Callable[[int], InboundHttpReadOutcome]:
        return self._reader

    @property
    def writer(self) -> Callable[[bytes], InboundHttpResponseWriteOutcome]:
        return self._writer

    @property
    def closed(self) -> bool:
        return self._closed

    def _validate_bindings(self) -> None:
        if type(self) is not BoundedInboundHttpSingleConnectionIO:
            _fail("CONNECTION_IO_BINDING_DRIFT", "M51 connection I/O adapter changed type")
        if (
            BoundedInboundHttpSingleConnectionIO._validate_bindings is not self._validate_function
            or BoundedInboundHttpSingleConnectionIO._ensure_open is not self._ensure_open_function
            or BoundedInboundHttpSingleConnectionIO._read_once is not self._read_function
            or BoundedInboundHttpSingleConnectionIO._write_once is not self._write_function
            or BoundedInboundHttpSingleConnectionIO._close_once is not self._close_function
        ):
            _fail("CONNECTION_IO_BINDING_DRIFT", "M51 adapter method graph changed")
        for name, captured in (
            ("recv", self._recv),
            ("send", self._send),
            ("close", self._connection_close),
        ):
            current = getattr(self._connection, name, None)
            if not callable(current) or not _same_callable(current, captured):
                _fail(
                    "CONNECTION_METHOD_BINDING_DRIFT",
                    f"captured connection {name} binding changed",
                )

    def _ensure_open(self) -> None:
        self._validate_function(self)
        if self._close_attempted or self._closed:
            _fail("CONNECTION_CLOSED", "M51 connection I/O adapter is closed")

    def _read_once(self, max_bytes: int) -> InboundHttpReadOutcome:
        ensure_open = self._ensure_open_function
        validate = self._validate_function
        ensure_open(self)
        if type(max_bytes) is not int or max_bytes <= 0:
            _fail(
                "CONNECTION_READ_BUDGET_INVALID",
                "read budget MUST be a positive exact integer",
            )
        self._read_calls += 1
        try:
            chunk = self._recv(max_bytes)
        except Exception:
            validate(self)
            raise
        validate(self)
        if type(chunk) is not bytes:
            _fail("CONNECTION_READ_RESULT_INVALID", "connection recv MUST return exact bytes")
        if len(chunk) > max_bytes:
            _fail(
                "CONNECTION_READ_BUDGET_EXCEEDED",
                "connection recv exceeded the supplied budget",
            )
        if not chunk:
            return InboundHttpReadOutcome.eof()
        self._read_bytes += len(chunk)
        return InboundHttpReadOutcome.data(chunk)

    def _write_once(self, data: bytes) -> InboundHttpResponseWriteOutcome:
        ensure_open = self._ensure_open_function
        validate = self._validate_function
        ensure_open(self)
        if type(data) is not bytes or not data:
            _fail(
                "CONNECTION_WRITE_INPUT_INVALID",
                "write input MUST be non-empty exact bytes",
            )
        self._write_calls += 1
        try:
            accepted = self._send(data)
        except Exception:
            validate(self)
            raise
        validate(self)
        if type(accepted) is not int:
            _fail(
                "CONNECTION_WRITE_RESULT_INVALID",
                "connection send MUST return an exact integer",
            )
        if accepted < 0 or accepted > len(data):
            _fail(
                "CONNECTION_WRITE_COUNT_INVALID",
                "connection send returned an impossible byte count",
            )
        if accepted == 0:
            return InboundHttpResponseWriteOutcome.zero()
        self._write_bytes += accepted
        return InboundHttpResponseWriteOutcome.progress(accepted)

    def _close_once(self) -> None:
        if self._close_attempted:
            if self._closed:
                return
            _fail(
                "CONNECTION_CLEANUP_UNCERTAIN",
                "connection close was previously attempted but not verified",
            )
        self._close_attempted = True
        close_error = False
        try:
            self._connection_close()
        except Exception:
            close_error = True
        finally:
            self._connection = None
            self._recv = None
            self._send = None
            self._connection_close = None
        if close_error:
            _fail("CONNECTION_CLEANUP_UNCERTAIN", "captured connection close failed")
        self._closed = True

    def close(self) -> None:
        self._closer()


@dataclass(frozen=True)
class CompletedInboundHttpSingleConnectionTransport:
    """Detached M51 result; contains accounting only, never request/response bytes."""

    host_authority: str
    route_kind: str
    route_operation: str
    status_code: int
    olp_message_type: str
    request_bytes: int
    response_bytes: int
    response_body_bytes: int
    read_calls: int
    read_bytes: int
    write_calls: int
    write_bytes: int
    read_driver_steps: int
    write_driver_steps: int
    preparation_integrity_sha256: str
    write_completion_integrity_sha256: str
    integrity_snapshot: tuple[Any, ...] | None = field(default=None, repr=False)
    transaction_completed: bool = field(default=True, init=False)
    connection_closed: bool = field(default=True, init=False)
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
            "request_bytes",
            "response_bytes",
            "response_body_bytes",
            "read_calls",
            "read_bytes",
            "write_calls",
            "write_bytes",
            "read_driver_steps",
            "write_driver_steps",
        ):
            value = getattr(self, name)
            if type(value) is not int or value <= 0:
                raise ValueError(f"{name} MUST be a positive exact integer")
        if self.read_bytes != self.request_bytes:
            raise ValueError("M51 read accounting MUST cover the exact request")
        if self.write_bytes != self.response_bytes:
            raise ValueError("M51 write accounting MUST cover the exact response")
        if self.response_body_bytes > self.response_bytes:
            raise ValueError("response body bytes exceed response wire bytes")
        if self.read_driver_steps != self.read_calls + 1:
            raise ValueError("M51 read driver accounting MUST include one completion transfer")
        if self.write_driver_steps != self.write_calls + 1:
            raise ValueError("M51 write driver accounting MUST include one completion transfer")
        for name in (
            "preparation_integrity_sha256",
            "write_completion_integrity_sha256",
        ):
            value = getattr(self, name)
            if type(value) is not str or len(value) != 64:
                raise ValueError(f"{name} MUST be lowercase SHA-256 hex")
            if any(character not in "0123456789abcdef" for character in value):
                raise ValueError(f"{name} MUST be lowercase SHA-256 hex")
        if self.transaction_completed is not True or self.connection_closed is not True:
            raise ValueError("M51 completion state is invalid")
        for name in _AUTHORITY_NEGATIVE_FIELDS:
            if getattr(self, name, None) is not False:
                raise ValueError("M51 result promoted a forbidden authority fact")
        current = (
            _RESULT_MARKER,
            self.host_authority,
            self.route_kind,
            self.route_operation,
            self.status_code,
            self.olp_message_type,
            self.request_bytes,
            self.response_bytes,
            self.response_body_bytes,
            self.read_calls,
            self.read_bytes,
            self.write_calls,
            self.write_bytes,
            self.read_driver_steps,
            self.write_driver_steps,
            self.preparation_integrity_sha256,
            self.write_completion_integrity_sha256,
            self.transaction_completed,
            self.connection_closed,
            *(getattr(self, name) for name in _AUTHORITY_NEGATIVE_FIELDS),
        )
        if self.integrity_snapshot is not None and self.integrity_snapshot != current:
            raise ValueError("M51 result integrity snapshot mismatch")
        if self.integrity_snapshot is None:
            object.__setattr__(self, "integrity_snapshot", current)


class BoundedInboundHttpSingleConnectionTransport:
    """Run exactly one M50 transaction over one captured connection adapter."""

    __slots__ = (
        "_io",
        "_preparer",
        "_driver",
        "_invoker",
        "_transaction",
        "_transaction_run_function",
        "_transaction_close_function",
        "_transaction_run",
        "_transaction_close",
        "_io_close",
        "_io_closed_getter",
        "_binding_snapshot_function",
        "_validate_function",
        "_cleanup_connection_function",
        "_wrap_transaction_failure_function",
        "_completed_result_function",
        "_run_function",
        "_close_function",
        "_binding_witness",
        "_used",
    )

    def __init__(
        self,
        *,
        connection_io: BoundedInboundHttpSingleConnectionIO,
        response_preparer: BoundedInboundHttpResponsePreparer,
        clock: Callable[[], float],
        write_limits: InboundHttpResponseWriteLimits | None = None,
        write_driver_limits: InboundHttpResponseWriteDriverLimits | None = None,
    ) -> None:
        if type(connection_io) is not BoundedInboundHttpSingleConnectionIO:
            raise TypeError("connection_io MUST be exact M51 connection adapter")
        if type(response_preparer) is not BoundedInboundHttpResponsePreparer:
            raise TypeError("response_preparer MUST be exact M43 preparer")
        if not callable(clock):
            raise TypeError("clock MUST be callable")

        driver = getattr(response_preparer, "_driver", None)
        invoker = getattr(driver, "_invoker", None)
        if type(driver) is not BoundedInboundHttpReadDriver:
            raise ValueError("M43 MUST retain one exact M42 read driver")
        if type(invoker) is not BoundedInboundHttpReadInvoker:
            raise ValueError("M42 MUST retain one exact M41 read invoker")
        if getattr(invoker, "_reader", None) is not connection_io._reader:
            raise ValueError("M43 read graph MUST use this exact M51 connection reader")

        session = getattr(response_preparer, "_session", None)
        if session is None:
            raise ValueError("M43 read session is unavailable")
        try:
            progress = session.progress()
        except Exception as exc:
            raise ValueError("M43 read session could not be verified pristine") from exc
        if progress.buffered_bytes != 0 or progress.reads_completed != 0:
            raise ValueError("M51 requires a pristine M43 read session")

        transaction = BoundedInboundHttpRequestResponseTransaction(
            response_preparer=response_preparer,
            writer=connection_io._writer,
            clock=clock,
            write_limits=write_limits,
            write_driver_limits=write_driver_limits,
        )
        self._io = connection_io
        self._preparer = response_preparer
        self._driver = driver
        self._invoker = invoker
        self._transaction = transaction
        self._transaction_run_function = BoundedInboundHttpRequestResponseTransaction.run
        self._transaction_close_function = BoundedInboundHttpRequestResponseTransaction.close
        self._transaction_run = self._transaction_run_function.__get__(
            transaction, BoundedInboundHttpRequestResponseTransaction
        )
        self._transaction_close = self._transaction_close_function.__get__(
            transaction, BoundedInboundHttpRequestResponseTransaction
        )
        self._io_close = connection_io._closer
        closed_function = BoundedInboundHttpSingleConnectionIO.closed.fget
        if closed_function is None:
            raise ValueError("M51 closed property MUST retain an exact getter")
        self._io_closed_getter = closed_function.__get__(
            connection_io, BoundedInboundHttpSingleConnectionIO
        )
        self._binding_snapshot_function = BoundedInboundHttpSingleConnectionTransport._binding_snapshot
        self._validate_function = BoundedInboundHttpSingleConnectionTransport._validate_bindings
        self._cleanup_connection_function = BoundedInboundHttpSingleConnectionTransport._cleanup_connection
        self._wrap_transaction_failure_function = BoundedInboundHttpSingleConnectionTransport._wrap_transaction_failure
        self._completed_result_function = BoundedInboundHttpSingleConnectionTransport._completed_result
        self._run_function = BoundedInboundHttpSingleConnectionTransport.run
        self._close_function = BoundedInboundHttpSingleConnectionTransport.close
        self._binding_witness = self._binding_snapshot_function(self)
        self._used = False
        self._validate_function(self)

    @property
    def used(self) -> bool:
        return self._used

    def _binding_snapshot(self) -> tuple[Any, ...]:
        return (
            "inbound-http-single-connection-transport-binding-v1",
            self._io,
            self._preparer,
            self._driver,
            self._invoker,
            self._transaction,
            self._transaction_run_function,
            self._transaction_close_function,
            self._io._reader,
            self._io._writer,
            self._binding_snapshot_function,
            self._validate_function,
            self._cleanup_connection_function,
            self._wrap_transaction_failure_function,
            self._completed_result_function,
            self._run_function,
            self._close_function,
        )

    def _validate_bindings(self) -> None:
        witness = self._binding_witness
        current = self._binding_snapshot_function(self)
        if (
            type(witness) is not tuple
            or len(witness) != 17
            or witness[0] != "inbound-http-single-connection-transport-binding-v1"
            or any(witness[index] is not current[index] for index in range(1, 17))
        ):
            _fail(
                "CONNECTION_TRANSPORT_BINDING_DRIFT",
                "M51 transport binding witness changed",
            )
        if type(self) is not BoundedInboundHttpSingleConnectionTransport:
            _fail("CONNECTION_TRANSPORT_BINDING_DRIFT", "M51 transport changed type")
        if (
            BoundedInboundHttpSingleConnectionTransport._binding_snapshot
            is not self._binding_snapshot_function
            or BoundedInboundHttpSingleConnectionTransport._validate_bindings
            is not self._validate_function
            or BoundedInboundHttpSingleConnectionTransport._cleanup_connection
            is not self._cleanup_connection_function
            or BoundedInboundHttpSingleConnectionTransport._wrap_transaction_failure
            is not self._wrap_transaction_failure_function
            or BoundedInboundHttpSingleConnectionTransport._completed_result
            is not self._completed_result_function
            or BoundedInboundHttpSingleConnectionTransport.run is not self._run_function
            or BoundedInboundHttpSingleConnectionTransport.close is not self._close_function
        ):
            _fail("CONNECTION_TRANSPORT_BINDING_DRIFT", "M51 transport method graph changed")
        if type(self._transaction) is not BoundedInboundHttpRequestResponseTransaction:
            _fail("CONNECTION_TRANSPORT_BINDING_DRIFT", "M50 transaction changed type")
        if getattr(self._driver, "_invoker", None) is not self._invoker:
            _fail("CONNECTION_TRANSPORT_BINDING_DRIFT", "M42 to M41 binding changed")
        if getattr(self._invoker, "_reader", None) is not self._io._reader:
            _fail(
                "CONNECTION_TRANSPORT_BINDING_DRIFT",
                "M41 reader no longer matches M51",
            )
        if getattr(self._transaction, "_writer", None) is not self._io._writer:
            _fail(
                "CONNECTION_TRANSPORT_BINDING_DRIFT",
                "M50 writer no longer matches M51",
            )
        self._io._validate_function(self._io)

    def _cleanup_connection(
        self,
        *,
        transaction_error: InboundHttpRequestResponseTransactionError | None = None,
    ) -> None:
        try:
            self._io_close()
            closed = self._io_closed_getter()
        except Exception:
            metadata: dict[str, str | None] = {}
            transaction_code = None
            if transaction_error is not None:
                transaction_code = transaction_error.code
                metadata = {
                    name: getattr(transaction_error, name, None)
                    for name in _M50_ERROR_FIELDS
                }
            _fail(
                "CONNECTION_CLEANUP_UNCERTAIN",
                "M51 could not verify captured connection cleanup",
                transaction_code=transaction_code,
                **metadata,
            )
        if closed is not True:
            _fail(
                "CONNECTION_CLEANUP_UNCERTAIN",
                "M51 connection did not verify closed",
            )

    def _wrap_transaction_failure(
        self, exc: InboundHttpRequestResponseTransactionError
    ) -> None:
        _fail(
            "CONNECTION_TRANSACTION_REJECTED",
            "M50 rejected the M51 single-connection transaction",
            transaction_code=exc.code,
            **{name: getattr(exc, name, None) for name in _M50_ERROR_FIELDS},
        )

    def _completed_result(
        self, transaction_result: CompletedInboundHttpRequestResponseTransaction
    ) -> CompletedInboundHttpSingleConnectionTransport:
        try:
            replayed = replace(transaction_result)
        except ValueError as exc:
            raise InboundHttpSingleConnectionTransportError(
                "CONNECTION_TRANSACTION_INTEGRITY_DRIFT",
                "M50 result failed integrity replay",
            ) from exc
        if self._io._read_calls != replayed.reader_invocations:
            _fail(
                "CONNECTION_READ_ACCOUNTING_DRIFT",
                "M51 read-call accounting diverged from M50",
            )
        if self._io._write_calls != replayed.writer_invocations:
            _fail(
                "CONNECTION_WRITE_ACCOUNTING_DRIFT",
                "M51 write-call accounting diverged from M50",
            )
        if self._io._read_bytes != replayed.request_bytes:
            _fail(
                "CONNECTION_READ_ACCOUNTING_DRIFT",
                "M51 read-byte accounting diverged from M50",
            )
        if self._io._write_bytes != replayed.response_bytes:
            _fail(
                "CONNECTION_WRITE_ACCOUNTING_DRIFT",
                "M51 write-byte accounting diverged from M50",
            )
        for name in _AUTHORITY_NEGATIVE_FIELDS:
            if getattr(replayed, name, None) is not False:
                _fail(
                    "CONNECTION_AUTHORITY_PROMOTION",
                    "M50 result promoted forbidden authority",
                )
        return CompletedInboundHttpSingleConnectionTransport(
            host_authority=replayed.host_authority,
            route_kind=replayed.route_kind,
            route_operation=replayed.route_operation,
            status_code=replayed.status_code,
            olp_message_type=replayed.olp_message_type,
            request_bytes=replayed.request_bytes,
            response_bytes=replayed.response_bytes,
            response_body_bytes=replayed.response_body_bytes,
            read_calls=self._io._read_calls,
            read_bytes=self._io._read_bytes,
            write_calls=self._io._write_calls,
            write_bytes=self._io._write_bytes,
            read_driver_steps=replayed.read_driver_steps,
            write_driver_steps=replayed.write_driver_steps,
            preparation_integrity_sha256=replayed.preparation_integrity_sha256,
            write_completion_integrity_sha256=replayed.write_completion_integrity_sha256,
        )

    def run(self) -> CompletedInboundHttpSingleConnectionTransport:
        if self._used:
            _fail("CONNECTION_TRANSPORT_USED", "M51 transport is one-shot")
        self._used = True
        try:
            self._validate_function(self)
        except InboundHttpSingleConnectionTransportError:
            self._cleanup_connection_function(self)
            raise

        try:
            transaction_result = self._transaction_run()
        except InboundHttpRequestResponseTransactionError as exc:
            self._cleanup_connection_function(self, transaction_error=exc)
            self._wrap_transaction_failure_function(self, exc)
        except Exception:
            self._cleanup_connection_function(self)
            _fail("CONNECTION_TRANSACTION_FAILED", "M50 transaction failed unexpectedly")

        try:
            self._validate_function(self)
        except InboundHttpSingleConnectionTransportError:
            self._cleanup_connection_function(self)
            raise
        self._cleanup_connection_function(self)
        return self._completed_result_function(self, transaction_result)

    def close(self) -> None:
        if not self._used:
            self._used = True
            transaction_failed = False
            try:
                self._transaction_close()
            except Exception:
                transaction_failed = True
            self._cleanup_connection_function(self)
            if transaction_failed:
                _fail("CONNECTION_CLEANUP_UNCERTAIN", "M50 close could not be verified")
            return
        if self._io_closed_getter():
            return
        self._cleanup_connection_function(self)
