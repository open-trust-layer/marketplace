from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WEB_INDEX = ROOT / "web" / "index.html"
WEB_APP = ROOT / "web" / "app.js"
WEB_SESSION = ROOT / "web" / "client_session.js"
ANDROID = ROOT / "android" / "app" / "src" / "main" / "java" / "org" / "opentrustlayer" / "marketplace"
ANDROID_MAIN = ANDROID / "MainActivity.kt"
ANDROID_CLIENT = ANDROID / "MarketplaceApiClient.kt"
ANDROID_TRANSPORT = ANDROID / "LoopbackMarketplaceTransport.kt"
ANDROID_SESSION = ANDROID / "MarketplaceClientSession.kt"
ANDROID_CACHE = ANDROID / "MarketplaceOfflineCache.kt"
DOC = ROOT / "docs" / "m17-5e-client-session.md"


class M175EClientSessionArtifactTests(unittest.TestCase):
    def test_required_source_only_client_session_artifacts_exist(self):
        for path in (WEB_SESSION, ANDROID_SESSION, DOC):
            self.assertTrue(path.is_file(), str(path))

    def test_active_web_and_android_composition_remain_unselected(self):
        index = WEB_INDEX.read_text(encoding="utf-8")
        app = WEB_APP.read_text(encoding="utf-8")
        main = ANDROID_MAIN.read_text(encoding="utf-8")
        self.assertNotIn("client_session.js", index)
        self.assertNotIn("MarketplaceMemorySession", app)
        self.assertIn('credentials: "omit"', app)
        self.assertNotIn("Authorization", app)
        self.assertNotIn("MarketplaceSessionClient", main)
        self.assertIn("LoopbackMarketplaceTransport()", main)

    def test_web_memory_session_uses_private_token_and_exact_bearer_shape(self):
        text = WEB_SESSION.read_text(encoding="utf-8")
        for marker in (
            r"/^mkt1_[A-Za-z0-9_-]{43}$/",
            "#bearerToken",
            'return `Bearer ${token}`',
            "MarketplaceMemorySession(active=",
            "AUTH_REQUIRED",
            "AUTH_SESSION_INVALID",
        ):
            self.assertIn(marker, text)
        self.assertNotIn("this.bearerToken", text)

    def test_web_bearer_is_route_scoped_and_anonymous_reads_remain_bearer_negative(self):
        text = WEB_SESSION.read_text(encoding="utf-8")
        for marker in (
            'path === "/api/auth/session"',
            'path === "/api/auth/logout"',
            'path === "/api/product-listings"',
            'path === "/api/intents"',
            'tail === "responses"',
            'tail === "proposals"',
            'headers.Authorization = authorization',
        ):
            self.assertIn(marker, text)
        self.assertIn("if (!reviewedAuthenticatedRoute(method, path)) return null;", text)
        self.assertNotIn('path.startsWith("/api/") && authorization', text)

    def test_web_authenticated_structured_authoring_derives_principal(self):
        text = WEB_SESSION.read_text(encoding="utf-8")
        listing_start = text.index("function productListingForSession")
        proposal_start = text.index("function proposalForSession", listing_start)
        raw_start = text.index("function requireRawIssuer", proposal_start)
        listing = text[listing_start:proposal_start]
        proposal = text[proposal_start:raw_start]
        self.assertIn("seller_principal: session.requirePrincipal()", listing)
        self.assertIn('Object.hasOwn(fields, "seller_principal")', listing)
        self.assertIn("buyer_principal: session.requirePrincipal()", proposal)
        self.assertIn('Object.hasOwn(fields, "buyer_principal")', proposal)
        self.assertIn("AUTH_PRINCIPAL_MISMATCH", listing + proposal)

    def test_web_logout_is_local_first_single_attempt_and_never_restores(self):
        text = WEB_SESSION.read_text(encoding="utf-8")
        start = text.index("async function logout")
        end = text.index("export {", start)
        block = text[start:end]
        self.assertIn("session.detachAuthorizationForLogout()", block)
        self.assertEqual(block.count("fetchImpl("), 1)
        self.assertNotIn("retry", block.lower())
        self.assertNotIn("adoptEstablishedSession", block)

    def test_web_has_no_persistence_background_or_secret_reflection_capability(self):
        text = WEB_SESSION.read_text(encoding="utf-8").lower()
        for forbidden in (
            "localstorage", "sessionstorage", "indexeddb", "caches.open",
            "document.cookie", "serviceworker", "setinterval", "settimeout",
            "websocket", "eventsource", "console.log", "console.error",
        ):
            self.assertNotIn(forbidden, text)

    def test_android_request_value_object_remains_credential_negative(self):
        text = ANDROID_CLIENT.read_text(encoding="utf-8")
        start = text.index("data class ApiRequest")
        end = text.index("data class ApiResponse", start)
        request_block = text[start:end]
        self.assertNotIn("authorization", request_block.lower())
        self.assertNotIn("bearer", request_block.lower())
        self.assertNotIn("token", request_block.lower())

    def test_android_memory_session_is_private_and_has_safe_representation(self):
        text = ANDROID_SESSION.read_text(encoding="utf-8")
        for marker in (
            'Regex("mkt1_[A-Za-z0-9_-]{43}")',
            "private var bearerToken: String?",
            'return "Bearer $token"',
            'override fun toString(): String = "MarketplaceMemorySession(active=$isActive)"',
            "AUTH_REQUIRED",
            "AUTH_SESSION_INVALID",
        ):
            self.assertIn(marker, text)
        self.assertNotIn("data class MarketplaceMemorySession", text)
    def test_android_ephemeral_transport_keeps_authorization_out_of_api_request(self):
        session = ANDROID_SESSION.read_text(encoding="utf-8")
        transport = ANDROID_TRANSPORT.read_text(encoding="utf-8")
        self.assertIn("interface EphemeralAuthorizationTransport", session)
        self.assertIn("authorization: String?", session)
        self.assertIn("EphemeralAuthorizationTransport", transport)
        self.assertIn('connection.setRequestProperty("Authorization", authorization)', transport)
        self.assertIn("reviewedBearerAuthorization(authorization)", transport)
        self.assertIn("reviewedAuthenticatedClientRoute(request.method, request.path)", transport)
        self.assertIn("executeEphemeral(request, null)", transport)

    def test_android_route_scope_is_exact_and_anonymous_reads_are_negative(self):
        text = ANDROID_SESSION.read_text(encoding="utf-8")
        for marker in (
            'path == "/api/auth/session"',
            'path == "/api/auth/logout"',
            'path == "/api/product-listings"',
            'path == "/api/intents"',
            'tail == "responses"',
            'tail == "proposals"',
            "if (!reviewedAuthenticatedClientRoute(method, path)) return null",
        ):
            self.assertIn(marker, text)

    def test_android_authenticated_input_types_exclude_editable_principal(self):
        text = ANDROID_SESSION.read_text(encoding="utf-8")
        listing_start = text.index("data class AuthenticatedProductListingInput")
        proposal_start = text.index("data class AuthenticatedProposalInput", listing_start)
        client_start = text.index("class MarketplaceSessionClient", proposal_start)
        listing = text[listing_start:proposal_start]
        proposal = text[proposal_start:client_start]
        self.assertNotIn("seller_principal", listing)
        self.assertNotIn("buyer_principal", proposal)
        client = text[client_start:]
        self.assertIn("seller_principal = session.requirePrincipal()", client)
        self.assertIn("buyer_principal = session.requirePrincipal()", client)

    def test_android_raw_publication_requires_exact_session_principal_before_dispatch(self):
        text = ANDROID_SESSION.read_text(encoding="utf-8")
        for marker in (
            "private val rawIssuerPrincipal: (String) -> String",
            "requireRawIssuer(rawRecordJson)",
            "issuer != session.requirePrincipal()",
            '"AUTH_PRINCIPAL_MISMATCH"',
            "delegate.createIntent(rawRecordJson)",
            "delegate.respondToIntent(parentId, rawRecordJson)",
        ):
            self.assertIn(marker, text)

    def test_android_logout_is_local_first_and_has_no_retry(self):
        text = ANDROID_SESSION.read_text(encoding="utf-8")
        start = text.index("suspend fun logout")
        end = text.index("private suspend fun <T> authenticated", start)
        block = text[start:end]
        self.assertIn("session.detachAuthorizationForLogout()", block)
        self.assertEqual(block.count("executeEphemeral("), 1)
        self.assertNotIn("retry", block.lower())
        self.assertNotIn("adoptEstablishedSession", block)
    def test_android_offline_and_persistence_surfaces_remain_credential_negative(self):
        session = ANDROID_SESSION.read_text(encoding="utf-8").lower()
        cache = ANDROID_CACHE.read_text(encoding="utf-8").lower()
        combined = session + "\n" + cache
        for forbidden in (
            "sharedpreferences", "datastore", "roomdatabase", "sqlite",
            "savedstate", "workmanager", "alarmmanager", "startservice(",
            "startforegroundservice(", "notificationmanager", "clipboardmanager",
            "keystore", "keychain", "token.dat", "session.dat",
        ):
            self.assertNotIn(forbidden, combined)
        self.assertNotIn("bearer", cache)
        self.assertNotIn("authorization", cache)

    def test_document_records_high_risk_source_only_boundary(self):
        self.assertTrue(DOC.is_file())
        text = DOC.read_text(encoding="utf-8")
        for marker in (
            "MARKETPLACE_APPLICATION_CLIENT_SESSION_V1",
            "memory-only",
            "Authorization: Bearer mkt1_",
            "anonymous reads remain bearer-negative",
            "local-first logout",
            "seller principal",
            "buyer principal",
            "offline cache remains credential-negative",
            "No runtime activation",
            "no Android build",
            "no credential persistence",
            "source-only rollback",
        ):
            self.assertIn(marker, text)


if __name__ == "__main__":
    unittest.main()
