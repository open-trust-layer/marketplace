from __future__ import annotations

import ast
import dataclasses
import inspect
import unittest

import marketplace.runtime.inbound_http_stream as stream_module
from marketplace.runtime.inbound_http import (
    ROUTE_IMMUTABLE_RECORD,
    BoundedInboundHttpApplicationAdapter,
    InboundHttpApplicationLimits,
    PreparedInboundHttpResponse,
)
from marketplace.runtime.inbound_http_stream import (
    PROGRESS_COMPLETE,
    PROGRESS_NEED_MORE,
    BoundedInboundHttpStreamAssembler,
    InboundHttpStreamError,
    InboundHttpStreamLimits,
    InboundHttpStreamProgress,
)
from marketplace.runtime.inbound_http_wire import (
    BoundedInboundHttpWireAdapter,
    PreparedInboundHttpWireExchange,
)
from marketplace.runtime.inbound_record import INBOUND_RECORD_RETRIEVAL_OPERATION
from marketplace.runtime.record_retrieval import _get_request_bytes

AUTHORITY = "market.example"
RECORD_ID = "r1_qcU6rT-ADJiC75Bg9w7qLSvauhY6zcEmy1dk-LrRlZc"


class _ExplodingIterable:
    def __iter__(self):
        raise AssertionError("arbitrary iterable MUST NOT be enumerated")


class _ApplicationHarness:
    def __init__(self):
        self.calls = []
        adapter = object.__new__(BoundedInboundHttpApplicationAdapter)
        object.__setattr__(adapter, "_limits", InboundHttpApplicationLimits())
        object.__setattr__(adapter, "handle", self._handle)
        self.adapter = adapter

    def _handle(self, request):
        self.calls.append(request)
        body = b'{"olp":"prepared"}'
        return PreparedInboundHttpResponse(
            request=request,
            route_kind=ROUTE_IMMUTABLE_RECORD,
            route_operation=INBOUND_RECORD_RETRIEVAL_OPERATION,
            status_code=200,
            headers=(
                ("connection", "close"),
                ("content-length", str(len(body))),
                ("content-type", "application/json"),
            ),
            body=body,
            olp_message_type="record",
        )


