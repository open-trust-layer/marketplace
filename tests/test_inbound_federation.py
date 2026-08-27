from __future__ import annotations

import unittest
from unittest.mock import Mock

from olp import RecordV1

from marketplace.reference import CORE_PROFILE, TYPE_INTENT, federation_v1, record_identity_text, validate_market_record
from marketplace.runtime.federation import FederationOperationProfile
from marketplace.runtime.inbound_federation import (
    BoundedInboundFederationResponder,
    InboundFederationError,
    InboundFederationPageMaterial,
)


SOURCE = "urn:example:source:local-m32"
ACTION = "https://example.test/actions/sell"
SUBJECT = "urn:example:item:m32"


def intent(principal: str) -> RecordV1:
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


def capability_advertisement(*, source: str = SOURCE) -> dict[str, object]:
    capabilities = sorted(
        [federation_v1.CAP_SNAPSHOT, federation_v1.CAP_SYNC],
        key=lambda value: value.encode("utf-8"),
    )
    return {
        "version": 1,
        "source": source,
        "implemented": capabilities,
        "enabled": capabilities,
        "configured": capabilities,
        "limits": {
            "max_page_records": federation_v1.MAX_PAGE_RECORDS,
            "max_cursor_bytes": federation_v1.MAX_CURSOR_BYTES,
            "max_submission_records": federation_v1.MAX_SUBMISSION_RECORDS,
        },
    }


def request(
    *,
    source: str = SOURCE,
    operation: str = federation_v1.OP_SNAPSHOT,
    page_size: int = 4,
    cursor: bytes | None = None,
    required_capabilities: list[str] | None = None,
) -> dict[str, object]:
    capability = {
        federation_v1.OP_SNAPSHOT: federation_v1.CAP_SNAPSHOT,
        federation_v1.OP_SYNC: federation_v1.CAP_SYNC,
    }[operation]
    capabilities = required_capabilities or [capability]
    capabilities = sorted(capabilities, key=lambda value: value.encode("utf-8"))
    result: dict[str, object] = {
        "version": 1,
        "source": source,
        "operation": operation,
        "scope": scope(),
        "required_capabilities": capabilities,
        "page_size": page_size,
    }
    if cursor is not None:
        result["cursor"] = cursor
    return result


def request_envelope(**kwargs: object):
    operation = kwargs.get("operation", federation_v1.OP_SNAPSHOT)
    message_type = {
        federation_v1.OP_SNAPSHOT: federation_v1.MSG_SNAPSHOT_REQUEST,
        federation_v1.OP_SYNC: federation_v1.MSG_SYNC_REQUEST,
    }[operation]
    return federation_v1.make_transport_envelope(message_type, request(**kwargs))


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


def responder(*, authorize=None, page_source=None, max_page_records: int = 256):
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
        operation_profiles=profiles(),
        max_page_records=max_page_records,
    )


