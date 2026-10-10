from __future__ import annotations

import ast
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = (
    ROOT
    / "src"
    / "marketplace"
    / "reference"
    / "auth_enrollment_runtime_uvicorn_v1.py"
)
TESTS = ROOT / "tests" / "test_m17_6w_reference_auth_enrollment_runtime_uvicorn.py"
ARTIFACTS = (
    ROOT
    / "tests"
    / "test_m17_6w_reference_auth_enrollment_runtime_uvicorn_artifacts.py"
)
DOC = ROOT / "docs" / "m17-6w-reference-auth-enrollment-runtime-uvicorn.md"
PACKAGE_GATE = ROOT / "tools" / "package_artifact_gate.py"
PACKAGE_TESTS = ROOT / "tests" / "test_package_artifact_gate.py"

NONSELECTING = (
    ROOT
    / "src"
    / "marketplace"
    / "reference"
    / "auth_enrollment_launch_policy_nonce_ed25519_v1.py",
    ROOT
    / "src"
    / "marketplace"
    / "reference"
    / "auth_enrollment_runtime_v1.py",
    ROOT / "src" / "marketplace" / "application" / "uvicorn_provider.py",
    ROOT / "web" / "auth_bootstrap.js",
    ROOT
    / "android"
    / "app"
    / "src"
    / "main"
    / "java"
    / "org"
    / "opentrustlayer"
    / "marketplace"
    / "MainActivity.kt",
)


class M176WReferenceAuthenticationEnrollmentRuntimeUvicornArtifactTests(
    unittest.TestCase
):
    def test_exact_m17_6w_artifacts_exist(self) -> None:
        for path in (SOURCE, TESTS, ARTIFACTS, DOC, PACKAGE_GATE, PACKAGE_TESTS):
            self.assertTrue(path.is_file(), str(path))

    def test_source_imports_only_exact_u_v_token_and_uvicorn_provider(self) -> None:
        text = SOURCE.read_text(encoding="utf-8")
        tree = ast.parse(text)
        modules: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                modules.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                modules.add(node.module or "")
        self.assertEqual(
            modules,
            {
                "__future__",
                "typing",
                "application.auth_enrollment_runtime_server",
                "application.uvicorn_provider",
                "auth_enrollment_launch_policy_nonce_ed25519_v1",
                "auth_enrollment_runtime_v1",
            },
        )

    def test_source_reuses_exact_token_constructs_provider_once_and_calls_v_once(
        self,
    ) -> None:
        text = SOURCE.read_text(encoding="utf-8")
        tree = ast.parse(text)
        calls = [
            node.func.id
            for node in ast.walk(tree)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
        ]
        self.assertEqual(calls.count("UvicornLoopbackServerProvider"), 1)
        self.assertEqual(
            calls.count("run_reference_authentication_enrollment_foreground"),
            1,
        )
        string_literals = {
            node.value
            for node in ast.walk(tree)
            if isinstance(node, ast.Constant) and isinstance(node.value, str)
        }
        self.assertNotIn(
            "EXECUTE_ONE_AUTHENTICATION_ENROLLMENT_MARKETPLACE_LOOPBACK_SERVER",
            string_literals,
        )
        self.assertIn(
            "EXECUTE_ONE_AUTHENTICATION_ENROLLMENT_MARKETPLACE_LOOPBACK_SERVER",
            text,
        )
        self.assertIn("reference=reference", text)
        self.assertIn("provider=provider", text)
        self.assertIn("execute_token=execute_token", text)

    def test_source_performs_no_provider_discovery_or_external_io(self) -> None:
        text = SOURCE.read_text(encoding="utf-8")
        for marker in (
            "import_module",
            "socket",
            "open(",
            "Path(",
            "os.environ",
            "getenv(",
            "subprocess",
            "requests",
            "urlopen",
            "psycopg",
            "sqlite",
            "keyring",
            "vault",
            "HSM",
            "Ed25519PrivateKey",
            ".sign(",
            "token_bytes",
            "uvicorn.run",
        ):
            self.assertNotIn(marker, text)

    def test_existing_u_v_provider_web_and_android_do_not_select_w(self) -> None:
        for path in NONSELECTING:
            self.assertTrue(path.is_file(), str(path))
            text = path.read_text(encoding="utf-8")
            self.assertNotIn("auth_enrollment_runtime_uvicorn_v1", text, str(path))
            self.assertNotIn(
                "run_reference_authentication_enrollment_uvicorn_foreground",
                text,
                str(path),
            )
            self.assertNotIn(
                "MARKETPLACE_REFERENCE_AUTHENTICATION_ENROLLMENT_UVICORN_RUNTIME_V1",
                text,
                str(path),
            )

    def test_package_controls_require_new_reference_module(self) -> None:
        gate = PACKAGE_GATE.read_text(encoding="utf-8")
        tests = PACKAGE_TESTS.read_text(encoding="utf-8")
        member = "marketplace/reference/auth_enrollment_runtime_uvicorn_v1.py"
        self.assertEqual(gate.count(f'"{member}"'), 1)
        self.assertGreaterEqual(tests.count(member), 2)

    def test_document_records_provider_selection_nonselection_and_rollback(
        self,
    ) -> None:
        text = DOC.read_text(encoding="utf-8")
        for marker in (
            "MARKETPLACE_REFERENCE_AUTHENTICATION_ENROLLMENT_UVICORN_RUNTIME_V1",
            "HIGH security/privacy",
            "U → W → V → N",
            "exact existing execution token",
            "real Uvicorn is never run",
            "unselected",
            "Moon Company",
            "source-only rollback",
        ):
            self.assertIn(marker, text)


if __name__ == "__main__":
    unittest.main()
