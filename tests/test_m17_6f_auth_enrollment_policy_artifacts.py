from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src" / "marketplace" / "application" / "auth_enrollment_policy.py"
TESTS = ROOT / "tests" / "test_m17_6f_auth_enrollment_policy.py"
ARTIFACTS = ROOT / "tests" / "test_m17_6f_auth_enrollment_policy_artifacts.py"
DOC = ROOT / "docs" / "m17-6f-auth-enrollment-policy.md"
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


class M176FAuthenticationEnrollmentPolicyArtifactTests(unittest.TestCase):
    def test_exact_m17_6f_artifacts_exist(self) -> None:
        for path in (SOURCE, TESTS, ARTIFACTS, DOC, PACKAGE_GATE, PACKAGE_TESTS):
            self.assertTrue(path.is_file(), str(path))

    def test_source_reuses_existing_proposal_authority_and_evidence_types(self) -> None:
        text = SOURCE.read_text(encoding="utf-8")
        for marker in (
            "MarketplaceAuthenticationEnrollmentProposal",
            "AuthenticationEnrollmentAuthorityAttestor",
            "issue_marketplace_authentication_enrollment_evidence",
            "AuthenticationVerificationMethodEvidenceClaim",
            "MarketplaceAuthenticationVerificationMethodEvidenceClaims",
            "parse_marketplace_auth_verification_public_key",
        ):
            self.assertIn(marker, text)

    def test_source_exposes_only_one_purpose_specific_policy_operation(self) -> None:
        text = SOURCE.read_text(encoding="utf-8")
        self.assertIn("def approve_authentication_enrollment(", text)
        self.assertEqual(text.count("approved = operation("), 1)
        self.assertEqual(
            text.count("return issue_marketplace_authentication_enrollment_evidence("),
            1,
        )

    def test_source_has_no_concrete_policy_provider_or_external_io(self) -> None:
        text = SOURCE.read_text(encoding="utf-8")
        for marker in (
            "allowlist", "denylist", "role", "membership", "requests", "httpx",
            "urllib", "socket", "open(", "Path(", "os.environ", "getenv",
            "psycopg", "sqlite", "subprocess", "threading", "multiprocessing",
            "asyncio", "setTimeout", "setInterval", "retry", "fallback",
        ):
            self.assertNotIn(marker, text)

    def test_policy_remains_unselected_by_runtime_web_and_android(self) -> None:
        for path in NONSELECTING:
            text = path.read_text(encoding="utf-8")
            self.assertNotIn("auth_enrollment_policy", text, str(path))
            self.assertNotIn(
                "issue_marketplace_authentication_enrollment_evidence_after_policy",
                text,
                str(path),
            )
            self.assertNotIn(
                "MARKETPLACE_APPLICATION_AUTH_ENROLLMENT_POLICY_V1",
                text,
                str(path),
            )

    def test_package_controls_require_new_module(self) -> None:
        gate = PACKAGE_GATE.read_text(encoding="utf-8")
        tests = PACKAGE_TESTS.read_text(encoding="utf-8")
        member = "marketplace/application/auth_enrollment_policy.py"
        self.assertEqual(gate.count(f'"{member}"'), 1)
        self.assertGreaterEqual(tests.count(member), 2)

    def test_document_records_policy_gate_and_non_authority(self) -> None:
        text = DOC.read_text(encoding="utf-8")
        for marker in (
            "MARKETPLACE_APPLICATION_AUTH_ENROLLMENT_POLICY_V1",
            "HIGH security/privacy",
            "exact boolean `True`",
            "policy exactly once",
            "attestor not called",
            "unselected",
            "source-only rollback",
        ):
            self.assertIn(marker, text)


if __name__ == "__main__":
    unittest.main()
