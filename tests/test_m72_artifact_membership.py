from pathlib import Path
import ast
import unittest


REPO_ROOT = Path(__file__).parents[1]
APPLICATION = REPO_ROOT / "src" / "marketplace" / "application" / "listing.py"
REFERENCE = REPO_ROOT / "src" / "marketplace" / "reference" / "product_listing_v1.py"
BEHAVIOR = REPO_ROOT / "tests" / "test_m72_product_listing.py"
INTEGRATION = REPO_ROOT / "tests" / "test_m72_product_listing_integration.py"
DOCUMENT = REPO_ROOT / "docs" / "human-product-listing-profile.md"
PYPROJECT = REPO_ROOT / "pyproject.toml"


class M72ArtifactMembershipTests(unittest.TestCase):
    def test_m72_required_sources_tests_and_document_are_present(self):
        for path in (APPLICATION, REFERENCE, BEHAVIOR, INTEGRATION, DOCUMENT):
            with self.subTest(path=path):
                self.assertTrue(path.is_file())

    def test_application_projection_has_no_external_io_or_olp_import(self):
        tree = ast.parse(APPLICATION.read_text(encoding="utf-8"))
        blocked = {
            "olp", "socket", "ssl", "http", "urllib", "asyncio",
            "threading", "subprocess", "sqlite3", "requests",
        }
        imported_roots: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported_roots.update(alias.name.split(".", 1)[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported_roots.add(node.module.split(".", 1)[0])
        self.assertTrue(imported_roots.isdisjoint(blocked))

    def test_reference_adapter_adds_no_network_persistence_or_process_surface(self):
        tree = ast.parse(REFERENCE.read_text(encoding="utf-8"))
        blocked = {
            "socket", "ssl", "http", "urllib", "asyncio", "threading",
            "subprocess", "sqlite3", "requests", "pathlib", "logging",
        }
        imported_roots: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported_roots.update(alias.name.split(".", 1)[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported_roots.add(node.module.split(".", 1)[0])
        self.assertTrue(imported_roots.isdisjoint(blocked))

    def test_m72_keeps_zero_declared_runtime_dependencies(self):
        project = PYPROJECT.read_text(encoding="utf-8")
        self.assertIn("dependencies = []", project)

    def test_m72_does_not_add_mutable_listing_status_shortcuts(self):
        source = APPLICATION.read_text(encoding="utf-8")
        for forbidden in (
            "is_active", "is_sold", "view_count", "ranking_score", "current_status"
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, source)

    def test_application_builder_revalidates_exact_draft_and_decimal_state(self):
        source = APPLICATION.read_text(encoding="utf-8")
        self.assertIn("def _review_exact_decimal", source)
        self.assertIn("type(value) is not ExactDecimal", source)
        self.assertIn("def _review_draft", source)
        self.assertIn("reviewed = _review_draft(draft)", source)

    def test_reference_extractor_detaches_reviewed_frozen_graph_before_validation(self):
        source = REFERENCE.read_text(encoding="utf-8")
        self.assertIn("_FROZEN_MAX_DEPTH = 16", source)
        self.assertIn("_FROZEN_MAX_COLLECTION_ITEMS = 64", source)
        self.assertIn("gc.get_referents(value)", source)
        self.assertIn("type(referents[0]) is not dict", source)
        self.assertIn("type(content_value) is not MappingProxyType", source)
        self.assertIn("reviewed_record = RecordV1(", source)
        self.assertIn("validate_market_record(reviewed_record)", source)


if __name__ == "__main__":
    unittest.main()
