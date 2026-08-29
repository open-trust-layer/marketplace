from __future__ import annotations

import unittest

from marketplace.runtime.inbound_http_accept import BoundedInboundHttpSingleAccept
from marketplace.runtime.inbound_tcp_listener import BoundedInboundTcpListenerConstruction


class _Listener:
    def __init__(self) -> None:
        self.bind_calls: list[tuple[str, int]] = []
        self.listen_calls: list[int] = []
        self.close_calls = 0

    def bind(self, address: tuple[str, int]) -> None:
        self.bind_calls.append(address)

    def listen(self, backlog: int) -> None:
        self.listen_calls.append(backlog)

    def accept(self):
        raise AssertionError("source acceptance MUST NOT call accept")

    def close(self) -> None:
        self.close_calls += 1


class InboundTcpListenerConstructionTests(unittest.TestCase):
    def test_construct_once_binds_listens_and_returns_exact_m52_boundary(self):
        listener = _Listener()
        factory_calls: list[object] = []

        def factory():
            factory_calls.append(object())
            return listener

        boundary = BoundedInboundTcpListenerConstruction(
            factory=factory,
            host="127.0.0.1",
            port=18443,
            backlog=1,
        )

        accept_boundary = boundary.construct_once()

        self.assertIs(type(accept_boundary), BoundedInboundHttpSingleAccept)
        self.assertEqual(len(factory_calls), 1)
        self.assertEqual(listener.bind_calls, [("127.0.0.1", 18443)])
        self.assertEqual(listener.listen_calls, [1])
        self.assertEqual(listener.close_calls, 0)


if __name__ == "__main__":
    unittest.main()


class _ConfigurableListener(_Listener):
    def __init__(self) -> None:
        super().__init__()
        self.bind_exception: Exception | None = None
        self.listen_exception: Exception | None = None
        self.close_exception: Exception | None = None
        self.mutate_on_bind = None
        self.mutate_on_listen = None

    def bind(self, address: tuple[str, int]) -> None:
        self.bind_calls.append(address)
        if self.mutate_on_bind is not None:
            self.mutate_on_bind(self)
        if self.bind_exception is not None:
            raise self.bind_exception

    def listen(self, backlog: int) -> None:
        self.listen_calls.append(backlog)
        if self.mutate_on_listen is not None:
            self.mutate_on_listen(self)
        if self.listen_exception is not None:
            raise self.listen_exception

    def close(self) -> None:
        self.close_calls += 1
        if self.close_exception is not None:
            raise self.close_exception


class _InvalidListener:
    def __init__(self) -> None:
        self.close_calls = 0

    def bind(self, address: tuple[str, int]) -> None:
        return None

    def close(self) -> None:
        self.close_calls += 1


class _HostileLookupListener(_ConfigurableListener):
    def __init__(self) -> None:
        super().__init__()
        self.hostile_lookup = False

    def __getattribute__(self, name: str):
        if name in {"bind", "listen", "accept"} and object.__getattribute__(self, "hostile_lookup"):
            raise RuntimeError("TOP-SECRET-LISTENER-LOOKUP")
        return object.__getattribute__(self, name)


class _HostileCloseLookupListener(_InvalidListener):
    def __getattribute__(self, name: str):
        if name == "close":
            raise RuntimeError("TOP-SECRET-CLOSE-LOOKUP")
        return object.__getattribute__(self, name)


import ast
import inspect
import pathlib

import marketplace.runtime.inbound_tcp_listener as listener_module
from marketplace.runtime.inbound_tcp_listener import InboundTcpListenerConstructionError

ROOT = pathlib.Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src/marketplace/runtime/inbound_tcp_listener.py"


