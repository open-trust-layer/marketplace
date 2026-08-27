from __future__ import annotations

import ast
from dataclasses import replace
from pathlib import Path
import unittest
from unittest.mock import Mock

from marketplace.reference import TYPE_INTENT, federation_v1
from marketplace.runtime.federation import FederationOperationProfile
from marketplace.runtime.inbound_federation import (
    BoundedInboundFederationResponder,
    InboundFederationError,
    InboundFederationPageMaterial,
)


SOURCE = "urn:example:source:local-m32-hardening"


def scope() -> dict[str, object]:
    return {"version": 1, "record_types": [TYPE_INTENT]}


def capability_advertisement(*, source: str = SOURCE) -> dict[str, object]:
    capabilities = [federation_v1.CAP_SNAPSHOT]
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


def request(*, page_size: int = 4, required_capabilities: list[str] | None = None) -> dict[str, object]:
    capabilities = required_capabilities or [federation_v1.CAP_SNAPSHOT]
    return {
        "version": 1,
        "source": SOURCE,
        "operation": federation_v1.OP_SNAPSHOT,
        "scope": scope(),
        "required_capabilities": sorted(capabilities, key=lambda value: value.encode("utf-8")),
        "page_size": page_size,
    }


def envelope(**kwargs: object):
    return federation_v1.make_transport_envelope(
        federation_v1.MSG_SNAPSHOT_REQUEST,
        request(**kwargs),
    )


def profiles() -> tuple[FederationOperationProfile, ...]:
    return (
        FederationOperationProfile(
            federation_v1.OP_SNAPSHOT,
            federation_v1.MSG_SNAPSHOT_REQUEST,
            federation_v1.MSG_SNAPSHOT_RESULT,
        ),
    )


def service(
    *,
    validate_transport_envelope=federation_v1.validate_transport_envelope,
    validate_exchange_request=federation_v1.validate_exchange_request,
    scope_fingerprint=federation_v1.scope_fingerprint,
    negotiate_capabilities=federation_v1.negotiate_capabilities,
    advertisement=None,
    evaluate_exchange_page=federation_v1.evaluate_exchange_page,
    validate_exchange_result=federation_v1.validate_exchange_result,
    make_transport_envelope=federation_v1.make_transport_envelope,
    validate_record=lambda record: None,
    record_identity_text=lambda record: record,
    authorize_disclosure=lambda context: True,
    page_source=None,
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
        validate_transport_envelope=validate_transport_envelope,
        validate_exchange_request=validate_exchange_request,
        scope_fingerprint=scope_fingerprint,
        negotiate_capabilities=negotiate_capabilities,
        capability_advertisement=advertisement or capability_advertisement(),
        evaluate_exchange_page=evaluate_exchange_page,
        validate_exchange_result=validate_exchange_result,
        make_transport_envelope=make_transport_envelope,
        validate_record=validate_record,
        record_identity_text=record_identity_text,
        authorize_disclosure=authorize_disclosure,
        page_source=page_source,
        operation_profiles=profiles(),
    )


class MutableRecord:
    def __init__(self, identity: str) -> None:
        self.identity = identity


