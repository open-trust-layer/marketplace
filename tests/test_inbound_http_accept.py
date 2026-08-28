from __future__ import annotations

import ast
import inspect
import pathlib
import unittest

import marketplace.runtime.inbound_http_accept as accept_module
from marketplace.runtime.inbound_http_accept import (
    BoundedInboundHttpSingleAccept,
    InboundHttpSingleAcceptError,
)
from marketplace.runtime.inbound_http_connection import (
    BoundedInboundHttpSingleConnectionIO,
)

ROOT = pathlib.Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src/marketplace/runtime/inbound_http_accept.py"


class _Connection:
    def __init__(self) -> None:
        self.recv_calls = 0
        self.send_calls = 0
        self.close_calls = 0
        self.close_exception: Exception | None = None

    def recv(self, max_bytes: int) -> bytes:
        self.recv_calls += 1
        return b""

    def send(self, data: bytes) -> int:
        self.send_calls += 1
        return len(data)

    def close(self) -> None:
        self.close_calls += 1
        if self.close_exception is not None:
            raise self.close_exception


class _InvalidConnection:
    def __init__(self) -> None:
        self.close_calls = 0

    def recv(self, max_bytes: int) -> bytes:
        return b""

    def close(self) -> None:
        self.close_calls += 1


class _Acceptor:
    def __init__(self, connection: object) -> None:
        self.connection = connection
        self.accept_calls = 0
        self.close_calls = 0
        self.accept_exception: Exception | None = None
        self.close_exception: Exception | None = None
        self.mutate_on_accept = None

    def accept(self):
        self.accept_calls += 1
        if self.mutate_on_accept is not None:
            self.mutate_on_accept(self)
        if self.accept_exception is not None:
            raise self.accept_exception
        return self.connection

    def close(self) -> None:
        self.close_calls += 1
        if self.close_exception is not None:
            raise self.close_exception


class _HostileAttributeAcceptor(_Acceptor):
    def __init__(self, connection: object) -> None:
        super().__init__(connection)
        self.hostile_lookup = False

    def __getattribute__(self, name: str):
        if name in {"accept", "close"} and object.__getattribute__(self, "hostile_lookup"):
            raise RuntimeError("TOP-SECRET-ATTRIBUTE-TEXT")
        return object.__getattribute__(self, name)


class _HostileCloseLookupConnection(_Connection):
    def __getattribute__(self, name: str):
        if name == "close":
            raise RuntimeError("TOP-SECRET-CONNECTION-LOOKUP")
        return object.__getattribute__(self, name)


