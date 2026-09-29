from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src" / "marketplace" / "application" / "auth_enrollment_launch.py"
TESTS = ROOT / "tests" / "test_m17_6m_auth_enrollment_launch.py"
ARTIFACTS = ROOT / "tests" / "test_m17_6m_auth_enrollment_launch_artifacts.py"
DOC = ROOT / "docs" / "m17-6m-auth-enrollment-launch.md"
PACKAGE_GATE = ROOT / "tools" / "package_artifact_gate.py"
PACKAGE_TESTS = ROOT / "tests" / "test_package_artifact_gate.py"

NONSELECTING = (
    ROOT / "src" / "marketplace" / "application" / "auth_launch.py",
    ROOT / "src" / "marketplace" / "application" / "auth_runtime_server.py",
    ROOT / "web" / "auth_bootstrap.js",
    ROOT / "android" / "app" / "src" / "main" / "java" / "org" / "opentrustlayer" / "marketplace" / "MainActivity.kt",
)


class M176MAuthenticationEnrollmentLaunchArtifactTests(unittest.TestCase):
    def test_exact_m17_6m_artifacts_exist(self) -> None:
        for path in (SOURCE, TESTS, ARTIFACTS, DOC, PACKAGE_GATE, PACKAGE_TESTS):
            self.assertTrue(path.is_file(), str(path))

    def test_source_freezes_exact_profile_loopback_and_l_selection(self) -> None:
        text = SOURCE.read_text(encoding="utf-8")
        for marker in (
            'PROFILE_NAME: Final = (',
            '"MARKETPLACE_APPLICATION_AUTH_ENROLLMENT_LOOPBACK_LAUNCH_PLAN_V1"',
            "LOOPBACK_LAUNCH_HOST",
            "MIN_LAUNCH_PORT",
            "MAX_LAUNCH_PORT",
            "MarketplaceAuthenticationEnrollmentStartupComposition",
            "startup.enrollment_asgi.asgi",
            "startup.enrollment_http.enrollment_http",
            "startup.runtime_inputs.clock",
        ):
            self.assertIn(marker, text)

    def test_source_has_no_runtime_provider_socket_or_consumption_calls(self) -> None:
        text = SOURCE.read_text(encoding="utf-8")
        for marker in (
            "clock.now(",
            "challenge_bytes(",
            "session_token_bytes(",
            "enrollment_nonce_bytes(",
            "issue_authentication_enrollment_nonce(",
            "consume_authentication_enrollment_nonce(",
            "approve_authentication_enrollment(",
            "attest_authentication_enrollment(",
            ".handle(",
            ".run(",
            "socket.",
            "bind(",
            "listen(",
            "accept(",
            "open(",
            "subprocess",
            "requests",
            "httpx",
            "psycopg",
            "sqlite",
            "uvicorn",
            "asyncio.run",
        ):
            self.assertNotIn(marker, text)

    def test_existing_launch_runtime_and_clients_do_not_select_m(self) -> None:
        for path in NONSELECTING:
            text = path.read_text(encoding="utf-8")
            self.assertNotIn("auth_enrollment_launch", text, str(path))
            self.assertNotIn(
                "build_marketplace_authentication_enrollment_loopback_launch_plan",
                text,
                str(path),
            )
            self.assertNotIn(
                "MARKETPLACE_APPLICATION_AUTH_ENROLLMENT_LOOPBACK_LAUNCH_PLAN_V1",
                text,
                str(path),
            )

    def test_package_controls_require_new_module(self) -> None:
        gate = PACKAGE_GATE.read_text(encoding="utf-8")
        tests = PACKAGE_TESTS.read_text(encoding="utf-8")
        member = "marketplace/application/auth_enrollment_launch.py"
        self.assertEqual(gate.count(f'"{member}"'), 1)
        self.assertGreaterEqual(tests.count(member), 2)

    def test_document_records_inert_moon_and_rollback_boundaries(self) -> None:
        text = DOC.read_text(encoding="utf-8")
        for marker in (
            "MARKETPLACE_APPLICATION_AUTH_ENROLLMENT_LOOPBACK_LAUNCH_PLAN_V1",
            "HIGH security/privacy",
            "127.0.0.1",
            "inert",
            "does not run a server",
            "Moon Company",
            "source-only rollback",
        ):
            self.assertIn(marker, text)


if __name__ == "__main__":
    unittest.main()
