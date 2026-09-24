from __future__ import annotations

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src" / "marketplace" / "application" / "agreement_assent_http_composition.py"
DOC = ROOT / "docs" / "product-agreement-assent-http-composition.md"
RUNTIME_FILES = (
    ROOT / "src" / "marketplace" / "application" / "asgi.py",
    ROOT / "src" / "marketplace" / "application" / "auth_session_asgi.py",
    ROOT / "src" / "marketplace" / "application" / "launch.py",
    ROOT / "src" / "marketplace" / "application" / "runtime_server.py",
)
WEB_FILES = (
    ROOT / "web" / "index.html",
    ROOT / "web" / "app.js",
    ROOT / "web" / "auth_bootstrap.js",
)


class MarketplaceAgreementAssentHttpCompositionArtifactTests(unittest.TestCase):
    def test_profile_and_document_exist(self) -> None:
        source = SOURCE.read_text(encoding="utf-8")
        self.assertIn(
            'PROFILE_NAME: Final = "MARKETPLACE_AGREEMENT_ASSENT_HTTP_COMPOSITION_V1"',
            source,
        )
        self.assertTrue(DOC.is_file())

    def test_source_has_no_runtime_provisioning_or_external_io(self) -> None:
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

    def test_runtime_and_web_entry_points_do_not_select_profile(self) -> None:
        marker = "agreement_assent_http_composition"
        for path in RUNTIME_FILES + WEB_FILES:
            if not path.is_file():
                continue
            with self.subTest(path=path.name):
                self.assertNotIn(marker, path.read_text(encoding="utf-8"))

    def test_document_records_inert_shared_auth_boundary(self) -> None:
        doc = DOC.read_text(encoding="utf-8")
        for marker in (
            "MARKETPLACE_AGREEMENT_ASSENT_HTTP_COMPOSITION_V1",
            "same exact authentication graph",
            "no ASGI",
            "no site-host",
            "no browser activation",
            "no runtime selection",
            "source-only rollback",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, doc)


if __name__ == "__main__":
    unittest.main()
