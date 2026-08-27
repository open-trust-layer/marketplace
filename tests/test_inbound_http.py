from __future__ import annotations

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
from marketplace.reference.record_retrieval_v1 import verify_retrieved_market_record
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
    ROUTE_FEDERATION_CONTROL,
    ROUTE_IMMUTABLE_RECORD,
    BoundedInboundHttpApplicationAdapter,
    InboundFederationHttpRoute,
    InboundHttpApplicationLimits,
    InboundHttpError,
    InboundHttpRequest,
)
from marketplace.runtime.inbound_record import BoundedInboundRecordResponder

SOURCE = "urn:example:source:m34"
SNAPSHOT_PATH = "/v1/federation/snapshot"
SYNC_PATH = "/v1/federation/sync"
ACTION = "https://example.test/actions/sell"
SUBJECT = "urn:example:item:m34"


def market_record(principal: str = "did:example:alice") -> RecordV1:
    return RecordV1.from_mapping(
        {
            "envelope_version": 1,
            "type": TYPE_INTENT,
            "content": {
                "version": 1,
                "issuer": {"principal": principal},
                "subjects": [{"uri": SUBJECT}],
                "action": {"id": ACTION},
                "terms": {},
            },
            "profiles": [CORE_PROFILE],
        }
    )


def scope() -> dict[str, object]:
    return {"version": 1, "record_types": [TYPE_INTENT]}


def capability_advertisement() -> dict[str, object]:
    capabilities = sorted(
        [federation_v1.CAP_SNAPSHOT, federation_v1.CAP_SYNC],
        key=lambda value: value.encode("utf-8"),
    )
    return {
        "version": 1,
        "source": SOURCE,
        "implemented": capabilities,
        "enabled": capabilities,
        "configured": capabilities,
        "limits": {
            "max_page_records": federation_v1.MAX_PAGE_RECORDS,
            "max_cursor_bytes": federation_v1.MAX_CURSOR_BYTES,
            "max_submission_records": federation_v1.MAX_SUBMISSION_RECORDS,
        },
    }


def federation_request(*, operation: str = federation_v1.OP_SNAPSHOT) -> dict[str, object]:
    capability = {
        federation_v1.OP_SNAPSHOT: federation_v1.CAP_SNAPSHOT,
        federation_v1.OP_SYNC: federation_v1.CAP_SYNC,
    }[operation]
    return {
        "version": 1,
        "source": SOURCE,
        "operation": operation,
        "scope": scope(),
        "required_capabilities": [capability],
        "page_size": 4,
    }


def federation_request_envelope(*, operation: str = federation_v1.OP_SNAPSHOT):
    message_type = {
        federation_v1.OP_SNAPSHOT: federation_v1.MSG_SNAPSHOT_REQUEST,
        federation_v1.OP_SYNC: federation_v1.MSG_SYNC_REQUEST,
    }[operation]
    return federation_v1.make_transport_envelope(
        message_type,
        federation_request(operation=operation),
    )


def operation_profiles() -> tuple[FederationOperationProfile, ...]:
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


class FakeRecordSource:
    def __init__(self, value):
        self.value = value
        self.calls: list[str] = []

    def get(self, record_id: str):
        self.calls.append(record_id)
        return self.value


def federation_responder(*, authorize=None, page_source=None):
    authorize = authorize or (lambda context: True)
    page_source = page_source or (
        lambda context: InboundFederationPageMaterial(
            records=(),
            source_completeness="PARTIAL_SOURCE",
            page_truncated=False,
        )
    )
    return BoundedInboundFederationResponder(
        local_source=SOURCE,
        validate_transport_envelope=federation_v1.validate_transport_envelope,
        validate_exchange_request=federation_v1.validate_exchange_request,
        scope_fingerprint=federation_v1.scope_fingerprint,
        negotiate_capabilities=federation_v1.negotiate_capabilities,
        capability_advertisement=capability_advertisement(),
        evaluate_exchange_page=federation_v1.evaluate_exchange_page,
        validate_exchange_result=federation_v1.validate_exchange_result,
        make_transport_envelope=federation_v1.make_transport_envelope,
        validate_record=validate_market_record,
        record_identity_text=record_identity_text,
        authorize_disclosure=authorize,
        page_source=page_source,
        operation_profiles=operation_profiles(),
    )


