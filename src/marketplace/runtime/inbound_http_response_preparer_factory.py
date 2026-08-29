"""Transport-free composition factory for the exact M36 -> M43 read path.

M56 constructs one bounded response-preparation graph around an already-supplied
reader capability. Construction itself never invokes the reader or performs
network I/O.
"""
from __future__ import annotations

from typing import Callable

from .inbound_http import (
    BoundedInboundHttpApplicationAdapter,
    InboundHttpApplicationLimits,
)
from .inbound_http_read_driver import BoundedInboundHttpReadDriver
from .inbound_http_read_invoke import BoundedInboundHttpReadInvoker
from .inbound_http_read_outcome import (
    BoundedInboundHttpReadOutcomeHandler,
    InboundHttpReadOutcome,
)
from .inbound_http_read_plan import BoundedInboundHttpReadPlanner
from .inbound_http_read_session import BoundedInboundHttpReadSession
from .inbound_http_read_transition import BoundedInboundHttpReadTransitioner
from .inbound_http_response_prepare import BoundedInboundHttpResponsePreparer
from .inbound_http_stream import BoundedInboundHttpStreamAssembler
from .inbound_http_wire import BoundedInboundHttpWireAdapter, InboundHttpWireLimits

__all__ = [
    "BoundedInboundHttpResponsePreparerCompositionFactory",
    "InboundHttpResponsePreparerCompositionError",
]

_BINDING_MARKER = "inbound-http-response-preparer-composition-factory-binding-v1"
_GRAPH_MARKER = "m56-m34-m43-class-identity-graph-v1"


