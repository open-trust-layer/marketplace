from __future__ import annotations

import ast
from dataclasses import replace
from pathlib import Path
import unittest
from unittest.mock import Mock

from olp import RecordV1

from marketplace.reference import (
    CORE_PROFILE,
    TYPE_INTENT,
    federation_v1,
    record_identity_text,
    validate_market_record,
)
from marketplace.reference.inbound_http_v1 import (
    decode_inbound_control_envelope_json,
    encode_prepared_inbound_response_json,
)
from marketplace.reference.record_serving_v1 import (
    make_record_transport_envelope,
    market_record_transport_payload,
    verify_prepared_record_transport_envelope,
)
from marketplace.reference.transport_json_v1 import encode_transport_envelope_json
from marketplace.runtime.federation import FederationOperationProfile
from marketplace.runtime.inbound_federation import (
    BoundedInboundFederationResponder,
    InboundFederationPageMaterial,
)
from marketplace.runtime.inbound_http import (
    BoundedInboundHttpApplicationAdapter,
    InboundFederationHttpRoute,
    InboundHttpApplicationLimits,
    InboundHttpError,
    InboundHttpRequest,
)
from marketplace.runtime.inbound_record import BoundedInboundRecordResponder

SOURCE = "urn:example:source:m34-hardening"
SNAPSHOT_PATH = "/v1/federation/snapshot"
SYNC_PATH = "/v1/federation/sync"
ACTION = "https://example.test/actions/sell"
SUBJECT = "urn:example:item:m34-hardening"


def record(principal: str = "did:example:alice", *, subject: str = SUBJECT) -> RecordV1:
    return RecordV1.from_mapping(
        {
            "envelope_version": 1,
            "type": TYPE_INTENT,
            "content": {
                "version": 1,
                "issuer": {"principal": principal},
                "subjects": [{"uri": subject}],
                "action": {"id": ACTION},
                "terms": {},
            },
            "profiles": [CORE_PROFILE],
        }
    )


def scope() -> dict[str, object]:
    return {"version": 1, "record_types": [TYPE_INTENT]}


def capabilities() -> dict[str, object]:
    caps = sorted(
        [federation_v1.CAP_SNAPSHOT, federation_v1.CAP_SYNC],
        key=lambda value: value.encode("utf-8"),
    )
    return {
        "version": 1,
        "source": SOURCE,
        "implemented": caps,
        "enabled": caps,
        "configured": caps,
        "limits": {
            "max_page_records": federation_v1.MAX_PAGE_RECORDS,
            "max_cursor_bytes": federation_v1.MAX_CURSOR_BYTES,
            "max_submission_records": federation_v1.MAX_SUBMISSION_RECORDS,
        },
    }


def profiles() -> tuple[FederationOperationProfile, ...]:
    return (
        FederationOperationProfile(
            federation_v1.OP_SNAPSHOT,
            federation_v1.MSG_SNAPSHOT_REQUEST,
            federation_v1.MSG_SNAPSHOT_RESULT,
        ),
        FederationOperationProfile(
            federation_v1.OP_SYNC,
            federation_v1.MSG_SYNC_REQUEST,
            federation_v1.MSG_SYNC_RESULT,
        ),
    )


def request_envelope(*, operation: str = federation_v1.OP_SNAPSHOT):
    capability = {
        federation_v1.OP_SNAPSHOT: federation_v1.CAP_SNAPSHOT,
        federation_v1.OP_SYNC: federation_v1.CAP_SYNC,
    }[operation]
    message_type = {
        federation_v1.OP_SNAPSHOT: federation_v1.MSG_SNAPSHOT_REQUEST,
        federation_v1.OP_SYNC: federation_v1.MSG_SYNC_REQUEST,
    }[operation]
    return federation_v1.make_transport_envelope(
        message_type,
        {
            "version": 1,
            "source": SOURCE,
            "operation": operation,
            "scope": scope(),
            "required_capabilities": [capability],
            "page_size": 2,
        },
    )


class FakeSource:
    def __init__(self, value):
        self.value = value
        self.calls: list[str] = []

    def get(self, record_id: str):
        self.calls.append(record_id)
        return self.value


def federation_responder(*, authorize=None, page_source=None):
    return BoundedInboundFederationResponder(
        local_source=SOURCE,
        validate_transport_envelope=federation_v1.validate_transport_envelope,
        validate_exchange_request=federation_v1.validate_exchange_request,
        scope_fingerprint=federation_v1.scope_fingerprint,
        negotiate_capabilities=federation_v1.negotiate_capabilities,
        capability_advertisement=capabilities(),
        evaluate_exchange_page=federation_v1.evaluate_exchange_page,
        validate_exchange_result=federation_v1.validate_exchange_result,
        make_transport_envelope=federation_v1.make_transport_envelope,
        validate_record=validate_market_record,
        record_identity_text=record_identity_text,
        authorize_disclosure=authorize or (lambda context: True),
        page_source=page_source
        or (
            lambda context: InboundFederationPageMaterial(
                records=(),
                source_completeness="PARTIAL_SOURCE",
                page_truncated=False,
            )
        ),
        operation_profiles=profiles(),
    )


