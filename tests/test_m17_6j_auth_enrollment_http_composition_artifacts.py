from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = (
    ROOT
    / "src"
    / "marketplace"
    / "application"
    / "auth_enrollment_http_composition.py"
)
TESTS = ROOT / "tests" / "test_m17_6j_auth_enrollment_http_composition.py"
ARTIFACTS = (
    ROOT / "tests" / "test_m17_6j_auth_enrollment_http_composition_artifacts.py"
)
DOC = ROOT / "docs" / "m17-6j-auth-enrollment-http-composition.md"
PACKAGE_GATE = ROOT / "tools" / "package_artifact_gate.py"
PACKAGE_TESTS = ROOT / "tests" / "test_package_artifact_gate.py"

NONSELECTING = (
    ROOT / "src" / "marketplace" / "application" / "auth_http_composition.py",
    ROOT / "src" / "marketplace" / "application" / "auth_asgi_composition.py",
    ROOT / "src" / "marketplace" / "application" / "auth_session_asgi.py",
    ROOT / "src" / "marketplace" / "application" / "auth_startup_composition.py",
    ROOT / "src" / "marketplace" / "application" / "auth_launch.py",
    ROOT / "web" / "auth_bootstrap.js",
    ROOT / "android" / "app" / "src" / "main" / "java" / "org" / "opentrustlayer" / "marketplace" / "MainActivity.kt",
)


class M176JAuthenticationEnrollmentHttpCompositionArtifactTests(
    unittest.TestCase
):
    def test_exact_m17_6j_artifacts_exist(self) -> None:
        for path in (SOURCE, TESTS, ARTIFACTS, DOC, PACKAGE_GATE, PACKAGE_TESTS):
            self.assertTrue(path.is_file(), str(path))

    def test_source_freezes_profile_and_exact_composed_types(self) -> None:
        text = SOURCE.read_text(encoding="utf-8")
        for marker in (
            '"MARKETPLACE_APPLICATION_AUTH_ENROLLMENT_HTTP_COMPOSITION_V1"',
            "MarketplaceAuthenticatedHttpComposition",
            "MarketplaceAuthenticationEnrollmentNonceAuthority",
            "MarketplaceAuthenticationEnrollmentHttpAdapter",
            "compose_marketplace_authentication_enrollment_http",
        ):
            self.assertIn(marker, text)

    def test_source_proves_same_auth_service_identity(self) -> None:
        text = SOURCE.read_text(encoding="utf-8")
        for marker in (
            "http.authentication.auth_service",
            "http.application_http._auth is not auth_service",
            "http.session_http._auth is not auth_service",
            "self.enrollment_http._auth is not auth_service",
        ):
            self.assertIn(marker, text)

    def test_composition_does_not_consume_material_policy_or_attestor(self) -> None:
        text = SOURCE.read_text(encoding="utf-8")
        for forbidden in (
            "challenge_bytes()",
            "session_token_bytes()",
            "enrollment_nonce_bytes()",
            "approve_authentication_enrollment(",
            "attest_authentication_enrollment(",
            "issue_authentication_enrollment_nonce(",
            "consume_authentication_enrollment_nonce(",
            "coordinate_marketplace_authentication_enrollment(",
        ):
            self.assertNotIn(forbidden, text)

    def test_source_has_no_runtime_external_io_or_secret_generation(self) -> None:
        text = SOURCE.read_text(encoding="utf-8")
        for marker in (
            "import os", "from os", "os.environ", "pathlib", "Path(",
            "open(", "socket", "subprocess", "requests", "httpx", "urllib",
            "psycopg", "sqlite", "secrets.", "token_bytes", "os.urandom",
            "random.", "uvicorn", "asyncio.run",
        ):
            self.assertNotIn(marker, text)

    def test_new_composition_remains_unselected_by_runtime_and_clients(self) -> None:
        for path in NONSELECTING:
            text = path.read_text(encoding="utf-8")
            self.assertNotIn("auth_enrollment_http_composition", text, str(path))
            self.assertNotIn(
                "compose_marketplace_authentication_enrollment_http",
                text,
                str(path),
            )
            self.assertNotIn(
                "MARKETPLACE_APPLICATION_AUTH_ENROLLMENT_HTTP_COMPOSITION_V1",
                text,
                str(path),
            )

    def test_package_controls_require_new_module(self) -> None:
        gate = PACKAGE_GATE.read_text(encoding="utf-8")
        tests = PACKAGE_TESTS.read_text(encoding="utf-8")
        member = "marketplace/application/auth_enrollment_http_composition.py"
        self.assertEqual(gate.count(f'"{member}"'), 1)
        self.assertGreaterEqual(tests.count(member), 2)

    def test_document_records_static_nonconsuming_source_only_boundary(self) -> None:
        text = DOC.read_text(encoding="utf-8")
        for marker in (
            "MARKETPLACE_APPLICATION_AUTH_ENROLLMENT_HTTP_COMPOSITION_V1",
            "HIGH security/privacy",
            "same exact auth-service instance",
            "zero collaborator calls",
            "source-only",
            "unselected",
            "no ASGI",
            "source-only rollback",
        ):
            self.assertIn(marker, text)


if __name__ == "__main__":
    unittest.main()