class InboundHttpStreamHardeningTests(unittest.TestCase):
    def setUp(self):
        self.harness = _ApplicationHarness()
        self.wire = BoundedInboundHttpWireAdapter(
            application_adapter=self.harness.adapter,
            authority=AUTHORITY,
        )
        self.assembler = BoundedInboundHttpStreamAssembler(wire_adapter=self.wire)
        self.raw = _get_request_bytes(f"/v1/records/{RECORD_ID}", AUTHORITY, 443)

    def test_arbitrary_chunk_iterable_is_rejected_without_enumeration(self):
        with self.assertRaises(InboundHttpStreamError) as caught:
            self.assembler.prepare_chunks(_ExplodingIterable())
        self.assertEqual(caught.exception.code, "INVALID_CHUNK_COLLECTION")
        self.assertEqual(self.harness.calls, [])

    def test_chunk_count_limit_is_checked_before_chunk_validation(self):
        assembler = BoundedInboundHttpStreamAssembler(
            wire_adapter=self.wire,
            limits=InboundHttpStreamLimits(max_chunks=1, max_chunk_bytes=64),
        )
        with self.assertRaises(InboundHttpStreamError) as caught:
            assembler.prepare_chunks((b"not-http", b"also-not-http"))
        self.assertEqual(caught.exception.code, "CHUNK_COUNT_LIMIT_EXCEEDED")
        self.assertEqual(self.harness.calls, [])

    def test_chunk_size_limit_is_checked_before_copy_or_disclosure(self):
        assembler = BoundedInboundHttpStreamAssembler(
            wire_adapter=self.wire,
            limits=InboundHttpStreamLimits(max_chunks=4, max_chunk_bytes=8),
        )
        with self.assertRaises(InboundHttpStreamError) as caught:
            assembler.prepare_chunks((b"x" * 9,))
        self.assertEqual(caught.exception.code, "CHUNK_SIZE_LIMIT_EXCEEDED")
        self.assertEqual(self.harness.calls, [])

    def test_stream_limits_are_detached_from_caller_alias(self):
        limits = InboundHttpStreamLimits(max_chunks=2, max_chunk_bytes=128)
        assembler = BoundedInboundHttpStreamAssembler(wire_adapter=self.wire, limits=limits)
        object.__setattr__(limits, "max_chunks", 1024)
        object.__setattr__(limits, "max_chunk_bytes", 1024 * 1024)
        self.assertEqual(assembler.limits.max_chunks, 2)
        self.assertEqual(assembler.limits.max_chunk_bytes, 128)

    def test_prepare_chunks_uses_single_join_and_single_progress_probe(self):
        source = inspect.getsource(BoundedInboundHttpStreamAssembler.prepare_chunks)
        self.assertNotIn("bytearray(", source)
        self.assertIn('raw = b"".join(chunks)', source)
        self.assertEqual(source.count("self.probe(raw)"), 1)
        self.assertLess(source.index("for chunk in chunks:"), source.index('raw = b"".join(chunks)'))

    def test_attacker_sized_decimal_length_is_textually_rejected_before_bounded_conversion(self):
        raw = (
            "POST /v1/federation/snapshot HTTP/1.1\r\n"
            f"Host: {AUTHORITY}\r\n"
            "Content-Type: application/json\r\n"
            "Accept: application/json\r\n"
            "Connection: close\r\n"
            f"Content-Length: {'9' * 1024}\r\n\r\n"
        ).encode("ascii")
        with self.assertRaises(InboundHttpStreamError) as caught:
            self.assembler.probe(raw)
        self.assertEqual(caught.exception.code, "DECLARED_BODY_LIMIT_EXCEEDED")
        self.assertEqual(self.harness.calls, [])

        source = inspect.getsource(stream_module)
        self.assertLess(
            source.index("_decimal_exceeds_bound(declared, body_limit)"),
            source.index("return int(declared)"),
        )
        tree = ast.parse(source)
        int_args = [
            ast.unparse(node.args[0])
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "int"
            and node.args
        ]
        self.assertEqual(int_args, ["declared"])

    def test_noncanonical_m35_head_fails_closed_with_stable_wire_code(self):
        raw = (
            f"GET /v1/records/{RECORD_ID} HTTP/1.1\r\n"
            f"host: {AUTHORITY}\r\n"
            "Connection: close\r\n\r\n"
        ).encode("ascii")
        with self.assertRaises(InboundHttpStreamError) as caught:
            self.assembler.probe(raw)
        self.assertEqual(caught.exception.code, "WIRE_PROFILE_REJECTED")
        self.assertEqual(caught.exception.wire_code, "NONCANONICAL_HEADER_NAME")
        self.assertEqual(self.harness.calls, [])

    def test_m35_authority_promotion_is_rejected_after_one_application_call(self):
        original_prepare = self.wire.prepare

        def hostile_prepare(raw):
            result = original_prepare(raw)
            object.__setattr__(result, "transmitted", True)
            return result

        object.__setattr__(self.wire, "prepare", hostile_prepare)
        with self.assertRaises(InboundHttpStreamError) as caught:
            self.assembler.prepare_chunks((self.raw,))
        self.assertEqual(caught.exception.code, "WIRE_AUTHORITY_ESCALATION")
        self.assertEqual(len(self.harness.calls), 1)

    def test_m35_original_integrity_witness_blocks_post_prepare_route_mutation(self):
        original_prepare = self.wire.prepare

        def hostile_prepare(raw):
            result = original_prepare(raw)
            object.__setattr__(result, "route_operation", "https://example.test/changed")
            return result

        object.__setattr__(self.wire, "prepare", hostile_prepare)
        with self.assertRaises(InboundHttpStreamError) as caught:
            self.assembler.prepare_chunks((self.raw,))
        self.assertEqual(caught.exception.code, "WIRE_INTEGRITY_DRIFT")
        self.assertEqual(len(self.harness.calls), 1)

    def test_self_consistent_wrong_m35_request_is_rejected_by_stream_binding(self):
        original_prepare = self.wire.prepare

        def hostile_prepare(raw):
            result = original_prepare(raw)
            wrong_request = dataclasses.replace(result.request, path="/v1/records/other")
            return PreparedInboundHttpWireExchange(
                request=wrong_request,
                host_authority=result.host_authority,
                route_kind=result.route_kind,
                route_operation=result.route_operation,
                status_code=result.status_code,
                response_body_bytes=result.response_body_bytes,
                response_bytes=result.response_bytes,
                olp_message_type=result.olp_message_type,
            )

        object.__setattr__(self.wire, "prepare", hostile_prepare)
        with self.assertRaises(InboundHttpStreamError) as caught:
            self.assembler.prepare_chunks((self.raw,))
        self.assertEqual(caught.exception.code, "WIRE_REQUEST_BINDING_DRIFT")

    def test_self_consistent_wrong_m35_authority_is_rejected_by_stream_binding(self):
        original_prepare = self.wire.prepare

        def hostile_prepare(raw):
            result = original_prepare(raw)
            return PreparedInboundHttpWireExchange(
                request=result.request,
                host_authority="other.example",
                route_kind=result.route_kind,
                route_operation=result.route_operation,
                status_code=result.status_code,
                response_body_bytes=result.response_body_bytes,
                response_bytes=result.response_bytes,
                olp_message_type=result.olp_message_type,
            )

        object.__setattr__(self.wire, "prepare", hostile_prepare)
        with self.assertRaises(InboundHttpStreamError) as caught:
            self.assembler.prepare_chunks((self.raw,))
        self.assertEqual(caught.exception.code, "WIRE_AUTHORITY_BINDING_DRIFT")

    def test_prepared_stream_witness_blocks_dataclass_rebinding(self):
        prepared = self.assembler.prepare_chunks((self.raw,))
        with self.assertRaises(ValueError):
            dataclasses.replace(prepared, request_bytes=prepared.request_bytes + 1)

    def test_prepared_stream_detects_nested_m35_integrity_drift(self):
        prepared = self.assembler.prepare_chunks((self.raw,))
        object.__setattr__(prepared.wire_exchange, "route_operation", "https://example.test/changed")
        with self.assertRaises(ValueError):
            prepared.__post_init__()

    def test_prepared_result_does_not_retain_raw_chunk_collection_or_assembled_bytes(self):
        prepared = self.assembler.prepare_chunks((self.raw[:20], self.raw[20:]))
        fields = {field.name for field in dataclasses.fields(prepared)}
        self.assertNotIn("chunks", fields)
        self.assertNotIn("raw_request", fields)
        self.assertNotIn("assembled", fields)
        self.assertFalse(any(value is self.raw for value in vars(prepared).values()))

    def test_progress_invariants_fail_closed(self):
        with self.assertRaises(ValueError):
            InboundHttpStreamProgress(
                state=PROGRESS_COMPLETE,
                buffered_bytes=10,
                expected_total_bytes=11,
                missing_bytes=1,
                head_complete=True,
                head_validated=True,
                request_complete=True,
            )
        with self.assertRaises(ValueError):
            InboundHttpStreamProgress(
                state=PROGRESS_NEED_MORE,
                buffered_bytes=10,
                expected_total_bytes=10,
                missing_bytes=0,
                head_complete=True,
                head_validated=True,
                request_complete=False,
            )

    def test_m36_source_has_no_network_tls_server_reader_writer_process_background_filesystem_or_logging_surface(self):
        source = inspect.getsource(stream_module)
        tree = ast.parse(source)
        forbidden_roots = {
            "socket",
            "ssl",
            "http",
            "urllib",
            "asyncio",
            "threading",
            "subprocess",
            "logging",
            "pathlib",
            "os",
        }
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name.split(".", 1)[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.split(".", 1)[0])
        self.assertTrue(imported.isdisjoint(forbidden_roots), imported & forbidden_roots)
        for token in (
            ".recv(",
            ".read(",
            ".send(",
            ".sendall(",
            ".write(",
            ".listen(",
            ".accept(",
        ):
            self.assertNotIn(token, source)


if __name__ == "__main__":
    unittest.main()
