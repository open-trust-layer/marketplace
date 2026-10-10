from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src" / "marketplace" / "application" / "auth_enrollment_coordination.py"
TESTS = ROOT / "tests" / "test_m17_6g_auth_enrollment_coordination.py"
ARTIFACTS = ROOT / "tests" / "test_m17_6g_auth_enrollment_coordination_artifacts.py"
DOC = ROOT / "docs" / "m17-6g-auth-enrollment-coordination.md"
PACKAGE_GATE = ROOT / "tools" / "package_artifact_gate.py"
PACKAGE_TESTS = ROOT / "tests" / "test_package_artifact_gate.py"

NONSELECTING = (
    ROOT / "src" / "marketplace" / "application" / "auth_http_composition.py",
    ROOT / "src" / "marketplace" / "application" / "auth_session_asgi.py",
    ROOT / "src" / "marketplace" / "application" / "auth_startup_composition.py",
    ROOT / "web" / "auth_bootstrap.js",
    ROOT / "android" / "app" / "src" / "main" / "java" / "org" / "opentrustlayer" / "marketplace" / "MainActivity.kt",
)


class M176GAuthenticationEnrollmentCoordinationArtifactTests(unittest.TestCase):
    def test_exact_m17_6g_artifacts_exist(self) -> None:
        for path in (SOURCE, TESTS, ARTIFACTS, DOC, PACKAGE_GATE, PACKAGE_TESTS):
            self.assertTrue(path.is_file(), str(path))

    def test_source_reuses_existing_auth_policy_and_evidence_boundaries(self) -> None:
        text = SOURCE.read_text(encoding="utf-8")
        for marker in (
            "MarketplaceApplicationAuthService",
            "authorize_principal",
            "MarketplaceAuthenticationEnrollmentProposal",
            "issue_marketplace_authentication_enrollment_evidence_after_policy",
            "MarketplaceAuthenticationVerificationMethodEvidenceClaims",
            "AUTH_EVIDENCE_MAX_LEASE_SECONDS",
        ):
            self.assertIn(marker, text)

    def test_replay_consumption_is_purpose_specific_and_precedes_policy(self) -> None:
        text = SOURCE.read_text(encoding="utf-8")
        self.assertIn("def consume_authentication_enrollment_nonce(", text)
        self.assertEqual(text.count("consumed = consume("), 1)
        self.assertLess(
            text.index("consumed = consume("),
            text.index("issue_marketplace_authentication_enrollment_evidence_after_policy("),
        )

    def test_source_has_no_transport_nonce_store_or_external_io(self) -> None:
        text = SOURCE.read_text(encoding="utf-8")
        for marker in (
            "ApplicationHttpRequest", "ApplicationHttpResponse", "/api/", "ASGI",
            "requests", "httpx", "urllib", "socket", "open(", "Path(",
            "os.environ", "getenv", "psycopg", "sqlite", "subprocess",
            "threading", "multiprocessing", "asyncio", "setTimeout", "setInterval",
            "nonce_store", "nonce_source", "secrets.", "token_bytes",
        ):
            self.assertNotIn(marker, text)

    def test_coordination_remains_unselected_by_http_asgi_web_and_android(self) -> None:
        for path in NONSELECTING:
            text = path.read_text(encoding="utf-8")
            self.assertNotIn("auth_enrollment_coordination", text, str(path))
            self.assertNotIn(
                "coordinate_marketplace_authentication_enrollment",
                text,
                str(path),
            )
            self.assertNotIn(
                "MARKETPLACE_APPLICATION_AUTH_ENROLLMENT_COORDINATION_V1",
                text,
                str(path),
            )

    def test_package_controls_require_new_module(self) -> None:
        gate = PACKAGE_GATE.read_text(encoding="utf-8")
        tests = PACKAGE_TESTS.read_text(encoding="utf-8")
        member = "marketplace/application/auth_enrollment_coordination.py"
        self.assertEqual(gate.count(f'"{member}"'), 1)
        self.assertGreaterEqual(tests.count(member), 2)

    def test_document_records_burn_before_policy_and_rollback_boundaries(self) -> None:
        text = DOC.read_text(encoding="utf-8")
        for marker in (
            "MARKETPLACE_APPLICATION_AUTH_ENROLLMENT_COORDINATION_V1",
            "HIGH security/privacy",
            "authorize_principal",
            "consumed even if policy rejects",
            "transport-neutral",
            "unselected",
            "source-only rollback",
        ):
            self.assertIn(marker, text)


if __name__ == "__main__":
    unittest.main()