class InboundTcpListenerConstructionSecurityTests(unittest.TestCase):
    def _boundary(self, listener: object, **overrides):
        values = {
            "factory": lambda: listener,
            "host": "127.0.0.1",
            "port": 18443,
            "backlog": 1,
        }
        values.update(overrides)
        return BoundedInboundTcpListenerConstruction(**values)

    def test_configuration_is_loopback_explicit_port_and_single_backlog_only(self):
        listener = _ConfigurableListener()
        for host in ("0.0.0.0", "localhost", "::1", "127.0.0.1 "):
            with self.assertRaises(InboundTcpListenerConstructionError) as caught:
                self._boundary(listener, host=host)
            self.assertEqual(caught.exception.code, "LISTENER_HOST_FORBIDDEN")
        for port in (True, 0, 1023, 65536, "18443"):
            with self.assertRaises(InboundTcpListenerConstructionError) as caught:
                self._boundary(listener, port=port)
            self.assertEqual(caught.exception.code, "LISTENER_PORT_INVALID")
        for backlog in (True, 0, 2, "1"):
            with self.assertRaises(InboundTcpListenerConstructionError) as caught:
                self._boundary(listener, backlog=backlog)
            self.assertEqual(caught.exception.code, "LISTENER_BACKLOG_INVALID")
        self.assertEqual(listener.bind_calls, [])
        self.assertEqual(listener.listen_calls, [])

    def test_factory_must_be_callable(self):
        with self.assertRaises(InboundTcpListenerConstructionError) as caught:
            BoundedInboundTcpListenerConstruction(
                factory=object(), host="127.0.0.1", port=18443, backlog=1
            )
        self.assertEqual(caught.exception.code, "LISTENER_FACTORY_INVALID")

    def test_close_before_construct_is_idempotent_and_never_calls_factory(self):
        listener = _ConfigurableListener()
        calls = []
        boundary = self._boundary(listener, factory=lambda: calls.append(1) or listener)
        boundary.close()
        boundary.close()
        self.assertEqual(calls, [])
        self.assertTrue(boundary.closed)
        with self.assertRaises(InboundTcpListenerConstructionError) as caught:
            boundary.construct_once()
        self.assertEqual(caught.exception.code, "LISTENER_CONSTRUCTION_USED")

    def test_success_releases_m53_references_and_is_one_shot(self):
        listener = _ConfigurableListener()
        boundary = self._boundary(listener)
        accept_boundary = boundary.construct_once()
        self.assertIs(type(accept_boundary), BoundedInboundHttpSingleAccept)
        self.assertTrue(boundary.used)
        self.assertTrue(boundary.closed)
        self.assertTrue(boundary.transferred)
        self.assertIsNone(boundary._factory)
        self.assertIsNone(boundary._host)
        self.assertIsNone(boundary._port)
        self.assertIsNone(boundary._backlog)
        self.assertIsNone(boundary._binding_witness)
        with self.assertRaises(InboundTcpListenerConstructionError) as caught:
            boundary.construct_once()
        self.assertEqual(caught.exception.code, "LISTENER_CONSTRUCTION_USED")
        self.assertEqual(listener.bind_calls, [("127.0.0.1", 18443)])
        self.assertEqual(listener.listen_calls, [1])
        accept_boundary.close()
        self.assertEqual(listener.close_calls, 1)

    def test_factory_exception_is_redacted_and_terminal(self):
        def factory():
            raise RuntimeError("TOP-SECRET-FACTORY")

        boundary = self._boundary(_ConfigurableListener(), factory=factory)
        with self.assertRaises(InboundTcpListenerConstructionError) as caught:
            boundary.construct_once()
        self.assertEqual(caught.exception.code, "LISTENER_FACTORY_FAILED")
        self.assertNotIn("TOP-SECRET", str(caught.exception))
        self.assertTrue(boundary.closed)

    def test_invalid_listener_is_closed_once(self):
        listener = _InvalidListener()
        boundary = self._boundary(listener)
        with self.assertRaises(InboundTcpListenerConstructionError) as caught:
            boundary.construct_once()
        self.assertEqual(caught.exception.code, "LISTENER_INTERFACE_INVALID")
        self.assertEqual(listener.close_calls, 1)

    def test_hostile_listener_lookup_is_redacted_and_closed(self):
        listener = _HostileLookupListener()
        listener.hostile_lookup = True
        boundary = self._boundary(listener)
        with self.assertRaises(InboundTcpListenerConstructionError) as caught:
            boundary.construct_once()
        self.assertEqual(caught.exception.code, "LISTENER_INTERFACE_UNVERIFIABLE")
        self.assertNotIn("TOP-SECRET", str(caught.exception))
        self.assertEqual(listener.close_calls, 1)

    def test_invalid_listener_with_hostile_close_lookup_is_cleanup_uncertain(self):
        listener = _HostileCloseLookupListener()
        boundary = self._boundary(listener)
        with self.assertRaises(InboundTcpListenerConstructionError) as caught:
            boundary.construct_once()
        self.assertEqual(caught.exception.code, "LISTENER_CLEANUP_UNCERTAIN")
        self.assertNotIn("TOP-SECRET", str(caught.exception))

    def test_bind_exception_is_redacted_closes_once_and_never_listens(self):
        listener = _ConfigurableListener()
        listener.bind_exception = RuntimeError("TOP-SECRET-BIND")
        boundary = self._boundary(listener)
        with self.assertRaises(InboundTcpListenerConstructionError) as caught:
            boundary.construct_once()
        self.assertEqual(caught.exception.code, "LISTENER_BIND_FAILED")
        self.assertNotIn("TOP-SECRET", str(caught.exception))
        self.assertEqual(listener.bind_calls, [("127.0.0.1", 18443)])
        self.assertEqual(listener.listen_calls, [])
        self.assertEqual(listener.close_calls, 1)

    def test_listen_exception_is_redacted_and_closes_once(self):
        listener = _ConfigurableListener()
        listener.listen_exception = RuntimeError("TOP-SECRET-LISTEN")
        boundary = self._boundary(listener)
        with self.assertRaises(InboundTcpListenerConstructionError) as caught:
            boundary.construct_once()
        self.assertEqual(caught.exception.code, "LISTENER_LISTEN_FAILED")
        self.assertNotIn("TOP-SECRET", str(caught.exception))
        self.assertEqual(listener.close_calls, 1)

    def test_cleanup_failure_is_uncertain_and_never_retried(self):
        listener = _ConfigurableListener()
        listener.bind_exception = RuntimeError("bind")
        listener.close_exception = RuntimeError("TOP-SECRET-CLOSE")
        boundary = self._boundary(listener)
        with self.assertRaises(InboundTcpListenerConstructionError) as caught:
            boundary.construct_once()
        self.assertEqual(caught.exception.code, "LISTENER_CLEANUP_UNCERTAIN")
        self.assertNotIn("TOP-SECRET", str(caught.exception))
        self.assertEqual(listener.close_calls, 1)
        boundary.close()
        self.assertEqual(listener.close_calls, 1)

    def test_bind_method_rebinding_is_detected_and_original_close_is_used(self):
        listener = _ConfigurableListener()
        listener.mutate_on_bind = lambda current: setattr(
            current, "bind", lambda address: None
        )
        boundary = self._boundary(listener)
        with self.assertRaises(InboundTcpListenerConstructionError) as caught:
            boundary.construct_once()
        self.assertEqual(caught.exception.code, "LISTENER_METHOD_BINDING_DRIFT")
        self.assertEqual(listener.bind_calls, [("127.0.0.1", 18443)])
        self.assertEqual(listener.listen_calls, [])
        self.assertEqual(listener.close_calls, 1)

    def test_listen_method_rebinding_is_detected_and_closed(self):
        listener = _ConfigurableListener()
        listener.mutate_on_listen = lambda current: setattr(
            current, "listen", lambda backlog: None
        )
        boundary = self._boundary(listener)
        with self.assertRaises(InboundTcpListenerConstructionError) as caught:
            boundary.construct_once()
        self.assertEqual(caught.exception.code, "LISTENER_METHOD_BINDING_DRIFT")
        self.assertEqual(listener.bind_calls, [("127.0.0.1", 18443)])
        self.assertEqual(listener.listen_calls, [1])
        self.assertEqual(listener.close_calls, 1)

    def test_private_factory_rebinding_fails_before_factory_invocation(self):
        listener = _ConfigurableListener()
        calls = []
        boundary = self._boundary(listener, factory=lambda: calls.append(1) or listener)
        boundary._factory = lambda: listener
        with self.assertRaises(InboundTcpListenerConstructionError) as caught:
            boundary.construct_once()
        self.assertEqual(caught.exception.code, "LISTENER_CONSTRUCTION_BINDING_DRIFT")
        self.assertEqual(calls, [])
        self.assertEqual(listener.bind_calls, [])

    def test_m52_class_swap_during_bind_fails_before_hostile_handoff(self):
        listener = _ConfigurableListener()
        original = listener_module.BoundedInboundHttpSingleAccept
        constructed = []

        class _HostileM52:
            def __init__(self, *, acceptor):
                constructed.append(acceptor)

        listener.mutate_on_bind = lambda current: setattr(
            listener_module, "BoundedInboundHttpSingleAccept", _HostileM52
        )
        boundary = self._boundary(listener)
        try:
            with self.assertRaises(InboundTcpListenerConstructionError) as caught:
                boundary.construct_once()
        finally:
            listener_module.BoundedInboundHttpSingleAccept = original
        self.assertEqual(caught.exception.code, "LISTENER_CONSTRUCTION_BINDING_DRIFT")
        self.assertEqual(constructed, [])
        self.assertEqual(listener.close_calls, 1)

    def test_public_constructor_has_only_bounded_source_configuration(self):
        params = inspect.signature(BoundedInboundTcpListenerConstruction).parameters
        self.assertEqual(set(params), {"factory", "host", "port", "backlog"})
        forbidden = {
            "tls", "certificate", "key", "resolver", "deployment",
            "service", "workers", "retries", "proxy", "credentials",
        }
        self.assertTrue(forbidden.isdisjoint(params))

    def test_source_has_no_os_network_tls_process_or_background_imports(self):
        tree = ast.parse(SOURCE.read_text(encoding="utf-8-sig"))
        imported_roots = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported_roots.update(alias.name.split(".", 1)[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                imported_roots.add(node.module.split(".", 1)[0])
        self.assertTrue(
            {"socket", "ssl", "asyncio", "threading", "multiprocessing", "subprocess", "os", "pathlib", "logging", "http", "urllib"}.isdisjoint(imported_roots)
        )
        source = SOURCE.read_text(encoding="utf-8-sig")
        self.assertNotIn("import socket", source)
        self.assertNotIn("from socket", source)
        self.assertNotIn(".accept(", source)
        self.assertNotIn("getaddrinfo(", source)
        self.assertNotIn("wrap_socket(", source)

    def test_construct_and_close_have_no_loop_or_retry_surface(self):
        tree = ast.parse(SOURCE.read_text(encoding="utf-8-sig"))
        targets = {"construct_once", "close"}
        methods = [
            node for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name in targets
        ]
        self.assertEqual({node.name for node in methods}, targets)
        for method in methods:
            self.assertFalse(
                any(
                    isinstance(node, (ast.For, ast.AsyncFor, ast.While))
                    for node in ast.walk(method)
                ),
                method.name,
            )


class _MutableFactory:
    def __init__(self, listener: object) -> None:
        self.listener = listener
        self.calls = 0

    def __call__(self):
        self.calls += 1
        return self.listener


class InboundTcpListenerConstructionFactoryBindingTests(unittest.TestCase):
    def test_factory_call_graph_rebinding_fails_before_factory_invocation(self):
        listener = _ConfigurableListener()
        factory = _MutableFactory(listener)
        boundary = BoundedInboundTcpListenerConstruction(
            factory=factory, host="127.0.0.1", port=18443, backlog=1
        )
        original = _MutableFactory.__call__
        hostile_calls = []
        _MutableFactory.__call__ = lambda self: hostile_calls.append(self) or listener
        try:
            with self.assertRaises(InboundTcpListenerConstructionError) as caught:
                boundary.construct_once()
        finally:
            _MutableFactory.__call__ = original
        self.assertEqual(caught.exception.code, "LISTENER_FACTORY_BINDING_DRIFT")
        self.assertEqual(factory.calls, 0)
        self.assertEqual(hostile_calls, [])
        self.assertEqual(listener.bind_calls, [])


class _EndpointMutationOnSecondBindLookup(_ConfigurableListener):
    def __init__(self) -> None:
        super().__init__()
        self.boundary = None
        self.bind_lookups = 0

    def __getattribute__(self, name: str):
        if name == "bind":
            count = object.__getattribute__(self, "bind_lookups") + 1
            object.__setattr__(self, "bind_lookups", count)
            boundary = object.__getattribute__(self, "boundary")
            if count == 2 and boundary is not None:
                boundary._host = "0.0.0.0"
        return object.__getattribute__(self, name)


class InboundTcpListenerConstructionEndpointBindingTests(unittest.TestCase):
    def test_listener_getter_cannot_rebind_endpoint_before_bind(self):
        listener = _EndpointMutationOnSecondBindLookup()
        boundary = BoundedInboundTcpListenerConstruction(
            factory=lambda: listener,
            host="127.0.0.1",
            port=18443,
            backlog=1,
        )
        listener.boundary = boundary
        with self.assertRaises(InboundTcpListenerConstructionError) as caught:
            boundary.construct_once()
        self.assertEqual(caught.exception.code, "LISTENER_CONSTRUCTION_BINDING_DRIFT")
        self.assertEqual(listener.bind_calls, [])
        self.assertEqual(listener.listen_calls, [])
        self.assertEqual(listener.close_calls, 1)


class _AcceptedConnection:
    def __init__(self) -> None:
        self.close_calls = 0

    def recv(self, max_bytes: int) -> bytes:
        return b""

    def send(self, data: bytes) -> int:
        return len(data)

    def close(self) -> None:
        self.close_calls += 1


class _LateAcceptMutationListener(_ConfigurableListener):
    def __init__(self, connection: object, hostile_calls: list[object]) -> None:
        super().__init__()
        self.connection = connection
        self.accept_calls = 0
        self.close_lookups = 0
        self.hostile_calls = hostile_calls

    def accept(self):
        self.accept_calls += 1
        return self.connection

    def __getattribute__(self, name: str):
        if name == "close":
            count = object.__getattribute__(self, "close_lookups") + 1
            object.__setattr__(self, "close_lookups", count)
            if count == 4:
                hostile_calls = object.__getattribute__(self, "hostile_calls")
                connection = object.__getattribute__(self, "connection")
                object.__setattr__(self, "accept", lambda: hostile_calls.append(connection) or connection)
        return object.__getattribute__(self, name)


class InboundTcpListenerConstructionHandoffBindingTests(unittest.TestCase):
    def test_handoff_uses_originally_captured_accept_authority(self):
        connection = _AcceptedConnection()
        hostile_calls: list[object] = []
        listener = _LateAcceptMutationListener(connection, hostile_calls)
        boundary = BoundedInboundTcpListenerConstruction(
            factory=lambda: listener,
            host="127.0.0.1",
            port=18443,
            backlog=1,
        )

        accept_boundary = boundary.construct_once()
        io = accept_boundary.accept_once()

        self.assertEqual(listener.accept_calls, 1)
        self.assertEqual(hostile_calls, [])
        self.assertEqual(listener.close_calls, 1)
        self.assertFalse(io.closed)
        io.close()
        self.assertEqual(connection.close_calls, 1)


class InboundTcpListenerCapturedAcceptorHardeningTests(unittest.TestCase):
    def _constructed(self):
        connection = _AcceptedConnection()
        listener = _LateAcceptMutationListener(connection, [])
        boundary = BoundedInboundTcpListenerConstruction(
            factory=lambda: listener,
            host="127.0.0.1",
            port=18443,
            backlog=1,
        )
        return connection, listener, boundary.construct_once()

    def test_private_captured_accept_rebinding_never_substitutes_authority(self):
        connection, listener, accept_boundary = self._constructed()
        hostile_calls = []
        wrapper = accept_boundary._acceptor
        wrapper._accept = lambda: hostile_calls.append(1) or connection
        with self.assertRaises(Exception) as caught:
            accept_boundary.accept_once()
        self.assertEqual(getattr(caught.exception, "code", None), "ACCEPTOR_CLEANUP_UNCERTAIN")
        self.assertEqual(hostile_calls, [])
        self.assertEqual(listener.close_calls, 0)
        self.assertEqual(connection.close_calls, 0)

    def test_private_captured_close_rebinding_fails_without_cleanup_substitution(self):
        connection, listener, accept_boundary = self._constructed()
        hostile_calls = []
        wrapper = accept_boundary._acceptor
        wrapper._close = lambda: hostile_calls.append(1)
        with self.assertRaises(Exception) as caught:
            accept_boundary.accept_once()
        self.assertEqual(getattr(caught.exception, "code", None), "ACCEPTOR_CLEANUP_UNCERTAIN")
        self.assertEqual(hostile_calls, [])
        self.assertEqual(listener.close_calls, 0)
        self.assertEqual(connection.close_calls, 0)


class InboundTcpListenerCapturedWitnessHardeningTests(unittest.TestCase):
    def test_private_binding_witness_replacement_never_substitutes_cleanup_authority(self):
        connection = _AcceptedConnection()
        listener = _LateAcceptMutationListener(connection, [])
        boundary = BoundedInboundTcpListenerConstruction(
            factory=lambda: listener,
            host="127.0.0.1",
            port=18443,
            backlog=1,
        )
        accept_boundary = boundary.construct_once()
        wrapper = accept_boundary._acceptor
        hostile_calls = []
        wrapper._binding_witness = (
            "m53-captured-listener-acceptor-v1",
            wrapper._listener,
            wrapper._accept,
            lambda: hostile_calls.append("forged-close"),
            wrapper._accept_function,
            wrapper._close_function,
        )

        with self.assertRaises(Exception) as caught:
            accept_boundary.close()

        self.assertEqual(getattr(caught.exception, "code", None), "ACCEPTOR_CLEANUP_UNCERTAIN")
        self.assertEqual(hostile_calls, [])
        self.assertEqual(listener.close_calls, 0)


class InboundTcpListenerDownstreamConstructionBindingTests(unittest.TestCase):
    def test_m52_init_mutation_during_bind_fails_before_substituted_constructor(self):
        listener = _ConfigurableListener()
        boundary = BoundedInboundTcpListenerConstruction(
            factory=lambda: listener,
            host="127.0.0.1",
            port=18443,
            backlog=1,
        )
        original = BoundedInboundHttpSingleAccept.__init__
        hostile_calls = []

        def hostile(_self, **_kwargs):
            hostile_calls.append(True)
            raise AssertionError("substituted M52 constructor MUST NOT run")

        listener.mutate_on_bind = lambda _listener: setattr(
            BoundedInboundHttpSingleAccept,
            "__init__",
            hostile,
        )
        try:
            with self.assertRaises(InboundTcpListenerConstructionError) as caught:
                boundary.construct_once()
        finally:
            BoundedInboundHttpSingleAccept.__init__ = original

        self.assertEqual(caught.exception.code, "LISTENER_CONSTRUCTION_BINDING_DRIFT")
        self.assertEqual(hostile_calls, [])
        self.assertEqual(listener.listen_calls, [])
        self.assertEqual(listener.close_calls, 1)

    def test_m52_validation_helper_mutation_during_bind_fails_before_constructor(self):
        listener = _ConfigurableListener()
        boundary = BoundedInboundTcpListenerConstruction(
            factory=lambda: listener,
            host="127.0.0.1",
            port=18443,
            backlog=1,
        )
        original = BoundedInboundHttpSingleAccept._validate_bindings
        hostile_calls = []

        def hostile(_self):
            hostile_calls.append(True)
            raise AssertionError("substituted M52 validation MUST NOT run")

        listener.mutate_on_bind = lambda _listener: setattr(
            BoundedInboundHttpSingleAccept,
            "_validate_bindings",
            hostile,
        )
        try:
            with self.assertRaises(InboundTcpListenerConstructionError) as caught:
                boundary.construct_once()
        finally:
            BoundedInboundHttpSingleAccept._validate_bindings = original

        self.assertEqual(caught.exception.code, "LISTENER_CONSTRUCTION_BINDING_DRIFT")
        self.assertEqual(hostile_calls, [])
        self.assertEqual(listener.listen_calls, [])
        self.assertEqual(listener.close_calls, 1)
