from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src" / "marketplace" / "application" / "auth_enrollment_nonce.py"
TESTS = ROOT / "tests" / "test_m17_6h_auth_enrollment_nonce.py"
ARTIFACTS = ROOT / "tests" / "test_m17_6h_auth_enrollment_nonce_artifacts.py"
DOC = ROOT / "docs" / "m17-6h-auth-enrollment-nonce.md"
PACKAGE_GATE = ROOT / "tools" / "package_artifact_gate.py"
PACKAGE_TESTS = ROOT / "tests" / "test_package_artifact_gate.py"

NONSELECTING = (
    ROOT / "src" / "marketplace" / "application" / "auth_enrollment_coordination.py",
    ROOT / "src" / "marketplace" / "application" / "auth_http_composition.py",
    ROOT / "src" / "marketplace" / "application" / "auth_session_asgi.py",
    ROOT / "src" / "marketplace" / "application" / "auth_startup_composition.py",
    ROOT / "web" / "auth_bootstrap.js",
    ROOT / "android" / "app" / "src" / "main" / "java" / "org" / "opentrustlayer" / "marketplace" / "MainActivity.kt",
)


class M176HAuthenticationEnrollmentNonceArtifactTests(unittest.TestCase):
    def test_exact_m17_6h_artifacts_exist(self) -> None:
        for path in (SOURCE, TESTS, ARTIFACTS, DOC, PACKAGE_GATE, PACKAGE_TESTS):
            self.assertTrue(path.is_file(), str(path))

    def test_source_uses_digest_only_state_and_lock_protected_atomic_pop(self) -> None:
        text = SOURCE.read_text(encoding="utf-8")
        self.assertIn("import hashlib", text)
        self.assertIn("from threading import Lock", text)
        self.assertIn("hashlib.sha256(nonce).digest()", text)
        self.assertIn("with self._lock:", text)
        self.assertIn("state = self._outstanding.pop(digest, None)", text)
        start = text.index("class _NonceState:")
        end = text.index("def _review_issue_binding", start)
        state_block = text[start:end]
        self.assertIn("digest: bytes", state_block)
        self.assertNotIn("nonce: bytes", state_block)

    def test_source_reuses_existing_m17_6g_and_m17_5l_bounds(self) -> None:
        text = SOURCE.read_text(encoding="utf-8")
        for marker in (
            "AUTH_ENROLLMENT_NONCE_BYTES",
            "AUTH_EVIDENCE_MAX_LEASE_SECONDS",
            "AuthenticationVerificationMethodEvidenceClaim",
            "MarketplaceAuthenticationVerificationMethodEvidenceClaims",
            "parse_marketplace_auth_verification_public_key",
        ):
            self.assertIn(marker, text)

    def test_source_has_no_external_io_persistence_runtime_or_secret_generation(self) -> None:
        text = SOURCE.read_text(encoding="utf-8")
        for marker in (
            "requests", "httpx", "urllib", "socket", "open(", "Path(",
            "os.environ", "getenv", "psycopg", "sqlite", "subprocess",
            "asyncio", "multiprocessing", "Thread(", "ThreadPool",
            "secrets.", "token_bytes", "os.urandom", "random.",
            "ApplicationHttpRequest", "ApplicationHttpResponse", "/api/", "ASGI",
        ):
            self.assertNotIn(marker, text)

    def test_nonce_authority_remains_unselected_by_runtime_http_web_and_android(self) -> None:
        for path in NONSELECTING:
            text = path.read_text(encoding="utf-8")
            self.assertNotIn("auth_enrollment_nonce", text, str(path))
            self.assertNotIn(
                "MarketplaceAuthenticationEnrollmentNonceAuthority",
                text,
                str(path),
            )
            self.assertNotIn(
                "MARKETPLACE_APPLICATION_AUTH_ENROLLMENT_NONCE_V1",
                text,
                str(path),
            )

    def test_package_controls_require_new_module(self) -> None:
        gate = PACKAGE_GATE.read_text(encoding="utf-8")
        tests = PACKAGE_TESTS.read_text(encoding="utf-8")
        member = "marketplace/application/auth_enrollment_nonce.py"
        self.assertEqual(gate.count(f'"{member}"'), 1)
        self.assertGreaterEqual(tests.count(member), 2)

    def test_document_records_digest_only_atomic_and_nonselection_boundaries(self) -> None:
        text = DOC.read_text(encoding="utf-8")
        for marker in (
            "MARKETPLACE_APPLICATION_AUTH_ENROLLMENT_NONCE_V1",
            "HIGH security/privacy",
            "digest-only",
            "atomic",
            "120 seconds",
            "process-memory",
            "unselected",
            "source-only rollback",
        ):
            self.assertIn(marker, text)


if __name__ == "__main__":
    unittest.main()
