from __future__ import annotations

import unittest
from unittest.mock import patch

from marketplace.reference import federation_v1, record_identity_text
from marketplace.reference.inbound_http_v1 import (
    decode_inbound_control_envelope_json,
    encode_prepared_inbound_response_json,
)
from marketplace.runtime.inbound_federation import BoundedInboundFederationResponder
from marketplace.runtime.inbound_http import InboundHttpApplicationLimits, InboundHttpError
from marketplace.runtime.inbound_record import BoundedInboundRecordResponder
from tests.test_inbound_http_hardening import (
    FakeSource,
    get,
    post,
    record,
    record_responder,
    federation_responder,
    service,
)


class InboundHttpM58RetainedBindingHardeningTests(unittest.TestCase):
    def test_m32_class_method_substitution_is_blocked_before_execution(self):
        app = service()
        hostile_calls = []
        def hostile_prepare_response(self, envelope, *, operation):
            hostile_calls.append((envelope, operation))
            raise AssertionError("hostile M32 method MUST NOT execute")

        with patch.object(
            BoundedInboundFederationResponder,
            "prepare_response",
            hostile_prepare_response,
        ):
            with self.assertRaises(InboundHttpError) as raised:
                app.handle(post())

        self.assertEqual(raised.exception.code, "APPLICATION_BINDING_DRIFT")
        self.assertEqual(hostile_calls, [])

    def test_m33_class_method_substitution_is_blocked_before_execution(self):
        expected = record()
        record_id = record_identity_text(expected)
        app = service(records=record_responder(FakeSource(expected)))
        hostile_calls = []

        def hostile_prepare(self, *, requested_record_identity):
            hostile_calls.append(requested_record_identity)
            raise AssertionError("hostile M33 method MUST NOT execute")

        with patch.object(BoundedInboundRecordResponder, "prepare", hostile_prepare):
            with self.assertRaises(InboundHttpError) as raised:
                app.handle(get(record_id))
        self.assertEqual(raised.exception.code, "APPLICATION_BINDING_DRIFT")
        self.assertEqual(hostile_calls, [])

    def test_private_responder_rebinding_is_blocked(self):
        app = service()
        object.__setattr__(app, "_federation_responder", federation_responder())
        with self.assertRaises(InboundHttpError) as raised:
            app.handle(post())
        self.assertEqual(raised.exception.code, "APPLICATION_BINDING_DRIFT")

        expected = record()
        record_id = record_identity_text(expected)
        app = service(records=record_responder(FakeSource(expected)))
        object.__setattr__(
            app,
            "_record_responder",
            record_responder(FakeSource(expected)),
        )
        with self.assertRaises(InboundHttpError) as raised:
            app.handle(get(record_id))
        self.assertEqual(raised.exception.code, "APPLICATION_BINDING_DRIFT")

    def test_private_decoder_and_encoder_rebinding_are_blocked(self):
        app = service()
        decoder_calls = []

        def hostile_decoder(body):
            decoder_calls.append(body)
            raise AssertionError("hostile decoder MUST NOT execute")
        object.__setattr__(app, "_decode_json", hostile_decoder)
        with self.assertRaises(InboundHttpError) as raised:
            app.handle(post())
        self.assertEqual(raised.exception.code, "APPLICATION_BINDING_DRIFT")
        self.assertEqual(decoder_calls, [])

        app = service()
        encoder_calls = []

        def hostile_encoder(envelope):
            encoder_calls.append(envelope)
            raise AssertionError("hostile encoder MUST NOT execute")

        object.__setattr__(app, "_encode_json", hostile_encoder)
        with self.assertRaises(InboundHttpError) as raised:
            app.handle(post())
        self.assertEqual(raised.exception.code, "APPLICATION_BINDING_DRIFT")
        self.assertEqual(encoder_calls, [])

    def test_route_map_mutation_and_rebinding_are_blocked(self):
        app = service()
        app._routes["/v1/federation/snapshot"] = federation_v1.OP_SYNC
        with self.assertRaises(InboundHttpError) as mutated:
            app.handle(post())
        self.assertEqual(
            mutated.exception.code,
            "APPLICATION_CONFIGURATION_DRIFT",
        )
        app = service()
        object.__setattr__(app, "_routes", dict(app._routes))
        with self.assertRaises(InboundHttpError) as rebound:
            app.handle(post())
        self.assertEqual(rebound.exception.code, "APPLICATION_BINDING_DRIFT")

    def test_limit_rebinding_is_blocked(self):
        app = service()
        object.__setattr__(
            app,
            "_limits",
            InboundHttpApplicationLimits(
                max_request_body_bytes=app.limits.max_request_body_bytes,
                max_response_body_bytes=app.limits.max_response_body_bytes,
                max_header_bytes=app.limits.max_header_bytes,
            ),
        )
        with self.assertRaises(InboundHttpError) as raised:
            app.handle(post())
        self.assertEqual(raised.exception.code, "APPLICATION_BINDING_DRIFT")

    def test_in_place_limit_configuration_drift_is_blocked(self):
        app = service()
        object.__setattr__(app._limits, "max_request_body_bytes", 1)
        with self.assertRaises(InboundHttpError) as raised:
            app.handle(post())
        self.assertEqual(
            raised.exception.code,
            "APPLICATION_CONFIGURATION_DRIFT",
        )

    def test_private_helper_poisoning_never_executes(self):
        app = service()
        hostile_calls = []

        def hostile_decode(_self, _request):
            hostile_calls.append(True)
            raise AssertionError("hostile M34 helper MUST NOT execute")

        object.__setattr__(app, "_decode_control_request_function", hostile_decode)
        with self.assertRaises(InboundHttpError) as raised:
            app.handle(post())
        self.assertEqual(raised.exception.code, "APPLICATION_BINDING_DRIFT")
        self.assertEqual(hostile_calls, [])
    def test_private_validator_poisoning_never_executes(self):
        app = service()
        hostile_calls = []

        def hostile_validate(_self):
            hostile_calls.append(True)
            raise AssertionError("hostile M34 validator MUST NOT execute")

        object.__setattr__(app, "_validate_bindings_function", hostile_validate)
        with self.assertRaises(InboundHttpError) as raised:
            app.handle(post())
        self.assertEqual(raised.exception.code, "APPLICATION_BINDING_DRIFT")
        self.assertEqual(hostile_calls, [])

    def test_decoder_cannot_rebind_responder_before_dispatch(self):
        app = None
        replacement = federation_responder()
        hostile_calls = []

        def hostile_prepare_response(envelope, *, operation):
            hostile_calls.append((envelope, operation))
            raise AssertionError("rebound responder MUST NOT execute")

        replacement.prepare_response = hostile_prepare_response

        def mutating_decoder(body):
            decoded = decode_inbound_control_envelope_json(body)
            object.__setattr__(app, "_federation_responder", replacement)
            return decoded

        app = service(decoder=mutating_decoder)
        with self.assertRaises(InboundHttpError) as raised:
            app.handle(post())
        self.assertEqual(raised.exception.code, "APPLICATION_BINDING_DRIFT")
        self.assertEqual(hostile_calls, [])

    def test_encoder_cannot_rebind_round_trip_decoder(self):
        app = None
        hostile_calls = []
        def hostile_decoder(body):
            hostile_calls.append(body)
            raise AssertionError("rebound round-trip decoder MUST NOT execute")

        def mutating_encoder(envelope):
            body = encode_prepared_inbound_response_json(envelope)
            object.__setattr__(app, "_decode_json", hostile_decoder)
            return body

        app = service(encoder=mutating_encoder)
        with self.assertRaises(InboundHttpError) as raised:
            app.handle(post())
        self.assertEqual(raised.exception.code, "APPLICATION_BINDING_DRIFT")
        self.assertEqual(hostile_calls, [])


if __name__ == "__main__":
    unittest.main()
