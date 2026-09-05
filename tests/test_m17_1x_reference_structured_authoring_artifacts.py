from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
FACTORY = ROOT / "src" / "marketplace" / "reference" / "application_v1.py"
REFERENCE_INIT = ROOT / "src" / "marketplace" / "reference" / "__init__.py"
APPLICATION = ROOT / "src" / "marketplace" / "application"
DOC = ROOT / "docs" / "m17-1x-reference-structured-authoring-composition.md"


class M17ReferenceStructuredAuthoringArtifactsTests(unittest.TestCase):
    def test_reference_factory_exists_and_fixes_reviewed_builders(self):
        self.assertTrue(FACTORY.is_file())
        text = FACTORY.read_text(encoding="utf-8-sig")
        self.assertIn("def build_reference_marketplace_application_launch_plan(", text)
        self.assertIn("from .product_listing_v1 import build_product_listing_record", text)
        self.assertIn("from .proposal_v1 import build_buyer_request_proposal_record", text)
        self.assertIn("build_product_listing_record=build_product_listing_record", text)
        self.assertIn("build_proposal_record=build_buyer_request_proposal_record", text)
        self.assertIn("return build_marketplace_application_launch_plan(", text)

    def test_reference_factory_is_inert_and_does_not_choose_runtime_resources(self):
        text = FACTORY.read_text(encoding="utf-8-sig")
        for forbidden in (
            "run_marketplace_application_foreground",
            "UvicornLoopbackServerProvider",
            "PostgresApplicationStateStore",
            "PostgresIntentQuery",
            "connection_factory=",
            "open(",
            "Path(",
            "os.environ",
            "getenv(",
            "socket.",
        ):
            self.assertNotIn(forbidden, text)

    def test_application_layer_does_not_import_reference_layer(self):
        for path in APPLICATION.glob("*.py"):
            text = path.read_text(encoding="utf-8-sig")
            self.assertNotIn("marketplace.reference", text, path.name)
            self.assertNotIn("from ..reference", text, path.name)
            self.assertNotIn("from marketplace.reference", text, path.name)

    def test_reference_package_exports_factory(self):
        text = REFERENCE_INIT.read_text(encoding="utf-8-sig")
        self.assertIn("build_reference_marketplace_application_launch_plan", text)

    def test_document_records_exact_inert_boundary(self):
        self.assertTrue(DOC.is_file())
        text = DOC.read_text(encoding="utf-8-sig")
        for marker in (
            "reference-layer inert factory",
            "genuine OLP reference builders",
            "no runtime activation",
            "no PostgreSQL connection",
            "no filesystem asset loading",
            "merge remains a separate exact-head governance boundary",
        ):
            self.assertIn(marker, text)


if __name__ == "__main__":
    unittest.main()