class InboundFederationTests(unittest.TestCase):
    def test_empty_final_page_is_prepared_but_never_transmitted(self):
        service = responder()
        prepared = service.prepare_response(
            request_envelope(),
            operation=federation_v1.OP_SNAPSHOT,
        )
        self.assertEqual(prepared.record_ids, ())
        self.assertEqual(prepared.envelope[2], federation_v1.MSG_SNAPSHOT_RESULT)
        self.assertFalse(prepared.transmitted)
        self.assertFalse(prepared.request_authenticated)
        self.assertFalse(prepared.peer_identity_proven)
        self.assertEqual(prepared.global_completeness, "UNKNOWN")
        self.assertFalse(prepared.absence_is_deletion_evidence)
        self.assertFalse(prepared.creates_agreement)
        self.assertFalse(prepared.establishes_truth)
        self.assertFalse(prepared.establishes_trust)
        self.assertFalse(prepared.authorizes_protected_side_effects)
        self.assertFalse(hasattr(prepared, "records"))

    def test_one_record_page_returns_only_canonical_identity(self):
        record = intent("did:example:alice")
        service = responder(
            page_source=lambda context: InboundFederationPageMaterial(
                records=(record,),
                source_completeness="PARTIAL_SOURCE",
                page_truncated=False,
            )
        )
        prepared = service.prepare_response(
            request_envelope(),
            operation=federation_v1.OP_SNAPSHOT,
        )
        record_id = record_identity_text(record)
        self.assertEqual(prepared.record_ids, (record_id,))
        self.assertEqual(tuple(prepared.envelope[3]["record_ids"]), (record_id,))
        self.assertFalse(hasattr(prepared, "records"))

    def test_disclosure_denial_happens_before_page_source(self):
        authorize = Mock(return_value=False)
        page_source = Mock()
        service = responder(authorize=authorize, page_source=page_source)
        with self.assertRaises(InboundFederationError) as caught:
            service.prepare_response(request_envelope(), operation=federation_v1.OP_SNAPSHOT)
        self.assertEqual(caught.exception.code, "DISCLOSURE_DENIED")
        authorize.assert_called_once()
        page_source.assert_not_called()

    def test_nonboolean_disclosure_decision_fails_closed(self):
        page_source = Mock()
        service = responder(authorize=lambda context: 1, page_source=page_source)
        with self.assertRaises(InboundFederationError) as caught:
            service.prepare_response(request_envelope(), operation=federation_v1.OP_SNAPSHOT)
        self.assertEqual(caught.exception.code, "INVALID_DISCLOSURE_AUTHORIZER_RESULT")
        page_source.assert_not_called()

    def test_nonlocal_source_fails_before_authorizer(self):
        authorize = Mock(return_value=True)
        service = responder(authorize=authorize)
        with self.assertRaises(InboundFederationError) as caught:
            service.prepare_response(
                request_envelope(source="urn:example:source:other"),
                operation=federation_v1.OP_SNAPSHOT,
            )
        self.assertEqual(caught.exception.code, "REQUEST_SOURCE_MISMATCH")
        authorize.assert_not_called()

    def test_wrong_route_operation_fails_before_authorizer(self):
        authorize = Mock(return_value=True)
        service = responder(authorize=authorize)
        with self.assertRaises(InboundFederationError) as caught:
            service.prepare_response(
                request_envelope(operation=federation_v1.OP_SNAPSHOT),
                operation=federation_v1.OP_SYNC,
            )
        self.assertEqual(caught.exception.code, "REQUEST_ENVELOPE_VALIDATION_FAILED")
        authorize.assert_not_called()

    def test_local_page_limit_fails_before_authorizer(self):
        authorize = Mock(return_value=True)
        service = responder(authorize=authorize, max_page_records=2)
        with self.assertRaises(InboundFederationError) as caught:
            service.prepare_response(
                request_envelope(page_size=3),
                operation=federation_v1.OP_SNAPSHOT,
            )
        self.assertEqual(caught.exception.code, "LOCAL_PAGE_LIMIT_EXCEEDED")
        authorize.assert_not_called()

    def test_unavailable_required_capability_fails_before_authorizer_and_page_source(self):
        authorize = Mock(return_value=True)
        page_source = Mock()
        service = responder(authorize=authorize, page_source=page_source)
        unsupported = "https://example.test/federation/capability/not-local-v1"
        with self.assertRaises(InboundFederationError) as caught:
            service.prepare_response(
                request_envelope(
                    required_capabilities=[federation_v1.CAP_SNAPSHOT, unsupported],
                ),
                operation=federation_v1.OP_SNAPSHOT,
            )
        self.assertEqual(caught.exception.code, "REQUIRED_CAPABILITY_UNAVAILABLE")
        authorize.assert_not_called()
        page_source.assert_not_called()

    def test_page_source_runs_exactly_once_after_authorization(self):
        authorize = Mock(return_value=True)
        page_source = Mock(
            return_value=InboundFederationPageMaterial(
                records=(),
                source_completeness="UNKNOWN_SOURCE",
                page_truncated=False,
            )
        )
        service = responder(authorize=authorize, page_source=page_source)
        service.prepare_response(request_envelope(), operation=federation_v1.OP_SNAPSHOT)
        authorize.assert_called_once()
        page_source.assert_called_once()

    def test_record_overflow_stops_before_record_validation(self):
        validate_record = Mock()
        service = BoundedInboundFederationResponder(
            local_source=SOURCE,
            validate_transport_envelope=federation_v1.validate_transport_envelope,
            validate_exchange_request=federation_v1.validate_exchange_request,
            scope_fingerprint=federation_v1.scope_fingerprint,
            negotiate_capabilities=federation_v1.negotiate_capabilities,
            capability_advertisement=capability_advertisement(),
            evaluate_exchange_page=federation_v1.evaluate_exchange_page,
            validate_exchange_result=federation_v1.validate_exchange_result,
            make_transport_envelope=federation_v1.make_transport_envelope,
            validate_record=validate_record,
            record_identity_text=record_identity_text,
            authorize_disclosure=lambda context: True,
            page_source=lambda context: InboundFederationPageMaterial(
                records=(object(), object()),
                source_completeness="UNKNOWN_SOURCE",
                page_truncated=False,
            ),
            operation_profiles=profiles(),
        )
        with self.assertRaises(InboundFederationError) as caught:
            service.prepare_response(
                request_envelope(page_size=1),
                operation=federation_v1.OP_SNAPSHOT,
            )
        self.assertEqual(caught.exception.code, "PAGE_RECORD_LIMIT_EXCEEDED")
        validate_record.assert_not_called()

    def test_incoming_cursor_is_opaque_context_not_authorization(self):
        seen = {}
        cursor = b"opaque-request-cursor"

        def authorize(context):
            seen["authorize_cursor"] = context.cursor
            return True

        def source(context):
            seen["source_cursor"] = context.cursor
            return InboundFederationPageMaterial(
                records=(),
                source_completeness="PARTIAL_SOURCE",
                page_truncated=False,
            )

        service = responder(authorize=authorize, page_source=source)
        prepared = service.prepare_response(
            request_envelope(operation=federation_v1.OP_SYNC, cursor=cursor),
            operation=federation_v1.OP_SYNC,
        )
        self.assertEqual(seen, {"authorize_cursor": cursor, "source_cursor": cursor})
        self.assertEqual(prepared.request_context.cursor, cursor)
        self.assertFalse(prepared.request_authenticated)
        self.assertFalse(prepared.peer_identity_proven)

    def test_truncated_page_requires_and_preserves_opaque_next_cursor(self):
        cursor = b"opaque-next-cursor"
        service = responder(
            page_source=lambda context: InboundFederationPageMaterial(
                records=(),
                source_completeness="PARTIAL_SOURCE",
                page_truncated=True,
                next_cursor=cursor,
            )
        )
        prepared = service.prepare_response(request_envelope(), operation=federation_v1.OP_SNAPSHOT)
        self.assertTrue(prepared.page_truncated)
        self.assertEqual(prepared.next_cursor, cursor)
        self.assertEqual(prepared.envelope[3]["next_cursor"], cursor)


if __name__ == "__main__":
    unittest.main()
