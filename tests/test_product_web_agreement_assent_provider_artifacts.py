from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "web" / "agreement_ed25519_assent_provider.js"
INDEX = ROOT / "web" / "index.html"
APP = ROOT / "web" / "app.js"
AUTH_BOOTSTRAP = ROOT / "web" / "auth_bootstrap.js"
LOCALHOST = ROOT / "tools" / "marketplace_localhost.py"
SITE_HOST = ROOT / "src" / "marketplace" / "application" / "site_host.py"
ANDROID_MAIN = (
    ROOT / "android" / "app" / "src" / "main" / "java"
    / "org" / "opentrustlayer" / "marketplace" / "MainActivity.kt"
)


class ProductWebAgreementAssentProviderArtifactTests(unittest.TestCase):
    def test_provider_exists_and_remains_unselected_and_undelivered(self) -> None:
        self.assertTrue(SOURCE.is_file())
        marker = "agreement_ed25519_assent_provider.js"
        for path in (INDEX, APP, AUTH_BOOTSTRAP, LOCALHOST, SITE_HOST, ANDROID_MAIN):
            self.assertNotIn(marker, path.read_text(encoding="utf-8"), str(path))

    def test_source_has_no_key_lifecycle_or_persistence_capability(self) -> None:
        text = SOURCE.read_text(encoding="utf-8")
        for marker in (
            "generateKey", "importKey", "exportKey", "wrapKey", "unwrapKey",
            "localStorage", "sessionStorage", "indexedDB", "document.cookie",
            "caches.open", "serviceWorker", "navigator.credentials",
            "mnemonic", "seedPhrase", "passphrase",
        ):
            self.assertNotIn(marker, text)

    def test_source_has_no_network_ambient_crypto_or_background_activity(self) -> None:
        text = SOURCE.read_text(encoding="utf-8")
        for marker in (
            "window.crypto", "globalThis.crypto", "crypto.subtle",
            "setTimeout", "setInterval", "Worker(", "BroadcastChannel",
            "postMessage", "fetch(", "XMLHttpRequest", "WebSocket", "EventSource",
        ):
            self.assertNotIn(marker, text)

    def test_source_does_not_construct_or_interpret_olp(self) -> None:
        text = SOURCE.read_text(encoding="utf-8")
        for marker in (
            "OLPProof", "recordCommitment", "RecordCommitment", "proofPurpose",
            "cryptosuite", "CBOR", "cbor", "sha256", "digest(",
        ):
            self.assertNotIn(marker, text)

    def test_source_has_one_sign_call_and_no_generic_sign_export(self) -> None:
        text = SOURCE.read_text(encoding="utf-8")
        self.assertEqual(text.count("reviewedSigner.sign("), 1)
        self.assertIn(
            "return Object.freeze({ createAgreementAssentSignature });",
            text,
        )
        exported = text[text.rindex("export {"):]
        self.assertNotIn("reviewedSubtle", exported)
        self.assertNotIn("reviewedPrivateKey", exported)

    def test_errors_are_stable_and_nonreflective(self) -> None:
        text = SOURCE.read_text(encoding="utf-8")
        self.assertIn(
            'new Error("Marketplace Web Agreement assent signing failed")',
            text,
        )
        self.assertIn(
            'error.code = "AGREEMENT_ASSENT_SIGNING_UNAVAILABLE"',
            text,
        )
        for marker in (
            "console.log", "console.error", "error.message",
            "JSON.stringify(error", "signature.toString",
        ):
            self.assertNotIn(marker, text)


if __name__ == "__main__":
    unittest.main()
