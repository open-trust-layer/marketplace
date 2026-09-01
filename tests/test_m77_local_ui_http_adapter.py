from __future__ import annotations

from dataclasses import FrozenInstanceError
from urllib.parse import urlencode
import unittest

from marketplace.reference.local_ui_http_v1 import (
    MAX_LOCAL_UI_HTTP_BODY_BYTES,
    LocalUiHttpError,
    LocalUiHttpRequest,
    LocalUiHttpResponse,
    handle_local_ui_http_request,
)
from marketplace.reference.local_visual_v1 import render_local_buy_sell_form


FIELDS = {
    "seller_principal": "did:example:seller",
    "subject_uri": "urn:example:product:bicycle-1",
    "title": "City bicycle",
    "description": "One carefully maintained bicycle.",
    "consideration": "125.00",
    "currency_code": "EUR",
    "quantity": "1",
    "unit_uri": "https://open-trust-layer.github.io/marketplace/semantics/v1/profile/product-listing-v1/unit/item",
    "latitude": "52.520000",
    "longitude": "13.405000",
    "buyer_principal": "did:example:buyer",
    "buyer_action_uri": "https://example.test/actions/buy",
}


def form_request(body: bytes | None = None, *, content_type: str = "application/x-www-form-urlencoded") -> LocalUiHttpRequest:
    if body is None:
        body = urlencode(FIELDS).encode("ascii")
    return LocalUiHttpRequest(
        method="POST",
        target="/local-buy-sell",
        content_type=content_type,
        body=body,
    )


class M77LocalUiHttpAdapterTests(unittest.TestCase):
    def assert_safe_html_response(self, response: LocalUiHttpResponse, expected_status: int) -> None:
        self.assertIs(type(response), LocalUiHttpResponse)
        self.assertEqual(response.status_code, expected_status)
        headers = dict(response.headers)
        self.assertEqual(headers["Content-Type"], "text/html; charset=utf-8")
        self.assertEqual(headers["Content-Length"], str(len(response.body)))
        self.assertEqual(headers["Cache-Control"], "no-store")
        self.assertEqual(headers["X-Content-Type-Options"], "nosniff")
        self.assertEqual(headers["Referrer-Policy"], "no-referrer")
        self.assertIn("default-src 'none'", headers["Content-Security-Policy"])
        self.assertNotIn("Set-Cookie", headers)

    def test_get_root_returns_exact_reviewed_m76_form(self):
        request = LocalUiHttpRequest(method="GET", target="/", content_type=None, body=b"")

        response = handle_local_ui_http_request(request)

        self.assert_safe_html_response(response, 200)
        self.assertEqual(response.body, render_local_buy_sell_form().encode("utf-8"))

    def test_valid_post_completes_exact_m76_path(self):
        response = handle_local_ui_http_request(form_request())

        self.assert_safe_html_response(response, 200)
        page = response.body.decode("utf-8")
        self.assertIn("COMPATIBLE_UNDER_METHOD", page)
        self.assertIn("protocol_truth=false", page)
        self.assertIn("creates_agreement=false", page)
        self.assertNotIn(FIELDS["description"], page)
        self.assertNotIn(FIELDS["buyer_principal"], page)
        self.assertNotIn(FIELDS["buyer_action_uri"], page)

    def test_form_requires_exact_twelve_unique_known_fields(self):
        cases = {
            "missing": urlencode(list(FIELDS.items())[:-1]).encode("ascii"),
            "duplicate": (urlencode(FIELDS) + "&title=again").encode("ascii"),
            "unknown": (urlencode(list(FIELDS.items())[:-1]) + "&surprise=value").encode("ascii"),
        }
        for name, body in cases.items():
            with self.subTest(name=name):
                response = handle_local_ui_http_request(form_request(body))
                self.assert_safe_html_response(response, 400)
                self.assertNotIn(body[:40], response.body)

    def test_malformed_percent_encoding_and_invalid_utf8_fail_non_reflectively(self):
        base = urlencode(list(FIELDS.items())[:-1])
        for hostile in ("buyer_action_uri=%ZZ-HOSTILE", "buyer_action_uri=%FF-HOSTILE"):
            with self.subTest(hostile=hostile):
                response = handle_local_ui_http_request(form_request(f"{base}&{hostile}".encode("ascii")))
                self.assert_safe_html_response(response, 400)
                self.assertNotIn(b"HOSTILE", response.body)

    def test_routes_methods_and_content_type_are_exact(self):
        cases = (
            (LocalUiHttpRequest("GET", "/local-buy-sell", None, b""), 405, "POST"),
            (LocalUiHttpRequest("POST", "/", "application/x-www-form-urlencoded", b""), 405, "GET"),
            (LocalUiHttpRequest("GET", "/missing", None, b""), 404, None),
            (form_request(content_type="application/x-www-form-urlencoded; charset=utf-8"), 415, None),
            (LocalUiHttpRequest("get", "/", None, b""), 405, "GET"),
        )
        for request, status, allow in cases:
            with self.subTest(request=request):
                response = handle_local_ui_http_request(request)
                self.assert_safe_html_response(response, status)
                headers = dict(response.headers)
                if allow is None:
                    self.assertNotIn("Allow", headers)
                else:
                    self.assertEqual(headers["Allow"], allow)

    def test_get_request_rejects_body_or_content_type(self):
        for request in (
            LocalUiHttpRequest("GET", "/", None, b"x"),
            LocalUiHttpRequest("GET", "/", "text/plain", b""),
        ):
            response = handle_local_ui_http_request(request)
            self.assert_safe_html_response(response, 400)

    def test_oversized_body_is_rejected_before_decoding(self):
        body = b"x" * (MAX_LOCAL_UI_HTTP_BODY_BYTES + 1)
        response = handle_local_ui_http_request(form_request(body))
        self.assert_safe_html_response(response, 413)

    def test_request_is_frozen_and_exact_type_is_required(self):
        request = LocalUiHttpRequest("GET", "/", None, b"")
        with self.assertRaises(FrozenInstanceError):
            request.method = "POST"  # type: ignore[misc]

        class DerivedRequest(LocalUiHttpRequest):
            pass

        with self.assertRaises(LocalUiHttpError) as raised:
            handle_local_ui_http_request(DerivedRequest("GET", "/", None, b""))
        self.assertEqual(raised.exception.code, "REQUEST_INVALID")

    def test_non_exact_request_field_types_fail_closed(self):
        hostile_requests = (
            LocalUiHttpRequest(b"GET", "/", None, b""),  # type: ignore[arg-type]
            LocalUiHttpRequest("GET", b"/", None, b""),  # type: ignore[arg-type]
            LocalUiHttpRequest("GET", "/", None, bytearray()),  # type: ignore[arg-type]
        )
        for request in hostile_requests:
            with self.subTest(request=request):
                with self.assertRaises(LocalUiHttpError) as raised:
                    handle_local_ui_http_request(request)
                self.assertEqual(raised.exception.code, "REQUEST_INVALID")


if __name__ == "__main__":
    unittest.main()
