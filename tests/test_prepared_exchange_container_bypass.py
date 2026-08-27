from __future__ import annotations

import unittest

from marketplace.reference import TYPE_INTENT, federation_v1
from marketplace.reference.transport_json_v1 import encode_transport_envelope_json
from marketplace.runtime import FederationOperationProfile, compose_offline_federation_service, create_in_memory_runtime
from marketplace.runtime.prepared_integrity import prepared_exchange_integrity_snapshot

SOURCE = "https://peer.example/federation"


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


class PreparedExchangeContainerBypassTests(unittest.TestCase):
    def test_explicit_base_dict_and_list_mutation_cannot_change_authoritative_payload_or_bytes(self):
        runtime = create_in_memory_runtime(
            validate_record=lambda value: value,
            record_identity_text=lambda value: "r1_" + "A" * 43,
            evaluate_discovery=lambda *args, **kwargs: {},
            evaluate_match=lambda *args, **kwargs: {},
            max_entries=8,
        )
        try:
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
            expected = _request()
            prepared = service.prepare(_request())
            before_bytes = encode_transport_envelope_json(prepared.envelope)
            before_snapshot = prepared.integrity_snapshot

            payload = prepared.envelope[3]
            scope = payload["scope"]
            record_types = scope["record_types"]
            capabilities = payload["required_capabilities"]

            # Directly invoke built-in base mutation primitives. M30's authoritative
            # data lives in private tuples, so these calls can touch only ignored
            # empty base-class storage and cannot affect Mapping/list behavior used
            # by Marketplace or the pinned OLP encoder.
            dict.__setitem__(payload, "source", "https://attacker.example/federation")
            dict.__setitem__(payload, "page_size", 1)
            dict.__setitem__(scope, "version", 2)
            list.append(record_types, "https://attacker.example/type")
            list.append(capabilities, "https://attacker.example/capability")

            self.assertEqual(payload, expected)
            self.assertEqual(payload["source"], SOURCE)
            self.assertEqual(payload["page_size"], 4)
            self.assertEqual(scope["version"], 1)
            self.assertEqual(record_types, [TYPE_INTENT])
            self.assertEqual(capabilities, [federation_v1.CAP_SYNC])
            self.assertEqual(dict(payload), expected)
            self.assertEqual(list(record_types), [TYPE_INTENT])
            self.assertEqual(list(capabilities), [federation_v1.CAP_SYNC])

            after_bytes = encode_transport_envelope_json(prepared.envelope)
            after_snapshot = prepared_exchange_integrity_snapshot(prepared.binding, prepared.envelope)
            self.assertEqual(after_bytes, before_bytes)
            self.assertEqual(after_snapshot, before_snapshot)
        finally:
            runtime.close()


if __name__ == "__main__":
    unittest.main()
