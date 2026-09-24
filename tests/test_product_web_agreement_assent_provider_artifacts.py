from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "web" / "agreement_ed25519_assent_provider.js"
CONTRACT = ROOT / "tests" / "test_product_web_agreement_assent_provider_contract.py"
DOC = ROOT / "docs" / "product-agreement-assent-browser-signer.md"

UNSELECTED_SURFACES = (
    ROOT / "web" / "index.html",
    ROOT / "web" / "app.js",
    ROOT / "web" / "client_session.js",
    ROOT / "web" / "auth_establishment.js",
    ROOT / "web" / "auth_bootstrap.js",
    ROOT / "android" / "app" / "src" / "main" / "java"
    / "org" / "opentrustlayer" / "marketplace" / "MainActivity.kt",
)

DELIVERY_SURFACES = (
    ROOT / "src" / "marketplace" / "application" / "site_host.py",
    ROOT / "tools" / "marketplace_localhost.py",
)


class ProductWebAgreementAssentProviderArtifactTests(unittest.TestCase):
    def test_exact_source_contract_and_doc_exist(self) -> None:
        for path in (SOURCE, CONTRACT, DOC):
            self.assertTrue(path.is_file(), str(path))

    def test_provider_is_delivered_but_unselected(self) -> None:
        for path in DELIVERY_SURFACES:
            text = path.read_text(encoding="utf-8")
            self.assertIn("agreement_ed25519_assent_provider.js", text, str(path))
            self.assertNotIn(
                "createMarketplaceWebAgreementEd25519AssentProvider",
                text,
                str(path),
            )
        for path in UNSELECTED_SURFACES:
            text = path.read_text(encoding="utf-8")
            self.assertNotIn("agreement_ed25519_assent_provider.js", text, str(path))
            self.assertNotIn(
                "createMarketplaceWebAgreementEd25519AssentProvider",
                text,
                str(path),
            )

    def test_source_has_no_key_lifecycle_or_persistence_capability(self) -> None:
        text = SOURCE.read_text(encoding="utf-8")
        for marker in (
            "generateKey", "importKey", "exportKey", "wrapKey", "unwrapKey",
            "localStorage", "sessionStorage", "indexedDB", "document.cookie",
            "caches.open", "serviceWorker", "navigator.credentials",
            "mnemonic", "seedPhrase", "passphrase", "wallet",
        ):
            self.assertNotIn(marker, text)

    def test_source_has_no_network_ambient_crypto_or_background_activity(self) -> None:
        text = SOURCE.read_text(encoding="utf-8")
        for marker in (
            "window.crypto", "globalThis.crypto", "crypto.subtle",
            "setTimeout", "setInterval", "Worker(", "BroadcastChannel",
            "postMessage", "fetch(", "XMLHttpRequest", "WebSocket",
            "EventSource",
        ):
            self.assertNotIn(marker, text)

    def test_source_does_not_build_or_interpret_olp_proof_material(self) -> None:
        text = SOURCE.read_text(encoding="utf-8")
        for marker in (
            "RecordCommitment", "OLPProof", "ProofInput", "CBOR", "cbor",
            "sha256", "SHA-256", ".digest(", "proofPurpose",
            "cryptosuite", "proofValue",
        ):
            self.assertNotIn(marker, text)

    def test_source_has_one_purpose_specific_sign_call(self) -> None:
        text = SOURCE.read_text(encoding="utf-8")
        self.assertEqual(text.count("reviewedSigner.sign("), 1)
        self.assertIn(
            "return Object.freeze({ createAgreementAssentSignature });",
            text,
        )
        self.assertNotIn("return Object.freeze({ sign", text)

    def test_errors_are_stable_and_nonreflective(self) -> None:
        text = SOURCE.read_text(encoding="utf-8")
        self.assertIn(
            'new Error("Marketplace Web Agreement assent signing operation failed")',
            text,
        )
        self.assertIn(
            'error.code = "AGREEMENT_ASSENT_SIGNATURE_UNAVAILABLE"',
            text,
        )
        for marker in (
            "console.log", "console.error", "error.message",
            "JSON.stringify(error",
        ):
            self.assertNotIn(marker, text)

    def test_document_records_source_only_authority_boundary(self) -> None:
        text = DOC.read_text(encoding="utf-8")
        for marker in (
            "MARKETPLACE_WEB_AGREEMENT_ED25519_ASSENT_PROVIDER_V1",
            "source-only",
            "unselected",
            "non-extractable Ed25519",
            "exact signing bytes",
            "no key generation",
            "no key import",
            "no key export",
            "no network",
            "no Agreement publication",
            "source-only rollback",
        ):
            self.assertIn(marker, text)


if __name__ == "__main__":
    unittest.main()