def record_responder(source: FakeRecordSource, *, authorize=None):
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


def adapter(*, federation=None, records=None, limits=None, decoder=None, encoder=None):
    if federation is None:
        federation = federation_responder()
    if records is None:
        records = record_responder(FakeRecordSource(market_record()))
    return BoundedInboundHttpApplicationAdapter(
        federation_responder=federation,
        record_responder=records,
        control_routes=(
            InboundFederationHttpRoute(SNAPSHOT_PATH, federation_v1.OP_SNAPSHOT),
            InboundFederationHttpRoute(SYNC_PATH, federation_v1.OP_SYNC),
        ),
        decode_transport_envelope_json=decoder or decode_inbound_control_envelope_json,
        encode_transport_envelope_json=encoder or encode_prepared_inbound_response_json,
        limits=limits,
    )


def post_request(path: str, envelope=None) -> InboundHttpRequest:
    envelope = envelope or federation_request_envelope()
    body = encode_transport_envelope_json(envelope)
    return InboundHttpRequest(
        method="POST",
        path=path,
        headers=(
            ("accept", "application/json"),
            ("connection", "close"),
            ("content-length", str(len(body))),
            ("content-type", "application/json"),
        ),
        body=body,
    )


def get_request(record_id: str, *, body: bytes = b"", headers=None) -> InboundHttpRequest:
    return InboundHttpRequest(
        method="GET",
        path=f"/v1/records/{record_id}",
        headers=headers
        if headers is not None
        else (("accept", "application/json"), ("connection", "close")),
        body=body,
    )


