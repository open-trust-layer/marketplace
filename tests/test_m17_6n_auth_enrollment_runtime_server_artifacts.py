from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src" / "marketplace" / "application" / "auth_enrollment_runtime_server.py"
TESTS = ROOT / "tests" / "test_m17_6n_auth_enrollment_runtime_server.py"
ARTIFACTS = ROOT / "tests" / "test_m17_6n_auth_enrollment_runtime_server_artifacts.py"
DOC = ROOT / "docs" / "m17-6n-auth-enrollment-runtime-server.md"
PACKAGE_GATE = ROOT / "tools" / "package_artifact_gate.py"
PACKAGE_TESTS = ROOT / "tests" / "test_package_artifact_gate.py"

NONSELECTING = (
    ROOT / "src" / "marketplace" / "application" / "auth_runtime_server.py",
    ROOT / "src" / "marketplace" / "application" / "auth_enrollment_launch.py",
    ROOT / "src" / "marketplace" / "application" / "auth_startup_composition.py",
    ROOT / "src" / "marketplace" / "reference" / "auth_application_v1.py",
)


class M176NAuthenticationEnrollmentRuntimeServerArtifactTests(unittest.TestCase):
    def test_exact_m17_6n_artifacts_exist(self) -> None:
        for path in (SOURCE, TESTS, ARTIFACTS, DOC, PACKAGE_GATE, PACKAGE_TESTS):
            self.assertTrue(path.is_file(), str(path))

    def test_source_freezes_profile_token_plan_and_single_provider_boundary(self) -> None:
        text = SOURCE.read_text(encoding="utf-8")
        for marker in (
            '"MARKETPLACE_APPLICATION_AUTH_ENROLLMENT_FOREGROUND_RUNTIME_V1"',
            '"EXECUTE_ONE_AUTHENTICATION_ENROLLMENT_MARKETPLACE_LOOPBACK_SERVER"',
            "MarketplaceAuthenticationEnrollmentLoopbackLaunchPlan",
            "MarketplaceAuthenticationEnrollmentStartupComposition",
            "MarketplaceSessionEstablishmentAsgiHttpAdapter",
            "startup.enrollment_http.enrollment_http",
            "startup.runtime_inputs.clock",
            "run(application=plan.asgi, host=plan.host, port=plan.port)",
        ):
            self.assertIn(marker, text)
        self.assertEqual(
            text.count("run(application=plan.asgi, host=plan.host, port=plan.port)"),
            1,
        )

    def test_source_has_no_concrete_provider_discovery_or_socket_implementation(self) -> None:
        text = SOURCE.read_text(encoding="utf-8")
        for marker in (
            "uvicorn",
            "socket.",
            "subprocess",
            "threading",
            "multiprocessing",
            "asyncio.run",
            "os.environ",
            "getenv(",
            "open(",
            "requests",
            "httpx",
            "psycopg",
            "sqlite",
        ):
            self.assertNotIn(marker, text)

    def test_existing_runtime_launch_reference_paths_do_not_select_n(self) -> None:
        for path in NONSELECTING:
            text = path.read_text(encoding="utf-8")
            self.assertNotIn("auth_enrollment_runtime_server", text, str(path))
            self.assertNotIn(
                "run_marketplace_authentication_enrollment_foreground",
                text,
                str(path),
            )
            self.assertNotIn(
                "EXECUTE_ONE_AUTHENTICATION_ENROLLMENT_MARKETPLACE_LOOPBACK_SERVER",
                text,
                str(path),
            )

    def test_package_controls_require_new_module(self) -> None:
        gate = PACKAGE_GATE.read_text(encoding="utf-8")
        tests = PACKAGE_TESTS.read_text(encoding="utf-8")
        member = "marketplace/application/auth_enrollment_runtime_server.py"
        self.assertEqual(gate.count(f'"{member}"'), 1)
        self.assertGreaterEqual(tests.count(member), 2)

    def test_document_records_explicit_unselected_moon_and_rollback_boundaries(self) -> None:
        text = DOC.read_text(encoding="utf-8")
        for marker in (
            "MARKETPLACE_APPLICATION_AUTH_ENROLLMENT_FOREGROUND_RUNTIME_V1",
            "HIGH security/privacy",
            "explicit execution token",
            "deterministic provider probe",
            "unselected",
            "Moon Company",
            "source-only rollback",
        ):
            self.assertIn(marker, text)


if __name__ == "__main__":
    unittest.main()