def record_responder(source: FakeSource, *, authorize=None):
    return BoundedInboundRecordResponder(
        local_source=SOURCE,
        record_source=source,
        authorize_disclosure=authorize or (lambda context: True),
        validate_record=validate_market_record,
        record_identity=record_identity_text,
        prepare_payload=market_record_transport_payload,
        make_record_envelope=make_record_transport_envelope,
        verify_record_envelope=verify_prepared_record_transport_envelope,
    )


def service(*, federation=None, records=None, decoder=None, encoder=None, limits=None):
    return BoundedInboundHttpApplicationAdapter(
        federation_responder=federation or federation_responder(),
        record_responder=records or record_responder(FakeSource(record())),
        control_routes=(
            InboundFederationHttpRoute(SNAPSHOT_PATH, federation_v1.OP_SNAPSHOT),
            InboundFederationHttpRoute(SYNC_PATH, federation_v1.OP_SYNC),
        ),
        decode_transport_envelope_json=decoder or decode_inbound_control_envelope_json,
        encode_transport_envelope_json=encoder or encode_prepared_inbound_response_json,
        limits=limits,
    )


def post(*, path: str = SNAPSHOT_PATH, operation: str = federation_v1.OP_SNAPSHOT):
    body = encode_transport_envelope_json(request_envelope(operation=operation))
    return InboundHttpRequest(
        method="POST",
        path=path,
        headers=(
            ("content-length", str(len(body))),
            ("content-type", "application/json"),
        ),
        body=body,
    )


def get(record_id: str):
    return InboundHttpRequest(
        method="GET",
        path=f"/v1/records/{record_id}",
        headers=(),
        body=b"",
    )


