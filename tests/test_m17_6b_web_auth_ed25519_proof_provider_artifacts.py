from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "web" / "auth_ed25519_proof_provider.js"
CONTRACT = ROOT / "tests" / "test_m17_6b_web_auth_ed25519_proof_provider_contract.py"
DOC = ROOT / "docs" / "m17-6b-web-auth-ed25519-proof-provider.md"
INDEX = ROOT / "web" / "index.html"
APP = ROOT / "web" / "app.js"
CLIENT_SESSION = ROOT / "web" / "client_session.js"
AUTH_ESTABLISHMENT = ROOT / "web" / "auth_establishment.js"
ANDROID_MAIN = ROOT / "android" / "app" / "src" / "main" / "java" / "org" / "opentrustlayer" / "marketplace" / "MainActivity.kt"


class M176BWebAuthEd25519ProofProviderArtifactTests(unittest.TestCase):
    def test_exact_m17_6b_artifacts_exist(self) -> None:
        for path in (SOURCE, CONTRACT, DOC):
            self.assertTrue(path.is_file(), str(path))

    def test_new_provider_remains_unselected(self) -> None:
        for path in (INDEX, APP, CLIENT_SESSION, AUTH_ESTABLISHMENT, ANDROID_MAIN):
            text = path.read_text(encoding="utf-8")
            self.assertNotIn("auth_ed25519_proof_provider.js", text, str(path))
            self.assertNotIn("createMarketplaceWebAuthEd25519ProofProvider", text, str(path))

    def test_source_has_no_key_lifecycle_or_persistence_capability(self) -> None:
        text = SOURCE.read_text(encoding="utf-8")
        forbidden = (
            "generateKey", "importKey", "exportKey", "wrapKey", "unwrapKey",
            "localStorage", "sessionStorage", "indexedDB", "document.cookie",
            "caches.open", "serviceWorker", "navigator.credentials", "WebAuthn",
            "mnemonic", "seedPhrase", "passphrase", "wallet", "extension",
        )
        for marker in forbidden:
            self.assertNotIn(marker, text)

    def test_source_has_no_ambient_crypto_selection_or_background_activity(self) -> None:
        text = SOURCE.read_text(encoding="utf-8")
        for marker in (
            "window.crypto", "globalThis.crypto", "crypto.subtle", "setTimeout",
            "setInterval", "Worker(", "BroadcastChannel", "postMessage",
            "fetch(", "XMLHttpRequest", "WebSocket", "EventSource",
        ):
            self.assertNotIn(marker, text)

    def test_source_has_one_purpose_specific_sign_call_and_no_generic_export(self) -> None:
        text = SOURCE.read_text(encoding="utf-8")
        self.assertEqual(text.count("reviewedSigner.sign("), 1)
        self.assertIn("return Object.freeze({ createAuthenticationProof });", text)
        exported = text[text.rindex("export {"):]
        self.assertIn("PROFILE", exported)
        self.assertIn("createMarketplaceWebAuthEd25519ProofProvider", exported)
        self.assertNotIn("buildTranscript", exported)

    def test_errors_are_stable_and_nonreflective(self) -> None:
        text = SOURCE.read_text(encoding="utf-8")
        self.assertIn('new Error("Marketplace Web authentication proof operation failed")', text)
        self.assertIn('error.code = "AUTH_PROOF_UNAVAILABLE"', text)
        for marker in ("console.log", "console.error", "error.message", "JSON.stringify(error"):
            self.assertNotIn(marker, text)

    def test_document_records_authority_boundary_and_later_gates(self) -> None:
        text = DOC.read_text(encoding="utf-8")
        for marker in (
            "MARKETPLACE_WEB_AUTH_ED25519_PROOF_PROVIDER_V1",
            "HIGH security/privacy",
            "already-supplied non-extractable Ed25519 private CryptoKey",
            "purpose-specific",
            "unselected",
            "no key generation",
            "no key import",
            "no key export",
            "no credential persistence",
            "no active Web authentication selection",
            "source-only rollback",
            "real-browser secure-context acceptance",
        ):
            self.assertIn(marker, text)


if __name__ == "__main__":
    unittest.main()
