"""Bounded Python TCP socket-constructor adapter for exact M53.

M54 fixes constructor arguments to the Python standard-library IPv4 TCP stream
profile while requiring the constructor capability itself to be supplied by the
caller. Source acceptance uses deterministic constructor doubles only; invoking
a real operating-system socket constructor is a separate NETWORK_EXTERNAL act.
"""
from __future__ import annotations

from socket import AF_INET as _AF_INET
from socket import IPPROTO_TCP as _IPPROTO_TCP
from socket import SOCK_STREAM as _SOCK_STREAM
from typing import Protocol, runtime_checkable

__all__ = [
    "BoundedPythonTcpSocketFactory",
    "PythonTcpSocketConstructor",
    "PythonTcpSocketFactoryError",
]


@runtime_checkable
class PythonTcpSocketConstructor(Protocol):
    """Explicit constructor capability compatible with Python TCP sockets."""

    def __call__(self, family: object, kind: object, protocol: object) -> object: ...


class PythonTcpSocketFactoryError(RuntimeError):
    """Stable M54 failure without reflecting arbitrary constructor text."""
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def _fail(code: str, message: str) -> None:
    raise PythonTcpSocketFactoryError(code, message)


class BoundedPythonTcpSocketFactory:
    """Adapt one explicit constructor into M53's zero-argument factory shape."""

    __slots__ = (
        "_constructor",
        "_constructor_type",
        "_constructor_call",
        "_family",
        "_kind",
        "_protocol",
        "_call_function",
        "_binding_witness",
        "_attempted",
        "_closed",
    )

    def __init__(self, *, constructor: PythonTcpSocketConstructor) -> None:
        if not callable(constructor):
            _fail("SOCKET_CONSTRUCTOR_INVALID", "M54 socket constructor MUST be callable")

        constructor_type = type(constructor)
        try:
            constructor_call = getattr(constructor_type, "__call__", None)
        except Exception:
            _fail(
                "SOCKET_CONSTRUCTOR_BINDING_UNVERIFIABLE",
                "M54 socket constructor binding could not be inspected",
            )
        if not callable(constructor_call):
            _fail(
                "SOCKET_CONSTRUCTOR_INVALID",
                "M54 socket constructor call binding is invalid",
            )

        self._constructor = constructor
        self._constructor_type = constructor_type
        self._constructor_call = constructor_call
        self._family = _AF_INET
        self._kind = _SOCK_STREAM
        self._protocol = _IPPROTO_TCP
        self._call_function = BoundedPythonTcpSocketFactory.__call__
        self._binding_witness = self._binding_snapshot()
        self._attempted = False
        self._closed = False
        self._validate_bindings()

    @property
    def used(self) -> bool:
        return self._attempted

    @property
    def closed(self) -> bool:
        return self._closed

    def _binding_snapshot(self) -> tuple[object, ...]:
        return (
            "python-tcp-socket-factory-v1",
            self._constructor,
            self._constructor_type,
            self._constructor_call,
            self._family,
            self._kind,
            self._protocol,
            self._call_function,
        )

    def _validate_bindings(self) -> None:
        witness = self._binding_witness
        if (
            type(witness) is not tuple
            or len(witness) != 8
            or witness[0] != "python-tcp-socket-factory-v1"
            or witness[1] is not self._constructor
            or witness[2] is not self._constructor_type
            or witness[3] is not self._constructor_call
            or witness[4] is not self._family
            or witness[5] is not self._kind
            or witness[6] is not self._protocol
            or witness[7] is not self._call_function
        ):
            _fail(
                "SOCKET_FACTORY_BINDING_DRIFT",
                "M54 socket factory binding witness changed",
            )
        if type(self) is not BoundedPythonTcpSocketFactory:
            _fail(
                "SOCKET_FACTORY_BINDING_DRIFT",
                "M54 socket factory changed type",
            )
        if BoundedPythonTcpSocketFactory.__call__ is not self._call_function:
            _fail(
                "SOCKET_FACTORY_BINDING_DRIFT",
                "M54 socket factory call graph changed",
            )
        if type(self._constructor) is not self._constructor_type:
            _fail(
                "SOCKET_CONSTRUCTOR_BINDING_DRIFT",
                "M54 socket constructor type binding changed",
            )
        try:
            current_call = getattr(self._constructor_type, "__call__", None)
        except Exception:
            _fail(
                "SOCKET_CONSTRUCTOR_BINDING_UNVERIFIABLE",
                "M54 socket constructor binding could not be verified",
            )
        if current_call is not self._constructor_call:
            _fail(
                "SOCKET_CONSTRUCTOR_BINDING_DRIFT",
                "M54 socket constructor call binding changed",
            )

    def _release(self) -> None:
        self._constructor = None
        self._constructor_type = None
        self._constructor_call = None
        self._family = None
        self._kind = None
        self._protocol = None
        self._binding_witness = None
        self._closed = True

    def __call__(self) -> object:
        if self._attempted or self._closed:
            _fail("SOCKET_FACTORY_USED", "M54 socket factory is already terminal")
        self._attempted = True
        try:
            self._validate_bindings()
        except PythonTcpSocketFactoryError:
            self._release()
            raise

        witness = self._binding_witness
        constructor = witness[1]
        constructor_call = witness[3]
        try:
            listener = constructor_call(
                constructor,
                witness[4],
                witness[5],
                witness[6],
            )
        except Exception:
            self._release()
            _fail("SOCKET_CONSTRUCTOR_FAILED", "M54 socket constructor failed")

        if listener is self:
            self._release()
            _fail(
                "SOCKET_CONSTRUCTOR_ALIASES_FACTORY",
                "M54 socket constructor MUST NOT return the factory",
            )
        if listener is constructor:
            self._release()
            _fail(
                "SOCKET_CONSTRUCTOR_ALIASES_CONSTRUCTOR",
                "M54 socket constructor MUST NOT return itself",
            )

        self._release()
        return listener