class InboundHttpApplicationTests(unittest.TestCase):
    def test_control_post_routes_exactly_once_and_prepares_unsent_json_response(self):
        authorize = Mock(return_value=True)
        page_source = Mock(
            return_value=InboundFederationPageMaterial(
                records=(),
                source_completeness="PARTIAL_SOURCE",
                page_truncated=False,
            )
        )
        service = adapter(federation=federation_responder(authorize=authorize, page_source=page_source))
        prepared = service.handle(post_request(SNAPSHOT_PATH))

        self.assertEqual(prepared.route_kind, ROUTE_FEDERATION_CONTROL)
        self.assertEqual(prepared.route_operation, federation_v1.OP_SNAPSHOT)
        self.assertEqual(prepared.status_code, 200)
        self.assertFalse(prepared.transmitted)
        self.assertFalse(prepared.request_authenticated)
        self.assertFalse(prepared.peer_identity_proven)
        self.assertFalse(prepared.establishes_marketplace_truth)
        self.assertFalse(prepared.establishes_trust)
        self.assertFalse(prepared.establishes_authorization)
        self.assertFalse(prepared.authorizes_protected_side_effects)
        self.assertEqual(
            prepared.headers,
            (
                ("connection", "close"),
                ("content-length", str(len(prepared.body))),
                ("content-type", "application/json"),
            ),
        )
        decoded = decode_inbound_control_envelope_json(prepared.body)
        self.assertEqual(decoded[2], federation_v1.MSG_SNAPSHOT_RESULT)
        authorize.assert_called_once()
        page_source.assert_called_once()

    def test_record_get_uses_m33_and_returns_same_verified_record_identity(self):
        expected = market_record()
        record_id = record_identity_text(expected)
        source = FakeRecordSource(expected)
        authorize = Mock(return_value=True)
        service = adapter(records=record_responder(source, authorize=authorize))

        prepared = service.handle(get_request(record_id))

        self.assertEqual(prepared.route_kind, ROUTE_IMMUTABLE_RECORD)
        self.assertEqual(prepared.olp_message_type, "record")
        self.assertFalse(prepared.transmitted)
        decoded = decode_inbound_control_envelope_json(prepared.body)
        verified = verify_retrieved_market_record(decoded, expected_record_identity=record_id)
        self.assertEqual(verified.recomputed_record_identity, record_id)
        self.assertEqual(source.calls, [record_id])
        authorize.assert_called_once()

    def test_control_wrong_method_fails_before_m32_authorizer_or_page_source(self):
        authorize = Mock(return_value=True)
        page_source = Mock()
        service = adapter(federation=federation_responder(authorize=authorize, page_source=page_source))
        request = InboundHttpRequest(
            method="GET",
            path=SNAPSHOT_PATH,
            headers=(),
            body=b"",
        )
        with self.assertRaises(InboundHttpError) as raised:
            service.handle(request)
        self.assertEqual(raised.exception.code, "METHOD_NOT_ALLOWED")
        authorize.assert_not_called()
        page_source.assert_not_called()

    def test_snapshot_body_on_sync_route_fails_before_disclosure(self):
        authorize = Mock(return_value=True)
        page_source = Mock()
        service = adapter(federation=federation_responder(authorize=authorize, page_source=page_source))
        with self.assertRaises(InboundHttpError) as raised:
            service.handle(post_request(SYNC_PATH, federation_request_envelope(operation=federation_v1.OP_SNAPSHOT)))
        self.assertEqual(raised.exception.code, "FEDERATION_REQUEST_REJECTED")
        authorize.assert_not_called()
        page_source.assert_not_called()

    def test_missing_or_wrong_control_entity_headers_fail_before_disclosure(self):
        authorize = Mock(return_value=True)
        page_source = Mock()
        service = adapter(federation=federation_responder(authorize=authorize, page_source=page_source))
        body = encode_transport_envelope_json(federation_request_envelope())
        cases = (
            (("content-length", str(len(body))),),
            (("content-length", str(len(body))), ("content-type", "text/plain")),
            (("content-length", str(len(body) + 1)), ("content-type", "application/json")),
        )
        for headers in cases:
            with self.subTest(headers=headers):
                request = InboundHttpRequest(method="POST", path=SNAPSHOT_PATH, headers=headers, body=body)
                with self.assertRaises(InboundHttpError):
                    service.handle(request)
        authorize.assert_not_called()
        page_source.assert_not_called()

    def test_empty_and_oversized_control_bodies_fail_before_disclosure(self):
        authorize = Mock(return_value=True)
        page_source = Mock()
        limits = InboundHttpApplicationLimits(max_request_body_bytes=8)
        service = adapter(
            federation=federation_responder(authorize=authorize, page_source=page_source),
            limits=limits,
        )
        empty = InboundHttpRequest(
            method="POST",
            path=SNAPSHOT_PATH,
            headers=(("content-length", "0"), ("content-type", "application/json")),
            body=b"",
        )
        with self.assertRaises(InboundHttpError) as raised:
            service.handle(empty)
        self.assertEqual(raised.exception.code, "EMPTY_CONTROL_BODY")

        body = b"123456789"
        oversized = InboundHttpRequest(
            method="POST",
            path=SNAPSHOT_PATH,
            headers=(("content-length", "9"), ("content-type", "application/json")),
            body=body,
        )
        with self.assertRaises(InboundHttpError) as raised:
            service.handle(oversized)
        self.assertEqual(raised.exception.code, "REQUEST_BODY_LIMIT_EXCEEDED")
        authorize.assert_not_called()
        page_source.assert_not_called()

    def test_record_get_body_and_entity_headers_fail_before_m33_authorizer(self):
        expected = market_record()
        record_id = record_identity_text(expected)
        source = FakeRecordSource(expected)
        authorize = Mock(return_value=True)
        service = adapter(records=record_responder(source, authorize=authorize))

        with self.assertRaises(InboundHttpError) as raised:
            service.handle(get_request(record_id, body=b"x"))
        self.assertEqual(raised.exception.code, "RECORD_GET_BODY_FORBIDDEN")

        with self.assertRaises(InboundHttpError) as raised:
            service.handle(
                get_request(
                    record_id,
                    headers=(("content-length", "0"),),
                )
            )
        self.assertEqual(raised.exception.code, "RECORD_GET_ENTITY_HEADERS_FORBIDDEN")
        authorize.assert_not_called()
        self.assertEqual(source.calls, [])

    def test_malformed_record_identity_fails_before_m33_authorizer(self):
        source = FakeRecordSource(market_record())
        authorize = Mock(return_value=True)
        service = adapter(records=record_responder(source, authorize=authorize))
        request = InboundHttpRequest(
            method="GET",
            path="/v1/records/not-a-record-id",
            headers=(),
            body=b"",
        )
        with self.assertRaises(InboundHttpError) as raised:
            service.handle(request)
        self.assertEqual(raised.exception.code, "INVALID_RECORD_ROUTE")
        authorize.assert_not_called()
        self.assertEqual(source.calls, [])

    def test_request_paths_are_exact_and_never_normalized(self):
        invalid = (
            SNAPSHOT_PATH + "?x=1",
            SNAPSHOT_PATH + "#fragment",
            "/v1/federation/%73napshot",
            "/v1//federation/snapshot",
            "/v1/./federation/snapshot",
            "/v1/federation/../snapshot",
        )
        for path in invalid:
            with self.subTest(path=path):
                with self.assertRaises(ValueError):
                    InboundHttpRequest(method="POST", path=path, headers=(), body=b"")

        service = adapter()
        trailing = InboundHttpRequest(method="POST", path=SNAPSHOT_PATH + "/", headers=(), body=b"")
        with self.assertRaises(InboundHttpError) as raised:
            service.handle(trailing)
        self.assertEqual(raised.exception.code, "ROUTE_NOT_FOUND")

    def test_header_representation_is_exact_unique_lowercase_and_bounded(self):
        cases = (
            [("accept", "application/json")],
            (("Accept", "application/json"),),
            (("accept", "application/json"), ("accept", "application/json")),
            (("authorization", "secret"),),
            (("content-type", "application/json"), ("accept", "application/json")),
        )
        for headers in cases:
            with self.subTest(headers=headers):
                with self.assertRaises(ValueError):
                    InboundHttpRequest(method="GET", path="/v1/records/x", headers=headers, body=b"")

    def test_unknown_route_fails_without_any_disclosure_authorizer(self):
        federation_auth = Mock(return_value=True)
        record_auth = Mock(return_value=True)
        source = FakeRecordSource(market_record())
        service = adapter(
            federation=federation_responder(authorize=federation_auth, page_source=Mock()),
            records=record_responder(source, authorize=record_auth),
        )
        request = InboundHttpRequest(method="GET", path="/v1/unknown", headers=(), body=b"")
        with self.assertRaises(InboundHttpError) as raised:
            service.handle(request)
        self.assertEqual(raised.exception.code, "ROUTE_NOT_FOUND")
        federation_auth.assert_not_called()
        record_auth.assert_not_called()
        self.assertEqual(source.calls, [])

    def test_response_serializer_drift_is_detected(self):
        def hostile_encoder(envelope):
            changed = (envelope[0], envelope[1], "wrong-message-type", envelope[3])
            return encode_transport_envelope_json(changed)

        service = adapter(encoder=hostile_encoder)
        with self.assertRaises(InboundHttpError) as raised:
            service.handle(post_request(SNAPSHOT_PATH))
        self.assertEqual(raised.exception.code, "RESPONSE_SERIALIZATION_DRIFT")

    def test_raw_request_content_is_not_reflected_in_local_error_message(self):
        secret = "do-not-reflect-this-secret"
        body = ("{" + secret).encode("utf-8")
        request = InboundHttpRequest(
            method="POST",
            path=SNAPSHOT_PATH,
            headers=(("content-length", str(len(body))), ("content-type", "application/json")),
            body=body,
        )
        with self.assertRaises(InboundHttpError) as raised:
            adapter().handle(request)
        self.assertEqual(raised.exception.code, "CONTROL_BODY_REJECTED")
        self.assertNotIn(secret, str(raised.exception))

    def test_control_routes_cannot_alias_operations_or_record_namespace(self):
        with self.assertRaises(ValueError):
            InboundFederationHttpRoute("/v1/records/example", federation_v1.OP_SNAPSHOT)
        with self.assertRaises(ValueError):
            BoundedInboundHttpApplicationAdapter(
                federation_responder=federation_responder(),
                record_responder=record_responder(FakeRecordSource(market_record())),
                control_routes=(
                    InboundFederationHttpRoute(SNAPSHOT_PATH, federation_v1.OP_SNAPSHOT),
                    InboundFederationHttpRoute("/v1/federation/snapshot-alias", federation_v1.OP_SNAPSHOT),
                ),
                decode_transport_envelope_json=decode_inbound_control_envelope_json,
                encode_transport_envelope_json=encode_prepared_inbound_response_json,
            )


if __name__ == "__main__":
    unittest.main()
