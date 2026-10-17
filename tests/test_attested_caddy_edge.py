"""Synthetic tests for dormant attested Caddy->ASGI trust boundary."""
from __future__ import annotations

import unittest

from marketplace.application.attested_caddy_edge import (
    MarketplaceAttestedCaddyEdgeAsgiAdapter,
)
from marketplace.application.canonical_origin_guard import (
    CANONICAL_HOST,
    CANONICAL_ORIGIN,
    MarketplaceCanonicalOriginAsgiGuard,
)


def caddy_scope(method="GET", headers=None, scheme="http"):
    return {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "scheme": scheme,
        "root_path": "",
        "method": method,
        "path": "/api/agreements",
        "headers": (
            [(b"host", CANONICAL_HOST),
             (b"x-forwarded-host", CANONICAL_HOST),
             (b"x-forwarded-proto", b"https"),
             (b"x-forwarded-for", b"198.51.100.8")]
            if headers is None else headers
        ),
    }


class Verifier:
    def __init__(self, result=True, *, raises=False):
        self.result = result
        self.raises = raises
        self.calls = 0
        self.seen = None

    def verify_connection(self, scope):
        self.calls += 1
        self.seen = scope
        if self.raises:
            raise RuntimeError("client-token-secret")
        return self.result


class AttestedCaddyEdgeTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.app_calls = 0
        self.receives = 0
        self.events = []

        async def app(scope, receive, send):
            self.app_calls += 1
            self.app_scope = scope
            await send({"type": "http.response.start", "status": 204, "headers": []})
            await send({"type": "http.response.body", "body": b"", "more_body": False})

        self.app = app
        self.verifier = Verifier()

        async def receive():
            self.receives += 1
            return {"type": "http.request", "body": b""}

        async def send(event):
            self.events.append(event)

        self.receive = receive
        self.send = send

    def adapter(self, verifier=None):
        return MarketplaceAttestedCaddyEdgeAsgiAdapter(
            guard=MarketplaceCanonicalOriginAsgiGuard(app=self.app),
            verifier=self.verifier if verifier is None else verifier,
        )

    async def check(self, request, verifier=None):
        await self.adapter(verifier)(request, self.receive, self.send)
        return self.events[0]["status"]

    def assert_deny(self):
        self.assertEqual(self.events[0]["status"], 403)
        self.assertEqual(self.events[1]["body"], b"TRUSTED_EDGE_REQUIRED")
        self.assertEqual(self.app_calls, 0)
        self.assertEqual(self.receives, 0)
        self.assertIn((b"cache-control", b"no-store"), self.events[0]["headers"])

    async def test_proven_caddy_headers_normalized_before_guard(self):
        original = caddy_scope()
        self.assertEqual(await self.check(original), 204)
        self.assertEqual(self.verifier.calls, 1)
        self.assertIs(self.verifier.seen, original)
        self.assertEqual(self.app_calls, 1)
        self.assertEqual(self.app_scope["scheme"], "https")
        self.assertEqual(self.app_scope["headers"], [(b"host", CANONICAL_HOST)])
        self.assertEqual(original["scheme"], "http")
        self.assertEqual(len(original["headers"]), 4)

    async def test_attested_post_with_exact_origin_delegates(self):
        headers = caddy_scope()["headers"] + [(b"origin", CANONICAL_ORIGIN)]
        self.assertEqual(await self.check(caddy_scope(method="POST", headers=headers)), 204)
        self.assertEqual(self.app_calls, 1)

    async def test_post_without_origin_is_still_rejected_by_downstream_guard(self):
        self.assertEqual(await self.check(caddy_scope(method="POST")), 403)
        self.assertEqual(self.verifier.calls, 1)
        self.assertEqual(self.app_calls, 0)
        self.assertEqual(self.receives, 0)
        self.assertEqual(self.events[1]["body"], b"ORIGIN_REQUIRED")

    async def test_peer_denial_does_not_delegate_even_with_perfect_headers(self):
        for verifier in (Verifier(False), Verifier(1), Verifier(None), Verifier(raises=True)):
            with self.subTest(verifier=verifier.result, raises=verifier.raises):
                self.events.clear()
                self.assertEqual(await self.check(caddy_scope(), verifier), 403)
                self.assert_deny()
                self.assertEqual(verifier.calls, 1)
                self.assertNotIn(b"client-token-secret", repr(self.events).encode("utf-8"))

    async def test_no_evidence_from_loopback_scope_without_real_verifier(self):
        bad = Verifier(False)
        s = caddy_scope()
        s["client"] = ("127.0.0.1", 33333)
        s["server"] = ("127.0.0.1", 24081)
        self.assertEqual(await self.check(s, bad), 403)
        self.assert_deny()

    async def test_malformed_forwarding_never_checks_peer_or_app(self):
        original = caddy_scope()["headers"]
        variations = (
            original[:1],  # no metadata
            original[:2] + [(b"x-forwarded-proto", b"http")],
            original[:2] + [(b"x-forwarded-proto", b"HTTPS")],
            original[:2] + [(b"x-forwarded-proto", b"https,https")],
            original[:2] + [(b"x-forwarded-proto", b"https\r\n")],
            original[:1] + [(b"x-forwarded-host", b"evil.example"), (b"x-forwarded-proto", b"https")],
            original + [(b"X-Forwarded-Proto", b"https")],
            original + [(b"x-forwarded-host", CANONICAL_HOST)],
            original + [(b"forwarded", b"proto=https;host=evil.example")],
            original + [(b"x-real-ip", b"127.0.0.1")],
            original + [(b"x-forwarded-port", b"443")],
            original + [(b"x-forwarded-prefix", b"/")],
            original + [(b"x-original-host", b"evil.example")],
            original + [(b"host", CANONICAL_HOST)],
            original + [(b"origin", b"attack\x00")],
            original + [(b"x-note", b"\xff")]*65,
        )
        for headers in variations:
            with self.subTest(headers_count=len(headers), tail=headers[-1] if headers else None):
                self.events.clear()
                self.assertEqual(await self.check(caddy_scope(headers=headers)), 403)
                self.assert_deny()
                self.assertEqual(self.verifier.calls, 0)

    async def test_wrong_scope_scheme_and_asgi_never_delegates(self):
        cases = (
            {**caddy_scope(), "scheme": "https"},
            {**caddy_scope(), "scheme": "ws"},
            {**caddy_scope(), "type": "websocket"},
            {**caddy_scope(), "asgi": {"version": "2.0"}},
            {**caddy_scope(), "root_path": "/prefix"},
        )
        for case in cases:
            with self.subTest(case=case.get("scheme")):
                self.events.clear()
                self.assertEqual(await self.check(case), 403)
                self.assert_deny()
                self.assertEqual(self.verifier.calls, 0)

    async def test_host_and_origin_protection_remains_in_force(self):
        variants = (
            ([(b"host", b"evil.example"),
              (b"x-forwarded-host", b"evil.example"),
              (b"x-forwarded-proto", b"https")], 403),
            ([(b"host", CANONICAL_HOST),
              (b"x-forwarded-host", CANONICAL_HOST),
              (b"x-forwarded-proto", b"https"),
              (b"origin", b"https://evil.example")], 403),
        )
        for headers, expected in variants:
            with self.subTest(headers=headers):
                self.events.clear()
                self.assertEqual(await self.check(caddy_scope(headers=headers)), expected)
                self.assertEqual(self.app_calls, 0)

    async def test_forwarded_client_identity_discarded(self):
        s = caddy_scope(headers=caddy_scope()["headers"][:3] + [
            (b"x-forwarded-for", b"203.0.113.5, 192.0.2.33")
        ])
        self.assertEqual(await self.check(s), 204)
        self.assertNotIn(b"x-forwarded-for", [p[0] for p in self.app_scope["headers"]])
        self.assertEqual(self.app_calls, 1)

    async def test_requires_exact_guard_and_verifier(self):
        with self.assertRaises(TypeError):
            MarketplaceAttestedCaddyEdgeAsgiAdapter(guard=self.app, verifier=Verifier())
        with self.assertRaises(TypeError):
            MarketplaceAttestedCaddyEdgeAsgiAdapter(
                guard=MarketplaceCanonicalOriginAsgiGuard(app=self.app),
                verifier=object(),
            )
        self.assertEqual(self.app_calls, 0)


if __name__ == "__main__":
    unittest.main()
