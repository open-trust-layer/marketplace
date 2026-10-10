from __future__ import annotations

import ast
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src" / "marketplace" / "reference" / "auth_enrollment_nonce_material_v1.py"
TESTS = ROOT / "tests" / "test_m17_6p_reference_auth_enrollment_nonce_material.py"
ARTIFACTS = ROOT / "tests" / "test_m17_6p_reference_auth_enrollment_nonce_material_artifacts.py"
DOC = ROOT / "docs" / "m17-6p-reference-auth-enrollment-nonce-material.md"
PACKAGE_GATE = ROOT / "tools" / "package_artifact_gate.py"
PACKAGE_TESTS = ROOT / "tests" / "test_package_artifact_gate.py"

NONSELECTING = (
    ROOT / "src" / "marketplace" / "application" / "auth_enrollment_nonce.py",
    ROOT / "src" / "marketplace" / "reference" / "auth_enrollment_launch_v1.py",
    ROOT / "src" / "marketplace" / "application" / "auth_enrollment_runtime_server.py",
    ROOT / "src" / "marketplace" / "application" / "uvicorn_provider.py",
    ROOT / "web" / "auth_bootstrap.js",
    ROOT / "android" / "app" / "src" / "main" / "java" / "org" / "opentrustlayer" / "marketplace" / "MainActivity.kt",
)


class M176PReferenceAuthenticationEnrollmentNonceMaterialArtifactTests(unittest.TestCase):
    def test_exact_m17_6p_artifacts_exist(self) -> None:
        for path in (SOURCE, TESTS, ARTIFACTS, DOC, PACKAGE_GATE, PACKAGE_TESTS):
            self.assertTrue(path.is_file(), str(path))

    def test_source_uses_only_standard_library_csprng_and_existing_nonce_bound(self) -> None:
        text = SOURCE.read_text(encoding="utf-8")
        tree = ast.parse(text)
        imported_modules: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported_modules.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imported_modules.add(node.module or "")
        self.assertEqual(
            imported_modules,
            {"__future__", "secrets", "typing", "application.auth_enrollment_coordination"},
        )
        self.assertIn("from secrets import token_bytes as _token_bytes", text)
        self.assertIn("AUTH_ENROLLMENT_NONCE_BYTES", text)
        self.assertIn(
            '"MARKETPLACE_REFERENCE_AUTHENTICATION_ENROLLMENT_NONCE_MATERIAL_V1"',
            text,
        )

    def test_source_has_one_entropy_call_and_no_retry_fallback_or_state(self) -> None:
        text = SOURCE.read_text(encoding="utf-8")
        tree = ast.parse(text)
        entropy_calls = [
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "_token_bytes"
        ]
        self.assertEqual(len(entropy_calls), 1)
        self.assertFalse(
            any(isinstance(node, (ast.For, ast.AsyncFor, ast.While)) for node in ast.walk(tree))
        )
        self.assertIn("__slots__ = ()", text)
        source_class = next(
            node
            for node in tree.body
            if isinstance(node, ast.ClassDef)
            and node.name
            == "MarketplaceReferenceAuthenticationEnrollmentNonceMaterialSource"
        )
        self.assertFalse(
            any(
                isinstance(node, ast.FunctionDef) and node.name == "__init__"
                for node in source_class.body
            )
        )
        for marker in (
            "open(",
            "Path(",
            "os.environ",
            "getenv(",
            "socket",
            "subprocess",
            "threading",
            "multiprocessing",
            "psycopg",
            "sqlite",
            "logging",
            "private_key",
            "Ed25519PrivateKey",
        ):
            self.assertNotIn(marker, text)

    def test_existing_authority_reference_runtime_web_and_android_do_not_select_p(self) -> None:
        for path in NONSELECTING:
            self.assertTrue(path.is_file(), str(path))
            text = path.read_text(encoding="utf-8")
            self.assertNotIn("auth_enrollment_nonce_material_v1", text, str(path))
            self.assertNotIn(
                "MarketplaceReferenceAuthenticationEnrollmentNonceMaterialSource",
                text,
                str(path),
            )
            self.assertNotIn(
                "MARKETPLACE_REFERENCE_AUTHENTICATION_ENROLLMENT_NONCE_MATERIAL_V1",
                text,
                str(path),
            )

    def test_package_controls_require_new_reference_module(self) -> None:
        gate = PACKAGE_GATE.read_text(encoding="utf-8")
        tests = PACKAGE_TESTS.read_text(encoding="utf-8")
        member = "marketplace/reference/auth_enrollment_nonce_material_v1.py"
        self.assertEqual(gate.count(f'"{member}"'), 1)
        self.assertGreaterEqual(tests.count(member), 2)

    def test_document_records_csprng_unselected_moon_and_rollback_boundaries(self) -> None:
        text = DOC.read_text(encoding="utf-8")
        for marker in (
            "MARKETPLACE_REFERENCE_AUTHENTICATION_ENROLLMENT_NONCE_MATERIAL_V1",
            "HIGH security/privacy",
            "standard-library OS CSPRNG",
            "exact 32-byte",
            "unselected",
            "Moon Company",
            "source-only rollback",
        ):
            self.assertIn(marker, text)


if __name__ == "__main__":
    unittest.main()
