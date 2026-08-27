from __future__ import annotations

import ast
import inspect
import types
import unittest
from unittest.mock import patch

import marketplace.runtime.inbound_http_response_write_outcome as m47
from marketplace.runtime.inbound_http_response_write_outcome import (
    BoundedInboundHttpResponseWriteOutcomeHandler,
    InboundHttpResponseWriteOutcome,
    InboundHttpResponseWriteOutcomeError,
)
from marketplace.runtime.inbound_http_response_write_session import (
    BoundedInboundHttpResponseWriteSession,
)
from test_inbound_http_response_write_outcome import _parts


class InboundHttpResponseWriteOutcomeHardeningTests(unittest.TestCase):
    def test_public_m46_method_replacement_after_construction_cannot_substitute_authority(self):
        _, _, _, _, handler = _parts()
        with patch.object(
            BoundedInboundHttpResponseWriteSession,
            "progress",
            lambda self: (_ for _ in ()).throw(AssertionError("public substitution")),
        ), patch.object(
            BoundedInboundHttpResponseWriteSession,
            "accept_write_count",
            lambda self, count: (_ for _ in ()).throw(AssertionError("public substitution")),
        ):
            result = handler.accept_outcome(InboundHttpResponseWriteOutcome.progress(1))
        self.assertEqual(result.bytes_written, 1)

    def test_coherent_private_function_and_bound_rebinding_fails_binding_witness(self):
        _, _, _, session, handler = _parts()

        def hostile(self):
            raise AssertionError("must never execute")

        handler._progress_function = hostile
        handler._progress = types.MethodType(hostile, session)
        with self.assertRaises(InboundHttpResponseWriteOutcomeError) as ctx:
            handler.progress()
        self.assertEqual(ctx.exception.code, "WRITE_OUTCOME_BINDING_DRIFT")

    def test_promoted_original_m46_progress_is_rejected_before_dataclass_replay(self):
        original = BoundedInboundHttpResponseWriteSession.progress

        def hostile(self):
            result = original(self)
            object.__setattr__(result, "transmitted", True)
            return result

        _, _, _, session, _ = _parts()
        with patch.object(BoundedInboundHttpResponseWriteSession, "progress", hostile):
            handler = BoundedInboundHttpResponseWriteOutcomeHandler(write_session=session)
            with self.assertRaises(InboundHttpResponseWriteOutcomeError) as ctx:
                handler.progress()
        self.assertEqual(ctx.exception.code, "WRITE_OUTCOME_PROGRESS_AUTHORITY")

    def test_promoted_original_m46_completion_is_rejected_before_dataclass_replay(self):
        original = BoundedInboundHttpResponseWriteSession.take_completed

        def hostile(self):
            result = original(self)
            object.__setattr__(result, "transmitted", True)
            return result

        prepared, _, _, session, _ = _parts(max_write_bytes=1_000_000)
        session.accept_write_count(prepared.response_bytes)
        with patch.object(BoundedInboundHttpResponseWriteSession, "take_completed", hostile):
            handler = BoundedInboundHttpResponseWriteOutcomeHandler(write_session=session)
            with self.assertRaises(InboundHttpResponseWriteOutcomeError) as ctx:
                handler.take_completed()
        self.assertEqual(ctx.exception.code, "WRITE_OUTCOME_COMPLETION_AUTHORITY")

    def test_forged_returned_progress_accounting_is_terminal(self):
        original = BoundedInboundHttpResponseWriteSession.accept_write_count

        def hostile(self, count):
            result = original(self, count)
            object.__setattr__(result, "last_accepted_write_bytes", count + 1)
            object.__setattr__(result, "integrity_snapshot", None)
            return result

        _, _, _, session, _ = _parts()
        with patch.object(BoundedInboundHttpResponseWriteSession, "accept_write_count", hostile):
            handler = BoundedInboundHttpResponseWriteOutcomeHandler(write_session=session)
            with self.assertRaises(InboundHttpResponseWriteOutcomeError) as ctx:
                handler.accept_outcome(InboundHttpResponseWriteOutcome.progress(1))
        self.assertEqual(ctx.exception.code, "WRITE_OUTCOME_PROGRESS_DRIFT")
        self.assertTrue(session.closed)
        self.assertIsNone(session._prepared_response)

    def test_terminal_rejection_never_retries_lower_accept(self):
        _, _, _, session, handler = _parts(max_write_bytes=1)
        calls = 0
        original = handler._accept

        def counted(count):
            nonlocal calls
            calls += 1
            return original(count)

        handler._accept = counted
        # The altered callable is intentionally not a valid captured bound method.
        with self.assertRaises(InboundHttpResponseWriteOutcomeError) as ctx:
            handler.accept_outcome(InboundHttpResponseWriteOutcome.progress(2))
        self.assertEqual(ctx.exception.code, "WRITE_OUTCOME_BINDING_DRIFT")
        self.assertEqual(calls, 0)
        session.close()

    def test_outcome_and_progress_witnesses_contain_no_raw_response_bytes(self):
        prepared, _, _, _, handler = _parts()
        raw = prepared.wire_exchange.response_bytes
        outcome = InboundHttpResponseWriteOutcome.progress(1)
        progress = handler.progress()
        self.assertNotIn(raw, outcome.integrity_snapshot)
        self.assertNotIn(raw, progress.integrity_snapshot)
        self.assertFalse(hasattr(outcome, "response"))
        self.assertFalse(hasattr(progress, "response"))

    def test_source_has_no_writer_network_tls_process_persistence_or_loop_surface(self):
        source = inspect.getsource(m47)
        tree = ast.parse(source)
        imports = {
            alias.name.split(".")[0]
            for node in ast.walk(tree)
            if isinstance(node, (ast.Import, ast.ImportFrom))
            for alias in node.names
        }
        self.assertTrue(
            imports.isdisjoint(
                {
                    "socket",
                    "ssl",
                    "http",
                    "urllib",
                    "requests",
                    "subprocess",
                    "asyncio",
                    "threading",
                    "logging",
                    "pathlib",
                }
            )
        )
        accept_source = inspect.getsource(
            m47.BoundedInboundHttpResponseWriteOutcomeHandler.accept_outcome
        )
        self.assertNotIn("writer(", accept_source)
        self.assertNotIn("send(", accept_source)
        self.assertNotIn("while ", accept_source)
        self.assertNotIn("for ", accept_source)


if __name__ == "__main__":
    unittest.main()
