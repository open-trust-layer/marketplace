from __future__ import annotations

import ast
import inspect
import pathlib
import unittest
from socket import AF_INET, IPPROTO_TCP, SOCK_STREAM

from marketplace.runtime.inbound_tcp_listener import BoundedInboundTcpListenerConstruction
from marketplace.runtime.inbound_tcp_socket_factory import (
    BoundedPythonTcpSocketFactory,
    PythonTcpSocketConstructor,
    PythonTcpSocketFactoryError,
)

ROOT = pathlib.Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src/marketplace/runtime/inbound_tcp_socket_factory.py"


class FakeListener:
    def __init__(self) -> None:
        self.bind_calls = []
        self.listen_calls = []
        self.accept_calls = 0
        self.close_calls = 0

    def bind(self, address) -> None:
        self.bind_calls.append(address)

    def listen(self, backlog: int) -> None:
        self.listen_calls.append(backlog)

    def accept(self):
        self.accept_calls += 1
        return object()

    def close(self) -> None:
        self.close_calls += 1


class RecordingConstructor:
    def __init__(self, result) -> None:
        self.result = result
        self.calls = []

    def __call__(self, family, kind, protocol):
        self.calls.append((family, kind, protocol))
        return self.result


class EqualityTrapConstructor(RecordingConstructor):
    def __eq__(self, other):
        raise AssertionError("constructor equality must never be invoked")


