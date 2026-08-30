from __future__ import annotations

import base64
import unittest

import marketplace.runtime.inbound_record as inbound_record_module
from marketplace.runtime.inbound_record import BoundedInboundRecordResponder, InboundRecordError


RECORD_ID = "r1_" + base64.urlsafe_b64encode(bytes(32)).rstrip(b"=").decode("ascii")
SOURCE = "urn:example:source:m61"


class FakeSource:
    def __init__(self, value: object):
        self.value = value
        self.calls: list[str] = []

    def get(self, record_id: str) -> object:
        self.calls.append(record_id)
        return self.value


def validate_record(value: object) -> None:
    if not isinstance(value, dict) or value.get("id") != RECORD_ID:
        raise ValueError("invalid test record")


def record_identity(value: object) -> str:
    assert isinstance(value, dict)
    return value["id"]


def prepare_payload(value: object, *, expected_record_identity: str) -> dict[str, object]:
    return {"record_identity": expected_record_identity}


def make_record_envelope(payload: object) -> tuple[object, ...]:
    return ("OLP-TRANSPORT", 1, "record", payload)


def verify_record_envelope(envelope: object, *, expected_record_identity: str) -> dict[str, object]:
    return {
        "requested_record_identity": expected_record_identity,
        "recomputed_record_identity": expected_record_identity,
        "identity_verified": True,
        "marketplace_semantics_verified": True,
        "proofs_verified": False,
        "establishes_truth": False,
        "establishes_ownership": False,
        "establishes_authority": False,
        "establishes_trust": False,
        "establishes_authorization": False,
        "automatically_ingested": False,
    }


def responder(**overrides: object) -> BoundedInboundRecordResponder:
    values: dict[str, object] = {
        "local_source": SOURCE,
        "record_source": FakeSource({"id": RECORD_ID}),
        "authorize_disclosure": lambda context: True,
        "validate_record": validate_record,
        "record_identity": record_identity,
        "prepare_payload": prepare_payload,
        "make_record_envelope": make_record_envelope,
        "verify_record_envelope": verify_record_envelope,
    }
    values.update(overrides)
    return BoundedInboundRecordResponder(**values)


