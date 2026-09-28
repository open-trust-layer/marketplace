from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = (
    ROOT
    / "src"
    / "marketplace"
    / "application"
    / "auth_enrollment_startup_composition.py"
)
TESTS = ROOT / "tests" / "test_m17_6l_auth_enrollment_startup_composition.py"
ARTIFACTS = (
    ROOT
    / "tests"
    / "test_m17_6l_auth_enrollment_startup_composition_artifacts.py"
)
DOC = ROOT / "docs" / "m17-6l-auth-enrollment-startup-composition.md"
PACKAGE_GATE = ROOT / "tools" / "package_artifact_gate.py"
PACKAGE_TESTS = ROOT / "tests" / "test_package_artifact_gate.py"

NONSELECTING = (
    ROOT / "src" / "marketplace" / "application" / "auth_startup_composition.py",
    ROOT / "src" / "marketplace" / "application" / "auth_launch.py",
    ROOT / "src" / "marketplace" / "application" / "auth_runtime_server.py",
    ROOT / "web" / "auth_bootstrap.js",
    ROOT / "android" / "app" / "src" / "main" / "java" / "org" / "opentrustlayer" / "marketplace" / "MainActivity.kt",
)


class M176LAuthenticationEnrollmentStartupCompositionArtifactTests(
    unittest.TestCase
):
    def test_exact_m17_6l_artifacts_exist(self) -> None:
        for path in (SOURCE, TESTS, ARTIFACTS, DOC, PACKAGE_GATE, PACKAGE_TESTS):
            self.assertTrue(path.is_file(), str(path))

    def test_source_reuses_j_k_and_existing_startup_without_rebuilding_auth(self) -> None:
        text = SOURCE.read_text(encoding="utf-8")
        for marker in (
            "MarketplaceAuthenticatedStartupComposition",
            "compose_marketplace_authentication_enrollment_http",
            "compose_marketplace_authentication_enrollment_asgi",
            "authenticated_startup.http",
            "authenticated_startup.asgi.runtime_inputs is not runtime_inputs",
        ):
            self.assertIn(marker, text)
        self.assertNotIn("compose_marketplace_authenticated_startup", text)
        self.assertNotIn("compose_marketplace_static_authentication", text)
        self.assertNotIn("compose_marketplace_authenticated_http", text)

    def test_source_has_zero_consumption_runtime_or_provider_calls(self) -> None:
        text = SOURCE.read_text(encoding="utf-8")
        for marker in (
            ".now(",
            "challenge_bytes(",
            "session_token_bytes(",
            "enrollment_nonce_bytes(",
            "issue_authentication_enrollment_nonce(",
            "consume_authentication_enrollment_nonce(",
            "approve_authentication_enrollment(",
            "attest_authentication_enrollment(",
            ".handle(",
            "open(",
            "socket",
            "subprocess",
            "psycopg",
            "sqlite",
            "uvicorn",
            "asyncio.run",
        ):
            self.assertNotIn(marker, text)

    def test_launch_runtime_startup_and_clients_do_not_select_l(self) -> None:
        for path in NONSELECTING:
            text = path.read_text(encoding="utf-8")
            self.assertNotIn("auth_enrollment_startup_composition", text, str(path))
            self.assertNotIn(
                "compose_marketplace_authentication_enrollment_startup",
                text,
                str(path),
            )
            self.assertNotIn(
                "MARKETPLACE_APPLICATION_AUTH_ENROLLMENT_STARTUP_COMPOSITION_V1",
                text,
                str(path),
            )

    def test_package_controls_require_new_module(self) -> None:
        gate = PACKAGE_GATE.read_text(encoding="utf-8")
        tests = PACKAGE_TESTS.read_text(encoding="utf-8")
        member = "marketplace/application/auth_enrollment_startup_composition.py"
        self.assertEqual(gate.count(f'"{member}"'), 1)
        self.assertGreaterEqual(tests.count(member), 2)

    def test_document_records_overlay_moon_and_rollback_boundaries(self) -> None:
        text = DOC.read_text(encoding="utf-8")
        for marker in (
            "MARKETPLACE_APPLICATION_AUTH_ENROLLMENT_STARTUP_COMPOSITION_V1",
            "HIGH security/privacy",
            "same exact runtime-input object",
            "overlay",
            "zero new clock",
            "unselected by launch",
            "Moon Company",
            "source-only rollback",
        ):
            self.assertIn(marker, text)


if __name__ == "__main__":
    unittest.main()