class InboundFederationHardeningTests(unittest.TestCase):
    def test_transport_validator_cannot_promote_authentication_to_object_proof(self):
        authorizer = Mock(return_value=True)

        def hostile(value, expected):
            result = federation_v1.validate_transport_envelope(value, expected)
            result["transport_authentication_is_object_proof"] = True
            return result

        responder = service(
            validate_transport_envelope=hostile,
            authorize_disclosure=authorizer,
        )
        with self.assertRaises(InboundFederationError) as caught:
            responder.prepare_response(envelope(), operation=federation_v1.OP_SNAPSHOT)
        self.assertEqual(caught.exception.code, "TRANSPORT_OBJECT_PROOF_FORBIDDEN")
        authorizer.assert_not_called()

    def test_request_scope_fingerprint_drift_fails_before_capability_or_disclosure(self):
        authorizer = Mock(return_value=True)
        negotiator = Mock(side_effect=federation_v1.negotiate_capabilities)

        def hostile(value):
            result = federation_v1.validate_exchange_request(value)
            result["scope_fingerprint"] = "A" * 43
            return result

        responder = service(
            validate_exchange_request=hostile,
            negotiate_capabilities=negotiator,
            authorize_disclosure=authorizer,
        )
        with self.assertRaises(InboundFederationError) as caught:
            responder.prepare_response(envelope(), operation=federation_v1.OP_SNAPSHOT)
        self.assertEqual(caught.exception.code, "REQUEST_SCOPE_NORMALIZATION_DRIFT")
        negotiator.assert_not_called()
        authorizer.assert_not_called()

    def test_capability_negotiator_binding_drift_fails_before_disclosure(self):
        authorizer = Mock(return_value=True)

        def hostile(advertisement, required):
            result = federation_v1.negotiate_capabilities(advertisement, required)
            result["required_capabilities"] = ("urn:example:capability:other",)
            return result

        responder = service(
            negotiate_capabilities=hostile,
            authorize_disclosure=authorizer,
        )
        with self.assertRaises(InboundFederationError) as caught:
            responder.prepare_response(envelope(), operation=federation_v1.OP_SNAPSHOT)
        self.assertEqual(caught.exception.code, "CAPABILITY_NEGOTIATOR_BINDING_DRIFT")
        authorizer.assert_not_called()

    def test_capability_negotiator_cannot_hide_unavailable_requirement(self):
        authorizer = Mock(return_value=True)

        def hostile(advertisement, required):
            return {
                "status": "SUPPORTED",
                "required_capabilities": tuple(required),
                "unsupported_capabilities": (),
                "unavailable_capabilities": ("urn:example:capability:hidden",),
                "no_silent_downgrade": True,
            }

        responder = service(
            negotiate_capabilities=hostile,
            authorize_disclosure=authorizer,
        )
        with self.assertRaises(InboundFederationError) as caught:
            responder.prepare_response(envelope(), operation=federation_v1.OP_SNAPSHOT)
        self.assertEqual(caught.exception.code, "REQUIRED_CAPABILITY_UNAVAILABLE")
        authorizer.assert_not_called()

    def test_capability_advertisement_source_mismatch_is_constructor_error(self):
        with self.assertRaises(ValueError):
            service(advertisement=capability_advertisement(source="urn:example:source:other"))

    def test_capability_advertisement_is_detached_from_caller_alias(self):
        advertisement = capability_advertisement()
        responder = service(advertisement=advertisement)
        advertisement["source"] = "urn:example:source:attacker"
        advertisement["enabled"] = []
        prepared = responder.prepare_response(envelope(), operation=federation_v1.OP_SNAPSHOT)
        self.assertFalse(prepared.transmitted)

    def test_hostile_page_evaluator_cannot_promote_global_completeness(self):
        def hostile(records, **kwargs):
            result = federation_v1.evaluate_exchange_page(records, **kwargs)
            result["global_completeness"] = "COMPLETE"
            return result

        responder = service(evaluate_exchange_page=hostile)
        with self.assertRaises(InboundFederationError) as caught:
            responder.prepare_response(envelope(), operation=federation_v1.OP_SNAPSHOT)
        self.assertEqual(caught.exception.code, "GLOBAL_COMPLETENESS_FORBIDDEN")

    def test_hostile_result_validator_cannot_drift_source_binding(self):
        def hostile(value):
            result = federation_v1.validate_exchange_result(value)
            result["source"] = "urn:example:source:attacker"
            return result

        responder = service(validate_exchange_result=hostile)
        with self.assertRaises(InboundFederationError) as caught:
            responder.prepare_response(envelope(), operation=federation_v1.OP_SNAPSHOT)
        self.assertEqual(caught.exception.code, "RESULT_SOURCE_BINDING_DRIFT")

    def test_envelope_maker_cannot_change_result_message_profile(self):
        def hostile(message_type, payload):
            return (
                "OLP-TRANSPORT",
                1,
                federation_v1.MSG_SYNC_RESULT,
                payload,
            )

        responder = service(make_transport_envelope=hostile)
        with self.assertRaises(InboundFederationError) as caught:
            responder.prepare_response(envelope(), operation=federation_v1.OP_SNAPSHOT)
        self.assertEqual(caught.exception.code, "RESPONSE_ENVELOPE_PROFILE_DRIFT")

    def test_arbitrary_page_source_iterable_is_rejected_without_enumeration(self):
        touched = []

        def hostile_iterable():
            touched.append("enumerated")
            yield "record"

        responder = service(page_source=lambda context: hostile_iterable())
        with self.assertRaises(InboundFederationError) as caught:
            responder.prepare_response(envelope(), operation=federation_v1.OP_SNAPSHOT)
        self.assertEqual(caught.exception.code, "INVALID_PAGE_SOURCE_RESULT")
        self.assertEqual(touched, [])

    def test_hidden_cursor_on_final_page_is_rejected(self):
        material = object.__new__(InboundFederationPageMaterial)
        object.__setattr__(material, "records", ())
        object.__setattr__(material, "source_completeness", "UNKNOWN_SOURCE")
        object.__setattr__(material, "page_truncated", False)
        object.__setattr__(material, "next_cursor", b"hidden")
        responder = service(page_source=lambda context: material)
        with self.assertRaises(InboundFederationError) as caught:
            responder.prepare_response(envelope(), operation=federation_v1.OP_SNAPSHOT)
        self.assertEqual(caught.exception.code, "INVALID_PAGE_CURSOR")

    def test_truncated_page_without_cursor_is_rejected(self):
        material = object.__new__(InboundFederationPageMaterial)
        object.__setattr__(material, "records", ())
        object.__setattr__(material, "source_completeness", "PARTIAL_SOURCE")
        object.__setattr__(material, "page_truncated", True)
        object.__setattr__(material, "next_cursor", None)
        responder = service(page_source=lambda context: material)
        with self.assertRaises(InboundFederationError) as caught:
            responder.prepare_response(envelope(), operation=federation_v1.OP_SNAPSHOT)
        self.assertEqual(caught.exception.code, "INVALID_PAGE_CURSOR")

    def test_page_evaluator_record_mutation_is_detected_before_result_creation(self):
        record = MutableRecord("record-before")

        def identity(value):
            return value.identity

        def hostile(records, *, source, operation, scope, completeness, has_more, next_cursor, max_records):
            original_id = records[0].identity
            result = {
                "source": source,
                "operation": operation,
                "scope_fingerprint": federation_v1.scope_fingerprint(scope),
                "record_ids": (original_id,),
                "record_count": 1,
                "duplicate_record_count": 0,
                "source_completeness": completeness,
                "page_truncated": has_more,
                "next_cursor_present": next_cursor is not None,
                "global_completeness": "UNKNOWN",
                "absence_is_deletion_evidence": False,
                "ordering": "REPRODUCIBLE_IDENTITY_ORDER_NOT_CHRONOLOGY",
            }
            records[0].identity = "record-after"
            return result

        responder = service(
            evaluate_exchange_page=hostile,
            validate_record=lambda value: None,
            record_identity_text=identity,
            page_source=lambda context: InboundFederationPageMaterial(
                records=(record,),
                source_completeness="UNKNOWN_SOURCE",
                page_truncated=False,
            ),
        )
        with self.assertRaises(InboundFederationError) as caught:
            responder.prepare_response(envelope(), operation=federation_v1.OP_SNAPSHOT)
        self.assertEqual(caught.exception.code, "PAGE_RECORD_MUTATION_DETECTED")

    def test_response_is_detached_from_envelope_maker_alias(self):
        aliases = {}

        def maker(message_type, payload):
            result = list(federation_v1.make_transport_envelope(message_type, payload))
            aliases["envelope"] = result
            return result

        responder = service(make_transport_envelope=maker)
        prepared = responder.prepare_response(envelope(), operation=federation_v1.OP_SNAPSHOT)
        aliases["envelope"][2] = "urn:example:tampered"
        aliases["envelope"][3] = {"tampered": True}
        self.assertEqual(prepared.envelope[2], federation_v1.MSG_SNAPSHOT_RESULT)
        self.assertNotIn("tampered", prepared.envelope[3])

    def test_prepared_response_snapshot_prevents_dataclass_replace_drift(self):
        responder = service()
        prepared = responder.prepare_response(envelope(), operation=federation_v1.OP_SNAPSHOT)
        with self.assertRaises(ValueError):
            replace(prepared, record_ids=("tampered",))

    def test_authorizer_receives_immutable_scope_authoritative_state(self):
        def authorize(context):
            dict.__setitem__(context.scope, "record_types", ("urn:example:tampered",))
            self.assertEqual(tuple(context.scope["record_types"]), (TYPE_INTENT,))
            return True

        responder = service(authorize_disclosure=authorize)
        prepared = responder.prepare_response(envelope(), operation=federation_v1.OP_SNAPSHOT)
        self.assertEqual(tuple(prepared.request_context.scope["record_types"]), (TYPE_INTENT,))

    def test_m32_source_has_no_network_server_filesystem_background_or_logging_surface(self):
        source_path = Path(__file__).parents[1] / "src" / "marketplace" / "runtime" / "inbound_federation.py"
        tree = ast.parse(source_path.read_text(encoding="utf-8"))
        forbidden_roots = {
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
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name.split(".", 1)[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.split(".", 1)[0])
        self.assertTrue(forbidden_roots.isdisjoint(imported))
        source_text = source_path.read_text(encoding="utf-8")
        for token in ("listen(", "accept(", "serve_forever", "create_server", "open("):
            self.assertNotIn(token, source_text)


if __name__ == "__main__":
    unittest.main()
