from __future__ import annotations

import ast
import inspect
import pathlib
import unittest
from dataclasses import replace

from marketplace.runtime.inbound_http_connection import (
    BoundedInboundHttpSingleConnectionIO,
    BoundedInboundHttpSingleConnectionTransport,
    CompletedInboundHttpSingleConnectionTransport,
    InboundHttpSingleConnectionTransportError,
)
from marketplace.runtime.inbound_http_response_prepare import BoundedInboundHttpResponsePreparer
from marketplace.runtime.inbound_http_response_write_driver import InboundHttpResponseWriteDriverLimits
from marketplace.runtime.inbound_http_response_write_plan import InboundHttpResponseWriteLimits
from test_inbound_http_response_prepare import _build

ROOT = pathlib.Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src/marketplace/runtime/inbound_http_connection.py"


class _Connection:
    def __init__(self, *, recv_limit: int | None = None, send_limit: int | None = None):
        self.input_bytes = b""
        self.offset = 0
        self.recv_limit = recv_limit
        self.send_limit = send_limit
        self.read_budgets: list[int] = []
        self.sent_chunks: list[bytes] = []
        self.close_calls = 0
        self.recv_exception: Exception | None = None
        self.send_exception: Exception | None = None
        self.close_exception: Exception | None = None
        self.recv_override = None
        self.send_override = None
        self.mutate_on_recv = None
        self.mutate_on_send = None

    def recv(self, max_bytes: int) -> bytes:
        self.read_budgets.append(max_bytes)
        if self.mutate_on_recv is not None:
            self.mutate_on_recv(self)
        if self.recv_exception is not None:
            raise self.recv_exception
        if self.recv_override is not None:
            return self.recv_override
        limit = max_bytes if self.recv_limit is None else min(max_bytes, self.recv_limit)
        start = self.offset
        end = min(start + limit, len(self.input_bytes))
        self.offset = end
        return self.input_bytes[start:end]

    def send(self, data: bytes) -> int:
        if self.mutate_on_send is not None:
            self.mutate_on_send(self)
        if self.send_exception is not None:
            raise self.send_exception
        if self.send_override is not None:
            return self.send_override
        accepted = len(data) if self.send_limit is None else min(len(data), self.send_limit)
        if accepted:
            self.sent_chunks.append(bytes(data[:accepted]))
        return accepted

    def close(self) -> None:
        self.close_calls += 1
        if self.close_exception is not None:
            raise self.close_exception


def _transport(connection: _Connection, *, recv_bytes=64 * 1024, send_bytes=64 * 1024):
    io = BoundedInboundHttpSingleConnectionIO(connection=connection)
    harness, _, _, session, driver, raw = _build(
        io.reader,
        max_read_bytes=recv_bytes,
        max_read_calls=64,
    )
    preparer = BoundedInboundHttpResponsePreparer(read_driver=driver)
    transport = BoundedInboundHttpSingleConnectionTransport(
        connection_io=io,
        response_preparer=preparer,
        clock=lambda: 0.0,
        write_limits=InboundHttpResponseWriteLimits(
            max_write_calls=64,
            max_write_bytes=send_bytes,
        ),
        write_driver_limits=InboundHttpResponseWriteDriverLimits(
            max_steps=65,
            max_elapsed_seconds=1.0,
        ),
    )
    connection.input_bytes = raw
    return io, harness, session, preparer, transport, raw


def _contains_raw_bytes(value, *, seen=None):
    if type(value) in (bytes, bytearray, memoryview):
        return True
    if seen is None:
        seen = set()
    marker = id(value)
    if marker in seen:
        return False
    seen.add(marker)
    if isinstance(value, tuple):
        return any(_contains_raw_bytes(item, seen=seen) for item in value)
    if hasattr(value, "__dataclass_fields__"):
        return any(
            _contains_raw_bytes(getattr(value, name), seen=seen)
            for name in value.__dataclass_fields__
        )
    return False


