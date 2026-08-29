"""Bounded one-shot orchestration of the exact M54 -> M50 inbound chain.

M55 adds no live-network implementation. The socket-constructor capability and
M43 preparer factory are explicit caller inputs; source acceptance uses only
deterministic in-memory doubles.
"""
from __future__ import annotations

from typing import Callable, Protocol, runtime_checkable

from .inbound_http_accept import (
    BoundedInboundHttpSingleAccept,
    InboundHttpSingleAcceptError,
)
from .inbound_http_connection import (
    BoundedInboundHttpSingleConnectionIO,
    BoundedInboundHttpSingleConnectionTransport,
    CompletedInboundHttpSingleConnectionTransport,
    InboundHttpSingleConnectionTransportError,
)
from .inbound_http_response_prepare import BoundedInboundHttpResponsePreparer
from .inbound_tcp_listener import (
    BoundedInboundTcpListenerConstruction,
    InboundTcpListenerConstructionError,
)
from .inbound_tcp_socket_factory import (
    BoundedPythonTcpSocketFactory,
    PythonTcpSocketConstructor,
    PythonTcpSocketFactoryError,
)

__all__ = [
    "BoundedInboundHttpSingleSessionOrchestrator",
    "InboundHttpResponsePreparerFactory",
    "InboundHttpSingleSessionOrchestratorError",
]

_LOOPBACK_HOST = "127.0.0.1"
_EXACT_BACKLOG = 1


@runtime_checkable
class InboundHttpResponsePreparerFactory(Protocol):
    """Build one exact M43 preparer for the accepted M51 reader."""

    def __call__(
        self,
        reader: Callable[[int], object],
    ) -> BoundedInboundHttpResponsePreparer: ...