class BoundedPythonTcpSocketFactoryTests(unittest.TestCase):
    def test_constructor_surface_is_explicit_and_exact(self):
        signature = inspect.signature(BoundedPythonTcpSocketFactory)
        self.assertEqual(list(signature.parameters), ["constructor"])
        self.assertIsInstance(RecordingConstructor(FakeListener()), PythonTcpSocketConstructor)

    def test_one_call_uses_exact_ipv4_tcp_stream_profile_and_releases_constructor(self):
        listener = FakeListener()
        constructor = RecordingConstructor(listener)
        factory = BoundedPythonTcpSocketFactory(constructor=constructor)

        self.assertIs(factory(), listener)
        self.assertEqual(constructor.calls, [(AF_INET, SOCK_STREAM, IPPROTO_TCP)])
        self.assertTrue(factory.used)
        self.assertTrue(factory.closed)
        self.assertIsNone(factory._constructor)
        self.assertIsNone(factory._binding_witness)

    def test_second_call_is_terminal_and_never_reinvokes_constructor(self):
        listener = FakeListener()
        constructor = RecordingConstructor(listener)
        factory = BoundedPythonTcpSocketFactory(constructor=constructor)
        factory()

        with self.assertRaises(PythonTcpSocketFactoryError) as raised:
            factory()
        self.assertEqual(raised.exception.code, "SOCKET_FACTORY_USED")
        self.assertEqual(len(constructor.calls), 1)

    def test_constructor_exception_is_redacted_and_terminal(self):
        secret = "do-not-reflect-constructor-secret"

        class FailingConstructor:
            def __call__(self, family, kind, protocol):
                raise RuntimeError(secret)

        factory = BoundedPythonTcpSocketFactory(constructor=FailingConstructor())
        with self.assertRaises(PythonTcpSocketFactoryError) as raised:
            factory()
        self.assertEqual(raised.exception.code, "SOCKET_CONSTRUCTOR_FAILED")
        self.assertNotIn(secret, str(raised.exception))
        self.assertTrue(factory.closed)
        self.assertIsNone(factory._constructor)

    def test_noncallable_constructor_is_rejected(self):
        with self.assertRaises(PythonTcpSocketFactoryError) as raised:
            BoundedPythonTcpSocketFactory(constructor=object())
        self.assertEqual(raised.exception.code, "SOCKET_CONSTRUCTOR_INVALID")

    def test_private_constructor_rebinding_fails_before_invocation(self):
        original = RecordingConstructor(FakeListener())
        hostile = RecordingConstructor(FakeListener())
        factory = BoundedPythonTcpSocketFactory(constructor=original)
        factory._constructor = hostile

        with self.assertRaises(PythonTcpSocketFactoryError) as raised:
            factory()
        self.assertEqual(raised.exception.code, "SOCKET_FACTORY_BINDING_DRIFT")
        self.assertEqual(original.calls, [])
        self.assertEqual(hostile.calls, [])

    def test_private_binding_witness_replacement_fails_before_invocation(self):
        constructor = RecordingConstructor(FakeListener())
        factory = BoundedPythonTcpSocketFactory(constructor=constructor)
        factory._binding_witness = ("forged",)

        with self.assertRaises(PythonTcpSocketFactoryError) as raised:
            factory()
        self.assertEqual(raised.exception.code, "SOCKET_FACTORY_BINDING_DRIFT")
        self.assertEqual(constructor.calls, [])

    def test_constructor_call_graph_rebinding_fails_before_invocation(self):
        class MutableConstructor(RecordingConstructor):
            pass

        constructor = MutableConstructor(FakeListener())
        factory = BoundedPythonTcpSocketFactory(constructor=constructor)
        original_call = MutableConstructor.__call__

        def hostile_call(self, family, kind, protocol):
            raise AssertionError("hostile constructor must not run")

        MutableConstructor.__call__ = hostile_call
        try:
            with self.assertRaises(PythonTcpSocketFactoryError) as raised:
                factory()
            self.assertEqual(raised.exception.code, "SOCKET_CONSTRUCTOR_BINDING_DRIFT")
            self.assertEqual(constructor.calls, [])
        finally:
            MutableConstructor.__call__ = original_call

    def test_constructor_equality_is_never_invoked(self):
        constructor = EqualityTrapConstructor(FakeListener())
        factory = BoundedPythonTcpSocketFactory(constructor=constructor)
        factory()
        self.assertEqual(len(constructor.calls), 1)

    def test_constructor_result_cannot_alias_factory(self):
        class SelfReturningConstructor:
            def __init__(self) -> None:
                self.result = None
                self.calls = 0

            def __call__(self, family, kind, protocol):
                self.calls += 1
                return self.result

        constructor = SelfReturningConstructor()
        factory = BoundedPythonTcpSocketFactory(constructor=constructor)
        constructor.result = factory
        with self.assertRaises(PythonTcpSocketFactoryError) as raised:
            factory()
        self.assertEqual(raised.exception.code, "SOCKET_CONSTRUCTOR_ALIASES_FACTORY")
        self.assertEqual(constructor.calls, 1)

    def test_constructor_result_cannot_alias_constructor(self):
        class ConstructorReturningItself:
            def __init__(self) -> None:
                self.calls = 0

            def __call__(self, family, kind, protocol):
                self.calls += 1
                return self

        constructor = ConstructorReturningItself()
        factory = BoundedPythonTcpSocketFactory(constructor=constructor)
        with self.assertRaises(PythonTcpSocketFactoryError) as raised:
            factory()
        self.assertEqual(raised.exception.code, "SOCKET_CONSTRUCTOR_ALIASES_CONSTRUCTOR")
        self.assertEqual(constructor.calls, 1)

    def test_composes_directly_with_exact_m53_without_live_network(self):
        listener = FakeListener()
        constructor = RecordingConstructor(listener)
        factory = BoundedPythonTcpSocketFactory(constructor=constructor)
        m53 = BoundedInboundTcpListenerConstruction(
            factory=factory,
            host="127.0.0.1",
            port=18443,
            backlog=1,
        )

        m52 = m53.construct_once()
        self.assertEqual(constructor.calls, [(AF_INET, SOCK_STREAM, IPPROTO_TCP)])
        self.assertEqual(listener.bind_calls, [("127.0.0.1", 18443)])
        self.assertEqual(listener.listen_calls, [1])
        self.assertEqual(listener.accept_calls, 0)
        self.assertEqual(listener.close_calls, 0)
        self.assertEqual(type(m52).__name__, "BoundedInboundHttpSingleAccept")

    def test_call_path_has_no_loop_retry_or_direct_network_operations(self):
        source = SOURCE.read_text(encoding="utf-8")
        tree = ast.parse(source)
        call = next(
            node for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef) and node.name == "__call__"
        )
        self.assertFalse(any(isinstance(node, (ast.For, ast.While)) for node in ast.walk(call)))
        forbidden_calls = {
            "bind", "listen", "accept", "connect", "connect_ex",
            "getaddrinfo", "create_connection", "send", "sendall", "recv",
        }
        actual_calls = {
            node.func.attr
            for node in ast.walk(tree)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
        }
        self.assertTrue(forbidden_calls.isdisjoint(actual_calls))

        forbidden_import_roots = {
            "ssl", "subprocess", "threading", "asyncio", "logging",
            "pathlib", "os", "shutil", "tempfile",
        }
        imports = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(alias.name.split(".", 1)[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.add(node.module.split(".", 1)[0])
        self.assertTrue(forbidden_import_roots.isdisjoint(imports))
        self.assertNotIn("socket.socket", source)


if __name__ == "__main__":
    unittest.main()
