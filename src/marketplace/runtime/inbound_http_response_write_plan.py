"""Transport-free bounded planning for an already-prepared inbound HTTP response.

M44 never invokes a writer and never claims that locally-accounted bytes were
transmitted. It validates one exact M43 prepared response and derives the maximum
size of the next write a future transport boundary may request.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any, Final

from .inbound_http_response_prepare import PreparedInboundHttpReadResponse

WRITE_ACTION_WRITE: Final = "WRITE"
WRITE_ACTION_COMPLETE: Final = "COMPLETE"

DEFAULT_MAX_INBOUND_HTTP_WRITE_CALLS: Final = 64
DEFAULT_MAX_INBOUND_HTTP_WRITE_BYTES: Final = 16 * 1024
MAX_INBOUND_HTTP_WRITE_CALLS: Final = 1_024
MAX_INBOUND_HTTP_WRITE_BYTES: Final = 1 * 1024 * 1024

_AUTHORITY_NEGATIVE_FIELDS: Final = (
    "socket_access_proven",
    "network_origin_proven",
    "request_authenticated",
    "peer_identity_proven",
    "establishes_marketplace_truth",
    "establishes_trust",
    "establishes_authorization",
    "authorizes_protected_side_effects",
)


class InboundHttpResponseWritePlanError(RuntimeError):
    """Fail-closed M44 planning error with stable local reason metadata."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def _fail(code: str, message: str) -> None:
    raise InboundHttpResponseWritePlanError(code, message)


def _validate_prepared(value: PreparedInboundHttpReadResponse) -> PreparedInboundHttpReadResponse:
    if type(value) is not PreparedInboundHttpReadResponse:
        _fail("WRITE_PREPARED_RESPONSE_TYPE", "prepared_response MUST be exact M43 result")
    if value.response_prepared is not True or value.transmitted is not False:
        _fail("WRITE_PREPARED_RESPONSE_DRIFT", "M43 prepared response authority changed")
    for name in _AUTHORITY_NEGATIVE_FIELDS:
        if getattr(value, name, None) is not False:
            _fail("WRITE_AUTHORITY_ESCALATION", "M43 prepared response promoted authority")
    try:
        replayed = replace(value)
    except ValueError as exc:
        raise InboundHttpResponseWritePlanError(
            "WRITE_PREPARED_RESPONSE_DRIFT",
            "M43 prepared response failed integrity replay",
        ) from exc
    if replayed.response_prepared is not True or replayed.transmitted is not False:
        _fail("WRITE_PREPARED_RESPONSE_DRIFT", "M43 prepared response authority changed")
    for name in _AUTHORITY_NEGATIVE_FIELDS:
        if getattr(replayed, name, None) is not False:
            _fail("WRITE_AUTHORITY_ESCALATION", "M43 prepared response promoted authority")
    return replayed


@dataclass(frozen=True)
class InboundHttpResponseWriteLimits:
    max_write_calls: int = DEFAULT_MAX_INBOUND_HTTP_WRITE_CALLS
    max_write_bytes: int = DEFAULT_MAX_INBOUND_HTTP_WRITE_BYTES

    def __post_init__(self) -> None:
        if (
            type(self.max_write_calls) is not int
            or not 1 <= self.max_write_calls <= MAX_INBOUND_HTTP_WRITE_CALLS
        ):
            raise ValueError(
                f"max_write_calls MUST be within 1..{MAX_INBOUND_HTTP_WRITE_CALLS}"
            )
        if (
            type(self.max_write_bytes) is not int
            or not 1 <= self.max_write_bytes <= MAX_INBOUND_HTTP_WRITE_BYTES
        ):
            raise ValueError(
                f"max_write_bytes MUST be within 1..{MAX_INBOUND_HTTP_WRITE_BYTES}"
            )