class InboundHttpSingleSessionOrchestratorError(RuntimeError):
    """Stable M55 failure with at most one stable lower-layer code."""

    def __init__(
        self,
        code: str,
        message: str,
        *,
        lower_code: str | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.lower_code = lower_code


def _fail(
    code: str,
    message: str,
    *,
    lower_code: str | None = None,
) -> None:
    raise InboundHttpSingleSessionOrchestratorError(
        code,
        message,
        lower_code=lower_code,
    )


class BoundedInboundHttpSingleSessionOrchestrator:
    """Run exactly one deterministic M54 -> M50 inbound session."""

    __slots__ = (
        "_listener_construction",
        "_listener_construct_once",
        "_listener_close",
        "_preparer_factory",
        "_preparer_factory_type",
        "_preparer_factory_call",
        "_clock",
        "_m52_class",
        "_m52_accept_function",
        "_m52_close_function",
        "_io_class",
        "_io_validate_function",
        "_io_read_function",
        "_io_write_function",
        "_io_close_once_function",
        "_io_closed_getter_function",
        "_preparer_class",
        "_preparer_validate_function",
        "_preparer_close_function",
        "_transport_class",
        "_transport_construction_graph",
        "_transport_init_function",
        "_transport_run_function",
        "_transport_close_function",
        "_binding_snapshot_function",
        "_validate_function",
        "_validate_lower_graph_function",
        "_release_function",
        "_close_listener_before_construct_function",
        "_close_accept_boundary_function",
        "_close_io_function",
        "_close_preparer_function",
        "_cleanup_after_preparer_function",
        "_fail_before_accept_function",
        "_run_once_function",
        "_close_function",
        "_binding_witness",
        "_used",
        "_closed",
    )

    def __init__(
        self,
        *,
        constructor: PythonTcpSocketConstructor,
        response_preparer_factory: InboundHttpResponsePreparerFactory,
        clock: Callable[[], float],
        port: int,
    ) -> None:
        if not callable(response_preparer_factory):
            _fail(
                "SESSION_PREPARER_FACTORY_INVALID",
                "M55 response preparer factory MUST be callable",
            )
        if not callable(clock):
            _fail("SESSION_CLOCK_INVALID", "M55 clock MUST be callable")
        preparer_factory_type = type(response_preparer_factory)
        try:
            preparer_factory_call = getattr(preparer_factory_type, "__call__", None)
        except Exception:
            _fail(
                "SESSION_PREPARER_FACTORY_BINDING_UNVERIFIABLE",
                "M55 response preparer factory binding could not be inspected",
            )
        if not callable(preparer_factory_call):
            _fail(
                "SESSION_PREPARER_FACTORY_INVALID",
                "M55 response preparer factory call binding is invalid",
            )

        try:
            socket_factory = BoundedPythonTcpSocketFactory(constructor=constructor)
        except PythonTcpSocketFactoryError as exc:
            _fail(
                "SESSION_CONFIGURATION_REJECTED",
                "M54 rejected the M55 constructor capability",
                lower_code=exc.code,
            )
        try:
            listener_construction = BoundedInboundTcpListenerConstruction(
                factory=socket_factory,
                host=_LOOPBACK_HOST,
                port=port,
                backlog=_EXACT_BACKLOG,
            )
        except InboundTcpListenerConstructionError as exc:
            _fail(
                "SESSION_CONFIGURATION_REJECTED",
                "M53 rejected the M55 listener configuration",
                lower_code=exc.code,
            )
        io_closed_getter = BoundedInboundHttpSingleConnectionIO.closed.fget
        if io_closed_getter is None:
            _fail(
                "SESSION_LOWER_BINDING_DRIFT",
                "M51 connection closed getter is unavailable",
            )

        self._listener_construction = listener_construction
        self._listener_construct_once = (
            BoundedInboundTcpListenerConstruction.construct_once.__get__(
                listener_construction,
                BoundedInboundTcpListenerConstruction,
            )
        )
        self._listener_close = BoundedInboundTcpListenerConstruction.close.__get__(
            listener_construction,
            BoundedInboundTcpListenerConstruction,
        )
        self._preparer_factory = response_preparer_factory
        self._preparer_factory_type = preparer_factory_type
        self._preparer_factory_call = preparer_factory_call
        self._clock = clock
        self._m52_class = BoundedInboundHttpSingleAccept
        self._m52_accept_function = BoundedInboundHttpSingleAccept.accept_once
        self._m52_close_function = BoundedInboundHttpSingleAccept.close
        self._io_class = BoundedInboundHttpSingleConnectionIO
        self._io_validate_function = BoundedInboundHttpSingleConnectionIO._validate_bindings
        self._io_read_function = BoundedInboundHttpSingleConnectionIO._read_once
        self._io_write_function = BoundedInboundHttpSingleConnectionIO._write_once
        self._io_close_once_function = BoundedInboundHttpSingleConnectionIO._close_once
        self._io_closed_getter_function = io_closed_getter
        self._preparer_class = BoundedInboundHttpResponsePreparer
        self._preparer_validate_function = BoundedInboundHttpResponsePreparer._validate_bindings
        self._preparer_close_function = BoundedInboundHttpResponsePreparer.close
        self._transport_class = BoundedInboundHttpSingleConnectionTransport
        self._transport_construction_graph = (
            "m51-transport-construction-graph-v1",
            BoundedInboundHttpSingleConnectionTransport.__new__,
            BoundedInboundHttpSingleConnectionTransport.__init__,
            BoundedInboundHttpSingleConnectionTransport._binding_snapshot,
            BoundedInboundHttpSingleConnectionTransport._validate_bindings,
            BoundedInboundHttpSingleConnectionTransport._cleanup_connection,
            BoundedInboundHttpSingleConnectionTransport._wrap_transaction_failure,
            BoundedInboundHttpSingleConnectionTransport._completed_result,
            BoundedInboundHttpSingleConnectionTransport.run,
            BoundedInboundHttpSingleConnectionTransport.close,
        )
        self._transport_init_function = BoundedInboundHttpSingleConnectionTransport.__init__
        self._transport_run_function = BoundedInboundHttpSingleConnectionTransport.run
        self._transport_close_function = BoundedInboundHttpSingleConnectionTransport.close
        self._binding_snapshot_function = BoundedInboundHttpSingleSessionOrchestrator._binding_snapshot
        self._validate_function = BoundedInboundHttpSingleSessionOrchestrator._validate_bindings
        self._validate_lower_graph_function = BoundedInboundHttpSingleSessionOrchestrator._validate_lower_graph
        self._release_function = BoundedInboundHttpSingleSessionOrchestrator._release
        self._close_listener_before_construct_function = BoundedInboundHttpSingleSessionOrchestrator._close_listener_before_construct
        self._close_accept_boundary_function = BoundedInboundHttpSingleSessionOrchestrator._close_accept_boundary
        self._close_io_function = BoundedInboundHttpSingleSessionOrchestrator._close_io
        self._close_preparer_function = BoundedInboundHttpSingleSessionOrchestrator._close_preparer
        self._cleanup_after_preparer_function = BoundedInboundHttpSingleSessionOrchestrator._cleanup_after_preparer
        self._fail_before_accept_function = BoundedInboundHttpSingleSessionOrchestrator._fail_before_accept
        self._run_once_function = BoundedInboundHttpSingleSessionOrchestrator.run_once
        self._close_function = BoundedInboundHttpSingleSessionOrchestrator.close
        self._binding_witness = self._binding_snapshot_function(self)
        self._used = False
        self._closed = False
        self._validate_function(self)

    @property
    def used(self) -> bool:
        return self._used

    @property
    def closed(self) -> bool:
        return self._closed

    def _binding_snapshot(self) -> tuple[object, ...]:
        return (
            "inbound-http-single-session-orchestrator-v1",
            self._listener_construction,
            self._preparer_factory,
            self._preparer_factory_type,
            self._preparer_factory_call,
            self._clock,
            self._m52_class,
            self._m52_accept_function,
            self._m52_close_function,
            self._io_class,
            self._io_validate_function,
            self._io_read_function,
            self._io_write_function,
            self._io_close_once_function,
            self._io_closed_getter_function,
            self._preparer_class,
            self._preparer_validate_function,
            self._preparer_close_function,
            self._transport_class,
            self._transport_construction_graph,
            self._transport_init_function,
            self._transport_run_function,
            self._transport_close_function,
            self._binding_snapshot_function,
            self._validate_function,
            self._validate_lower_graph_function,
            self._release_function,
            self._close_listener_before_construct_function,
            self._close_accept_boundary_function,
            self._close_io_function,
            self._close_preparer_function,
            self._cleanup_after_preparer_function,
            self._fail_before_accept_function,
            self._run_once_function,
            self._close_function,
        )

    def _validate_bindings(self) -> None:
        if (
            type(self) is not BoundedInboundHttpSingleSessionOrchestrator
            or self._binding_snapshot_function is not BoundedInboundHttpSingleSessionOrchestrator._binding_snapshot
            or self._validate_function is not BoundedInboundHttpSingleSessionOrchestrator._validate_bindings
            or self._validate_lower_graph_function is not BoundedInboundHttpSingleSessionOrchestrator._validate_lower_graph
            or self._release_function is not BoundedInboundHttpSingleSessionOrchestrator._release
            or self._close_listener_before_construct_function is not BoundedInboundHttpSingleSessionOrchestrator._close_listener_before_construct
            or self._close_accept_boundary_function is not BoundedInboundHttpSingleSessionOrchestrator._close_accept_boundary
            or self._close_io_function is not BoundedInboundHttpSingleSessionOrchestrator._close_io
            or self._close_preparer_function is not BoundedInboundHttpSingleSessionOrchestrator._close_preparer
            or self._cleanup_after_preparer_function is not BoundedInboundHttpSingleSessionOrchestrator._cleanup_after_preparer
            or self._fail_before_accept_function is not BoundedInboundHttpSingleSessionOrchestrator._fail_before_accept
            or self._run_once_function is not BoundedInboundHttpSingleSessionOrchestrator.run_once
            or self._close_function is not BoundedInboundHttpSingleSessionOrchestrator.close
        ):
            _fail(
                "SESSION_ORCHESTRATOR_BINDING_DRIFT",
                "M55 orchestrator helper graph changed",
            )
        witness = self._binding_witness
        current = self._binding_snapshot_function(self)
        if (
            type(witness) is not tuple
            or len(witness) != 35
            or witness[0] != "inbound-http-single-session-orchestrator-v1"
            or witness[1] is not current[1]
            or witness[2] is not current[2]
            or witness[3] is not current[3]
            or witness[4] is not current[4]
            or witness[5] is not current[5]
            or witness[6] is not current[6]
            or witness[7] is not current[7]
            or witness[8] is not current[8]
            or witness[9] is not current[9]
            or witness[10] is not current[10]
            or witness[11] is not current[11]
            or witness[12] is not current[12]
            or witness[13] is not current[13]
            or witness[14] is not current[14]
            or witness[15] is not current[15]
            or witness[16] is not current[16]
            or witness[17] is not current[17]
            or witness[18] is not current[18]
            or witness[19] is not current[19]
            or witness[20] is not current[20]
            or witness[21] is not current[21]
            or witness[22] is not current[22]
            or witness[23] is not current[23]
            or witness[24] is not current[24]
            or witness[25] is not current[25]
            or witness[26] is not current[26]
            or witness[27] is not current[27]
            or witness[28] is not current[28]
            or witness[29] is not current[29]
            or witness[30] is not current[30]
            or witness[31] is not current[31]
            or witness[32] is not current[32]
            or witness[33] is not current[33]
            or witness[34] is not current[34]
        ):
            _fail(
                "SESSION_ORCHESTRATOR_BINDING_DRIFT",
                "M55 orchestration binding witness changed",
            )
        if type(self._listener_construction) is not BoundedInboundTcpListenerConstruction:
            _fail(
                "SESSION_ORCHESTRATOR_BINDING_DRIFT",
                "M55 listener construction changed type",
            )
        if type(self._preparer_factory) is not self._preparer_factory_type:
            _fail(
                "SESSION_PREPARER_FACTORY_BINDING_DRIFT",
                "M55 response preparer factory type changed",
            )
        try:
            current_factory_call = getattr(self._preparer_factory_type, "__call__", None)
        except Exception:
            _fail(
                "SESSION_PREPARER_FACTORY_BINDING_UNVERIFIABLE",
                "M55 response preparer factory binding could not be verified",
            )
        if current_factory_call is not self._preparer_factory_call:
            _fail(
                "SESSION_PREPARER_FACTORY_BINDING_DRIFT",
                "M55 response preparer factory call binding changed",
            )
        self._validate_lower_graph_function(self)

    def _validate_lower_graph(self) -> None:
        if (
            BoundedInboundTcpListenerConstruction.construct_once
            is not getattr(self._listener_construct_once, "__func__", None)
            or BoundedInboundTcpListenerConstruction.close
            is not getattr(self._listener_close, "__func__", None)
        ):
            _fail(
                "SESSION_LOWER_BINDING_DRIFT",
                "M53 listener construction method graph changed",
            )
        if (
            BoundedInboundHttpSingleAccept is not self._m52_class
            or BoundedInboundHttpSingleAccept.accept_once is not self._m52_accept_function
            or BoundedInboundHttpSingleAccept.close is not self._m52_close_function
        ):
            _fail("SESSION_LOWER_BINDING_DRIFT", "M52 accept graph changed")
        if (
            BoundedInboundHttpSingleConnectionIO is not self._io_class
            or BoundedInboundHttpSingleConnectionIO._validate_bindings
            is not self._io_validate_function
            or BoundedInboundHttpSingleConnectionIO._read_once is not self._io_read_function
            or BoundedInboundHttpSingleConnectionIO._write_once is not self._io_write_function
            or BoundedInboundHttpSingleConnectionIO._close_once is not self._io_close_once_function
            or BoundedInboundHttpSingleConnectionIO.closed.fget
            is not self._io_closed_getter_function
        ):
            _fail("SESSION_LOWER_BINDING_DRIFT", "M51 connection I/O graph changed")
        if (
            BoundedInboundHttpResponsePreparer is not self._preparer_class
            or BoundedInboundHttpResponsePreparer._validate_bindings
            is not self._preparer_validate_function
            or BoundedInboundHttpResponsePreparer.close is not self._preparer_close_function
        ):
            _fail("SESSION_LOWER_BINDING_DRIFT", "M43 preparer graph changed")
        transport_graph = self._transport_construction_graph
        if (
            BoundedInboundHttpSingleConnectionTransport is not self._transport_class
            or type(transport_graph) is not tuple
            or len(transport_graph) != 10
            or transport_graph[0] != "m51-transport-construction-graph-v1"
            or transport_graph[1] is not BoundedInboundHttpSingleConnectionTransport.__new__
            or transport_graph[2] is not BoundedInboundHttpSingleConnectionTransport.__init__
            or transport_graph[3] is not BoundedInboundHttpSingleConnectionTransport._binding_snapshot
            or transport_graph[4] is not BoundedInboundHttpSingleConnectionTransport._validate_bindings
            or transport_graph[5] is not BoundedInboundHttpSingleConnectionTransport._cleanup_connection
            or transport_graph[6] is not BoundedInboundHttpSingleConnectionTransport._wrap_transaction_failure
            or transport_graph[7] is not BoundedInboundHttpSingleConnectionTransport._completed_result
            or transport_graph[8] is not BoundedInboundHttpSingleConnectionTransport.run
            or transport_graph[9] is not BoundedInboundHttpSingleConnectionTransport.close
            or BoundedInboundHttpSingleConnectionTransport.__init__ is not self._transport_init_function
            or BoundedInboundHttpSingleConnectionTransport.run is not self._transport_run_function
            or BoundedInboundHttpSingleConnectionTransport.close is not self._transport_close_function
        ):
            _fail("SESSION_LOWER_BINDING_DRIFT", "M51 transport graph changed")

    def _release(self) -> None:
        self._listener_construction = None
        self._listener_construct_once = None
        self._listener_close = None
        self._preparer_factory = None
        self._preparer_factory_type = None
        self._preparer_factory_call = None
        self._clock = None
        self._binding_witness = None
        self._closed = True

    def _close_listener_before_construct(self) -> None:
        close = self._listener_close
        if not callable(close):
            return
        try:
            close()
        except Exception:
            pass

    def _close_accept_boundary(self, boundary: BoundedInboundHttpSingleAccept) -> bool:
        try:
            self._m52_close_function(boundary)
        except Exception:
            return False
        return getattr(boundary, "_closed", None) is True

    def _close_io(self, io: BoundedInboundHttpSingleConnectionIO) -> bool:
        try:
            self._io_close_once_function(io)
            closed = self._io_closed_getter_function(io)
        except Exception:
            return False
        return closed is True

    def _close_preparer(self, preparer: BoundedInboundHttpResponsePreparer) -> bool:
        try:
            self._preparer_close_function(preparer)
        except Exception:
            return False
        return True

    def _cleanup_after_preparer(
        self,
        preparer: BoundedInboundHttpResponsePreparer | None,
        io: BoundedInboundHttpSingleConnectionIO,
    ) -> None:
        preparer_clear = True
        if preparer is not None:
            preparer_clear = self._close_preparer(preparer)
        io_clear = self._close_io(io)
        if not preparer_clear or not io_clear:
            self._release()
            _fail(
                "SESSION_CLEANUP_UNCERTAIN",
                "M55 could not verify accepted-session cleanup",
            )

    def _fail_before_accept(
        self,
        boundary: BoundedInboundHttpSingleAccept,
        exc: InboundHttpSingleSessionOrchestratorError,
    ) -> None:
        cleaned = self._close_accept_boundary(boundary)
        self._release()
        if not cleaned:
            _fail(
                "SESSION_CLEANUP_UNCERTAIN",
                "M55 could not verify listener cleanup before accept",
            )
        raise exc

    def run_once(self) -> CompletedInboundHttpSingleConnectionTransport:
        if self._used or self._closed:
            _fail("SESSION_ORCHESTRATOR_USED", "M55 orchestrator is already terminal")
        self._used = True

        validate_function = self._validate_function
        release_function = self._release_function
        listener_construct_once = self._listener_construct_once
        listener_close = self._listener_close
        m52_class = self._m52_class
        m52_accept_function = self._m52_accept_function
        m52_close_function = self._m52_close_function
        io_class = self._io_class
        io_validate_function = self._io_validate_function
        io_close_function = self._io_close_once_function
        io_closed_getter = self._io_closed_getter_function
        preparer_factory = self._preparer_factory
        preparer_factory_call = self._preparer_factory_call
        preparer_class = self._preparer_class
        preparer_validate_function = self._preparer_validate_function
        preparer_close_function = self._preparer_close_function
        transport_class = self._transport_class
        transport_run_function = self._transport_run_function
        transport_close_function = self._transport_close_function
        clock = self._clock

        if validate_function is not BoundedInboundHttpSingleSessionOrchestrator._validate_bindings:
            _fail(
                "SESSION_ORCHESTRATOR_BINDING_DRIFT",
                "M55 captured validator changed before execution",
            )

        def release() -> None:
            release_function(self)

        def close_listener_before_construct() -> None:
            if not callable(listener_close):
                return
            try:
                listener_close()
            except Exception:
                pass

        def close_accept_boundary(boundary: BoundedInboundHttpSingleAccept) -> bool:
            try:
                m52_close_function(boundary)
            except Exception:
                return False
            return getattr(boundary, "_closed", None) is True

        def close_io(io: BoundedInboundHttpSingleConnectionIO) -> bool:
            try:
                io_close_function(io)
                closed = io_closed_getter(io)
            except Exception:
                return False
            return closed is True

        def close_preparer(preparer: BoundedInboundHttpResponsePreparer) -> bool:
            try:
                preparer_close_function(preparer)
            except Exception:
                return False
            return True

        def cleanup_after_preparer(
            preparer: BoundedInboundHttpResponsePreparer | None,
            io: BoundedInboundHttpSingleConnectionIO,
        ) -> None:
            preparer_clear = preparer is None or close_preparer(preparer)
            io_clear = close_io(io)
            if not preparer_clear or not io_clear:
                release()
                _fail(
                    "SESSION_CLEANUP_UNCERTAIN",
                    "M55 could not verify accepted-session cleanup",
                )

        try:
            validate_function(self)
        except InboundHttpSingleSessionOrchestratorError:
            close_listener_before_construct()
            release()
            raise

        try:
            accept_boundary = listener_construct_once()
        except InboundTcpListenerConstructionError as exc:
            release()
            _fail(
                "SESSION_LISTENER_REJECTED",
                "M53 rejected M55 listener construction",
                lower_code=exc.code,
            )
        except Exception:
            release()
            _fail(
                "SESSION_LISTENER_FAILED",
                "M55 listener construction failed unexpectedly",
            )

        if type(accept_boundary) is not m52_class:
            release()
            _fail("SESSION_ACCEPT_BOUNDARY_INVALID", "M53 returned a non-exact M52 boundary")
        try:
            validate_function(self)
        except InboundHttpSingleSessionOrchestratorError as exc:
            cleaned = close_accept_boundary(accept_boundary)
            release()
            if not cleaned:
                _fail(
                    "SESSION_CLEANUP_UNCERTAIN",
                    "M55 could not verify listener cleanup before accept",
                )
            raise exc

        try:
            io = m52_accept_function(accept_boundary)
        except InboundHttpSingleAcceptError as exc:
            release()
            _fail(
                "SESSION_ACCEPT_REJECTED",
                "M52 rejected the M55 single accept",
                lower_code=exc.code,
            )
        except Exception:
            cleaned = close_accept_boundary(accept_boundary)
            release()
            if not cleaned:
                _fail(
                    "SESSION_CLEANUP_UNCERTAIN",
                    "M55 could not verify listener cleanup after accept failure",
                )
            _fail("SESSION_ACCEPT_FAILED", "M55 accept failed unexpectedly")

        if type(io) is not io_class:
            release()
            _fail("SESSION_CONNECTION_IO_INVALID", "M52 returned non-exact M51 connection I/O")
        try:
            validate_function(self)
        except InboundHttpSingleSessionOrchestratorError as exc:
            cleaned = close_io(io)
            release()
            if not cleaned:
                _fail(
                    "SESSION_CLEANUP_UNCERTAIN",
                    "M55 could not verify connection cleanup after binding drift",
                )
            raise exc

        try:
            preparer = preparer_factory_call(preparer_factory, io._reader)
        except Exception:
            cleaned = close_io(io)
            release()
            if not cleaned:
                _fail(
                    "SESSION_CLEANUP_UNCERTAIN",
                    "M55 could not verify connection cleanup after preparer failure",
                )
            _fail(
                "SESSION_PREPARER_FACTORY_FAILED",
                "M55 response preparer factory failed",
            )

        if type(preparer) is not preparer_class:
            cleaned = close_io(io)
            release()
            if not cleaned:
                _fail(
                    "SESSION_CLEANUP_UNCERTAIN",
                    "M55 could not verify connection cleanup after invalid preparer",
                )
            _fail(
                "SESSION_PREPARER_INVALID",
                "M55 preparer factory MUST return exact M43",
            )

        try:
            validate_function(self)
        except InboundHttpSingleSessionOrchestratorError as exc:
            cleanup_after_preparer(preparer, io)
            release()
            raise exc

        try:
            io_validate_function(io)
            preparer_validate_function(preparer)
        except Exception:
            cleanup_after_preparer(preparer, io)
            release()
            _fail(
                "SESSION_HANDOFF_BINDING_DRIFT",
                "M55 exact M51/M43 handoff binding changed",
            )

        try:
            transport = transport_class(
                connection_io=io,
                response_preparer=preparer,
                clock=clock,
            )
        except Exception:
            cleanup_after_preparer(preparer, io)
            release()
            _fail(
                "SESSION_TRANSPORT_CONSTRUCTION_FAILED",
                "M51 transport construction rejected the M55 handoff",
            )

        try:
            result = transport_run_function(transport)
        except InboundHttpSingleConnectionTransportError as exc:
            cleanup_ok = True
            try:
                transport_close_function(transport)
            except Exception:
                cleanup_ok = False
            release()
            if not cleanup_ok:
                _fail(
                    "SESSION_CLEANUP_UNCERTAIN",
                    "M55 could not verify M51 cleanup after transaction rejection",
                    lower_code=exc.code,
                )
            _fail(
                "SESSION_TRANSACTION_REJECTED",
                "M51 rejected the M55 single session",
                lower_code=exc.code,
            )
        except Exception:
            cleanup_ok = True
            try:
                transport_close_function(transport)
            except Exception:
                cleanup_ok = False
            release()
            if not cleanup_ok:
                _fail(
                    "SESSION_CLEANUP_UNCERTAIN",
                    "M55 could not verify M51 cleanup after unexpected failure",
                )
            _fail("SESSION_TRANSACTION_FAILED", "M55 single transaction failed unexpectedly")

        if type(result) is not CompletedInboundHttpSingleConnectionTransport:
            release()
            _fail(
                "SESSION_RESULT_INVALID",
                "M51 returned a non-exact M55 completion result",
            )
        release()
        return result

    def close(self) -> None:
        release_function = self._release_function
        if self._closed:
            return
        if self._used:
            release_function(self)
            return
        self._used = True
        close = self._listener_close
        cleanup_ok = True
        if callable(close):
            try:
                close()
            except Exception:
                cleanup_ok = False
        release_function(self)
        if not cleanup_ok:
            _fail(
                "SESSION_CLEANUP_UNCERTAIN",
                "M55 could not verify pre-run construction cleanup",
            )
