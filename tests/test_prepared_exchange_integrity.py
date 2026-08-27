from __future__ import annotations

import ast
import dataclasses
import unittest
from pathlib import Path

from marketplace.reference import TYPE_INTENT, federation_v1
from marketplace.reference.transport_json_v1 import encode_transport_envelope_json
from marketplace.runtime import FederationOperationProfile, compose_offline_federation_service, create_in_memory_runtime
from marketplace.runtime.federation import FederationRequestBinding, PreparedFederationExchange
from marketplace.runtime.prepared_integrity import (
    MAX_PREPARED_SNAPSHOT_DEPTH,
    MAX_PREPARED_SNAPSHOT_ITEMS,
    FrozenDict,
    FrozenList,
    PreparedExchangeIntegrityError,
)

SOURCE = "https://peer.example/federation"


def _runtime_and_service():
    runtime = create_in_memory_runtime(
        validate_record=lambda value: value,
        record_identity_text=lambda value: "r1_" + "A" * 43,
        evaluate_discovery=lambda *args, **kwargs: {},
        evaluate_match=lambda *args, **kwargs: {},
        max_entries=8,
    )
    service = compose_offline_federation_service(
        runtime,
        validate_record=lambda value: value,
        record_identity_text=lambda value: "r1_" + "A" * 43,
        validate_exchange_request=federation_v1.validate_exchange_request,
        make_transport_envelope=federation_v1.make_transport_envelope,
        validate_transport_envelope=federation_v1.validate_transport_envelope,
        validate_exchange_result=federation_v1.validate_exchange_result,
        operation_profiles=(
            FederationOperationProfile(
                federation_v1.OP_SYNC,
                federation_v1.MSG_SYNC_REQUEST,
                federation_v1.MSG_SYNC_RESULT,
            ),
        ),
    )
    return runtime, service


def _request() -> dict[str, object]:
    return {
        "version": 1,
        "source": SOURCE,
        "operation": federation_v1.OP_SYNC,
        "scope": {"version": 1, "record_types": [TYPE_INTENT]},
        "required_capabilities": [federation_v1.CAP_SYNC],
        "page_size": 4,
        "cursor": b"page-2",
    }