class InboundHttpHardeningTests(unittest.TestCase):
    def test_forged_m32_authority_promotion_is_rejected(self):
        federation = federation_responder()
        prepared = federation.prepare_response(
            request_envelope(),
            operation=federation_v1.OP_SNAPSHOT,
        )
        object.__setattr__(prepared, "establishes_truth", True)
        federation.prepare_response = lambda envelope, *, operation: prepared

        with self.assertRaises(InboundHttpError) as raised:
            service(federation=federation).handle(post())
        self.assertEqual(raised.exception.code, "FEDERATION_RESPONDER_AUTHORITY_ESCALATION")

    def test_forged_m33_authority_promotion_is_rejected(self):
        expected = record()
        record_id = record_identity_text(expected)
        records = record_responder(FakeSource(expected))
        prepared = records.prepare(requested_record_identity=record_id)
        object.__setattr__(prepared, "establishes_authority", True)
        records.prepare = lambda *, requested_record_identity: prepared

        with self.assertRaises(InboundHttpError) as raised:
            service(records=records).handle(get(record_id))
        self.assertEqual(raised.exception.code, "RECORD_RESPONDER_AUTHORITY_ESCALATION")

    def test_m32_result_operation_cannot_drift_from_selected_route(self):
        federation = federation_responder()
        snapshot = federation.prepare_response(
            request_envelope(operation=federation_v1.OP_SNAPSHOT),
            operation=federation_v1.OP_SNAPSHOT,
        )
        federation.prepare_response = lambda envelope, *, operation: snapshot

        with self.assertRaises(InboundHttpError) as raised:
            service(federation=federation).handle(post(path=SYNC_PATH, operation=federation_v1.OP_SYNC))
        self.assertEqual(raised.exception.code, "FEDERATION_ROUTE_BINDING_DRIFT")

    def test_m33_result_identity_cannot_drift_from_selected_record_path(self):
        first = record("did:example:alice")
        second = record("did:example:bob", subject="urn:example:item:other")
        first_id = record_identity_text(first)
        second_id = record_identity_text(second)
        records = record_responder(FakeSource(second))
        prepared = records.prepare(requested_record_identity=second_id)
        records.prepare = lambda *, requested_record_identity: prepared

        with self.assertRaises(InboundHttpError) as raised:
            service(records=records).handle(get(first_id))
        self.assertEqual(raised.exception.code, "RECORD_ROUTE_BINDING_DRIFT")

    def test_response_round_trip_decoder_cannot_hide_serialization_drift(self):
        calls = 0

        def decoder(body: bytes):
            nonlocal calls
            calls += 1
            decoded = decode_inbound_control_envelope_json(body)
            if calls == 2:
                return (decoded[0], decoded[1], "attacker-type", decoded[3])
            return decoded

        with self.assertRaises(InboundHttpError) as raised:
            service(decoder=decoder).handle(post())
        self.assertEqual(raised.exception.code, "RESPONSE_SERIALIZATION_DRIFT")

    def test_base_dict_mutation_by_encoder_cannot_change_authoritative_response(self):
        def encoder(envelope):
            payload = envelope[3]
            dict.__setitem__(payload, "attacker", True)
            return encode_prepared_inbound_response_json(envelope)

        prepared = service(encoder=encoder).handle(post())
        decoded = decode_inbound_control_envelope_json(prepared.body)
        self.assertNotIn("attacker", decoded[3])

    def test_prepared_http_integrity_snapshot_blocks_route_rebinding(self):
        prepared = service().handle(post())
        with self.assertRaises(ValueError):
            replace(
                prepared,
                route_operation="https://example.test/runtime/operation/other",
            )

    def test_arbitrary_header_iterable_is_rejected_without_enumeration(self):
        class HostileHeaders:
            def __iter__(self):
                raise AssertionError("headers MUST NOT be enumerated")

        with self.assertRaises(ValueError):
            InboundHttpRequest(
                method="GET",
                path="/v1/records/not-used",
                headers=HostileHeaders(),
                body=b"",
            )

    def test_arbitrary_control_route_iterable_is_rejected_without_enumeration(self):
        class HostileRoutes:
            def __iter__(self):
                raise AssertionError("routes MUST NOT be enumerated")

        with self.assertRaises(ValueError):
            BoundedInboundHttpApplicationAdapter(
                federation_responder=federation_responder(),
                record_responder=record_responder(FakeSource(record())),
                control_routes=HostileRoutes(),
                decode_transport_envelope_json=decode_inbound_control_envelope_json,
                encode_transport_envelope_json=encode_prepared_inbound_response_json,
            )

    def test_noncanonical_content_length_fails_before_m32(self):
        authorize = Mock(return_value=True)
        federation = federation_responder(authorize=authorize, page_source=Mock())
        request = post()
        changed = InboundHttpRequest(
            method=request.method,
            path=request.path,
            headers=(
                ("content-length", "0" + str(len(request.body))),
                ("content-type", "application/json"),
            ),
            body=request.body,
        )
        with self.assertRaises(InboundHttpError) as raised:
            service(federation=federation).handle(changed)
        self.assertEqual(raised.exception.code, "CANONICAL_CONTENT_LENGTH_REQUIRED")
        authorize.assert_not_called()

    def test_response_size_bound_is_enforced_before_prepared_http_result(self):
        limits = InboundHttpApplicationLimits(max_response_body_bytes=8)
        with self.assertRaises(InboundHttpError) as raised:
            service(limits=limits).handle(post())
        self.assertEqual(raised.exception.code, "RESPONSE_BODY_LIMIT_EXCEEDED")

    def test_underlying_policy_exception_text_is_not_reflected(self):
        secret = "private-policy-detail-do-not-reflect"
        federation = federation_responder(authorize=lambda context: (_ for _ in ()).throw(RuntimeError(secret)))
        with self.assertRaises(InboundHttpError) as raised:
            service(federation=federation).handle(post())
        self.assertEqual(raised.exception.code, "FEDERATION_REQUEST_REJECTED")
        self.assertNotIn(secret, str(raised.exception))

    def test_m34_runtime_has_no_network_server_filesystem_background_or_logging_surface(self):
        source_path = Path(__file__).resolve().parents[1] / "src" / "marketplace" / "runtime" / "inbound_http.py"
        tree = ast.parse(source_path.read_text(encoding="utf-8"))
        imported_roots: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported_roots.update(alias.name.split(".", 1)[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported_roots.add(node.module.split(".", 1)[0])
        forbidden = {
            "socket",
            "ssl",
            "http",
            "urllib",
            "asyncio",
            "threading",
            "subprocess",
            "logging",
            "os",
            "pathlib",
        }
        self.assertTrue(imported_roots.isdisjoint(forbidden), imported_roots & forbidden)

    def test_m34_reference_bridge_has_no_network_server_or_process_surface(self):
        source_path = Path(__file__).resolve().parents[1] / "src" / "marketplace" / "reference" / "inbound_http_v1.py"
        tree = ast.parse(source_path.read_text(encoding="utf-8"))
        imported_roots: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported_roots.update(alias.name.split(".", 1)[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported_roots.add(node.module.split(".", 1)[0])
        forbidden = {
            "socket",
            "ssl",
            "http",
            "urllib",
            "asyncio",
            "threading",
            "subprocess",
            "logging",
            "os",
            "pathlib",
        }
        self.assertTrue(imported_roots.isdisjoint(forbidden), imported_roots & forbidden)


if __name__ == "__main__":
    unittest.main()
