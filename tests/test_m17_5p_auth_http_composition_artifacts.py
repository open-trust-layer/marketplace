from __future__ import annotations

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src" / "marketplace" / "application" / "auth_http_composition.py"
DOC = ROOT / "docs" / "m17-5p-auth-http-composition.md"
PACKAGE_GATE = ROOT / "tools" / "package_artifact_gate.py"
PACKAGE_TEST = ROOT / "tests" / "test_package_artifact_gate.py"
ASGI = ROOT / "src" / "marketplace" / "application" / "asgi.py"
AUTH_ASGI = ROOT / "src" / "marketplace" / "application" / "auth_session_asgi.py"
LAUNCH = ROOT / "src" / "marketplace" / "application" / "launch.py"
RUNTIME = ROOT / "src" / "marketplace" / "application" / "runtime_server.py"


class MarketplaceAuthenticatedHttpCompositionArtifactTests(unittest.TestCase):
    def test_profile_and_document_exist(self) -> None:
        source = SOURCE.read_text(encoding="utf-8")
        self.assertIn(
            'PROFILE_NAME: Final = "MARKETPLACE_APPLICATION_AUTH_HTTP_COMPOSITION_V1"',
            source,
        )
        self.assertTrue(DOC.is_file())

    def test_source_has_no_provisioning_or_runtime_surface(self) -> None:
        source = SOURCE.read_text(encoding="utf-8")
        for forbidden in (
            "import os",
            "from os",
            "os.environ",
            "pathlib",
            "Path(",
            "open(",
            "socket",
            "subprocess",
            "requests",
            "httpx",
            "urllib",
            "psycopg",
            "secrets",
            "random",
            "MarketplaceSessionEstablishmentAsgiHttpAdapter",
            "MarketplaceApplicationLaunchPlan",
            "MarketplaceAsgiServerProvider",
            "MarketplaceUvicornServerProvider",
            "run_marketplace_application_foreground",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, source)

    def test_composition_does_not_invoke_material_source(self) -> None:
        source = SOURCE.read_text(encoding="utf-8")
        self.assertNotIn("challenge_bytes()", source)
        self.assertNotIn("session_token_bytes()", source)
        self.assertIn('getattr(material_source, "challenge_bytes", None)', source)
        self.assertIn(
            'getattr(material_source, "session_token_bytes", None)',
            source,
        )

    def test_runtime_entry_points_do_not_select_profile(self) -> None:
        for path in (ASGI, AUTH_ASGI, LAUNCH, RUNTIME):
            with self.subTest(path=path.name):
                text = path.read_text(encoding="utf-8")
                self.assertNotIn("auth_http_composition", text)
                self.assertNotIn(
                    "compose_marketplace_authenticated_http",
                    text,
                )

    def test_package_gate_requires_new_module(self) -> None:
        gate = PACKAGE_GATE.read_text(encoding="utf-8")
        self.assertIn(
            '"marketplace/application/auth_http_composition.py"',
            gate,
        )
        package_test = PACKAGE_TEST.read_text(encoding="utf-8")
        self.assertIn(
            '"marketplace/application/auth_http_composition.py"',
            package_test,
        )
        self.assertIn(
            "test_missing_auth_http_composition_member_is_rejected",
            package_test,
        )

    def test_document_records_exact_boundary(self) -> None:
        doc = DOC.read_text(encoding="utf-8")
        for marker in (
            "MARKETPLACE_APPLICATION_AUTH_HTTP_COMPOSITION_V1",
            "exact six-file scope",
            "same exact auth-service instance",
            "zero credential-material calls",
            "no ASGI",
            "no runtime",
            "source-only rollback",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, doc)


if __name__ == "__main__":
    unittest.main()
