from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src" / "marketplace" / "application" / "auth_enrollment_authority.py"
TESTS = ROOT / "tests" / "test_m17_6e_auth_enrollment_authority.py"
ARTIFACTS = ROOT / "tests" / "test_m17_6e_auth_enrollment_authority_artifacts.py"
DOC = ROOT / "docs" / "m17-6e-auth-enrollment-authority.md"
PACKAGE_GATE = ROOT / "tools" / "package_artifact_gate.py"
PACKAGE_TESTS = ROOT / "tests" / "test_package_artifact_gate.py"

NONSELECTING = (
    ROOT / "src" / "marketplace" / "application" / "auth_static_composition.py",
    ROOT / "src" / "marketplace" / "application" / "auth_startup_composition.py",
    ROOT / "src" / "marketplace" / "application" / "auth_launch.py",
    ROOT / "src" / "marketplace" / "application" / "auth_runtime_server.py",
    ROOT / "web" / "auth_bootstrap.js",
    ROOT / "android" / "app" / "src" / "main" / "java" / "org" / "opentrustlayer" / "marketplace" / "MainActivity.kt",
)


class M176EAuthenticationEnrollmentAuthorityArtifactTests(unittest.TestCase):
    def test_exact_m17_6e_artifacts_exist(self) -> None:
        for path in (SOURCE, TESTS, ARTIFACTS, DOC, PACKAGE_GATE, PACKAGE_TESTS):
            self.assertTrue(path.is_file(), str(path))

    def test_source_reuses_existing_evidence_and_trust_boundaries(self) -> None:
        text = SOURCE.read_text(encoding="utf-8")
        for marker in (
            "MarketplaceAuthenticationVerificationMethodEvidenceClaims",
            "AuthenticationVerificationMethodEvidenceClaim",
            "MarketplaceAuthenticationVerificationMethodEvidenceEnvelope",
            "encode_marketplace_authentication_verification_method_evidence_claims",
            "parse_marketplace_auth_verification_public_key",
            "build_marketplace_authentication_evidence_trust_transcript",
        ):
            self.assertIn(marker, text)

    def test_source_has_no_concrete_private_key_or_generic_signing_capability(self) -> None:
        text = SOURCE.read_text(encoding="utf-8")
        for marker in (
            "Ed25519PrivateKey", "generate_private_key", "from_private_bytes",
            "private_key", "seed", "mnemonic", "passphrase", "keyring", "HSM",
            "vault", ".sign(", "def sign(", "sign(self", "sign(data",
        ):
            self.assertNotIn(marker, text)

    def test_source_has_no_network_persistence_provider_or_background_capability(self) -> None:
        text = SOURCE.read_text(encoding="utf-8")
        for marker in (
            "requests", "httpx", "urllib", "socket", "fetch(", "WebSocket",
            "open(", "Path(", "os.environ", "getenv", "psycopg", "sqlite",
            "subprocess", "threading", "multiprocessing", "asyncio",
            "setTimeout", "setInterval", "retry", "fallback",
        ):
            self.assertNotIn(marker, text)

    def test_source_exposes_only_purpose_specific_attestor_operation(self) -> None:
        text = SOURCE.read_text(encoding="utf-8")
        self.assertIn(
            "def attest_authentication_enrollment(self, transcript: bytes) -> bytes",
            text,
        )
        self.assertEqual(text.count("operation(transcript)"), 1)
        self.assertNotIn("signer", text.lower())

    def test_authority_remains_unselected_by_runtime_web_and_android(self) -> None:
        for path in NONSELECTING:
            text = path.read_text(encoding="utf-8")
            self.assertNotIn("auth_enrollment_authority", text, str(path))
            self.assertNotIn("issue_marketplace_authentication_enrollment_evidence", text, str(path))
            self.assertNotIn("MARKETPLACE_APPLICATION_AUTH_ENROLLMENT_AUTHORITY_V1", text, str(path))

    def test_package_controls_require_new_module(self) -> None:
        gate = PACKAGE_GATE.read_text(encoding="utf-8")
        tests = PACKAGE_TESTS.read_text(encoding="utf-8")
        member = "marketplace/application/auth_enrollment_authority.py"
        self.assertEqual(gate.count(f'"{member}"'), 1)
        self.assertGreaterEqual(tests.count(member), 2)

    def test_document_records_non_authority_and_rollback_boundaries(self) -> None:
        text = DOC.read_text(encoding="utf-8")
        for marker in (
            "MARKETPLACE_APPLICATION_AUTH_ENROLLMENT_AUTHORITY_V1",
            "HIGH security/privacy",
            "purpose-specific attestor",
            "no production private-key custody",
            "no generic signing oracle",
            "no network",
            "unselected",
            "source-only rollback",
        ):
            self.assertIn(marker, text)


if __name__ == "__main__":
    unittest.main()
