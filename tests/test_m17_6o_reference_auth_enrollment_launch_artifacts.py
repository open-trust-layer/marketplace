from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src" / "marketplace" / "reference" / "auth_enrollment_launch_v1.py"
TESTS = ROOT / "tests" / "test_m17_6o_reference_auth_enrollment_launch.py"
ARTIFACTS = ROOT / "tests" / "test_m17_6o_reference_auth_enrollment_launch_artifacts.py"
DOC = ROOT / "docs" / "m17-6o-reference-auth-enrollment-launch.md"
PACKAGE_GATE = ROOT / "tools" / "package_artifact_gate.py"
PACKAGE_TESTS = ROOT / "tests" / "test_package_artifact_gate.py"

NONSELECTING = (
    ROOT / "src" / "marketplace" / "reference" / "auth_application_v1.py",
    ROOT / "src" / "marketplace" / "reference" / "auth_postgres_application_v1.py",
    ROOT / "src" / "marketplace" / "application" / "auth_enrollment_runtime_server.py",
    ROOT / "src" / "marketplace" / "application" / "uvicorn_provider.py",
)


class M176OReferenceAuthenticationEnrollmentLaunchArtifactTests(unittest.TestCase):
    def test_exact_m17_6o_artifacts_exist(self) -> None:
        for path in (SOURCE, TESTS, ARTIFACTS, DOC, PACKAGE_GATE, PACKAGE_TESTS):
            self.assertTrue(path.is_file(), str(path))

    def test_source_freezes_profile_collaborators_l_m_and_identity_selection(self) -> None:
        text = SOURCE.read_text(encoding="utf-8")
        for marker in (
            '"MARKETPLACE_REFERENCE_AUTHENTICATION_ENROLLMENT_LAUNCH_V1"',
            "MarketplaceAuthenticatedLoopbackLaunchPlan",
            "MarketplaceAuthenticationEnrollmentNonceAuthority",
            "AuthenticationEnrollmentApprovalPolicy",
            "AuthenticationEnrollmentAuthorityAttestor",
            "compose_marketplace_authentication_enrollment_startup",
            "build_marketplace_authentication_enrollment_loopback_launch_plan",
            "authenticated_startup.asgi.runtime_inputs",
            "self.startup.enrollment_http.policy is not self.policy",
            "self.startup.enrollment_http.attestor is not self.attestor",
            "self.authenticated_plan.asgi._enrollment_http is not None",
        ):
            self.assertIn(marker, text)

    def test_source_does_not_select_runtime_provider_key_or_concrete_authority(self) -> None:
        text = SOURCE.read_text(encoding="utf-8")
        for marker in (
            "auth_enrollment_runtime_server",
            "run_marketplace_authentication_enrollment_foreground",
            "EXECUTE_ONE_AUTHENTICATION_ENROLLMENT_MARKETPLACE_LOOPBACK_SERVER",
            "UvicornLoopbackServerProvider",
            "uvicorn",
            "socket.",
            "private_key",
            "Ed25519PrivateKey",
            "os.environ",
            "getenv(",
            "subprocess",
            "threading",
            "multiprocessing",
            "psycopg",
            "sqlite",
        ):
            self.assertNotIn(marker, text)

    def test_existing_reference_runtime_and_provider_paths_do_not_select_o(self) -> None:
        for path in NONSELECTING:
            text = path.read_text(encoding="utf-8")
            self.assertNotIn("auth_enrollment_launch_v1", text, str(path))
            self.assertNotIn(
                "build_reference_authentication_enrollment_launch",
                text,
                str(path),
            )
            self.assertNotIn(
                "MARKETPLACE_REFERENCE_AUTHENTICATION_ENROLLMENT_LAUNCH_V1",
                text,
                str(path),
            )

    def test_package_controls_require_new_reference_module(self) -> None:
        gate = PACKAGE_GATE.read_text(encoding="utf-8")
        tests = PACKAGE_TESTS.read_text(encoding="utf-8")
        member = "marketplace/reference/auth_enrollment_launch_v1.py"
        self.assertEqual(gate.count(f'"{member}"'), 1)
        self.assertGreaterEqual(tests.count(member), 2)

    def test_document_records_caller_authority_inert_moon_and_rollback_boundaries(self) -> None:
        text = DOC.read_text(encoding="utf-8")
        for marker in (
            "MARKETPLACE_REFERENCE_AUTHENTICATION_ENROLLMENT_LAUNCH_V1",
            "HIGH security/privacy",
            "caller-supplied",
            "does not invoke M17.6N",
            "Moon Company",
            "source-only rollback",
        ):
            self.assertIn(marker, text)


if __name__ == "__main__":
    unittest.main()
