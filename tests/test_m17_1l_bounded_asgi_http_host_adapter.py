from __future__ import annotations

import asyncio
from pathlib import Path
import unittest

from marketplace.application.asgi import AsgiHttpAdapterError, MarketplaceAsgiHttpAdapter
from marketplace.application.http import ApplicationHttpResponse
from marketplace.application.site_host import MarketplaceSiteHostAdapter


ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs" / "m17-1l-bounded-asgi-http-host-adapter.md"
SOURCE = ROOT / "src" / "marketplace" / "application" / "asgi.py"
INDEX = b"<!doctype html><title>Marketplace</title>"
APP_JS = b"console.log('marketplace');\n"
STYLES = b"body { margin: 0; }\n"


class RecordingApplicationHttpPort:
    def __init__(self) -> None:
        self.requests = []

    def handle(self, request):
        self.requests.append(request)
        body = b'{"ok":true}'
        return ApplicationHttpResponse(
            200,
            "OK",
            (
                ("Content-Type", "application/json; charset=utf-8"),
                ("Content-Length", str(len(body))),
                ("Cache-Control", "no-store"),
            ),
            body,
        )


def make_adapter():
    port = RecordingApplicationHttpPort()
    site = MarketplaceSiteHostAdapter(
        application_http=port,
        index_html=INDEX,
        app_js=APP_JS,
        styles_css=STYLES,
    )
    return MarketplaceAsgiHttpAdapter(site=site), port


def scope(*, method="GET", path="/", query_string=b"", headers=()):
    return {
        "type": "http",
        "asgi": {"version": "3.0", "spec_version": "2.5"},
        "http_version": "1.1",
        "method": method,
        "scheme": "http",
        "path": path,
        "raw_path": path.encode("utf-8"),
        "query_string": query_string,
        "root_path": "",
        "headers": list(headers),
        "client": ("127.0.0.1", 12345),
        "server": ("127.0.0.1", 8080),
    }


async def invoke(adapter, request_scope, events):
    pending = list(events)
    sent = []

    async def receive():
        if not pending:
            raise AssertionError("adapter requested an unexpected extra ASGI event")
        return pending.pop(0)

    async def send(message):
        sent.append(message)

    await adapter(request_scope, receive, send)
    return sent


class M17BoundedAsgiHttpHostAdapterTests(unittest.TestCase):
    def test_static_site_round_trip_uses_existing_site_host(self):
        adapter, port = make_adapter()
        sent = asyncio.run(
            invoke(
                adapter,
                scope(headers=((b"accept", b"text/html"),)),
                ({"type": "http.request", "body": b"", "more_body": False},),
            )
        )
        self.assertEqual([message["type"] for message in sent], ["http.response.start", "http.response.body"])
        self.assertEqual(sent[0]["status"], 200)
        self.assertEqual(sent[1]["body"], INDEX)
        self.assertEqual(sent[1]["more_body"], False)
        self.assertEqual(port.requests, [])

    def test_decoded_path_and_strict_percent_decoded_query_reach_application_port(self):
        adapter, port = make_adapter()
        sent = asyncio.run(
            invoke(
                adapter,
                scope(
                    path="/api/intents/r:id",
                    query_string=b"cursor=r%3A1&limit=64",
                    headers=((b"accept", b"application/json"),),
                ),
                ({"type": "http.request", "body": b"", "more_body": False},),
            )
        )
        self.assertEqual(sent[0]["status"], 200)
        self.assertEqual(len(port.requests), 1)
        request = port.requests[0]
        self.assertEqual(request.path, "/api/intents/r:id")
        self.assertEqual(request.query, (("cursor", "r:1"), ("limit", "64")))
        self.assertIsNone(request.content_type)
        self.assertEqual(request.body, b"")

    def test_chunked_request_body_and_content_type_are_bounded_and_joined(self):
        adapter, port = make_adapter()
        asyncio.run(
            invoke(
                adapter,
                scope(
                    method="POST",
                    path="/api/intents",
                    headers=((b"content-type", b"application/json"), (b"content-length", b"7")),
                ),
                (
                    {"type": "http.request", "body": b'{"x":', "more_body": True},
                    {"type": "http.request", "body": b"1}", "more_body": False},
                ),
            )
        )
        request = port.requests[0]
        self.assertEqual(request.content_type, "application/json")
        self.assertEqual(request.body, b'{"x":1}')

    def test_non_http_scope_is_rejected_without_receive_or_send(self):
        adapter, _ = make_adapter()
        with self.assertRaises(AsgiHttpAdapterError) as caught:
            asyncio.run(
                invoke(
                    adapter,
                    {"type": "websocket", "asgi": {"version": "3.0"}},
                    (),
                )
            )
        self.assertEqual(caught.exception.code, "ASGI_SCOPE_UNSUPPORTED")

    def test_malformed_query_duplicate_sensitive_headers_and_disconnect_fail_closed(self):
        cases = (
            (
                scope(path="/api/intents", query_string=b"cursor=%ZZ"),
                ({"type": "http.request", "body": b"", "more_body": False},),
                "ASGI_QUERY_INVALID",
            ),
            (
                scope(headers=((b"content-type", b"application/json"), (b"content-type", b"application/json"))),
                ({"type": "http.request", "body": b"", "more_body": False},),
                "ASGI_HEADER_INVALID",
            ),
            (
                scope(headers=((b"authorization", b"Bearer secret"),)),
                ({"type": "http.request", "body": b"", "more_body": False},),
                "ASGI_SENSITIVE_HEADER_FORBIDDEN",
            ),
            (
                scope(),
                ({"type": "http.disconnect"},),
                "ASGI_REQUEST_DISCONNECTED",
            ),
        )
        for request_scope, events, code in cases:
            with self.subTest(code=code):
                adapter, _ = make_adapter()
                with self.assertRaises(AsgiHttpAdapterError) as caught:
                    asyncio.run(invoke(adapter, request_scope, events))
                self.assertEqual(caught.exception.code, code)

    def test_source_and_document_preserve_source_only_authority_boundary(self):
        self.assertTrue(SOURCE.is_file())
        source = SOURCE.read_text(encoding="utf-8")
        for forbidden in (
            "import socket",
            "from socket",
            "uvicorn",
            "hypercorn",
            "daphne",
            "os.environ",
            "Path(",
            "open(",
            ".initialize(",
        ):
            self.assertNotIn(forbidden, source)
        self.assertTrue(DOC.is_file())
        document = DOC.read_text(encoding="utf-8")
        for marker in (
            "source-only ASGI 3 HTTP adapter",
            "no server startup",
            "no socket bind/listen/accept/connect",
            "no live PostgreSQL connection",
            "no runtime filesystem asset loading",
            "no WebSocket or lifespan authority",
        ):
            self.assertIn(marker, document)


if __name__ == "__main__":
    unittest.main()
