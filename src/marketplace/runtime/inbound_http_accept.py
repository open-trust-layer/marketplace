"""Bounded one-shot adaptation of a caller-supplied inbound acceptor.

M52 never creates, binds, listens, resolves, connects, or negotiates TLS. It
accepts at most one connection from an already-listening caller capability and
hands back the exact M51 connection-I/O adapter after closing the acceptor.
"""
from __future__ import annotations

from typing import Protocol

from .inbound_http_connection import (
    BoundedInboundHttpSingleConnectionIO,
    InboundHttpSingleConnection,
)

__all__ = [
    "BoundedInboundHttpSingleAccept",
    "InboundHttpSingleConnectionAcceptor",
    "InboundHttpSingleAcceptError",
]


class InboundHttpSingleConnectionAcceptor(Protocol):
    """Caller-supplied already-listening one-connection accept capability."""

    def accept(self) -> InboundHttpSingleConnection: ...
    def close(self) -> None: ...


class InboundHttpSingleAcceptError(RuntimeError):
    """Stable M52 failure without reflecting arbitrary acceptor exception text."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def _fail(code: str, message: str) -> None:
    raise InboundHttpSingleAcceptError(code, message)


def _same_callable(current: object, captured: object) -> bool:
    current_self = getattr(current, "__self__", None)
    captured_self = getattr(captured, "__self__", None)
    current_func = getattr(current, "__func__", None)
    captured_func = getattr(captured, "__func__", None)
    if current_func is not None or captured_func is not None:
        return current_self is captured_self and current_func is captured_func
    return current is captured


def _close_unadapted_connection(connection: object) -> bool:
    try:
        close = getattr(connection, "close", None)
    except Exception:
        return False
    if not callable(close):
        return False
    try:
        close()
    except Exception:
        return False
    return True


class BoundedInboundHttpSingleAccept:
    """Consume one captured acceptor and transfer one exact M51 I/O capability."""

    __slots__ = (
        "_acceptor",
        "_accept",
        "_acceptor_close",
        "_io_class",
        "_io_construction_graph",
        "_accept_once_function",
        "_close_function",
        "_binding_witness",
        "_accept_attempted",
        "_close_attempted",
        "_closed",
    )

    def __init__(self, *, acceptor: InboundHttpSingleConnectionAcceptor) -> None:
        try:
            accept = getattr(acceptor, "accept", None)
            close = getattr(acceptor, "close", None)
        except Exception:
            _fail("ACCEPTOR_INTERFACE_INVALID", "M52 acceptor interface could not be inspected")
        if not callable(accept) or not callable(close):
            raise TypeError("acceptor MUST expose callable accept and close")
        self._acceptor = acceptor
        self._accept = accept
        self._acceptor_close = close
        self._io_class = BoundedInboundHttpSingleConnectionIO
        self._io_construction_graph = (
            "m51-io-construction-graph-v1",
            BoundedInboundHttpSingleConnectionIO.__new__,
            BoundedInboundHttpSingleConnectionIO.__init__,
            BoundedInboundHttpSingleConnectionIO._validate_bindings,
            BoundedInboundHttpSingleConnectionIO._ensure_open,
            BoundedInboundHttpSingleConnectionIO._read_once,
            BoundedInboundHttpSingleConnectionIO._write_once,
            BoundedInboundHttpSingleConnectionIO._close_once,
        )
        self._accept_once_function = BoundedInboundHttpSingleAccept.accept_once
        self._close_function = BoundedInboundHttpSingleAccept.close
        self._binding_witness = self._binding_snapshot()
        self._accept_attempted = False
        self._close_attempted = False
        self._closed = False
        self._validate_bindings()

    @property
    def used(self) -> bool:
        return self._accept_attempted

    @property
    def closed(self) -> bool:
        return self._closed

    def _binding_snapshot(self) -> tuple[object, ...]:
        return (
            "inbound-http-single-accept-binding-v1",
            self._acceptor,
            self._accept,
            self._acceptor_close,
            self._io_class,
            self._io_construction_graph,
            self._accept_once_function,
            self._close_function,
        )

    def _validate_bindings(self) -> None:
        witness = self._binding_witness
        if (
            type(witness) is not tuple
            or len(witness) != 8
            or type(witness[0]) is not str
            or witness[0] != "inbound-http-single-accept-binding-v1"
            or witness[1] is not self._acceptor
            or witness[2] is not self._accept
            or witness[3] is not self._acceptor_close
            or witness[4] is not self._io_class
            or witness[5] is not self._io_construction_graph
            or witness[6] is not self._accept_once_function
            or witness[7] is not self._close_function
        ):
            _fail("ACCEPTOR_BINDING_DRIFT", "M52 accept boundary binding witness changed")
        if type(self) is not BoundedInboundHttpSingleAccept:
            _fail("ACCEPTOR_BINDING_DRIFT", "M52 accept boundary changed type")
        if (
            BoundedInboundHttpSingleAccept.accept_once is not self._accept_once_function
            or BoundedInboundHttpSingleAccept.close is not self._close_function
        ):
            _fail("ACCEPTOR_BINDING_DRIFT", "M52 boundary method graph changed")
        if BoundedInboundHttpSingleConnectionIO is not self._io_class:
            _fail("ACCEPTOR_BINDING_DRIFT", "M52 M51 I/O class binding changed")
        graph = self._io_construction_graph
        if (
            type(graph) is not tuple
            or len(graph) != 8
            or graph[0] != "m51-io-construction-graph-v1"
            or graph[1] is not BoundedInboundHttpSingleConnectionIO.__new__
            or graph[2] is not BoundedInboundHttpSingleConnectionIO.__init__
            or graph[3] is not BoundedInboundHttpSingleConnectionIO._validate_bindings
            or graph[4] is not BoundedInboundHttpSingleConnectionIO._ensure_open
            or graph[5] is not BoundedInboundHttpSingleConnectionIO._read_once
            or graph[6] is not BoundedInboundHttpSingleConnectionIO._write_once
            or graph[7] is not BoundedInboundHttpSingleConnectionIO._close_once
        ):
            _fail("ACCEPTOR_BINDING_DRIFT", "M52 M51 I/O construction graph changed")
        if self._acceptor is None:
            _fail("ACCEPTOR_BINDING_DRIFT", "M52 acceptor reference is unavailable")
        for name, captured in (
            ("accept", self._accept),
            ("close", self._acceptor_close),
        ):
            try:
                current = getattr(self._acceptor, name, None)
                same = callable(current) and _same_callable(current, captured)
            except Exception:
                _fail(
                    "ACCEPTOR_METHOD_BINDING_UNVERIFIABLE",
                    f"captured acceptor {name} binding could not be verified",
                )
            if not same:
                _fail(
                    "ACCEPTOR_METHOD_BINDING_DRIFT",
                    f"captured acceptor {name} binding changed",
                )

    def _release_acceptor(self) -> None:
        self._acceptor = None
        self._accept = None
        self._acceptor_close = None
        self._binding_witness = None

    def _close_captured_acceptor(self) -> None:
        if self._close_attempted:
            return
        self._close_attempted = True
        witness = self._binding_witness
        close = witness[3] if type(witness) is tuple and len(witness) == 8 else None
        if not callable(close):
            self._release_acceptor()
            _fail(
                "ACCEPTOR_CLEANUP_UNCERTAIN",
                "M52 original acceptor cleanup binding is unavailable",
            )
        try:
            close()
        except Exception:
            self._release_acceptor()
            _fail(
                "ACCEPTOR_CLEANUP_UNCERTAIN",
                "M52 could not verify acceptor cleanup",
            )
        self._closed = True
        self._release_acceptor()

    def _cleanup_after_terminal_error(self) -> None:
        self._close_captured_acceptor()

    def accept_once(self) -> BoundedInboundHttpSingleConnectionIO:
        if self._accept_attempted or self._close_attempted:
            _fail("ACCEPTOR_USED", "M52 accept boundary is already terminal")
        self._accept_attempted = True
        try:
            self._validate_bindings()
        except InboundHttpSingleAcceptError:
            self._cleanup_after_terminal_error()
            raise

        try:
            connection = self._accept()
        except Exception:
            try:
                self._validate_bindings()
            except InboundHttpSingleAcceptError:
                self._cleanup_after_terminal_error()
                raise
            self._cleanup_after_terminal_error()
            _fail("ACCEPT_FAILED", "M52 acceptor did not return a connection")

        witness = self._binding_witness
        if type(witness) is tuple and len(witness) == 8 and connection is witness[1]:
            self._cleanup_after_terminal_error()
            _fail(
                "ACCEPTED_CONNECTION_ALIASES_ACCEPTOR",
                "M52 acceptor MUST NOT return itself as the accepted connection",
            )

        try:
            self._validate_bindings()
        except InboundHttpSingleAcceptError as binding_error:
            connection_closed = _close_unadapted_connection(connection)
            try:
                self._cleanup_after_terminal_error()
            except InboundHttpSingleAcceptError:
                raise
            if not connection_closed:
                _fail("ACCEPTED_CONNECTION_CLEANUP_UNCERTAIN", "M52 could not verify accepted connection cleanup")
            raise binding_error

        try:
            io = self._io_class(connection=connection)
        except Exception:
            connection_closed = _close_unadapted_connection(connection)
            try:
                self._cleanup_after_terminal_error()
            except InboundHttpSingleAcceptError:
                raise
            if not connection_closed:
                _fail(
                    "ACCEPTED_CONNECTION_CLEANUP_UNCERTAIN",
                    "M52 could not verify rejected connection cleanup",
                )
            _fail(
                "ACCEPTED_CONNECTION_INVALID",
                "M52 acceptor returned an invalid connection capability",
            )

        try:
            self._validate_bindings()
        except InboundHttpSingleAcceptError as binding_error:
            connection_closed = True
            try:
                io.close()
            except Exception:
                connection_closed = False
            try:
                self._cleanup_after_terminal_error()
            except InboundHttpSingleAcceptError:
                raise
            if not connection_closed:
                _fail(
                    "ACCEPTED_CONNECTION_CLEANUP_UNCERTAIN",
                    "M52 could not verify accepted connection cleanup",
                )
            raise binding_error

        try:
            self._close_captured_acceptor()
        except InboundHttpSingleAcceptError as cleanup_error:
            try:
                io.close()
            except Exception:
                _fail(
                    "ACCEPTED_CONNECTION_CLEANUP_UNCERTAIN",
                    "M52 could not verify accepted connection cleanup",
                )
            raise cleanup_error
        return io

    def close(self) -> None:
        if self._close_attempted:
            return
        if self._accept_attempted:
            return
        try:
            self._validate_bindings()
        except InboundHttpSingleAcceptError:
            self._close_captured_acceptor()
            raise
        self._close_captured_acceptor()
