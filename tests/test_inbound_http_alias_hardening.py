from __future__ import annotations

from pathlib import Path
import unittest
from unittest.mock import Mock

from marketplace.reference import federation_v1
from marketplace.reference.inbound_http_v1 import (
    decode_inbound_control_envelope_json,
    encode_prepared_inbound_response_json,
)
from marketplace.runtime.inbound_http import (
    BoundedInboundHttpApplicationAdapter,
    InboundFederationHttpRoute,
    InboundHttpApplicationLimits,
    InboundHttpError,
    InboundHttpRequest,
)

from test_inbound_http_hardening import (
    SNAPSHOT_PATH,
    SYNC_PATH,
    FakeSource,
    federation_responder,
    post,
    record,
    record_responder,
)


class InboundHttpAliasHardeningTests(unittest.TestCase):
    def _service(self, *, routes=None, limits=None, authorize=None):
        return BoundedInboundHttpApplicationAdapter(
            federation_responder=federation_responder(authorize=authorize),
            record_responder=record_responder(FakeSource(record())),
            control_routes=routes
            or (
                InboundFederationHttpRoute(SNAPSHOT_PATH, federation_v1.OP_SNAPSHOT),
                InboundFederationHttpRoute(SYNC_PATH, federation_v1.OP_SYNC),
            ),
            decode_transport_envelope_json=decode_inbound_control_envelope_json,
            encode_transport_envelope_json=encode_prepared_inbound_response_json,
            limits=limits,
        )

    def test_promoted_request_authentication_fails_before_disclosure(self):
        authorize = Mock(return_value=True)
        request = post()
        object.__setattr__(request, "request_authenticated", True)
        with self.assertRaises(InboundHttpError) as raised:
            self._service(authorize=authorize).handle(request)
        self.assertEqual(raised.exception.code, "REQUEST_AUTHORITY_PROMOTION")
        authorize.assert_not_called()

    def test_promoted_request_peer_identity_fails_before_disclosure(self):
        authorize = Mock(return_value=True)
        request = post()
        object.__setattr__(request, "peer_identity_proven", True)
        with self.assertRaises(InboundHttpError) as raised:
            self._service(authorize=authorize).handle(request)
        self.assertEqual(raised.exception.code, "REQUEST_AUTHORITY_PROMOTION")
        authorize.assert_not_called()

    def test_prepared_response_detaches_from_caller_request_alias(self):
        request = post()
        original_path = request.path
        prepared = self._service().handle(request)
        object.__setattr__(request, "path", "/attacker/changed-after-handle")
        object.__setattr__(request, "body", b"attacker")
        self.assertEqual(prepared.request.path, original_path)
        self.assertNotEqual(prepared.request.body, b"attacker")

    def test_adapter_detaches_route_operation_from_route_object_alias(self):
        snapshot_route = InboundFederationHttpRoute(SNAPSHOT_PATH, federation_v1.OP_SNAPSHOT)
        sync_route = InboundFederationHttpRoute(SYNC_PATH, federation_v1.OP_SYNC)
        service = self._service(routes=(snapshot_route, sync_route))
        object.__setattr__(snapshot_route, "operation", federation_v1.OP_SYNC)

        prepared = service.handle(post())
        self.assertEqual(prepared.route_operation, federation_v1.OP_SNAPSHOT)

    def test_adapter_detaches_limits_from_caller_alias(self):
        limits = InboundHttpApplicationLimits(max_response_body_bytes=8)
        service = self._service(limits=limits)
        object.__setattr__(limits, "max_response_body_bytes", 16 * 1024 * 1024)

        with self.assertRaises(InboundHttpError) as raised:
            service.handle(post())
        self.assertEqual(raised.exception.code, "RESPONSE_BODY_LIMIT_EXCEEDED")
        self.assertEqual(service.limits.max_response_body_bytes, 8)

    def test_large_decimal_content_length_is_compared_as_text_before_disclosure(self):
        authorize = Mock(return_value=True)
        body = b"{}"
        request = InboundHttpRequest(
            method="POST",
            path=SNAPSHOT_PATH,
            headers=(
                ("content-length", "9" * 4096),
                ("content-type", "application/json"),
            ),
            body=body,
        )
        with self.assertRaises(InboundHttpError) as raised:
            self._service(authorize=authorize).handle(request)
        self.assertEqual(raised.exception.code, "CONTENT_LENGTH_MISMATCH")
        authorize.assert_not_called()

    def test_source_never_parses_declared_content_length_as_python_integer(self):
        source_path = (
            Path(__file__).resolve().parents[1]
            / "src"
            / "marketplace"
            / "runtime"
            / "inbound_http.py"
        )
        source = source_path.read_text(encoding="utf-8")
        self.assertNotIn("int(declared)", source)


if __name__ == "__main__":
    unittest.main()
