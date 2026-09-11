from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "web" / "auth_ed25519_key_creation.js"
CONTRACT = ROOT / "tests" / "test_m17_6c_web_auth_ed25519_key_creation_contract.py"
ARTIFACTS = ROOT / "tests" / "test_m17_6c_web_auth_ed25519_key_creation_artifacts.py"
DOC = ROOT / "docs" / "m17-6c-web-auth-ed25519-key-creation.md"
INDEX = ROOT / "web" / "index.html"
APP = ROOT / "web" / "app.js"
CLIENT_SESSION = ROOT / "web" / "client_session.js"
AUTH_ESTABLISHMENT = ROOT / "web" / "auth_establishment.js"
PROOF_PROVIDER = ROOT / "web" / "auth_ed25519_proof_provider.js"
ANDROID_MAIN = ROOT / "android" / "app" / "src" / "main" / "java" / "org" / "opentrustlayer" / "marketplace" / "MainActivity.kt"


class M176CWebAuthEd25519KeyCreationArtifactTests(unittest.TestCase):
    def test_exact_four_m17_6c_artifacts_exist(self) -> None:
        for path in (SOURCE, CONTRACT, ARTIFACTS, DOC):
            self.assertTrue(path.is_file(), str(path))

    def test_key_creation_boundary_remains_unselected(self) -> None:
        for path in (INDEX, APP, CLIENT_SESSION, AUTH_ESTABLISHMENT, PROOF_PROVIDER, ANDROID_MAIN):
            text = path.read_text(encoding="utf-8")
            self.assertNotIn("auth_ed25519_key_creation.js", text, str(path))
            self.assertNotIn("createMarketplaceWebAuthEd25519KeyCreation", text, str(path))
            self.assertNotIn("MARKETPLACE_WEB_AUTH_ED25519_KEY_CREATION_V1", text, str(path))

    def test_source_has_one_creation_call_and_public_only_export_call(self) -> None:
        text = SOURCE.read_text(encoding="utf-8")
        self.assertEqual(text.count("reviewedCrypto.generateKey("), 1)
        self.assertEqual(text.count("reviewedCrypto.exportKey("), 1)
        self.assertIn('reviewedCrypto.exportKey("raw", publicKey)', text)
        self.assertNotIn('exportKey("raw", privateKey)', text)
        self.assertNotIn('exportKey("jwk", privateKey)', text)
        self.assertNotIn('exportKey("pkcs8", privateKey)', text)

    def test_source_has_no_private_import_wrapping_or_persistence_capability(self) -> None:
        text = SOURCE.read_text(encoding="utf-8")
        forbidden = (
            "importKey", "wrapKey", "unwrapKey", "deriveKey", "deriveBits",
            "localStorage", "sessionStorage", "indexedDB", "document.cookie",
            "caches.open", "serviceWorker", "navigator.credentials", "WebAuthn",
            "mnemonic", "seedPhrase", "passphrase", "privateKeyData", "pkcs8",
        )
        for marker in forbidden:
            self.assertNotIn(marker, text)

    def test_source_has_no_signing_network_or_background_capability(self) -> None:
        text = SOURCE.read_text(encoding="utf-8")
        for marker in (
            ".sign(", "window.crypto", "globalThis.crypto", "crypto.subtle",
            "setTimeout", "setInterval", "Worker(", "BroadcastChannel", "postMessage",
            "fetch(", "XMLHttpRequest", "WebSocket", "EventSource",
        ):
            self.assertNotIn(marker, text)

    def test_errors_are_stable_nonreflective_and_key_material_is_not_logged(self) -> None:
        text = SOURCE.read_text(encoding="utf-8")
        self.assertIn('new Error("Marketplace Web authentication key creation failed")', text)
        self.assertIn('error.code = "AUTH_KEY_CREATION_UNAVAILABLE"', text)
        for marker in (
            "console.log", "console.error", "console.warn", "error.message",
            "JSON.stringify", "String(privateKey)", "String(publicKey)",
        ):
            self.assertNotIn(marker, text)

    def test_document_records_authority_boundary_and_later_gates(self) -> None:
        text = DOC.read_text(encoding="utf-8")
        for marker in (
            "MARKETPLACE_WEB_AUTH_ED25519_KEY_CREATION_V1",
            "HIGH security/privacy",
            "non-extractable",
            "memory-only",
            "mkpk1_",
            "public-key export only",
            "no private-key export",
            "no private-key import",
            "no persistence",
            "no server enrollment",
            "no verification-method assignment",
            "unselected",
            "source-only rollback",
        ):
            self.assertIn(marker, text)


if __name__ == "__main__":
    unittest.main()
