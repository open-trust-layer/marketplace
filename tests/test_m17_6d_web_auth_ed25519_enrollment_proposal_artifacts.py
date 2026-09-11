from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "web" / "auth_ed25519_enrollment_proposal.js"
CONTRACT = ROOT / "tests" / "test_m17_6d_web_auth_ed25519_enrollment_proposal_contract.py"
ARTIFACTS = ROOT / "tests" / "test_m17_6d_web_auth_ed25519_enrollment_proposal_artifacts.py"
DOC = ROOT / "docs" / "m17-6d-web-auth-ed25519-enrollment-proposal.md"
INDEX = ROOT / "web" / "index.html"
APP = ROOT / "web" / "app.js"
CLIENT_SESSION = ROOT / "web" / "client_session.js"
AUTH_ESTABLISHMENT = ROOT / "web" / "auth_establishment.js"
PROOF_PROVIDER = ROOT / "web" / "auth_ed25519_proof_provider.js"
KEY_CREATION = ROOT / "web" / "auth_ed25519_key_creation.js"
ANDROID_MAIN = ROOT / "android" / "app" / "src" / "main" / "java" / "org" / "opentrustlayer" / "marketplace" / "MainActivity.kt"


class M176DWebAuthEd25519EnrollmentProposalArtifactTests(unittest.TestCase):
    def test_exact_four_m17_6d_artifacts_exist(self) -> None:
        for path in (SOURCE, CONTRACT, ARTIFACTS, DOC):
            self.assertTrue(path.is_file(), str(path))

    def test_enrollment_proposal_boundary_remains_unselected(self) -> None:
        for path in (
            INDEX,
            APP,
            CLIENT_SESSION,
            AUTH_ESTABLISHMENT,
            PROOF_PROVIDER,
            KEY_CREATION,
            ANDROID_MAIN,
        ):
            text = path.read_text(encoding="utf-8")
            self.assertNotIn("auth_ed25519_enrollment_proposal.js", text, str(path))
            self.assertNotIn("createMarketplaceWebAuthEd25519EnrollmentProposal", text, str(path))
            self.assertNotIn("MARKETPLACE_WEB_AUTH_ED25519_ENROLLMENT_PROPOSAL_V1", text, str(path))

    def test_source_has_no_private_key_or_webcrypto_capability(self) -> None:
        text = SOURCE.read_text(encoding="utf-8")
        for marker in (
            "privateKey", "generateKey", "importKey", "exportKey", "wrapKey", "unwrapKey",
            "deriveKey", "deriveBits", ".sign(", ".verify(", "window.crypto", "globalThis.crypto",
            "crypto.subtle", "navigator.credentials", "WebAuthn", "seedPhrase", "mnemonic",
            "passphrase", "pkcs8",
        ):
            self.assertNotIn(marker, text)

    def test_source_has_no_network_persistence_or_background_capability(self) -> None:
        text = SOURCE.read_text(encoding="utf-8")
        for marker in (
            "fetch(", "XMLHttpRequest", "WebSocket", "EventSource", "localStorage",
            "sessionStorage", "indexedDB", "document.cookie", "caches.open", "serviceWorker",
            "setTimeout", "setInterval", "Worker(", "BroadcastChannel", "postMessage",
            "FileReader", "showOpenFilePicker", "showSaveFilePicker",
        ):
            self.assertNotIn(marker, text)

    def test_source_has_no_evidence_trust_or_registration_authority(self) -> None:
        text = SOURCE.read_text(encoding="utf-8")
        for marker in (
            '"authority"', '"issuedAt"', '"expiresAt"', '"validFrom"', '"validUntil"',
            '"attestation"', '"accepted"', "EvidenceEnvelope", "TrustVerifier", "TrustAnchor",
            "register", "registration", "enroll(", "enrollmentEndpoint", "controllerPrincipal",
        ):
            self.assertNotIn(marker, text)

    def test_source_has_no_imports_or_external_dependencies(self) -> None:
        text = SOURCE.read_text(encoding="utf-8")
        self.assertNotIn("import ", text)
        self.assertNotIn("require(", text)
        self.assertNotIn("from ", text)

    def test_errors_are_stable_nonreflective_and_inputs_are_not_logged(self) -> None:
        text = SOURCE.read_text(encoding="utf-8")
        self.assertIn('new Error("Marketplace Web authentication enrollment proposal failed")', text)
        self.assertIn('error.code = "AUTH_ENROLLMENT_PROPOSAL_UNAVAILABLE"', text)
        for marker in (
            "console.log", "console.error", "console.warn", "error.message",
            "JSON.stringify", "String(requestValue)",
        ):
            self.assertNotIn(marker, text)

    def test_document_records_non_authority_and_later_gates(self) -> None:
        text = DOC.read_text(encoding="utf-8")
        for marker in (
            "MARKETPLACE_WEB_AUTH_ED25519_ENROLLMENT_PROPOSAL_V1",
            "HIGH security/privacy",
            "mkpk1_",
            "mkp1_",
            "non-authoritative",
            "no identity/controller inference",
            "no verification-method allocation",
            "no authority or attestation creation",
            "no private-key capability",
            "no network",
            "unselected",
            "source-only rollback",
        ):
            self.assertIn(marker, text)


if __name__ == "__main__":
    unittest.main()