class PreparedExchangeIntegrityTests(unittest.TestCase):
    def test_prepare_detaches_original_request_and_preserves_encoder_compatibility(self):
        runtime, service = _runtime_and_service()
        try:
            request = _request()
            expected = _request()
            prepared = service.prepare(request)

            request["source"] = "https://attacker.example/federation"
            request["page_size"] = 1
            request["cursor"] = b"attacker"
            request["scope"]["record_types"].clear()
            request["required_capabilities"].clear()

            payload = prepared.envelope[3]
            self.assertEqual(payload, expected)
            self.assertIsInstance(payload, FrozenDict)
            self.assertIsInstance(payload["scope"], FrozenDict)
            self.assertIsInstance(payload["scope"]["record_types"], FrozenList)
            self.assertIsInstance(payload["required_capabilities"], FrozenList)
            encoded = encode_transport_envelope_json(prepared.envelope)
            self.assertIsInstance(encoded, bytes)
            self.assertGreater(len(encoded), 0)
        finally:
            runtime.close()

    def test_prepared_payload_rejects_top_level_and_nested_mutation(self):
        runtime, service = _runtime_and_service()
        try:
            prepared = service.prepare(_request())
            payload = prepared.envelope[3]
            with self.assertRaises(TypeError):
                payload["operation"] = federation_v1.OP_SNAPSHOT
            with self.assertRaises(TypeError):
                payload["scope"]["record_types"].append(TYPE_INTENT)
            with self.assertRaises(TypeError):
                payload["required_capabilities"].clear()
            with self.assertRaises(TypeError):
                payload["scope"]["version"] = 2
        finally:
            runtime.close()

    def test_dataclass_replace_cannot_rebind_old_integrity_snapshot(self):
        runtime, service = _runtime_and_service()
        try:
            prepared = service.prepare(_request())
            hostile_binding = dataclasses.replace(prepared.binding, page_size=1)
            with self.assertRaises(PreparedExchangeIntegrityError) as caught:
                dataclasses.replace(prepared, binding=hostile_binding)
            self.assertEqual(caught.exception.code, "INTEGRITY_SNAPSHOT_MISMATCH")

            hostile_payload = dict(prepared.envelope[3])
            hostile_payload["page_size"] = 1
            hostile_envelope = prepared.envelope[:3] + (hostile_payload,)
            with self.assertRaises(PreparedExchangeIntegrityError) as caught:
                dataclasses.replace(prepared, envelope=hostile_envelope)
            self.assertEqual(caught.exception.code, "INTEGRITY_SNAPSHOT_MISMATCH")
        finally:
            runtime.close()

    def test_manual_constructor_also_detaches_payload_aliases(self):
        payload = {"version": 1, "nested": {"values": [1, 2, 3]}}
        prepared = PreparedFederationExchange(
            binding=FederationRequestBinding(
                source="https://source.example",
                operation=federation_v1.OP_SYNC,
                scope_fingerprint="scope",
                required_capabilities=(federation_v1.CAP_SYNC,),
                page_size=4,
                expected_result_message_type=federation_v1.MSG_SYNC_RESULT,
            ),
            envelope=("OLP-TRANSPORT", 1, federation_v1.MSG_SYNC_REQUEST, payload),
        )
        payload["version"] = 2
        payload["nested"]["values"].append(4)
        self.assertEqual(prepared.envelope[3]["version"], 1)
        self.assertEqual(prepared.envelope[3]["nested"]["values"], [1, 2, 3])

    def test_snapshot_bounds_fail_closed(self):
        binding = FederationRequestBinding(
            source="https://source.example",
            operation=federation_v1.OP_SYNC,
            scope_fingerprint="scope",
            required_capabilities=(federation_v1.CAP_SYNC,),
            page_size=4,
            expected_result_message_type=federation_v1.MSG_SYNC_RESULT,
        )
        oversized = {str(index): index for index in range(MAX_PREPARED_SNAPSHOT_ITEMS + 1)}
        with self.assertRaises(PreparedExchangeIntegrityError) as caught:
            PreparedFederationExchange(
                binding=binding,
                envelope=("OLP-TRANSPORT", 1, federation_v1.MSG_SYNC_REQUEST, oversized),
            )
        self.assertEqual(caught.exception.code, "SNAPSHOT_ITEM_LIMIT")

        nested: object = {"leaf": 1}
        for _ in range(MAX_PREPARED_SNAPSHOT_DEPTH + 1):
            nested = {"nested": nested}
        with self.assertRaises(PreparedExchangeIntegrityError) as caught:
            PreparedFederationExchange(
                binding=binding,
                envelope=("OLP-TRANSPORT", 1, federation_v1.MSG_SYNC_REQUEST, nested),
            )
        self.assertEqual(caught.exception.code, "SNAPSHOT_DEPTH_EXCEEDED")

    def test_snapshot_distinguishes_boolean_and_integer_scalars(self):
        binding = FederationRequestBinding(
            source="https://source.example",
            operation=federation_v1.OP_SYNC,
            scope_fingerprint="scope",
            required_capabilities=(federation_v1.CAP_SYNC,),
            page_size=4,
            expected_result_message_type=federation_v1.MSG_SYNC_RESULT,
        )
        prepared_int = PreparedFederationExchange(
            binding=binding,
            envelope=("OLP-TRANSPORT", 1, federation_v1.MSG_SYNC_REQUEST, {"value": 1}),
        )
        prepared_bool = PreparedFederationExchange(
            binding=binding,
            envelope=("OLP-TRANSPORT", 1, federation_v1.MSG_SYNC_REQUEST, {"value": True}),
        )
        self.assertNotEqual(prepared_int.integrity_snapshot, prepared_bool.integrity_snapshot)

    def test_m30_integrity_module_has_no_network_filesystem_process_concurrency_or_logging_surface(self):
        source_path = Path(__file__).resolve().parents[1] / "src" / "marketplace" / "runtime" / "prepared_integrity.py"
        tree = ast.parse(source_path.read_text(encoding="utf-8"))
        forbidden = {
            "socket",
            "ssl",
            "urllib",
            "http",
            "requests",
            "httpx",
            "aiohttp",
            "pathlib",
            "os",
            "subprocess",
            "threading",
            "asyncio",
            "concurrent",
            "logging",
        }
        imported: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name.split(".", 1)[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.split(".", 1)[0])
        self.assertEqual(imported & forbidden, set())


if __name__ == "__main__":
    unittest.main()
