from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src" / "marketplace" / "application" / "auth_enrollment_http.py"
TESTS = ROOT / "tests" / "test_m17_6i_auth_enrollment_http.py"
ARTIFACTS = ROOT / "tests" / "test_m17_6i_auth_enrollment_http_artifacts.py"
DOC = ROOT / "docs" / "m17-6i-auth-enrollment-http.md"
PACKAGE_GATE = ROOT / "tools" / "package_artifact_gate.py"
PACKAGE_TESTS = ROOT / "tests" / "test_package_artifact_gate.py"

NONSELECTING = (
    ROOT / "src" / "marketplace" / "application" / "auth_http.py",
    ROOT / "src" / "marketplace" / "application" / "auth_http_composition.py",
    ROOT / "src" / "marketplace" / "application" / "auth_startup_composition.py",
    ROOT / "web" / "auth_bootstrap.js",
    ROOT / "android" / "app" / "src" / "main" / "java" / "org" / "opentrustlayer" / "marketplace" / "MainActivity.kt",
)


class M176IAuthenticationEnrollmentHttpArtifactTests(unittest.TestCase):
    def test_exact_m17_6i_artifacts_exist(self) -> None:
        for path in (SOURCE, TESTS, ARTIFACTS, DOC, PACKAGE_GATE, PACKAGE_TESTS):
            self.assertTrue(path.is_file(), str(path))

    def test_source_freezes_exact_routes_profiles_and_wire_prefixes(self) -> None:
        text = SOURCE.read_text(encoding="utf-8")
        for marker in (
            'PROFILE_NAME: Final = "MARKETPLACE_APPLICATION_AUTH_ENROLLMENT_HTTP_V1"',
            'WEB_PROPOSAL_PROFILE: Final = "MARKETPLACE_WEB_AUTH_ED25519_ENROLLMENT_PROPOSAL_V1"',
            'AUTH_ENROLLMENT_NONCE_ROUTE: Final = "/api/authentication-enrollment/nonces"',
            'AUTH_ENROLLMENT_EVIDENCE_ROUTE: Final = "/api/authentication-enrollment/evidence"',
            'AUTH_ENROLLMENT_NONCE_PREFIX: Final = "mken1_"',
            'AUTH_ENROLLMENT_CLAIMS_PREFIX: Final = "mkec1_"',
            'AUTH_ENROLLMENT_ATTESTATION_PREFIX: Final = "mkea1_"',
        ):
            self.assertIn(marker, text)

    def test_request_shapes_do_not_accept_authority_or_lease(self) -> None:
        text = SOURCE.read_text(encoding="utf-8")
        self.assertIn('_NONCE_REQUEST_KEYS = frozenset({"profile", "proposal"})', text)
        self.assertIn(
            '_EVIDENCE_REQUEST_KEYS = frozenset({"profile", "proposal", "nonce"})',
            text,
        )
        self.assertNotIn('"authority", "proposal"', text)
        self.assertNotIn('"leaseSeconds"', text)

    def test_source_reuses_m17_6g_h_and_existing_session_authority(self) -> None:
        text = SOURCE.read_text(encoding="utf-8")
        for marker in (
            "MarketplaceApplicationAuthService",
            "MarketplaceAuthenticationEnrollmentNonceAuthority",
            "coordinate_marketplace_authentication_enrollment",
            "MarketplaceAuthenticationEnrollmentProposal",
            "AUTH_EVIDENCE_MAX_LEASE_SECONDS",
        ):
            self.assertIn(marker, text)

    def test_source_has_no_runtime_selection_external_io_or_secret_generation(self) -> None:
        text = SOURCE.read_text(encoding="utf-8")
        for marker in (
            "requests", "httpx", "urllib", "socket", "open(", "Path(",
            "os.environ", "getenv", "psycopg", "sqlite", "subprocess",
            "secrets.", "token_bytes", "os.urandom", "random.",
            "uvicorn.run", "asyncio.run", "serviceWorker", "fetch(",
        ):
            self.assertNotIn(marker, text)

    def test_http_carrier_remains_unselected_by_startup_runtime_and_clients(self) -> None:
        for path in NONSELECTING:
            text = path.read_text(encoding="utf-8")
            self.assertNotIn("auth_enrollment_http", text, str(path))
            self.assertNotIn(
                "MarketplaceAuthenticationEnrollmentHttpAdapter",
                text,
                str(path),
            )
            self.assertNotIn(
                "MARKETPLACE_APPLICATION_AUTH_ENROLLMENT_HTTP_V1",
                text,
                str(path),
            )

    def test_later_m17_6k_selection_is_explicit_and_exact_route_only(self) -> None:
        asgi = (
            ROOT
            / "src"
            / "marketplace"
            / "application"
            / "auth_session_asgi.py"
        ).read_text(encoding="utf-8")
        self.assertIn("MarketplaceAuthenticationEnrollmentHttpAdapter", asgi)
        self.assertIn("AUTH_ENROLLMENT_NONCE_ROUTE", asgi)
        self.assertIn("AUTH_ENROLLMENT_EVIDENCE_ROUTE", asgi)
        self.assertIn("AUTH_ENROLLMENT_HTTP_REQUEST_MAX_BYTES", asgi)
        self.assertNotIn('startswith("/api/authentication-enrollment/")', asgi)

    def test_package_controls_require_new_module(self) -> None:
        gate = PACKAGE_GATE.read_text(encoding="utf-8")
        tests = PACKAGE_TESTS.read_text(encoding="utf-8")
        member = "marketplace/application/auth_enrollment_http.py"
        self.assertEqual(gate.count(f'"{member}"'), 1)
        self.assertGreaterEqual(tests.count(member), 2)

    def test_document_records_source_only_http_and_later_activation_gate(self) -> None:
        text = DOC.read_text(encoding="utf-8")
        for marker in (
            "MARKETPLACE_APPLICATION_AUTH_ENROLLMENT_HTTP_V1",
            "HIGH security/privacy",
            "mken1_",
            "mkec1_",
            "mkea1_",
            "trusted composition",
            "source-only",
            "unselected",
            "source-only rollback",
        ):
            self.assertIn(marker, text)


if __name__ == "__main__":
    unittest.main()
