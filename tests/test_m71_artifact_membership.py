from pathlib import Path
import ast
import unittest


REPO_ROOT = Path(__file__).parents[1]
APPLICATION = REPO_ROOT / "src" / "marketplace" / "application" / "local.py"
APPLICATION_INIT = REPO_ROOT / "src" / "marketplace" / "application" / "__init__.py"
SECURITY_DOC = REPO_ROOT / "docs" / "local-marketplace-application-core.md"
M71_TESTS = REPO_ROOT / "tests" / "test_m71_local_marketplace_application.py"
M71_INTEGRATION = REPO_ROOT / "tests" / "test_m71_application_runtime_integration.py"
PYPROJECT = REPO_ROOT / "pyproject.toml"


class M71ArtifactMembershipTests(unittest.TestCase):
    def test_m71_required_application_tests_and_document_are_present(self):
        self.assertTrue(APPLICATION.is_file())
        self.assertTrue(APPLICATION_INIT.is_file())
        self.assertTrue(SECURITY_DOC.is_file())
        self.assertTrue(M71_TESTS.is_file())
        self.assertTrue(M71_INTEGRATION.is_file())

    def test_application_core_adds_no_network_persistence_or_olp_import(self):
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

    def test_application_core_keeps_zero_declared_runtime_dependencies(self):
        project = PYPROJECT.read_text(encoding="utf-8")
        self.assertIn("dependencies = []", project)


    def test_application_core_requires_exact_reviewed_result_shapes(self):
        source = APPLICATION.read_text(encoding="utf-8")
        self.assertIn("type(outcome) is not IngestOutcome", source)
        self.assertIn("if type(result) is not dict:", source)



if __name__ == "__main__":
    unittest.main()
