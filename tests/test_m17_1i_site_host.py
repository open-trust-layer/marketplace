from __future__ import annotations

import json
import unittest
from pathlib import Path

from marketplace.application.http import (
    ApplicationHttpRequest,
    ApplicationHttpResponse,
    MAX_APPLICATION_HTTP_BODY_BYTES,
    MAX_APPLICATION_HTTP_RESPONSE_BYTES,
)
from marketplace.application.site_host import MarketplaceSiteHostAdapter


ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs" / "m17-1i-same-origin-site-host.md"
SOURCE = ROOT / "src" / "marketplace" / "application" / "site_host.py"


class RecordingApplicationHttp:
    def __init__(self) -> None:
        self.requests: list[ApplicationHttpRequest] = []

    def handle(self, request: ApplicationHttpRequest) -> ApplicationHttpResponse:
        self.requests.append(request)
        return ApplicationHttpResponse(
            200,
            "OK",
            (("Content-Type", "application/json; charset=utf-8"), ("Content-Length", "11")),
            b'{"ok":true}',
        )


def make_host() -> tuple[MarketplaceSiteHostAdapter, RecordingApplicationHttp]:
    api = RecordingApplicationHttp()
    host = MarketplaceSiteHostAdapter(
        application_http=api,
        index_html=b"<!doctype html><title>Marketplace</title>",
        app_js=b"console.log('marketplace');\n",
        styles_css=b"body { margin: 0; }\n",
    )
    return host, api


def request(
    method: str,
    path: str,
    query: tuple[tuple[str, str], ...] = (),
    content_type: str | None = None,
    body: bytes = b"",
) -> ApplicationHttpRequest:
    return ApplicationHttpRequest(method, path, query, content_type, body)


def header(response: ApplicationHttpResponse, name: str) -> str | None:
    return dict(response.headers).get(name)


def error_code(response: ApplicationHttpResponse) -> str:
    return json.loads(response.body.decode("utf-8"))["error"]["code"]


class M17SameOriginSiteHostTests(unittest.TestCase):
    def test_exact_api_paths_delegate_without_rewriting_request_or_response(self):
        host, api = make_host()
        original = request("GET", "/api/intents", (("limit", "2"),))
        response = host.handle(original)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.body, b'{"ok":true}')
        self.assertEqual(api.requests, [original])

    def test_exact_static_surface_uses_injected_bytes_and_deterministic_content_types(self):
        host, api = make_host()
        expected = {
            "/": (b"<!doctype html><title>Marketplace</title>", "text/html; charset=utf-8"),
            "/index.html": (b"<!doctype html><title>Marketplace</title>", "text/html; charset=utf-8"),
            "/app.js": (b"console.log('marketplace');\n", "text/javascript; charset=utf-8"),
            "/styles.css": (b"body { margin: 0; }\n", "text/css; charset=utf-8"),
        }
        for path, (body, content_type) in expected.items():
            with self.subTest(path=path):
                response = host.handle(request("GET", path))
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.body, body)
                self.assertEqual(header(response, "Content-Type"), content_type)
                self.assertEqual(header(response, "Content-Length"), str(len(body)))
                self.assertEqual(header(response, "Cache-Control"), "no-store")
                self.assertEqual(header(response, "Cross-Origin-Resource-Policy"), "same-origin")
                self.assertIsNone(header(response, "Access-Control-Allow-Origin"))
        self.assertEqual(api.requests, [])

    def test_static_routes_reject_method_query_entity_and_content_type_fail_closed(self):
        host, _ = make_host()
        post = host.handle(request("POST", "/"))
        self.assertEqual(post.status_code, 405)
        self.assertEqual(header(post, "Allow"), "GET")
        self.assertEqual(error_code(post), "METHOD_NOT_ALLOWED")
        for candidate in (
            request("GET", "/", (("x", "1"),)),
            request("GET", "/", (), "application/json", b""),
            request("GET", "/", (), None, b"x"),
        ):
            with self.subTest(candidate=candidate):
                response = host.handle(candidate)
                self.assertEqual(response.status_code, 400)
                self.assertEqual(error_code(response), "REQUEST_INVALID")

    def test_unknown_alias_and_traversal_paths_do_not_delegate(self):
        host, api = make_host()
        for path in (
            "/INDEX.HTML",
            "//index.html",
            "/./index.html",
            "/../web/index.html",
            "/%2e%2e/index.html",
            "/app.js/",
            "/api",
        ):
            with self.subTest(path=path):
                response = host.handle(request("GET", path))
                self.assertEqual(response.status_code, 404)
                self.assertEqual(error_code(response), "ROUTE_NOT_FOUND")
        self.assertEqual(api.requests, [])

    def test_request_bounds_and_duplicate_query_fail_before_api_delegation(self):
        host, api = make_host()
        oversized = host.handle(request("POST", "/api/intents", body=b"x" * (MAX_APPLICATION_HTTP_BODY_BYTES + 1)))
        self.assertEqual(oversized.status_code, 413)
        self.assertEqual(error_code(oversized), "PAYLOAD_TOO_LARGE")
        duplicate = host.handle(request("GET", "/api/intents", (("limit", "1"), ("limit", "2"))))
        self.assertEqual(duplicate.status_code, 400)
        self.assertEqual(error_code(duplicate), "QUERY_INVALID")
        self.assertEqual(api.requests, [])

    def test_injected_static_assets_are_exact_bounded_bytes(self):
        api = RecordingApplicationHttp()
        with self.assertRaises(TypeError):
            MarketplaceSiteHostAdapter(application_http=api, index_html="x", app_js=b"x", styles_css=b"x")  # type: ignore[arg-type]
        with self.assertRaises(ValueError):
            MarketplaceSiteHostAdapter(application_http=api, index_html=b"", app_js=b"x", styles_css=b"x")
        with self.assertRaises(ValueError):
            MarketplaceSiteHostAdapter(
                application_http=api,
                index_html=b"x" * (MAX_APPLICATION_HTTP_RESPONSE_BYTES + 1),
                app_js=b"x",
                styles_css=b"x",
            )

    def test_source_has_no_runtime_file_network_process_or_cors_authority(self):
        text = SOURCE.read_text(encoding="utf-8").lower()
        for forbidden in (
            "open(",
            "pathlib",
            "os.environ",
            "socket",
            "http.server",
            "urllib",
            "requests",
            "subprocess",
            ".bind(",
            ".listen(",
            "access-control-allow-origin",
        ):
            self.assertNotIn(forbidden, text)

    def test_document_preserves_inert_same_origin_authority_boundary(self):
        self.assertTrue(DOC.is_file())
        text = DOC.read_text(encoding="utf-8")
        for marker in (
            "same-origin",
            "injected static asset bytes",
            "no socket/server activation",
            "no runtime filesystem traversal",
            "no live PostgreSQL connection",
            "no CORS expansion",
            "source-only",
        ):
            self.assertIn(marker, text)


if __name__ == "__main__":
    unittest.main()
