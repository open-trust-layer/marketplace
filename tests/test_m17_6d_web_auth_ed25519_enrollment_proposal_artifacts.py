from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "web" / "auth_ed25519_enrollment_proposal.js"
CONTRACT = ROOT / "tests" / "test_m17_6d_web_auth_ed25519_enrollment_proposal_contract.py"
ARTIFACTS = ROOT / "tests" / "test_m17_6d_web_auth_ed25519_enrollment_proposal_artifacts.py"
DOC = ROOT / "docs" / "m17-6d-web-auth-ed25519-enrollment-proposal.md"

ACTIVE_WEB = (
    ROOT / "web" / "index.html",
    ROOT / "web" / "app.js",
    ROOT / "web" / "client_session.js",
    ROOT / "web" / "auth_establishment.js",
    ROOT / "web" / "auth_ed25519_proof_provider.js",
    ROOT / "web" / "auth_bootstrap.js",
    ROOT / "web" / "agreement_assent_client.js",
    ROOT / "web" / "agreement_ed25519_assent_provider.js",
    ROOT / "web" / "proposal_acceptance_client.js",
)
ANDROID_MAIN = ROOT / "android" / "app" / "src" / "main" / "java" / "org" / "opentrustlayer" / "marketplace" / "MainActivity.kt"


class M176DWebAuthEd25519EnrollmentProposalArtifactTests(unittest.TestCase):
    def test_exact_four_m17_6d_artifacts_exist(self) -> None:
        for path in (SOURCE, CONTRACT, ARTIFACTS, DOC):
            self.assertTrue(path.is_file(), str(path))

    def test_handoff_remains_unselected_by_web_and_android_entry_points(self) -> None:
        for path in ACTIVE_WEB + (ANDROID_MAIN,):
            text = path.read_text(encoding="utf-8")
            self.assertNotIn("auth_ed25519_enrollment_proposal.js", text, str(path))
            self.assertNotIn("createMarketplaceWebAuthEd25519EnrollmentProposal", text, str(path))
            self.assertNotIn("MARKETPLACE_WEB_AUTH_ED25519_ENROLLMENT_PROPOSAL_V1", text, str(path))

    def test_source_has_no_private_key_or_webcrypto_capability(self) -> None:
        text = SOURCE.read_text(encoding="utf-8")
        for marker in (
            "privateKey", "generateKey", "importKey", "exportKey", "wrapKey", "unwrapKey",
            ".sign(", "subtle", "window.crypto", "globalThis.crypto", "crypto.subtle",
            "pkcs8", "seedPhrase", "mnemonic", "passphrase",
        ):
            self.assertNotIn(marker, text)

    def test_source_has_no_network_persistence_runtime_or_background_capability(self) -> None:
        text = SOURCE.read_text(encoding="utf-8")
        for marker in (
            "fetch(", "XMLHttpRequest", "WebSocket", "EventSource",
            "localStorage", "sessionStorage", "indexedDB", "document.cookie",
            "caches.open", "serviceWorker", "navigator.credentials",
            "setTimeout", "setInterval", "Worker(", "BroadcastChannel", "postMessage",
        ):
            self.assertNotIn(marker, text)

    def test_source_has_no_evidence_authority_or_acceptance_creation(self) -> None:
        text = SOURCE.read_text(encoding="utf-8")
        for marker in (
            "authority:", "issuedAt:", "expiresAt:", "validFrom:", "validUntil:",
            "attestation:", "accepted:", "trustStatus:",
            "MarketplaceAuthenticationVerificationMethodEvidenceBundle",
        ):
            self.assertNotIn(marker, text)

    def test_errors_are_stable_nonreflective(self) -> None:
        text = SOURCE.read_text(encoding="utf-8")
        self.assertIn(
            'new Error("Marketplace Web authentication enrollment proposal failed")',
            text,
        )
        self.assertIn('error.code = "AUTH_ENROLLMENT_PROPOSAL_UNAVAILABLE"', text)
        for marker in (
            "console.log", "console.error", "console.warn", "error.message",
            "JSON.stringify", "String(request", "String(value",
        ):
            self.assertNotIn(marker, text)

    def test_document_records_non_authority_and_rollback_boundaries(self) -> None:
        text = DOC.read_text(encoding="utf-8")
        for marker in (
            "MARKETPLACE_WEB_AUTH_ED25519_ENROLLMENT_PROPOSAL_V1",
            "HIGH security/privacy",
            "mkpk1_",
            "mkp1_",
            "non-authoritative",
            "no verification-method assignment",
            "no evidence bundle",
            "no trust mutation",
            "unselected",
            "source-only rollback",
        ):
            self.assertIn(marker, text)


if __name__ == "__main__":
    unittest.main()