class InboundHttpResponsePreparerCompositionError(RuntimeError):
    """Stable M56 construction failure with bounded stage metadata."""

    def __init__(self, code: str, message: str, *, stage: str | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.stage = stage


def _fail(code: str, message: str, *, stage: str | None = None) -> None:
    raise InboundHttpResponsePreparerCompositionError(
        code,
        message,
        stage=stage,
    ) from None


def _class_identity_snapshot(value: type) -> tuple[tuple[str, int], ...]:
    return tuple(map(lambda item: (item[0], id(item[1])), value.__dict__.items()))


class BoundedInboundHttpResponsePreparerCompositionFactory:
    """Construct exactly one reviewed M36 -> M43 response-preparation graph."""

    __slots__ = (
        "_wire_adapter",
        "_application_adapter",
        "_wire_limits_object",
        "_application_limits_object",
        "_wire_authority",
        "_wire_limits_snapshot",
        "_application_limits_snapshot",
        "_application_handle_witness",
        "_clock",
        "_construction_graph",
        "_class_snapshot_function",
        "_m39_close_function",
        "_m39_closed_getter",
        "_m43_close_function",
        "_binding_witness",
        "_used",
    )

    def __init__(
        self,
        *,
        wire_adapter: BoundedInboundHttpWireAdapter,
        clock: Callable[[], float],
    ) -> None:
        if type(wire_adapter) is not BoundedInboundHttpWireAdapter:
            raise TypeError("wire_adapter MUST be exact BoundedInboundHttpWireAdapter")
        if not callable(clock):
            _fail("PREPARER_FACTORY_CLOCK_INVALID", "M56 clock MUST be callable")

        application_adapter = getattr(wire_adapter, "_application_adapter", None)
        wire_limits = getattr(wire_adapter, "_limits", None)
        wire_authority = getattr(wire_adapter, "_authority", None)
        if type(application_adapter) is not BoundedInboundHttpApplicationAdapter:
            _fail(
                "PREPARER_FACTORY_BINDING_DRIFT",
                "M56 M35 retained M34 application adapter is invalid",
            )
        if type(wire_limits) is not InboundHttpWireLimits:
            _fail(
                "PREPARER_FACTORY_CONFIGURATION_DRIFT",
                "M56 M35 wire limits are invalid",
            )
        if type(wire_authority) is not str or not wire_authority:
            _fail(
                "PREPARER_FACTORY_CONFIGURATION_DRIFT",
                "M56 M35 authority is invalid",
            )
        application_limits = getattr(application_adapter, "_limits", None)
        if type(application_limits) is not InboundHttpApplicationLimits:
            _fail(
                "PREPARER_FACTORY_CONFIGURATION_DRIFT",
                "M56 M34 application limits are invalid",
            )
        application_handle = getattr(application_adapter, "handle", None)
        if not callable(application_handle):
            _fail(
                "PREPARER_FACTORY_BINDING_DRIFT",
                "M56 M34 application handle is invalid",
            )
        handle_owner = getattr(application_handle, "__self__", None)
        handle_function = getattr(application_handle, "__func__", None)
        if handle_owner is not None and handle_function is not None:
            application_handle_witness = ("bound", handle_owner, handle_function)
        else:
            application_handle_witness = ("callable", application_handle)

        m39_closed_getter = BoundedInboundHttpReadSession.closed.fget
        if m39_closed_getter is None:
            _fail(
                "PREPARER_FACTORY_BINDING_DRIFT",
                "M56 M39 closed getter is unavailable",
            )

        class_snapshot_function = _class_identity_snapshot
        self._wire_adapter = wire_adapter
        self._application_adapter = application_adapter
        self._wire_limits_object = wire_limits
        self._application_limits_object = application_limits
        self._wire_authority = wire_authority
        self._wire_limits_snapshot = (
            wire_limits.max_header_bytes,
            wire_limits.max_body_bytes,
            wire_limits.max_response_body_bytes,
        )
        self._application_limits_snapshot = (
            application_limits.max_request_body_bytes,
            application_limits.max_response_body_bytes,
            application_limits.max_header_bytes,
        )
        self._application_handle_witness = application_handle_witness
        self._clock = clock
        self._class_snapshot_function = class_snapshot_function
        self._construction_graph = (
            _GRAPH_MARKER,
            BoundedInboundHttpApplicationAdapter,
            class_snapshot_function(BoundedInboundHttpApplicationAdapter),
            BoundedInboundHttpWireAdapter,
            class_snapshot_function(BoundedInboundHttpWireAdapter),
            BoundedInboundHttpStreamAssembler,
            class_snapshot_function(BoundedInboundHttpStreamAssembler),
            BoundedInboundHttpReadPlanner,
            class_snapshot_function(BoundedInboundHttpReadPlanner),
            BoundedInboundHttpReadTransitioner,
            class_snapshot_function(BoundedInboundHttpReadTransitioner),
            BoundedInboundHttpReadSession,
            class_snapshot_function(BoundedInboundHttpReadSession),
            BoundedInboundHttpReadOutcomeHandler,
            class_snapshot_function(BoundedInboundHttpReadOutcomeHandler),
            BoundedInboundHttpReadInvoker,
            class_snapshot_function(BoundedInboundHttpReadInvoker),
            BoundedInboundHttpReadDriver,
            class_snapshot_function(BoundedInboundHttpReadDriver),
            BoundedInboundHttpResponsePreparer,
            class_snapshot_function(BoundedInboundHttpResponsePreparer),
        )
        self._m39_close_function = BoundedInboundHttpReadSession.close
        self._m39_closed_getter = m39_closed_getter
        self._m43_close_function = BoundedInboundHttpResponsePreparer.close
        self._used = False
        self._binding_witness = (
            _BINDING_MARKER,
            self._wire_adapter,
            self._application_adapter,
            self._wire_limits_object,
            self._application_limits_object,
            self._wire_authority,
            self._wire_limits_snapshot,
            self._application_limits_snapshot,
            self._application_handle_witness,
            self._clock,
            self._construction_graph,
            self._class_snapshot_function,
            self._m39_close_function,
            self._m39_closed_getter,
            self._m43_close_function,
            BoundedInboundHttpResponsePreparerCompositionFactory._validate_construction_graph,
            BoundedInboundHttpResponsePreparerCompositionFactory._validate_retained_wire,
            BoundedInboundHttpResponsePreparerCompositionFactory._cleanup,
            BoundedInboundHttpResponsePreparerCompositionFactory.__call__,
        )
        self._validate_construction_graph()
        self._validate_retained_wire()

    def _validate_construction_graph(self) -> None:
        graph = self._construction_graph
        snapshot = self._class_snapshot_function
        if snapshot is not _class_identity_snapshot:
            _fail(
                "PREPARER_FACTORY_BINDING_DRIFT",
                "M56 class-snapshot authority changed",
            )
        if type(graph) is not tuple or len(graph) != 21 or graph[0] != _GRAPH_MARKER:
            _fail(
                "PREPARER_FACTORY_BINDING_DRIFT",
                "M56 construction graph witness changed",
            )
        if (
            graph[1] is not BoundedInboundHttpApplicationAdapter
            or graph[3] is not BoundedInboundHttpWireAdapter
            or graph[5] is not BoundedInboundHttpStreamAssembler
            or graph[7] is not BoundedInboundHttpReadPlanner
            or graph[9] is not BoundedInboundHttpReadTransitioner
            or graph[11] is not BoundedInboundHttpReadSession
            or graph[13] is not BoundedInboundHttpReadOutcomeHandler
            or graph[15] is not BoundedInboundHttpReadInvoker
            or graph[17] is not BoundedInboundHttpReadDriver
            or graph[19] is not BoundedInboundHttpResponsePreparer
        ):
            _fail(
                "PREPARER_FACTORY_BINDING_DRIFT",
                "M56 retained class graph changed",
            )
        if (
            graph[2] != snapshot(BoundedInboundHttpApplicationAdapter)
            or graph[4] != snapshot(BoundedInboundHttpWireAdapter)
            or graph[6] != snapshot(BoundedInboundHttpStreamAssembler)
            or graph[8] != snapshot(BoundedInboundHttpReadPlanner)
            or graph[10] != snapshot(BoundedInboundHttpReadTransitioner)
            or graph[12] != snapshot(BoundedInboundHttpReadSession)
            or graph[14] != snapshot(BoundedInboundHttpReadOutcomeHandler)
            or graph[16] != snapshot(BoundedInboundHttpReadInvoker)
            or graph[18] != snapshot(BoundedInboundHttpReadDriver)
            or graph[20] != snapshot(BoundedInboundHttpResponsePreparer)
        ):
            _fail(
                "PREPARER_FACTORY_BINDING_DRIFT",
                "M56 reviewed class identity graph changed",
            )

    def _validate_retained_wire(self) -> None:
        wire = self._wire_adapter
        application = self._application_adapter
        wire_limits = self._wire_limits_object
        application_limits = self._application_limits_object
        if type(wire) is not BoundedInboundHttpWireAdapter:
            _fail("PREPARER_FACTORY_BINDING_DRIFT", "M56 retained M35 adapter changed")
        if type(application) is not BoundedInboundHttpApplicationAdapter:
            _fail("PREPARER_FACTORY_BINDING_DRIFT", "M56 retained M34 adapter changed")
        if getattr(wire, "_application_adapter", None) is not application:
            _fail("PREPARER_FACTORY_BINDING_DRIFT", "M56 M35 to M34 binding changed")
        current_wire_limits = getattr(wire, "_limits", None)
        current_application_limits = getattr(application, "_limits", None)
        if type(current_wire_limits) is not InboundHttpWireLimits:
            _fail("PREPARER_FACTORY_CONFIGURATION_DRIFT", "M56 retained M35 limits changed type")
        if type(current_application_limits) is not InboundHttpApplicationLimits:
            _fail("PREPARER_FACTORY_CONFIGURATION_DRIFT", "M56 retained M34 limits changed type")
        authority = getattr(wire, "_authority", None)
        if type(authority) is not str or authority != self._wire_authority:
            _fail("PREPARER_FACTORY_CONFIGURATION_DRIFT", "M56 retained M35 authority changed")
        if (
            current_wire_limits.max_header_bytes,
            current_wire_limits.max_body_bytes,
            current_wire_limits.max_response_body_bytes,
        ) != self._wire_limits_snapshot:
            _fail("PREPARER_FACTORY_CONFIGURATION_DRIFT", "M56 retained M35 limits changed")
        if (
            current_application_limits.max_request_body_bytes,
            current_application_limits.max_response_body_bytes,
            current_application_limits.max_header_bytes,
        ) != self._application_limits_snapshot:
            _fail("PREPARER_FACTORY_CONFIGURATION_DRIFT", "M56 retained M34 limits changed")
        if current_wire_limits is not wire_limits:
            _fail("PREPARER_FACTORY_BINDING_DRIFT", "M56 retained M35 limits object changed")
        if current_application_limits is not application_limits:
            _fail("PREPARER_FACTORY_BINDING_DRIFT", "M56 retained M34 limits object changed")
        handle = getattr(application, "handle", None)
        handle_witness = self._application_handle_witness
        if type(handle_witness) is not tuple or len(handle_witness) not in (2, 3):
            _fail("PREPARER_FACTORY_BINDING_DRIFT", "M56 retained M34 handle witness changed")
        if handle_witness[0] == "bound":
            if (
                len(handle_witness) != 3
                or getattr(handle, "__self__", None) is not handle_witness[1]
                or getattr(handle, "__func__", None) is not handle_witness[2]
            ):
                _fail("PREPARER_FACTORY_BINDING_DRIFT", "M56 retained M34 handle changed")
        elif handle_witness[0] == "callable":
            if len(handle_witness) != 2 or handle is not handle_witness[1]:
                _fail("PREPARER_FACTORY_BINDING_DRIFT", "M56 retained M34 handle changed")
        else:
            _fail("PREPARER_FACTORY_BINDING_DRIFT", "M56 retained M34 handle witness changed")

    def _cleanup(
        self,
        *,
        session: BoundedInboundHttpReadSession | None,
        preparer: BoundedInboundHttpResponsePreparer | None,
    ) -> None:
        close_session = self._m39_close_function
        closed_getter = self._m39_closed_getter
        close_preparer = self._m43_close_function
        try:
            if type(preparer) is BoundedInboundHttpResponsePreparer:
                close_preparer(preparer)
            elif type(session) is BoundedInboundHttpReadSession:
                close_session(session)
            if type(session) is BoundedInboundHttpReadSession:
                if closed_getter(session) is not True:
                    _fail(
                        "PREPARER_FACTORY_CLEANUP_UNCERTAIN",
                        "M56 partial read session did not close",
                    )
        except InboundHttpResponsePreparerCompositionError:
            raise
        except Exception:
            _fail(
                "PREPARER_FACTORY_CLEANUP_UNCERTAIN",
                "M56 partial read graph cleanup could not be verified",
            )

    def __call__(
        self,
        reader: Callable[[int], InboundHttpReadOutcome],
    ) -> BoundedInboundHttpResponsePreparer:
        if self._used:
            _fail(
                "PREPARER_FACTORY_EXHAUSTED",
                "M56 response preparer factory is one-shot",
            )
        object.__setattr__(self, "_used", True)

        try:
            witness = self._binding_witness
            if (
                type(self) is not BoundedInboundHttpResponsePreparerCompositionFactory
                or type(witness) is not tuple
                or len(witness) != 19
                or witness[0] != _BINDING_MARKER
                or witness[1] is not self._wire_adapter
                or witness[2] is not self._application_adapter
                or witness[3] is not self._wire_limits_object
                or witness[4] is not self._application_limits_object
                or witness[5] != self._wire_authority
                or witness[6] is not self._wire_limits_snapshot
                or witness[7] is not self._application_limits_snapshot
                or witness[8] is not self._application_handle_witness
                or witness[9] is not self._clock
                or witness[10] is not self._construction_graph
                or witness[11] is not self._class_snapshot_function
                or witness[12] is not self._m39_close_function
                or witness[13] is not self._m39_closed_getter
                or witness[14] is not self._m43_close_function
            ):
                _fail(
                    "PREPARER_FACTORY_BINDING_DRIFT",
                    "M56 factory binding witness changed",
                )
            validate_graph = witness[15]
            validate_retained = witness[16]
            cleanup = witness[17]
            call_function = witness[18]
            if (
                validate_graph
                is not BoundedInboundHttpResponsePreparerCompositionFactory._validate_construction_graph
                or validate_retained
                is not BoundedInboundHttpResponsePreparerCompositionFactory._validate_retained_wire
                or cleanup
                is not BoundedInboundHttpResponsePreparerCompositionFactory._cleanup
                or call_function
                is not BoundedInboundHttpResponsePreparerCompositionFactory.__call__
            ):
                _fail(
                    "PREPARER_FACTORY_BINDING_DRIFT",
                    "M56 factory helper graph changed",
                )

            validate_graph(self)
            validate_retained(self)
            wire_adapter = witness[1]
            clock = witness[9]
            session = None
            preparer = None
            stage = "M36"

            if not callable(reader):
                _fail(
                    "PREPARER_FACTORY_READER_INVALID",
                    "M56 reader MUST be callable",
                )

            try:
                stream = BoundedInboundHttpStreamAssembler(
                    wire_adapter=wire_adapter,
                )
                validate_graph(self)
                validate_retained(self)
                stage = "M37"
                planner = BoundedInboundHttpReadPlanner(
                    stream_assembler=stream,
                )
                validate_graph(self)
                validate_retained(self)
                stage = "M38"
                transitioner = BoundedInboundHttpReadTransitioner(
                    read_planner=planner,
                )
                validate_graph(self)
                validate_retained(self)
                stage = "M39"
                session = BoundedInboundHttpReadSession(
                    read_transitioner=transitioner,
                )
                validate_graph(self)
                validate_retained(self)
                stage = "M40"
                handler = BoundedInboundHttpReadOutcomeHandler(
                    read_session=session,
                )
                validate_graph(self)
                validate_retained(self)
                stage = "M41"
                invoker = BoundedInboundHttpReadInvoker(
                    read_outcome_handler=handler,
                    reader=reader,
                )
                validate_graph(self)
                validate_retained(self)
                stage = "M42"
                driver = BoundedInboundHttpReadDriver(
                    read_invoker=invoker,
                    clock=clock,
                )
                validate_graph(self)
                validate_retained(self)
                stage = "M43"
                preparer = BoundedInboundHttpResponsePreparer(
                    read_driver=driver,
                )
                validate_graph(self)
                validate_retained(self)
            except InboundHttpResponsePreparerCompositionError:
                cleanup(self, session=session, preparer=preparer)
                raise
            except Exception:
                cleanup(self, session=session, preparer=preparer)
                _fail(
                    "PREPARER_FACTORY_CONSTRUCTION_FAILED",
                    "M56 reviewed response-preparation graph construction failed",
                    stage=stage,
                )

            return preparer
        finally:
            object.__setattr__(self, "_wire_adapter", None)
            object.__setattr__(self, "_application_adapter", None)
            object.__setattr__(self, "_wire_limits_object", None)
            object.__setattr__(self, "_application_limits_object", None)
            object.__setattr__(self, "_wire_authority", None)
            object.__setattr__(self, "_wire_limits_snapshot", None)
            object.__setattr__(self, "_application_limits_snapshot", None)
            object.__setattr__(self, "_application_handle_witness", None)
            object.__setattr__(self, "_clock", None)
            object.__setattr__(self, "_construction_graph", None)
            object.__setattr__(self, "_class_snapshot_function", None)
            object.__setattr__(self, "_m39_close_function", None)
            object.__setattr__(self, "_m39_closed_getter", None)
            object.__setattr__(self, "_m43_close_function", None)
            object.__setattr__(self, "_binding_witness", None)
