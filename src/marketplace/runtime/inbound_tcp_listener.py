"""Bounded source-only construction of one inbound TCP listener capability.

M53 never imports or creates an operating-system socket. It applies one
loopback-only endpoint configuration to one caller-supplied deterministic
listener factory and transfers the configured capability into exact M52.
"""
from __future__ import annotations

from typing import Protocol

from .inbound_http_accept import BoundedInboundHttpSingleAccept

__all__ = [
    "BoundedInboundTcpListenerConstruction",
    "InboundTcpListenerCapability",
    "InboundTcpListenerConstructionError",
    "InboundTcpListenerFactory",
]

_LOOPBACK_HOST = "127.0.0.1"
_MIN_PORT = 1024
_MAX_PORT = 65535
_EXACT_BACKLOG = 1


class InboundTcpListenerCapability(Protocol):
    """Injected listener-shaped capability used only through deterministic tests."""

    def bind(self, address: tuple[str, int]) -> None: ...
    def listen(self, backlog: int) -> None: ...
    def accept(self): ...
    def close(self) -> None: ...


class InboundTcpListenerFactory(Protocol):
    """Caller-supplied constructor for one listener capability."""

    def __call__(self) -> InboundTcpListenerCapability: ...


class InboundTcpListenerConstructionError(RuntimeError):
    """Stable M53 failure without reflecting arbitrary caller exception text."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def _fail(code: str, message: str) -> None:
    raise InboundTcpListenerConstructionError(code, message)


def _same_callable(current: object, captured: object) -> bool:
    current_self = getattr(current, "__self__", None)
    captured_self = getattr(captured, "__self__", None)
    current_func = getattr(current, "__func__", None)
    captured_func = getattr(captured, "__func__", None)
    if current_func is not None or captured_func is not None:
        return current_self is captured_self and current_func is captured_func
    return current is captured


def _close_untrusted_listener(listener: object) -> bool:
    try:
        close = getattr(listener, "close", None)
    except Exception:
        return False
    if not callable(close):
        return False
    try:
        close()
    except Exception:
        return False
    return True


def _capture_listener(listener: object) -> tuple[object, ...]:
    try:
        bind = getattr(listener, "bind", None)
        listen = getattr(listener, "listen", None)
        accept = getattr(listener, "accept", None)
        close = getattr(listener, "close", None)
    except Exception:
        _fail("LISTENER_INTERFACE_UNVERIFIABLE", "M53 listener interface could not be inspected")
    if not all(callable(value) for value in (bind, listen, accept, close)):
        _fail("LISTENER_INTERFACE_INVALID", "M53 listener MUST expose bind, listen, accept, and close")
    return (
        "inbound-tcp-listener-capability-v1",
        listener,
        bind,
        listen,
        accept,
        close,
    )


def _validate_listener_bindings(witness: tuple[object, ...]) -> None:
    if type(witness) is not tuple or len(witness) != 6:
        _fail("LISTENER_BINDING_DRIFT", "M53 listener binding witness changed")
    listener = witness[1]
    for name, captured in (
        ("bind", witness[2]),
        ("listen", witness[3]),
        ("accept", witness[4]),
        ("close", witness[5]),
    ):
        try:
            current = getattr(listener, name, None)
            same = callable(current) and _same_callable(current, captured)
        except Exception:
            _fail(
                "LISTENER_METHOD_BINDING_UNVERIFIABLE",
                f"M53 listener {name} binding could not be verified",
            )
        if not same:
            _fail(
                "LISTENER_METHOD_BINDING_DRIFT",
                f"M53 listener {name} binding changed",
            )


def _close_captured_listener(witness: tuple[object, ...]) -> None:
    close = witness[5] if type(witness) is tuple and len(witness) == 6 else None
    if not callable(close):
        _fail(
            "LISTENER_CLEANUP_UNCERTAIN",
            "M53 original listener cleanup binding is unavailable",
        )
    try:
        close()
    except Exception:
        _fail("LISTENER_CLEANUP_UNCERTAIN", "M53 could not verify listener cleanup")


class BoundedInboundTcpListenerConstruction:
    """Configure one injected listener and transfer it directly into exact M52."""

    __slots__ = (
        "_factory",
        "_factory_type",
        "_factory_call",
        "_host",
        "_port",
        "_backlog",
        "_m52_class",
        "_construct_once_function",
        "_close_function",
        "_binding_witness",
        "_construct_attempted",
        "_closed",
        "_transferred",
    )

    def __init__(
        self,
        *,
        factory: InboundTcpListenerFactory,
        host: str,
        port: int,
        backlog: int = _EXACT_BACKLOG,
    ) -> None:
        if not callable(factory):
            _fail("LISTENER_FACTORY_INVALID", "M53 listener factory MUST be callable")
        factory_type = type(factory)
        try:
            factory_call = getattr(factory_type, "__call__", None)
        except Exception:
            _fail("LISTENER_FACTORY_BINDING_UNVERIFIABLE", "M53 factory call binding could not be inspected")
        if not callable(factory_call):
            _fail("LISTENER_FACTORY_INVALID", "M53 listener factory call binding is invalid")
        if type(host) is not str or host != _LOOPBACK_HOST:
            _fail("LISTENER_HOST_FORBIDDEN", "M53 host MUST be exact IPv4 loopback")
        if type(port) is not int or not (_MIN_PORT <= port <= _MAX_PORT):
            _fail("LISTENER_PORT_INVALID", "M53 port MUST be an explicit non-privileged TCP port")
        if type(backlog) is not int or backlog != _EXACT_BACKLOG:
            _fail("LISTENER_BACKLOG_INVALID", "M53 backlog MUST be exactly one")
        self._factory = factory
        self._factory_type = factory_type
        self._factory_call = factory_call
        self._host = host
        self._port = port
        self._backlog = backlog
        self._m52_class = BoundedInboundHttpSingleAccept
        self._construct_once_function = BoundedInboundTcpListenerConstruction.construct_once
        self._close_function = BoundedInboundTcpListenerConstruction.close
        self._binding_witness = self._binding_snapshot()
        self._construct_attempted = False
        self._closed = False
        self._transferred = False
        self._validate_bindings()

    @property
    def used(self) -> bool:
        return self._construct_attempted

    @property
    def closed(self) -> bool:
        return self._closed

    @property
    def transferred(self) -> bool:
        return self._transferred

    def _binding_snapshot(self) -> tuple[object, ...]:
        return (
            "inbound-tcp-listener-construction-v1",
            self._factory,
            self._factory_type,
            self._factory_call,
            self._host,
            self._port,
            self._backlog,
            self._m52_class,
            self._construct_once_function,
            self._close_function,
        )

    def _validate_bindings(self) -> None:
        witness = self._binding_witness
        if (
            type(witness) is not tuple
            or len(witness) != 10
            or witness[0] != "inbound-tcp-listener-construction-v1"
            or witness[1] is not self._factory
            or witness[2] is not self._factory_type
            or witness[3] is not self._factory_call
            or witness[4] is not self._host
            or witness[5] is not self._port
            or witness[6] is not self._backlog
            or witness[7] is not self._m52_class
            or witness[8] is not self._construct_once_function
            or witness[9] is not self._close_function
        ):
            _fail("LISTENER_CONSTRUCTION_BINDING_DRIFT", "M53 construction binding witness changed")
        if type(self._factory) is not self._factory_type:
            _fail("LISTENER_FACTORY_BINDING_DRIFT", "M53 factory type binding changed")
        try:
            current_factory_call = getattr(self._factory_type, "__call__", None)
        except Exception:
            _fail("LISTENER_FACTORY_BINDING_UNVERIFIABLE", "M53 factory call binding could not be verified")
        if current_factory_call is not self._factory_call:
            _fail("LISTENER_FACTORY_BINDING_DRIFT", "M53 factory call binding changed")
        if type(self) is not BoundedInboundTcpListenerConstruction:
            _fail("LISTENER_CONSTRUCTION_BINDING_DRIFT", "M53 construction boundary changed type")
        if (
            BoundedInboundTcpListenerConstruction.construct_once is not self._construct_once_function
            or BoundedInboundTcpListenerConstruction.close is not self._close_function
        ):
            _fail("LISTENER_CONSTRUCTION_BINDING_DRIFT", "M53 construction method graph changed")
        if BoundedInboundHttpSingleAccept is not self._m52_class:
            _fail("LISTENER_CONSTRUCTION_BINDING_DRIFT", "M53 M52 class binding changed")
        if self._factory is None:
            _fail("LISTENER_CONSTRUCTION_BINDING_DRIFT", "M53 factory reference is unavailable")

    def _release(self) -> None:
        self._factory = None
        self._factory_type = None
        self._factory_call = None
        self._host = None
        self._port = None
        self._backlog = None
        self._binding_witness = None
        self._closed = True

    def _cleanup_and_raise(
        self,
        witness: tuple[object, ...],
        code: str,
        message: str,
    ) -> None:
        try:
            _close_captured_listener(witness)
        except InboundTcpListenerConstructionError:
            self._release()
            raise
        self._release()
        _fail(code, message)

    def construct_once(self) -> BoundedInboundHttpSingleAccept:
        if self._construct_attempted or self._closed:
            _fail("LISTENER_CONSTRUCTION_USED", "M53 construction boundary is already terminal")
        self._construct_attempted = True
        self._validate_bindings()

        try:
            listener = self._factory_call(self._factory)
        except Exception:
            self._release()
            _fail("LISTENER_FACTORY_FAILED", "M53 listener factory failed")

        if listener is self._factory:
            closed = _close_untrusted_listener(listener)
            self._release()
            if not closed:
                _fail("LISTENER_CLEANUP_UNCERTAIN", "M53 could not verify aliased listener cleanup")
            _fail("LISTENER_FACTORY_ALIASES_LISTENER", "M53 factory MUST NOT return itself")

        try:
            listener_witness = _capture_listener(listener)
        except InboundTcpListenerConstructionError as interface_error:
            closed = _close_untrusted_listener(listener)
            self._release()
            if not closed:
                _fail("LISTENER_CLEANUP_UNCERTAIN", "M53 could not verify invalid listener cleanup")
            raise interface_error

        self._validate_bindings()
        try:
            _validate_listener_bindings(listener_witness)
        except InboundTcpListenerConstructionError as binding_error:
            self._cleanup_and_raise(
                listener_witness,
                binding_error.code,
                str(binding_error),
            )

        try:
            listener_witness[2]((self._host, self._port))
        except Exception:
            try:
                _validate_listener_bindings(listener_witness)
            except InboundTcpListenerConstructionError as binding_error:
                self._cleanup_and_raise(listener_witness, binding_error.code, str(binding_error))
            self._cleanup_and_raise(
                listener_witness,
                "LISTENER_BIND_FAILED",
                "M53 listener bind failed",
            )
        try:
            _validate_listener_bindings(listener_witness)
            self._validate_bindings()
        except InboundTcpListenerConstructionError as binding_error:
            self._cleanup_and_raise(listener_witness, binding_error.code, str(binding_error))

        try:
            listener_witness[3](self._backlog)
        except Exception:
            try:
                _validate_listener_bindings(listener_witness)
            except InboundTcpListenerConstructionError as binding_error:
                self._cleanup_and_raise(listener_witness, binding_error.code, str(binding_error))
            self._cleanup_and_raise(
                listener_witness,
                "LISTENER_LISTEN_FAILED",
                "M53 listener listen failed",
            )

        try:
            _validate_listener_bindings(listener_witness)
            self._validate_bindings()
        except InboundTcpListenerConstructionError as binding_error:
            self._cleanup_and_raise(listener_witness, binding_error.code, str(binding_error))

        try:
            accept_boundary = self._m52_class(acceptor=listener)
        except Exception:
            self._cleanup_and_raise(
                listener_witness,
                "M52_HANDOFF_FAILED",
                "M53 could not transfer listener capability into exact M52",
            )

        self._transferred = True
        self._release()
        return accept_boundary

    def close(self) -> None:
        if self._closed:
            return
        if self._construct_attempted:
            return
        self._validate_bindings()
        self._release()
