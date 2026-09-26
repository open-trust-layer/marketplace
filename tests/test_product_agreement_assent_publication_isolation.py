from __future__ import annotations

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
APPLICATION = ROOT / "src" / "marketplace" / "application"
REFERENCE = ROOT / "src" / "marketplace" / "reference"
WEB = ROOT / "web"

ASSENT_PYTHON = tuple(
    sorted(APPLICATION.glob("agreement_assent*.py"))
    + sorted(REFERENCE.glob("agreement_assent*.py"))
)
ASSENT_WEB = (
    WEB / "agreement_ed25519_assent_provider.js",
    WEB / "agreement_assent_client.js",
)
PUBLICATION_MODULES = (
    APPLICATION / "agreement_publication.py",
    APPLICATION / "agreement_publication_write.py",
)


class ProductAgreementAssentPublicationIsolationTests(unittest.TestCase):
    def test_publication_modules_exist_but_are_not_selected_by_assent_stack(self) -> None:
        for path in PUBLICATION_MODULES:
            self.assertTrue(path.is_file(), str(path))

        self.assertGreater(len(ASSENT_PYTHON), 0)
        forbidden = (
            "marketplace.application.agreement_publication",
            "marketplace.application.agreement_publication_write",
            "agreement_publication import",
            "agreement_publication_write import",
            "MarketplaceAgreementPublication",
            "publish_agreement",
            "publication_write",
        )
        for path in ASSENT_PYTHON:
            source = path.read_text(encoding="utf-8")
            for marker in forbidden:
                with self.subTest(path=path.name, marker=marker):
                    self.assertNotIn(marker, source)

    def test_browser_assent_surfaces_have_no_publication_capability(self) -> None:
        forbidden = (
            "agreement_publication",
            "agreementPublication",
            "publishAgreement",
            "publish_agreement",
            "/api/agreements/{proposal_record_id}",
        )
        for path in ASSENT_WEB:
            self.assertTrue(path.is_file(), str(path))
            source = path.read_text(encoding="utf-8")
            for marker in forbidden:
                with self.subTest(path=path.name, marker=marker):
                    self.assertNotIn(marker, source)

    def test_localhost_agreement_mode_does_not_select_publication_modules(self) -> None:
        source = (ROOT / "tools" / "marketplace_localhost.py").read_text(
            encoding="utf-8"
        )
        for marker in (
            "agreement_publication",
            "agreement_publication_write",
            "publish_agreement",
            "MarketplaceAgreementPublication",
        ):
            with self.subTest(marker=marker):
                self.assertNotIn(marker, source)

    def test_issue_364_stack_remains_assent_and_formation_only(self) -> None:
        expected = {
            "agreement_assent.py",
            "agreement_assent_coordination.py",
            "agreement_assent_formation.py",
            "agreement_assent_http.py",
            "agreement_assent_http_composition.py",
            "agreement_assent_asgi_composition.py",
            "agreement_assent_startup_composition.py",
            "agreement_assent_launch.py",
            "agreement_assent_runtime_server.py",
            "agreement_assent_workflow.py",
            "agreement_assent_candidate.py",
        }
        application_names = {path.name for path in ASSENT_PYTHON if path.parent == APPLICATION}
        self.assertTrue(expected.issubset(application_names))


if __name__ == "__main__":
    unittest.main()
