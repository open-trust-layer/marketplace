from __future__ import annotations

import unittest

import marketplace.runtime.inbound_federation as inbound_federation_module
from marketplace.reference import TYPE_INTENT, federation_v1
from marketplace.runtime.federation import FederationOperationProfile
from marketplace.runtime.inbound_federation import (
    BoundedInboundFederationResponder,
    InboundFederationError,
    InboundFederationPageMaterial,
)


SOURCE = "urn:example:source:m60"


def _scope() -> dict[str, object]:
    return {"version": 1, "record_types": [TYPE_INTENT]}


def _advertisement() -> dict[str, object]:
    caps = [federation_v1.CAP_SNAPSHOT]
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


def _profile() -> FederationOperationProfile:
    return FederationOperationProfile(
        federation_v1.OP_SNAPSHOT,
        federation_v1.MSG_SNAPSHOT_REQUEST,
        federation_v1.MSG_SNAPSHOT_RESULT,
    )


def _envelope() -> tuple[object, ...]:
    payload = {
        "version": 1,
        "source": SOURCE,
        "operation": federation_v1.OP_SNAPSHOT,
        "scope": _scope(),
        "required_capabilities": [federation_v1.CAP_SNAPSHOT],
        "page_size": 1,
    }
    return federation_v1.make_transport_envelope(
        federation_v1.MSG_SNAPSHOT_REQUEST,
        payload,
    )


def _empty_page() -> InboundFederationPageMaterial:
    return InboundFederationPageMaterial(
        records=(),
        source_completeness="UNKNOWN_SOURCE",
        page_truncated=False,
    )


def _service(*, authorize=None, page_source=None, **overrides):
    values = {
        "validate_transport_envelope": federation_v1.validate_transport_envelope,
        "validate_exchange_request": federation_v1.validate_exchange_request,
        "scope_fingerprint": federation_v1.scope_fingerprint,
        "negotiate_capabilities": federation_v1.negotiate_capabilities,
        "evaluate_exchange_page": federation_v1.evaluate_exchange_page,
        "validate_exchange_result": federation_v1.validate_exchange_result,
        "make_transport_envelope": federation_v1.make_transport_envelope,
        "validate_record": lambda record: None,
        "record_identity_text": lambda record: record,
    }
    values.update(overrides)
    return BoundedInboundFederationResponder(
        local_source=SOURCE,
        capability_advertisement=_advertisement(),
        authorize_disclosure=authorize or (lambda context: True),
        page_source=page_source or (lambda context: _empty_page()),
        operation_profiles=(_profile(),),
        max_page_records=8,
        **values,
    )


def _assert_binding_drift(testcase: unittest.TestCase, service) -> None:
    with testcase.assertRaises(InboundFederationError) as caught:
        service.prepare_response(
            _envelope(),
            operation=federation_v1.OP_SNAPSHOT,
        )
    testcase.assertEqual(caught.exception.code, "INBOUND_FEDERATION_BINDING_DRIFT")


class _HostileEqualityCallable:
    def __init__(self, result=True) -> None:
        self.result = result
        self.calls = 0
        self.equalities = 0

    def __call__(self, *args, **kwargs):
        self.calls += 1
        return self.result

    def __eq__(self, other):
        self.equalities += 1
        raise AssertionError("caller-controlled equality MUST NOT execute")

    def __ne__(self, other):
        self.equalities += 1
        raise AssertionError("caller-controlled equality MUST NOT execute")