class InboundHttpSingleAcceptTests(unittest.TestCase):
    def test_accept_once_returns_exact_m51_io_and_closes_acceptor(self):
        connection = _Connection()
        acceptor = _Acceptor(connection)
        boundary = BoundedInboundHttpSingleAccept(acceptor=acceptor)

        io = boundary.accept_once()

        self.assertIs(type(io), BoundedInboundHttpSingleConnectionIO)
        self.assertEqual(acceptor.accept_calls, 1)
        self.assertEqual(acceptor.close_calls, 1)
        self.assertTrue(boundary.used)
        self.assertTrue(boundary.closed)
        self.assertIsNone(boundary._acceptor)
        self.assertIsNone(boundary._accept)
        self.assertIsNone(boundary._acceptor_close)
        self.assertIsNone(boundary._binding_witness)
        self.assertFalse(io.closed)
        io.close()
        self.assertTrue(io.closed)
        self.assertEqual(connection.close_calls, 1)

    def test_accept_is_one_shot_and_never_retried(self):
        connection = _Connection()
        acceptor = _Acceptor(connection)
        boundary = BoundedInboundHttpSingleAccept(acceptor=acceptor)
        boundary.accept_once()

        with self.assertRaises(InboundHttpSingleAcceptError) as caught:
            boundary.accept_once()

        self.assertEqual(caught.exception.code, "ACCEPTOR_USED")
        self.assertEqual(acceptor.accept_calls, 1)
        self.assertEqual(acceptor.close_calls, 1)

    def test_hostile_acceptor_attribute_lookup_is_redacted_and_cleans_up(self):
        connection = _Connection()
        acceptor = _HostileAttributeAcceptor(connection)
        boundary = BoundedInboundHttpSingleAccept(acceptor=acceptor)
        acceptor.hostile_lookup = True

        with self.assertRaises(InboundHttpSingleAcceptError) as caught:
            boundary.accept_once()

        self.assertEqual(caught.exception.code, "ACCEPTOR_METHOD_BINDING_UNVERIFIABLE")
        self.assertNotIn("TOP-SECRET", str(caught.exception))
        self.assertEqual(acceptor.accept_calls, 0)
        self.assertEqual(acceptor.close_calls, 1)
        self.assertIsNone(boundary._acceptor)

    def test_hostile_returned_close_lookup_is_stable_cleanup_uncertainty(self):
        connection = _HostileCloseLookupConnection()
        acceptor = _Acceptor(connection)
        boundary = BoundedInboundHttpSingleAccept(acceptor=acceptor)

        with self.assertRaises(InboundHttpSingleAcceptError) as caught:
            boundary.accept_once()

        self.assertEqual(caught.exception.code, "ACCEPTED_CONNECTION_CLEANUP_UNCERTAIN")
        self.assertNotIn("TOP-SECRET", str(caught.exception))
        self.assertEqual(acceptor.accept_calls, 1)
        self.assertEqual(acceptor.close_calls, 1)

    def test_accept_exception_is_redacted_and_acceptor_closes_once(self):
        connection = _Connection()
        acceptor = _Acceptor(connection)
        acceptor.accept_exception = RuntimeError("TOP-SECRET-ACCEPT-TEXT")
        boundary = BoundedInboundHttpSingleAccept(acceptor=acceptor)

        with self.assertRaises(InboundHttpSingleAcceptError) as caught:
            boundary.accept_once()

        self.assertEqual(caught.exception.code, "ACCEPT_FAILED")
        self.assertNotIn("TOP-SECRET", str(caught.exception))
        self.assertEqual(acceptor.accept_calls, 1)
        self.assertEqual(acceptor.close_calls, 1)
        self.assertEqual(connection.close_calls, 0)
        self.assertTrue(boundary.used)
        self.assertTrue(boundary.closed)

    def test_acceptor_close_failure_closes_accepted_connection_and_is_uncertain(self):
        connection = _Connection()
        acceptor = _Acceptor(connection)
        acceptor.close_exception = RuntimeError("TOP-SECRET-CLOSE-TEXT")
        boundary = BoundedInboundHttpSingleAccept(acceptor=acceptor)

        with self.assertRaises(InboundHttpSingleAcceptError) as caught:
            boundary.accept_once()

        self.assertEqual(caught.exception.code, "ACCEPTOR_CLEANUP_UNCERTAIN")
        self.assertNotIn("TOP-SECRET", str(caught.exception))
        self.assertEqual(acceptor.accept_calls, 1)
        self.assertEqual(acceptor.close_calls, 1)
        self.assertEqual(connection.close_calls, 1)
        self.assertFalse(boundary.closed)
        boundary.close()
        self.assertEqual(acceptor.close_calls, 1)
        self.assertIsNone(boundary._acceptor)

    def test_private_captured_close_rebinding_uses_original_close(self):
        connection = _Connection()
        acceptor = _Acceptor(connection)
        boundary = BoundedInboundHttpSingleAccept(acceptor=acceptor)
        hostile_calls = []
        boundary._acceptor_close = lambda: hostile_calls.append("called")

        with self.assertRaises(InboundHttpSingleAcceptError) as caught:
            boundary.accept_once()

        self.assertEqual(caught.exception.code, "ACCEPTOR_BINDING_DRIFT")
        self.assertEqual(hostile_calls, [])
        self.assertEqual(acceptor.accept_calls, 0)
        self.assertEqual(acceptor.close_calls, 1)
        self.assertIsNone(boundary._acceptor)

    def test_method_rebinding_before_accept_fails_before_accept_and_uses_captured_close(self):
        connection = _Connection()
        acceptor = _Acceptor(connection)
        boundary = BoundedInboundHttpSingleAccept(acceptor=acceptor)
        acceptor.accept = lambda: connection

        with self.assertRaises(InboundHttpSingleAcceptError) as caught:
            boundary.accept_once()

        self.assertEqual(caught.exception.code, "ACCEPTOR_METHOD_BINDING_DRIFT")
        self.assertEqual(acceptor.accept_calls, 0)
        self.assertEqual(acceptor.close_calls, 1)
        self.assertEqual(connection.close_calls, 0)

    def test_method_rebinding_during_accept_closes_connection_and_fails_closed(self):
        connection = _Connection()
        acceptor = _Acceptor(connection)
        boundary = BoundedInboundHttpSingleAccept(acceptor=acceptor)
        acceptor.mutate_on_accept = lambda current: setattr(
            current, "accept", lambda: connection
        )

        with self.assertRaises(InboundHttpSingleAcceptError) as caught:
            boundary.accept_once()

        self.assertEqual(caught.exception.code, "ACCEPTOR_METHOD_BINDING_DRIFT")
        self.assertEqual(acceptor.accept_calls, 1)
        self.assertEqual(acceptor.close_calls, 1)
        self.assertEqual(connection.close_calls, 1)
        self.assertIsNone(boundary._acceptor)

    def test_m51_io_class_swap_during_accept_fails_before_hostile_construction(self):
        connection = _Connection()
        acceptor = _Acceptor(connection)
        boundary = BoundedInboundHttpSingleAccept(acceptor=acceptor)
        original = accept_module.BoundedInboundHttpSingleConnectionIO
        constructed = []

        class _HostileIO:
            def __init__(self, *, connection):
                constructed.append(connection)

        acceptor.mutate_on_accept = lambda current: setattr(
            accept_module, "BoundedInboundHttpSingleConnectionIO", _HostileIO
        )
        try:
            with self.assertRaises(InboundHttpSingleAcceptError) as caught:
                boundary.accept_once()
        finally:
            accept_module.BoundedInboundHttpSingleConnectionIO = original

        self.assertEqual(caught.exception.code, "ACCEPTOR_BINDING_DRIFT")
        self.assertEqual(constructed, [])
        self.assertEqual(acceptor.accept_calls, 1)
        self.assertEqual(acceptor.close_calls, 1)
        self.assertEqual(connection.close_calls, 1)

    def test_invalid_accepted_connection_is_closed_when_possible(self):
        connection = _InvalidConnection()
        acceptor = _Acceptor(connection)
        boundary = BoundedInboundHttpSingleAccept(acceptor=acceptor)

        with self.assertRaises(InboundHttpSingleAcceptError) as caught:
            boundary.accept_once()

        self.assertEqual(caught.exception.code, "ACCEPTED_CONNECTION_INVALID")
        self.assertEqual(acceptor.accept_calls, 1)
        self.assertEqual(acceptor.close_calls, 1)
        self.assertEqual(connection.close_calls, 1)
        self.assertTrue(boundary.closed)

    def test_close_before_accept_is_idempotent_and_blocks_accept(self):
        connection = _Connection()
        acceptor = _Acceptor(connection)
        boundary = BoundedInboundHttpSingleAccept(acceptor=acceptor)

        boundary.close()
        boundary.close()

        self.assertEqual(acceptor.accept_calls, 0)
        self.assertEqual(acceptor.close_calls, 1)
        self.assertTrue(boundary.closed)
        with self.assertRaises(InboundHttpSingleAcceptError) as caught:
            boundary.accept_once()
        self.assertEqual(caught.exception.code, "ACCEPTOR_USED")
        self.assertEqual(connection.close_calls, 0)

    def test_close_failure_before_accept_is_uncertain_and_not_retried(self):
        connection = _Connection()
        acceptor = _Acceptor(connection)
        acceptor.close_exception = RuntimeError("TOP-SECRET-CLOSE-TEXT")
        boundary = BoundedInboundHttpSingleAccept(acceptor=acceptor)

        with self.assertRaises(InboundHttpSingleAcceptError) as caught:
            boundary.close()

        self.assertEqual(caught.exception.code, "ACCEPTOR_CLEANUP_UNCERTAIN")
        self.assertNotIn("TOP-SECRET", str(caught.exception))
        self.assertEqual(acceptor.close_calls, 1)
        boundary.close()
        self.assertEqual(acceptor.close_calls, 1)
        self.assertFalse(boundary.closed)
        self.assertIsNone(boundary._acceptor)

    def test_constructor_exposes_only_caller_supplied_acceptor(self):
        params = inspect.signature(BoundedInboundHttpSingleAccept).parameters
        self.assertEqual(set(params), {"acceptor"})
        forbidden = {
            "host", "port", "address", "endpoint", "socket", "tls",
            "certificate", "key", "resolver", "deployment", "backlog",
        }
        self.assertTrue(forbidden.isdisjoint(params))

    def test_source_has_no_concrete_network_tls_process_or_background_surface(self):
        tree = ast.parse(SOURCE.read_text(encoding="utf-8-sig"))
        imported_roots = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported_roots.update(alias.name.split(".", 1)[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                imported_roots.add(node.module.split(".", 1)[0])
        self.assertTrue(
            {
                "socket", "ssl", "asyncio", "threading", "multiprocessing",
                "subprocess", "os", "pathlib", "logging", "sqlite3", "http", "urllib",
            }.isdisjoint(imported_roots)
        )
        source = SOURCE.read_text(encoding="utf-8-sig")
        for token in (
            ".bind(", ".listen(", ".connect(", "create_server(",
            "create_connection(", "getaddrinfo(", "wrap_socket(",
        ):
            self.assertNotIn(token, source)

    def test_accept_and_close_have_no_loop_or_retry_surface(self):
        tree = ast.parse(SOURCE.read_text(encoding="utf-8-sig"))
        targets = {"accept_once", "close"}
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


if __name__ == "__main__":
    unittest.main()