class InboundHttpSingleConnectionTransportTests(unittest.TestCase):
    def test_one_connection_completes_one_transaction_and_closes_once(self):
        connection = _Connection()
        io, harness, session, preparer, transport, raw = _transport(connection)

        result = transport.run()

        self.assertIs(type(result), CompletedInboundHttpSingleConnectionTransport)
        self.assertEqual(connection.offset, len(raw))
        self.assertEqual(result.request_bytes, len(raw))
        self.assertEqual(result.read_bytes, len(raw))
        self.assertEqual(result.read_calls, 1)
        self.assertEqual(result.write_calls, 1)
        self.assertEqual(result.write_bytes, result.response_bytes)
        self.assertEqual(sum(map(len, connection.sent_chunks)), result.response_bytes)
        self.assertEqual(len(harness.calls), 1)
        self.assertTrue(session.closed)
        self.assertTrue(preparer.used)
        self.assertTrue(transport.used)
        self.assertTrue(io.closed)
        self.assertTrue(result.connection_closed)
        self.assertEqual(connection.close_calls, 1)
        self.assertFalse(result.network_origin_proven)
        self.assertFalse(result.tls_terminated)
        self.assertFalse(result.transmitted)
        self.assertFalse(result.request_authenticated)
        self.assertFalse(result.peer_identity_proven)
        self.assertFalse(result.establishes_authorization)

    def test_multiple_bounded_reads_and_partial_writes_preserve_exact_accounting(self):
        connection = _Connection(recv_limit=7, send_limit=5)
        _, _, _, _, transport, raw = _transport(connection, recv_bytes=8, send_bytes=9)

        result = transport.run()

        self.assertGreater(result.read_calls, 1)
        self.assertGreater(result.write_calls, 1)
        self.assertEqual(result.read_bytes, len(raw))
        self.assertEqual(result.write_bytes, result.response_bytes)
        self.assertTrue(all(0 < budget <= 8 for budget in connection.read_budgets))
        self.assertTrue(all(0 < len(chunk) <= 5 for chunk in connection.sent_chunks))
        self.assertEqual(connection.close_calls, 1)

    def test_eof_before_request_completion_is_terminal_and_never_writes(self):
        connection = _Connection()
        _, _, _, _, transport, _ = _transport(connection)
        connection.input_bytes = b""

        with self.assertRaises(InboundHttpSingleConnectionTransportError) as caught:
            transport.run()

        self.assertEqual(caught.exception.code, "CONNECTION_TRANSACTION_REJECTED")
        self.assertEqual(caught.exception.transaction_code, "TRANSACTION_PREPARATION_REJECTED")
        self.assertEqual(connection.sent_chunks, [])
        self.assertEqual(connection.close_calls, 1)
        self.assertTrue(transport.used)

    def test_connection_exception_text_is_redacted_and_close_is_still_verified(self):
        connection = _Connection()
        _, _, _, _, transport, _ = _transport(connection)
        connection.send_exception = RuntimeError("TOP-SECRET-CONNECTION-TEXT")

        with self.assertRaises(InboundHttpSingleConnectionTransportError) as caught:
            transport.run()

        self.assertEqual(caught.exception.code, "CONNECTION_TRANSACTION_REJECTED")
        self.assertEqual(caught.exception.transaction_code, "TRANSACTION_WRITE_REJECTED")
        self.assertNotIn("TOP-SECRET", str(caught.exception))
        self.assertEqual(connection.close_calls, 1)

    def test_invalid_recv_shapes_fail_closed(self):
        for invalid in (bytearray(b"x"), True, 1, "x"):
            with self.subTest(invalid=invalid):
                connection = _Connection()
                _, _, _, _, transport, _ = _transport(connection)
                connection.recv_override = invalid
                with self.assertRaises(InboundHttpSingleConnectionTransportError) as caught:
                    transport.run()
                self.assertEqual(caught.exception.code, "CONNECTION_TRANSACTION_REJECTED")
                self.assertEqual(caught.exception.transaction_code, "TRANSACTION_PREPARATION_REJECTED")
                self.assertEqual(connection.close_calls, 1)

    def test_recv_cannot_exceed_supplied_budget(self):
        connection = _Connection()
        _, _, _, _, transport, _ = _transport(connection, recv_bytes=8)
        connection.recv_override = b"x" * 9

        with self.assertRaises(InboundHttpSingleConnectionTransportError) as caught:
            transport.run()

        self.assertEqual(caught.exception.transaction_code, "TRANSACTION_PREPARATION_REJECTED")
        self.assertEqual(connection.close_calls, 1)

    def test_invalid_send_counts_fail_closed(self):
        for invalid in (True, -1, 10_000_000, "1"):
            with self.subTest(invalid=invalid):
                connection = _Connection()
                _, _, _, _, transport, _ = _transport(connection)
                connection.send_override = invalid
                with self.assertRaises(InboundHttpSingleConnectionTransportError) as caught:
                    transport.run()
                self.assertEqual(caught.exception.code, "CONNECTION_TRANSACTION_REJECTED")
                self.assertEqual(caught.exception.transaction_code, "TRANSACTION_WRITE_REJECTED")
                self.assertEqual(connection.close_calls, 1)

    def test_m43_reader_must_be_the_same_connection_io_reader(self):
        first = _Connection()
        second = _Connection()
        first_io = BoundedInboundHttpSingleConnectionIO(connection=first)
        second_io = BoundedInboundHttpSingleConnectionIO(connection=second)
        _, _, _, _, driver, _ = _build(first_io.reader)
        preparer = BoundedInboundHttpResponsePreparer(read_driver=driver)

        with self.assertRaises(ValueError):
            BoundedInboundHttpSingleConnectionTransport(
                connection_io=second_io,
                response_preparer=preparer,
                clock=lambda: 0.0,
            )

        self.assertEqual(first.read_budgets, [])
        self.assertEqual(second.read_budgets, [])

    def test_m51_rejects_preconsumed_read_session(self):
        connection = _Connection()
        io = BoundedInboundHttpSingleConnectionIO(connection=connection)
        _, _, _, session, driver, raw = _build(io.reader)
        session.accept_chunk(raw[:1])
        preparer = BoundedInboundHttpResponsePreparer(read_driver=driver)

        with self.assertRaises(ValueError):
            BoundedInboundHttpSingleConnectionTransport(
                connection_io=io,
                response_preparer=preparer,
                clock=lambda: 0.0,
            )

    def test_method_rebinding_before_run_fails_before_read_and_uses_captured_close(self):
        connection = _Connection()
        io, _, _, _, transport, _ = _transport(connection)
        connection.recv = lambda _: b"hostile"

        with self.assertRaises(InboundHttpSingleConnectionTransportError) as caught:
            transport.run()

        self.assertEqual(caught.exception.code, "CONNECTION_METHOD_BINDING_DRIFT")
        self.assertEqual(connection.read_budgets, [])
        self.assertTrue(io.closed)
        self.assertEqual(connection.close_calls, 1)

    def test_method_rebinding_during_read_fails_after_consumption_and_closes(self):
        connection = _Connection()
        _, _, _, _, transport, _ = _transport(connection)
        connection.mutate_on_recv = lambda current: setattr(current, "send", lambda _: 1)

        with self.assertRaises(InboundHttpSingleConnectionTransportError) as caught:
            transport.run()

        self.assertEqual(caught.exception.code, "CONNECTION_TRANSACTION_REJECTED")
        self.assertEqual(caught.exception.transaction_code, "TRANSACTION_PREPARATION_REJECTED")
        self.assertEqual(len(connection.read_budgets), 1)
        self.assertEqual(connection.close_calls, 1)

    def test_close_failure_is_uncertain_and_never_retried(self):
        connection = _Connection()
        io, _, _, _, transport, _ = _transport(connection)
        connection.close_exception = RuntimeError("TOP-SECRET-CLOSE-TEXT")

        with self.assertRaises(InboundHttpSingleConnectionTransportError) as caught:
            transport.run()

        self.assertEqual(caught.exception.code, "CONNECTION_CLEANUP_UNCERTAIN")
        self.assertNotIn("TOP-SECRET", str(caught.exception))
        self.assertFalse(io.closed)
        self.assertEqual(connection.close_calls, 1)
        with self.assertRaises(InboundHttpSingleConnectionTransportError):
            transport.close()
        self.assertEqual(connection.close_calls, 1)

    def test_close_before_run_is_idempotent_and_blocks_transaction(self):
        connection = _Connection()
        io, _, session, _, transport, _ = _transport(connection)

        transport.close()
        transport.close()

        self.assertTrue(io.closed)
        self.assertTrue(session.closed)
        self.assertEqual(connection.read_budgets, [])
        self.assertEqual(connection.sent_chunks, [])
        self.assertEqual(connection.close_calls, 1)
        with self.assertRaises(InboundHttpSingleConnectionTransportError) as caught:
            transport.run()
        self.assertEqual(caught.exception.code, "CONNECTION_TRANSPORT_USED")

    def test_result_integrity_blocks_rebinding_and_contains_no_raw_bytes(self):
        connection = _Connection()
        _, _, _, _, transport, _ = _transport(connection)
        result = transport.run()

        self.assertFalse(_contains_raw_bytes(result))
        with self.assertRaises(ValueError):
            replace(result, route_kind=result.route_kind + "-drift")

    def test_constructor_surface_contains_no_endpoint_listener_tls_or_deployment(self):
        params = inspect.signature(BoundedInboundHttpSingleConnectionTransport).parameters
        self.assertEqual(
            set(params),
            {"connection_io", "response_preparer", "clock", "write_limits", "write_driver_limits"},
        )
        forbidden = {
            "host", "port", "address", "listener", "socket", "tls", "certificate",
            "key", "endpoint", "resolver", "connector", "deployment",
        }
        self.assertTrue(forbidden.isdisjoint(params))

    def test_source_has_no_listener_network_tls_process_persistence_or_concurrency_surface(self):
        tree = ast.parse(SOURCE.read_text(encoding="utf-8-sig"))
        imported_roots = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported_roots.update(alias.name.split(".", 1)[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                imported_roots.add(node.module.split(".", 1)[0])
        self.assertTrue(
            {
                "socket", "ssl", "asyncio", "threading", "multiprocessing", "subprocess",
                "os", "pathlib", "logging", "sqlite3", "http", "urllib",
            }.isdisjoint(imported_roots)
        )
        source = SOURCE.read_text(encoding="utf-8-sig")
        for token in ("bind(", "listen(", "accept(", "connect(", "create_server(", "create_connection("):
            self.assertNotIn(token, source)

    def test_m51_run_and_io_wrappers_have_no_loop_or_retry_surface(self):
        tree = ast.parse(SOURCE.read_text(encoding="utf-8-sig"))
        targets = {"run", "_read_once", "_write_once"}
        methods = [
            node for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in targets
        ]
        self.assertEqual({node.name for node in methods}, targets)
        for method in methods:
            self.assertFalse(
                any(isinstance(node, (ast.For, ast.AsyncFor, ast.While)) for node in ast.walk(method)),
                method.name,
            )


if __name__ == "__main__":
    unittest.main()