class InboundFederationM60RetainedBindingTests(unittest.TestCase):
    def test_disclosure_authorizer_rebinding_is_blocked_before_hostile_execution(self):
        service = _service()
        hostile = _HostileEqualityCallable(True)
        service._authorize_disclosure = hostile
        _assert_binding_drift(self, service)
        self.assertEqual(hostile.calls, 0)
        self.assertEqual(hostile.equalities, 0)

    def test_page_source_rebinding_is_blocked_before_hostile_execution(self):
        service = _service()
        hostile = _HostileEqualityCallable(_empty_page())
        service._page_source = hostile
        _assert_binding_drift(self, service)
        self.assertEqual(hostile.calls, 0)
        self.assertEqual(hostile.equalities, 0)

    def test_private_normalizer_poisoning_is_blocked_before_execution(self):
        service = _service()
        hostile = _HostileEqualityCallable(None)
        service._normalize_request = hostile
        _assert_binding_drift(self, service)
        self.assertEqual(hostile.calls, 0)
        self.assertEqual(hostile.equalities, 0)

    def test_profile_mapping_rebinding_is_configuration_drift(self):
        service = _service()
        service._profiles = dict(service._profiles)
        with self.assertRaises(InboundFederationError) as caught:
            service.prepare_response(_envelope(), operation=federation_v1.OP_SNAPSHOT)
        self.assertEqual(
            caught.exception.code,
            "INBOUND_FEDERATION_CONFIGURATION_DRIFT",
        )

    def test_max_page_limit_rebinding_is_configuration_drift(self):
        service = _service()
        service._max_page_records = 1
        with self.assertRaises(InboundFederationError) as caught:
            service.prepare_response(_envelope(), operation=federation_v1.OP_SNAPSHOT)
        self.assertEqual(
            caught.exception.code,
            "INBOUND_FEDERATION_CONFIGURATION_DRIFT",
        )

    def test_authorizer_cannot_replace_page_source_mid_call(self):
        holder = {}
        hostile = _HostileEqualityCallable(_empty_page())

        def authorize(context):
            holder["service"]._page_source = hostile
            return True

        service = _service(authorize=authorize)
        holder["service"] = service
        _assert_binding_drift(self, service)
        self.assertEqual(hostile.calls, 0)
        self.assertEqual(hostile.equalities, 0)

    def test_page_source_cannot_replace_evaluator_mid_call(self):
        holder = {}
        calls = []

        def hostile(*args, **kwargs):
            calls.append("hostile")
            return federation_v1.evaluate_exchange_page(*args, **kwargs)

        def page_source(context):
            holder["service"]._evaluate_exchange_page = hostile
            return _empty_page()

        service = _service(page_source=page_source)
        holder["service"] = service
        _assert_binding_drift(self, service)
        self.assertEqual(calls, [])

    def test_result_validator_cannot_replace_envelope_maker_mid_call(self):
        holder = {}
        calls = []

        def hostile(message_type, payload):
            calls.append("hostile")
            return federation_v1.make_transport_envelope(message_type, payload)

        def validate_result(payload):
            holder["service"]._make_transport_envelope = hostile
            return federation_v1.validate_exchange_result(payload)

        service = _service(validate_exchange_result=validate_result)
        holder["service"] = service
        _assert_binding_drift(self, service)
        self.assertEqual(calls, [])

    def test_binding_witness_poisoning_does_not_execute_equality(self):
        service = _service()
        hostile = _HostileEqualityCallable()
        service._binding_witness = hostile
        _assert_binding_drift(self, service)
        self.assertEqual(hostile.calls, 0)
        self.assertEqual(hostile.equalities, 0)

    def test_callable_with_hostile_equality_is_validated_by_identity_only(self):
        authorizer = _HostileEqualityCallable(True)
        service = _service(authorize=authorizer)
        prepared = service.prepare_response(
            _envelope(),
            operation=federation_v1.OP_SNAPSHOT,
        )
        self.assertFalse(prepared.transmitted)
        self.assertEqual(authorizer.calls, 1)
        self.assertEqual(authorizer.equalities, 0)

    def test_every_retained_helper_rebinding_is_blocked_before_execution(self):
        helper_names = (
            "_validate_transport_envelope",
            "_validate_exchange_request",
            "_scope_fingerprint",
            "_negotiate_capabilities",
            "_evaluate_exchange_page",
            "_validate_exchange_result",
            "_make_transport_envelope",
            "_validate_record",
            "_record_identity_text",
            "_authorize_disclosure",
            "_page_source",
        )
        for helper_name in helper_names:
            with self.subTest(helper=helper_name):
                service = _service()
                hostile = _HostileEqualityCallable(None)
                setattr(service, helper_name, hostile)
                _assert_binding_drift(self, service)
                self.assertEqual(hostile.calls, 0)
                self.assertEqual(hostile.equalities, 0)

    def test_capability_advertisement_rebinding_is_configuration_drift(self):
        service = _service()
        service._capability_advertisement = dict(service._capability_advertisement)
        with self.assertRaises(InboundFederationError) as caught:
            service.prepare_response(_envelope(), operation=federation_v1.OP_SNAPSHOT)
        self.assertEqual(caught.exception.code, "INBOUND_FEDERATION_CONFIGURATION_DRIFT")

    def test_advertised_limit_rebinding_is_configuration_drift(self):
        service = _service()
        service._advertised_cursor_limit = 1
        with self.assertRaises(InboundFederationError) as caught:
            service.prepare_response(_envelope(), operation=federation_v1.OP_SNAPSHOT)
        self.assertEqual(caught.exception.code, "INBOUND_FEDERATION_CONFIGURATION_DRIFT")

    def test_profile_field_mutation_is_configuration_drift(self):
        service = _service()
        profile = service._profiles[federation_v1.OP_SNAPSHOT]
        object.__setattr__(profile, "result_message_type", "urn:example:tampered-result")
        with self.assertRaises(InboundFederationError) as caught:
            service.prepare_response(_envelope(), operation=federation_v1.OP_SNAPSHOT)
        self.assertEqual(caught.exception.code, "INBOUND_FEDERATION_CONFIGURATION_DRIFT")

    def test_binding_witness_limit_poisoning_never_executes_equality(self):
        service = _service()
        hostile = _HostileEqualityCallable()
        witness = getattr(service, "_binding_witness", None)
        if type(witness) is tuple and len(witness) == 13:
            forged = list(witness)
            forged[6] = hostile
            service._binding_witness = tuple(forged)
        else:
            service._binding_witness = ("forged-m60-witness",)
        _assert_binding_drift(self, service)
        self.assertEqual(hostile.calls, 0)
        self.assertEqual(hostile.equalities, 0)


    def test_module_marker_poisoning_never_executes_equality(self):
        service = _service()
        hostile = _HostileEqualityCallable()
        original = getattr(inbound_federation_module, "_M60_BINDING_MARKER", None)
        inbound_federation_module._M60_BINDING_MARKER = hostile
        try:
            _assert_binding_drift(self, service)
        finally:
            if original is None:
                delattr(inbound_federation_module, "_M60_BINDING_MARKER")
            else:
                inbound_federation_module._M60_BINDING_MARKER = original
        self.assertEqual(hostile.calls, 0)
        self.assertEqual(hostile.equalities, 0)

    def test_module_helper_name_table_poisoning_never_executes_equality(self):
        service = _service()
        hostile = _HostileEqualityCallable()
        original = getattr(inbound_federation_module, "_M60_HELPER_NAMES", None)
        inbound_federation_module._M60_HELPER_NAMES = (hostile,) * 11
        try:
            _assert_binding_drift(self, service)
        finally:
            if original is None:
                delattr(inbound_federation_module, "_M60_HELPER_NAMES")
            else:
                inbound_federation_module._M60_HELPER_NAMES = original
        self.assertEqual(hostile.calls, 0)
        self.assertEqual(hostile.equalities, 0)

    def test_profile_snapshot_helper_rebinding_is_blocked_before_execution(self):
        service = _service()
        touched = []
        original = getattr(inbound_federation_module, "_profile_configuration_snapshot", None)

        def hostile(*args, **kwargs):
            touched.append("executed")
            return ()

        inbound_federation_module._profile_configuration_snapshot = hostile
        try:
            _assert_binding_drift(self, service)
        finally:
            if original is None:
                delattr(inbound_federation_module, "_profile_configuration_snapshot")
            else:
                inbound_federation_module._profile_configuration_snapshot = original
        self.assertEqual(touched, [])

    def test_module_responder_class_poisoning_fails_before_attribute_execution(self):
        service = _service()
        touched = []
        original = getattr(inbound_federation_module, "BoundedInboundFederationResponder")

        class HostileClassBinding:
            def __getattr__(self, name):
                touched.append(name)
                raise AssertionError("poisoned responder class binding MUST NOT execute")

        inbound_federation_module.BoundedInboundFederationResponder = HostileClassBinding()
        try:
            _assert_binding_drift(self, service)
        finally:
            inbound_federation_module.BoundedInboundFederationResponder = original
        self.assertEqual(touched, [])

    def test_private_binding_validator_poisoning_is_blocked_before_execution(self):
        service = _service()
        hostile = _HostileEqualityCallable()
        service._validate_bindings_function = hostile
        _assert_binding_drift(self, service)
        self.assertEqual(hostile.calls, 0)
        self.assertEqual(hostile.equalities, 0)

    def test_private_guarded_helper_poisoning_is_blocked_before_execution(self):
        service = _service()
        hostile = _HostileEqualityCallable()
        service._guarded_helper_function = hostile
        _assert_binding_drift(self, service)
        self.assertEqual(hostile.calls, 0)
        self.assertEqual(hostile.equalities, 0)

if __name__ == "__main__":
    unittest.main()
