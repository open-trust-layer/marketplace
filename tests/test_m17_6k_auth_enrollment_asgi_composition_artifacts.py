from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src" / "marketplace" / "application" / "auth_enrollment_asgi_composition.py"
ASGI_SOURCE = ROOT / "src" / "marketplace" / "application" / "auth_session_asgi.py"
TESTS = ROOT / "tests" / "test_m17_6k_auth_enrollment_asgi_composition.py"
ARTIFACTS = ROOT / "tests" / "test_m17_6k_auth_enrollment_asgi_composition_artifacts.py"
DOC = ROOT / "docs" / "m17-6k-auth-enrollment-asgi-composition.md"
PACKAGE_GATE = ROOT / "tools" / "package_artifact_gate.py"
PACKAGE_TESTS = ROOT / "tests" / "test_package_artifact_gate.py"

NONSELECTING = (
    ROOT / "src" / "marketplace" / "application" / "auth_startup_composition.py",
    ROOT / "src" / "marketplace" / "application" / "auth_launch.py",
    ROOT / "src" / "marketplace" / "application" / "auth_runtime_server.py",
    ROOT / "web" / "auth_bootstrap.js",
    ROOT / "android" / "app" / "src" / "main" / "java" / "org" / "opentrustlayer" / "marketplace" / "MainActivity.kt",
)


class M176KAuthenticationEnrollmentAsgiCompositionArtifactTests(unittest.TestCase):
    def test_exact_m17_6k_artifacts_exist(self) -> None:
        for path in (SOURCE, ASGI_SOURCE, TESTS, ARTIFACTS, DOC, PACKAGE_GATE, PACKAGE_TESTS):
            self.assertTrue(path.is_file(), str(path))

    def test_existing_asgi_uses_optional_exact_enrollment_slot_and_exact_routes(self) -> None:
        text = ASGI_SOURCE.read_text(encoding="utf-8")
        for marker in (
            "enrollment_http: MarketplaceAuthenticationEnrollmentHttpAdapter | None = None",
            "AUTH_ENROLLMENT_NONCE_ROUTE",
            "AUTH_ENROLLMENT_EVIDENCE_ROUTE",
            "AUTH_ENROLLMENT_HTTP_REQUEST_MAX_BYTES",
            "self._enrollment_http.handle(",
        ):
            self.assertIn(marker, text)
        self.assertNotIn('startswith("/api/authentication-enrollment/")', text)

    def test_existing_asgi_keeps_single_bearer_and_clock_path(self) -> None:
        text = ASGI_SOURCE.read_text(encoding="utf-8")
        self.assertEqual(text.count("parse_marketplace_bearer_authorization("), 1)
        self.assertEqual(text.count("now = self._now()"), 1)

    def test_composition_proves_auth_material_and_clock_identity(self) -> None:
        text = SOURCE.read_text(encoding="utf-8")
        for marker in (
            "http.authentication.auth_service",
            "http.application_http._auth is not auth_service",
            "http.session_http._auth is not auth_service",
            "enrollment.enrollment_http._auth is not auth_service",
            "http.session_http._challenge_bytes",
            "http.session_http._session_token_bytes",
            "runtime_inputs.material_source",
            "runtime_inputs.clock.now",
        ):
            self.assertIn(marker, text)

    def test_composition_has_no_runtime_io_or_consumption_calls(self) -> None:
        text = SOURCE.read_text(encoding="utf-8")
        for marker in (
            "challenge_bytes()",
            "session_token_bytes()",
            "enrollment_nonce_bytes()",
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

    def test_startup_launch_runtime_and_clients_do_not_select_k(self) -> None:
        for path in NONSELECTING:
            text = path.read_text(encoding="utf-8")
            self.assertNotIn("auth_enrollment_asgi_composition", text, str(path))
            self.assertNotIn(
                "compose_marketplace_authentication_enrollment_asgi",
                text,
                str(path),
            )
            self.assertNotIn(
                "MARKETPLACE_APPLICATION_AUTH_ENROLLMENT_ASGI_COMPOSITION_V1",
                text,
                str(path),
            )

    def test_package_controls_require_new_module(self) -> None:
        gate = PACKAGE_GATE.read_text(encoding="utf-8")
        tests = PACKAGE_TESTS.read_text(encoding="utf-8")
        member = "marketplace/application/auth_enrollment_asgi_composition.py"
        self.assertEqual(gate.count(f'"{member}"'), 1)
        self.assertGreaterEqual(tests.count(member), 2)

    def test_document_records_moon_independence_and_source_only_rollback(self) -> None:
        text = DOC.read_text(encoding="utf-8")
        for marker in (
            "MARKETPLACE_APPLICATION_AUTH_ENROLLMENT_ASGI_COMPOSITION_V1",
            "HIGH security/privacy",
            "exact-route",
            "single bearer",
            "unselected",
            "Moon Company",
            "source-only rollback",
        ):
            self.assertIn(marker, text)


if __name__ == "__main__":
    unittest.main()