class InboundRecordM61RetainedBindingTests(unittest.TestCase):
    def assert_binding_drift(self, operation) -> InboundRecordError:
        with self.assertRaises(InboundRecordError) as raised:
            operation()
        self.assertEqual(raised.exception.code, "INBOUND_RECORD_BINDING_DRIFT")
        return raised.exception

    def test_disclosure_authorizer_rebinding_is_blocked_before_hostile_execution(self):
        calls: list[str] = []
        subject = responder()
        subject._authorize_disclosure = lambda context: calls.append("hostile") or True

        self.assert_binding_drift(lambda: subject.prepare(requested_record_identity=RECORD_ID))
        self.assertEqual(calls, [])

    def test_record_source_rebinding_is_blocked_before_hostile_get(self):
        class HostileSource:
            def get(self, record_id: str) -> object:
                raise AssertionError("hostile get executed")

        subject = responder()
        subject._record_source = HostileSource()

        self.assert_binding_drift(lambda: subject.prepare(requested_record_identity=RECORD_ID))

    def test_effective_record_source_get_rebinding_is_blocked(self):
        source = FakeSource({"id": RECORD_ID})
        subject = responder(record_source=source)
        original_get = FakeSource.get
        calls: list[str] = []
        try:
            FakeSource.get = lambda self, record_id: calls.append("hostile") or {"id": RECORD_ID}
            self.assert_binding_drift(lambda: subject.prepare(requested_record_identity=RECORD_ID))
        finally:
            FakeSource.get = original_get
        self.assertEqual(calls, [])

    def test_validator_and_identity_rebinding_are_blocked(self):
        for attribute in ("_validate_record", "_record_identity"):
            with self.subTest(attribute=attribute):
                calls: list[str] = []
                subject = responder()
                setattr(subject, attribute, lambda value: calls.append("hostile") or RECORD_ID)
                self.assert_binding_drift(
                    lambda: subject.prepare(requested_record_identity=RECORD_ID)
                )
                self.assertEqual(calls, [])

    def test_payload_envelope_and_verifier_rebinding_are_blocked(self):
        for attribute in ("_prepare_payload", "_make_record_envelope", "_verify_record_envelope"):
            with self.subTest(attribute=attribute):
                calls: list[str] = []
                subject = responder()
                setattr(subject, attribute, lambda *args, **kwargs: calls.append("hostile"))
                self.assert_binding_drift(
                    lambda: subject.prepare(requested_record_identity=RECORD_ID)
                )
                self.assertEqual(calls, [])

    def test_authorizer_cannot_replace_later_source_mid_call(self):
        calls: list[str] = []

        class HostileSource:
            def get(self, record_id: str) -> object:
                calls.append("hostile-get")
                return {"id": RECORD_ID}

        class MutatingAuthorizer:
            subject: BoundedInboundRecordResponder | None = None

            def __call__(self, context) -> bool:
                assert self.subject is not None
                self.subject._record_source = HostileSource()
                return True

        authorizer = MutatingAuthorizer()
        subject = responder(authorize_disclosure=authorizer)
        authorizer.subject = subject

        self.assert_binding_drift(lambda: subject.prepare(requested_record_identity=RECORD_ID))
        self.assertEqual(calls, [])

    def test_private_validation_helper_poisoning_is_blocked_before_execution(self):
        subject = responder()
        calls: list[str] = []
        subject._validate_local_record = lambda *args, **kwargs: calls.append("hostile")

        self.assert_binding_drift(lambda: subject.prepare(requested_record_identity=RECORD_ID))
        self.assertEqual(calls, [])

    def test_private_validate_bindings_function_poisoning_never_executes(self):
        subject = responder()
        calls: list[str] = []
        subject._validate_bindings_function = lambda value: calls.append("hostile")

        self.assert_binding_drift(lambda: subject.prepare(requested_record_identity=RECORD_ID))
        self.assertEqual(calls, [])

    def test_hostile_equality_is_never_invoked_during_binding_validation(self):
        calls: list[str] = []

        class EqualityTrap:
            def __eq__(self, other: object) -> bool:
                calls.append("eq")
                raise AssertionError("caller equality executed")

            def __ne__(self, other: object) -> bool:
                calls.append("ne")
                raise AssertionError("caller inequality executed")

            def __call__(self, context) -> bool:
                calls.append("call")
                return True

        subject = responder()
        subject._authorize_disclosure = EqualityTrap()
        self.assert_binding_drift(lambda: subject.prepare(requested_record_identity=RECORD_ID))
        self.assertEqual(calls, [])

    def test_module_responder_class_poisoning_is_blocked_before_hostile_execution(self):
        subject = responder()
        original = inbound_record_module.BoundedInboundRecordResponder
        calls: list[str] = []
        try:
            class PoisonedResponder:
                @staticmethod
                def _validate_local_record(*args, **kwargs) -> None:
                    calls.append("hostile")

            inbound_record_module.BoundedInboundRecordResponder = PoisonedResponder
            self.assert_binding_drift(
                lambda: subject.prepare(requested_record_identity=RECORD_ID)
            )
        finally:
            inbound_record_module.BoundedInboundRecordResponder = original
        self.assertEqual(calls, [])

    def test_valid_existing_behavior_still_prepares_one_unsent_record(self):
        subject = responder()
        prepared = subject.prepare(requested_record_identity=RECORD_ID)
        self.assertEqual(prepared.request_context.requested_record_identity, RECORD_ID)
        self.assertEqual(prepared.envelope[2], "record")
        self.assertFalse(prepared.transmitted)


if __name__ == "__main__":
    unittest.main()
