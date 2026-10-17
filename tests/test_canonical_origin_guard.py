"""Synthetic public-origin ASGI guard security tests; no server or network."""
from __future__ import annotations

import unittest

from marketplace.application.canonical_origin_guard import (
    CANONICAL_HOST,
    CANONICAL_ORIGIN,
    MarketplaceCanonicalOriginAsgiGuard,
)


def scope(method: str = "GET", headers=None, scheme: str = "https"):
    return {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": method,
        "path": "/api/agreements",
        "root_path": "",
        "scheme": scheme,
        "headers": [(b"host", CANONICAL_HOST)] if headers is None else headers,
    }


class CanonicalOriginGuardTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.calls = 0
        self.receives = 0
        self.events: list[dict] = []

        async def app(request, receive, send):
            self.calls += 1
            self.assertEqual(request["path"], "/api/agreements")
            await send({"type": "http.response.start", "status": 204, "headers": []})
            await send({"type": "http.response.body", "body": b"", "more_body": False})

        async def receive():
            self.receives += 1
            return {"type": "http.request", "body": b""}

        async def send(event):
            self.events.append(event)

        self.guard = MarketplaceCanonicalOriginAsgiGuard(app=app)
        self.receive = receive
        self.send = send

    async def invoke(self, request):
        await self.guard(request, self.receive, self.send)
        return self.events[0]["status"]

    def assert_rejected(self, expected: int) -> None:
        self.assertEqual(self.calls, 0)
        self.assertEqual(self.receives, 0)
        self.assertEqual(len(self.events), 2)
        self.assertEqual(self.events[0]["status"], expected)
        self.assertTrue(self.events[1]["body"].isupper())
        self.assertIn((b"cache-control", b"no-store"), self.events[0]["headers"])

    async def test_get_canonical_host_delegates_without_mutating_scope(self):
        original = scope()
        self.assertEqual(await self.invoke(original), 204)
        self.assertEqual(self.calls, 1)
        self.assertEqual(self.receives, 0)
        self.assertEqual(original["headers"], [(b"host", CANONICAL_HOST)])

    async def test_same_origin_post_with_explicit_port_allowed(self):
        s = scope("POST", [(b"Host", CANONICAL_HOST + b":443"), (b"Origin", CANONICAL_ORIGIN)])
        self.assertEqual(await self.invoke(s), 204)
        self.assertEqual(self.calls, 1)

    async def test_valid_origin_allowed_on_get(self):
        s = scope("GET", [(b"host", CANONICAL_HOST), (b"origin", CANONICAL_ORIGIN)])
        self.assertEqual(await self.invoke(s), 204)

    async def test_host_is_required_and_noncanonical_host_rejected(self):
        for headers in (
            [], [(b"host", b"open-trust-layer.org")],
            [(b"host", b"attacker.example")],
            [(b"host", b"marketplace.open-trust-layer.org:80")],
            [(b"host", b"MARKETPLACE.OPEN-TRUST-LAYER.ORG")],
            [(b"host", CANONICAL_HOST + b".")],
            [(b"host", CANONICAL_HOST + b"@attacker.example")],
        ):
            with self.subTest(headers=headers):
                self.events.clear()
                self.assertEqual(await self.invoke(scope(headers=headers)), 421)
                self.assert_rejected(421)

    async def test_duplicate_host_or_origin_fails_before_app(self):
        cases = (
            ([(b"host", CANONICAL_HOST), (b"HOST", CANONICAL_HOST)], 400),
            ([(b"host", CANONICAL_HOST), (b"origin", CANONICAL_ORIGIN),
              (b"Origin", CANONICAL_ORIGIN)], 400),
        )
        for headers, expected in cases:
            with self.subTest(headers=headers):
                self.events.clear()
                self.assertEqual(await self.invoke(scope(headers=headers)), expected)
                self.assert_rejected(expected)

    async def test_unsafe_methods_require_exact_origin(self):
        for method in ("POST", "PUT", "PATCH", "DELETE"):
            with self.subTest(method=method):
                self.events.clear()
                self.assertEqual(await self.invoke(scope(method)), 403)
                self.assert_rejected(403)

    async def test_malformed_or_foreign_origin_rejected_even_on_get(self):
        for origin in (
            b"http://marketplace.open-trust-layer.org",
            b"https://evil.example",
            CANONICAL_ORIGIN + b"/",
            CANONICAL_ORIGIN + b":443",
            b"null",
            b"HTTPS://marketplace.open-trust-layer.org",
            b"https://marketplace.open-trust-layer.org.evil.example",
        ):
            with self.subTest(origin=origin):
                self.events.clear()
                s = scope(headers=[(b"host", CANONICAL_HOST), (b"origin", origin)])
                self.assertEqual(await self.invoke(s), 403)
                self.assert_rejected(403)

    async def test_http_or_untrusted_proxy_metadata_never_delegates(self):
        self.assertEqual(await self.invoke(scope(scheme="http")), 403)
        self.assert_rejected(403)
        for key in (b"x-forwarded-proto", b"x-forwarded-host", b"x-forwarded-for",
                    b"forwarded", b"x-real-ip", b"x-original-url"):
            with self.subTest(key=key):
                self.events.clear()
                s = scope(headers=[(b"host", CANONICAL_HOST), (key, b"evil")])
                self.assertEqual(await self.invoke(s), 400)
                self.assert_rejected(400)

    async def test_non_http_wrong_asgi_and_method_rejected(self):
        cases = (
            ({**scope(), "type": "websocket"}, 400),
            ({**scope(), "asgi": {"version": "2.0"}}, 400),
            ({**scope(), "root_path": "/app"}, 400),
            ({**scope(), "method": "TRACE"}, 405),
            ({**scope(), "method": "CONNECT"}, 405),
        )
        for s, expected in cases:
            with self.subTest(expected=expected):
                self.events.clear()
                self.assertEqual(await self.invoke(s), expected)
                self.assert_rejected(expected)

    async def test_header_limits_and_control_bytes_fail_closed(self):
        cases = (
            [(b"host", CANONICAL_HOST)] * 65,
            [(b"host", CANONICAL_HOST), (b"x-bad", b"a\r\nb")],
            [(b"host", CANONICAL_HOST), (b"\xff", b"value")],
            [(b"host", CANONICAL_HOST), (b"x-note", b"a" * 9000)],
            [(b"host", CANONICAL_HOST), ("x-string", b"value")],
            [(b"host", CANONICAL_HOST), (b"x-note", "string")],
            [(b"host", CANONICAL_HOST), (b"x-note", b"\0")],
        )
        for headers in cases:
            with self.subTest(headers_count=len(headers)):
                self.events.clear()
                self.assertEqual(await self.invoke(scope(headers=headers)), 400)
                self.assert_rejected(400)

    async def test_rejections_are_constant_not_reflecting_attacker_input(self):
        attack = b"my-private-token-89"
        s = scope(headers=[(b"host", CANONICAL_HOST), (b"origin", attack)])
        self.assertEqual(await self.invoke(s), 403)
        self.assertNotIn(attack, repr(self.events).encode("utf-8"))
        self.assertEqual(self.events[1]["body"], b"ORIGIN_REJECTED")

    async def test_no_application_or_resource_used_during_construction(self):
        counter = {"calls": 0}
        async def app(*_args):
            counter["calls"] += 1
        guard = MarketplaceCanonicalOriginAsgiGuard(app=app)
        self.assertEqual(counter["calls"], 0)
        self.assertIsNotNone(guard)
        with self.assertRaises(TypeError):
            MarketplaceCanonicalOriginAsgiGuard(app=object())


if __name__ == "__main__":
    unittest.main()
