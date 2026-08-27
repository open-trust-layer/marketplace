from __future__ import annotations

from dataclasses import replace
import unittest
from unittest.mock import Mock

from marketplace.reference import CORE_PROFILE, TYPE_INTENT, federation_v1
from marketplace.runtime.federation import FederationOperationProfile
from marketplace.runtime.inbound_federation import (
    BoundedInboundFederationResponder,
    InboundFederationError,
    InboundFederationPageMaterial,
)


SOURCE = "urn:example:source:local-m32-resource"


def scope() -> dict[str, object]:
    return {"version": 1, "record_types": [TYPE_INTENT]}


def advertisement(*, page_limit: int = 10_000, cursor_limit: int = 4_096) -> dict[str, object]:
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
            "max_page_records": page_limit,
            "max_cursor_bytes": cursor_limit,
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


def envelope(*, operation: str, cursor: bytes | None = None):
    capability = {
        federation_v1.OP_SNAPSHOT: federation_v1.CAP_SNAPSHOT,
        federation_v1.OP_SYNC: federation_v1.CAP_SYNC,
    }[operation]
    message_type = {
        federation_v1.OP_SNAPSHOT: federation_v1.MSG_SNAPSHOT_REQUEST,
        federation_v1.OP_SYNC: federation_v1.MSG_SYNC_REQUEST,
    }[operation]
    request: dict[str, object] = {
        "version": 1,
        "source": SOURCE,
        "operation": operation,
        "scope": scope(),
        "required_capabilities": [capability],
        "page_size": 4,
    }
    if cursor is not None:
        request["cursor"] = cursor
    return federation_v1.make_transport_envelope(message_type, request)


def responder(
    *,
    capability_advertisement=None,
    max_page_records: int = 256,
    authorize_disclosure=lambda context: True,
    page_source=None,
    evaluate_exchange_page=federation_v1.evaluate_exchange_page,
):
    page_source = page_source or (
        lambda context: InboundFederationPageMaterial(
            records=(),
            source_completeness="UNKNOWN_SOURCE",
            page_truncated=False,
        )
    )
    return BoundedInboundFederationResponder(
        local_source=SOURCE,
        validate_transport_envelope=federation_v1.validate_transport_envelope,
        validate_exchange_request=federation_v1.validate_exchange_request,
        scope_fingerprint=federation_v1.scope_fingerprint,
        negotiate_capabilities=federation_v1.negotiate_capabilities,
        capability_advertisement=capability_advertisement or advertisement(),
        evaluate_exchange_page=evaluate_exchange_page,
        validate_exchange_result=federation_v1.validate_exchange_result,
        make_transport_envelope=federation_v1.make_transport_envelope,
        validate_record=lambda record: None,
        record_identity_text=lambda record: record,
        authorize_disclosure=authorize_disclosure,
        page_source=page_source,
        operation_profiles=profiles(),
        max_page_records=max_page_records,
    )


class InboundFederationResourceIntegrityTests(unittest.TestCase):
    def test_configured_page_cap_cannot_exceed_local_advertised_limit(self):
        with self.assertRaises(ValueError):
            responder(
                capability_advertisement=advertisement(page_limit=128),
                max_page_records=256,
            )

    def test_incoming_cursor_over_local_advertised_limit_fails_before_disclosure(self):
        authorizer = Mock(return_value=True)
        service = responder(
            capability_advertisement=advertisement(cursor_limit=4),
            authorize_disclosure=authorizer,
        )
        with self.assertRaises(InboundFederationError) as caught:
            service.prepare_response(
                envelope(operation=federation_v1.OP_SYNC, cursor=b"12345"),
                operation=federation_v1.OP_SYNC,
            )
        self.assertEqual(caught.exception.code, "LOCAL_CURSOR_LIMIT_EXCEEDED")
        authorizer.assert_not_called()

    def test_outgoing_cursor_over_local_advertised_limit_fails_before_page_evaluation(self):
        evaluator = Mock(side_effect=federation_v1.evaluate_exchange_page)
        service = responder(
            capability_advertisement=advertisement(cursor_limit=4),
            evaluate_exchange_page=evaluator,
            page_source=lambda context: InboundFederationPageMaterial(
                records=(),
                source_completeness="PARTIAL_SOURCE",
                page_truncated=True,
                next_cursor=b"12345",
            ),
        )
        with self.assertRaises(InboundFederationError) as caught:
            service.prepare_response(
                envelope(operation=federation_v1.OP_SYNC),
                operation=federation_v1.OP_SYNC,
            )
        self.assertEqual(caught.exception.code, "LOCAL_CURSOR_LIMIT_EXCEEDED")
        evaluator.assert_not_called()

    def test_prepared_integrity_snapshot_binds_actual_scope_not_only_fingerprint(self):
        service = responder()
        prepared = service.prepare_response(
            envelope(operation=federation_v1.OP_SNAPSHOT),
            operation=federation_v1.OP_SNAPSHOT,
        )
        forged_context = replace(
            prepared.request_context,
            scope={
                "version": 1,
                "record_types": [TYPE_INTENT],
                "profiles_all": [CORE_PROFILE],
            },
        )
        with self.assertRaises(ValueError):
            replace(prepared, request_context=forged_context)


if __name__ == "__main__":
    unittest.main()
