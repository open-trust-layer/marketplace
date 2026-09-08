from __future__ import annotations

import ast
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src" / "marketplace" / "application" / "auth_material.py"
DOC = ROOT / "docs" / "m17-5g-auth-material.md"

UNSELECTED_ENTRY_POINTS = (
    ROOT / "src" / "marketplace" / "application" / "__init__.py",
    ROOT / "src" / "marketplace" / "application" / "auth_session_asgi.py",
    ROOT / "tools" / "marketplace_localhost.py",
    ROOT / "web" / "app.js",
    ROOT / "android" / "app" / "src" / "main" / "java" / "org" / "opentrustlayer" / "marketplace" / "MainActivity.kt",
)


class M17AuthMaterialArtifactTests(unittest.TestCase):
    def test_only_standard_library_csprng_and_existing_auth_constants_are_imported(self):
        text = SOURCE.read_text(encoding="utf-8")
        tree = ast.parse(text)
        imported_modules: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported_modules.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imported_modules.add(node.module or "")
        self.assertEqual(imported_modules, {"__future__", "secrets", "typing", "auth"})
        self.assertIn("from secrets import token_bytes as _token_bytes", text)
        for forbidden in (
            "random",
            "uuid",
            "hashlib",
            "os.environ",
            "socket",
            "subprocess",
            "pathlib",
            "logging",
            "cryptography",
            "requests",
            "httpx",
            "urllib",
            "psycopg",
        ):
            self.assertNotIn(forbidden, text)

    def test_source_has_one_entropy_call_and_no_retry_or_fallback_control_flow(self):
        tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
        entropy_calls = [
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "_token_bytes"
        ]
        self.assertEqual(len(entropy_calls), 1)
        self.assertFalse(any(isinstance(node, (ast.For, ast.AsyncFor, ast.While, ast.Try)) for node in ast.walk(tree)))

    def test_concrete_source_is_stateless_and_unselected_by_runtime_or_clients(self):
        text = SOURCE.read_text(encoding="utf-8")
        self.assertIn("__slots__ = ()", text)
        self.assertNotIn("def __init__", text)
        for path in UNSELECTED_ENTRY_POINTS:
            self.assertTrue(path.is_file(), str(path))
            entry_text = path.read_text(encoding="utf-8")
            self.assertNotIn("auth_material", entry_text)
            self.assertNotIn("MarketplaceCredentialMaterialSource", entry_text)

    def test_later_optional_verifier_dependency_does_not_widen_this_profile(self):
        pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
        workflow = (ROOT / ".github" / "workflows" / "conformance.yml").read_text(encoding="utf-8")
        source = SOURCE.read_text(encoding="utf-8")
        self.assertIn("dependencies = []", pyproject)
        self.assertIn('auth-verify = ["cryptography==50.0.1"]', pyproject)
        self.assertNotIn("cryptography", source)
        self.assertNotIn("auth_material", pyproject)
        self.assertIn("unittest", (ROOT / "tools" / "conformance_gate.py").read_text(encoding="utf-8"))
        self.assertNotIn("auth_material", workflow)

    def test_document_records_exact_authority_and_non_authority_boundaries(self):
        self.assertTrue(DOC.is_file())
        text = DOC.read_text(encoding="utf-8")
        for marker in (
            "MARKETPLACE_APPLICATION_CREDENTIAL_MATERIAL_SOURCE_V1",
            "042b1c09e9c024d527c10d169b7cc2c1dc48f340",
            "standard-library OS CSPRNG",
            "exact 32-byte challenge",
            "exact 32-byte session-token",
            "no fallback PRNG",
            "no persistence",
            "no runtime activation",
            "no private-key handling",
            "no proof/signature creation",
            "no real proof verification",
            "no resolver/provider/network activity",
            "no Android build",
            "source-only rollback",
        ):
            self.assertIn(marker, text)


if __name__ == "__main__":
    unittest.main()