@dataclass(frozen=True)
class InboundHttpResponseWritePlan:
    """One local write-budget decision; never evidence that a write occurred."""

    action: str
    response_bytes: int
    bytes_written: int
    write_calls_completed: int
    next_write_bytes: int
    remaining_bytes: int
    prepared_response_integrity: tuple[Any, ...]
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
        if self.action not in {WRITE_ACTION_WRITE, WRITE_ACTION_COMPLETE}:
            raise ValueError("action is outside the M44 write-plan profile")
        for name in (
            "response_bytes",
            "bytes_written",
            "write_calls_completed",
            "next_write_bytes",
            "remaining_bytes",
        ):
            value = getattr(self, name)
            if type(value) is not int or value < 0:
                raise ValueError(f"{name} MUST be a non-negative exact integer")
        if self.response_bytes <= 0:
            raise ValueError("response_bytes MUST be positive")
        if self.bytes_written > self.response_bytes:
            raise ValueError("bytes_written MUST NOT exceed response_bytes")
        if self.remaining_bytes != self.response_bytes - self.bytes_written:
            raise ValueError("remaining_bytes is inconsistent")
        if type(self.prepared_response_integrity) is not tuple:
            raise ValueError("prepared_response_integrity MUST be exact tuple")
        if self.action == WRITE_ACTION_COMPLETE:
            if self.remaining_bytes != 0 or self.next_write_bytes != 0:
                raise ValueError("COMPLETE requires zero remaining and next bytes")
        else:
            if self.remaining_bytes <= 0 or self.next_write_bytes <= 0:
                raise ValueError("WRITE requires positive remaining and next bytes")
            if self.next_write_bytes > self.remaining_bytes:
                raise ValueError("next_write_bytes exceeds remaining response")
        for name in (
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
        ):
            if getattr(self, name, None) is not False:
                raise ValueError("M44 plan promoted a forbidden authority fact")
        current = (
            "inbound-http-response-write-plan-v1",
            self.action,
            self.response_bytes,
            self.bytes_written,
            self.write_calls_completed,
            self.next_write_bytes,
            self.remaining_bytes,
            self.prepared_response_integrity,
            self.writer_invoked,
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
            raise ValueError("M44 write-plan integrity snapshot mismatch")
        if self.integrity_snapshot is None:
            object.__setattr__(self, "integrity_snapshot", current)


class BoundedInboundHttpResponseWritePlanner:
    """Derive finite next-write budgets without invoking a writer."""

    def __init__(self, *, limits: InboundHttpResponseWriteLimits | None = None) -> None:
        if limits is None:
            limits = InboundHttpResponseWriteLimits()
        if type(limits) is not InboundHttpResponseWriteLimits:
            raise TypeError("limits MUST be exact InboundHttpResponseWriteLimits")
        self._limits = InboundHttpResponseWriteLimits(
            max_write_calls=limits.max_write_calls,
            max_write_bytes=limits.max_write_bytes,
        )

    @property
    def limits(self) -> InboundHttpResponseWriteLimits:
        return InboundHttpResponseWriteLimits(
            max_write_calls=self._limits.max_write_calls,
            max_write_bytes=self._limits.max_write_bytes,
        )

    def plan(
        self,
        prepared_response: PreparedInboundHttpReadResponse,
        *,
        write_calls_completed: int,
        bytes_written: int,
    ) -> InboundHttpResponseWritePlan:
        replayed = _validate_prepared(prepared_response)
        if type(write_calls_completed) is not int or write_calls_completed < 0:
            _fail("WRITE_CALL_COUNT_INVALID", "write_calls_completed MUST be non-negative exact int")
        if type(bytes_written) is not int or bytes_written < 0:
            _fail("WRITE_BYTE_COUNT_INVALID", "bytes_written MUST be non-negative exact int")
        total = replayed.response_bytes
        if bytes_written > total:
            _fail("WRITE_BYTE_COUNT_OVERFLOW", "bytes_written exceeds prepared response length")

        remaining = total - bytes_written
        if remaining == 0:
            return InboundHttpResponseWritePlan(
                action=WRITE_ACTION_COMPLETE,
                response_bytes=total,
                bytes_written=bytes_written,
                write_calls_completed=write_calls_completed,
                next_write_bytes=0,
                remaining_bytes=0,
                prepared_response_integrity=replayed.integrity_snapshot,
            )
        if write_calls_completed >= self._limits.max_write_calls:
            _fail("WRITE_CALL_LIMIT_EXHAUSTED", "response remains after M44 write-call limit")
        next_write = min(self._limits.max_write_bytes, remaining)
        return InboundHttpResponseWritePlan(
            action=WRITE_ACTION_WRITE,
            response_bytes=total,
            bytes_written=bytes_written,
            write_calls_completed=write_calls_completed,
            next_write_bytes=next_write,
            remaining_bytes=remaining,
            prepared_response_integrity=replayed.integrity_snapshot,
        )
