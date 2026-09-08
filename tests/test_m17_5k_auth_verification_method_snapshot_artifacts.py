from __future__ import annotations

import ast
from pathlib import Path
import tomllib
import unittest


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src" / "marketplace" / "application" / "auth_verification_method_snapshot.py"
DOC = ROOT / "docs" / "m17-5k-auth-verification-method-snapshot.md"

UNSELECTED_ENTRY_POINTS = (
    ROOT / "src" / "marketplace" / "application" / "__init__.py",
    ROOT / "src" / "marketplace" / "application" / "auth.py",
    ROOT / "src" / "marketplace" / "application" / "auth_verifier_ed25519.py",
    ROOT / "src" / "marketplace" / "application" / "auth_session_asgi.py",
    ROOT / "tools" / "marketplace_localhost.py",
    ROOT / "web" / "index.html",
    ROOT / "web" / "app.js",
    ROOT / "web" / "client_session.js",
    ROOT / "android" / "app" / "src" / "main" / "java" / "org" / "opentrustlayer" / "marketplace" / "MainActivity.kt",
    ROOT / "android" / "app" / "src" / "main" / "java" / "org" / "opentrustlayer" / "marketplace" / "MarketplaceClientSession.kt",
)


class M17AuthVerificationMethodSnapshotArtifactTests(unittest.TestCase):
    def test_source_has_only_local_immutable_data_structure_imports(self):
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
            {
                "__future__",
                "dataclasses",
                "re",
                "types",
                "typing",
            },
        )
        self.assertIn("@dataclass(frozen=True, slots=True)", text)
        self.assertIn("MappingProxyType(copied)", text)
        self.assertIn("__slots__ = (\"_entries\",)", text)

    def test_source_has_no_crypto_private_key_resolution_io_or_refresh_authority(self):
        text = SOURCE.read_text(encoding="utf-8")
        for forbidden in (
            "cryptography.",
            "Ed25519PrivateKey",
            "private_key",
            "sign(",
            "sign_authentication_proof",
            "secrets",
            "random",
            "os.environ",
            "pathlib",
            "socket",
            "subprocess",
            "requests",
            "httpx",
            "urllib",
            "psycopg",
            "keyring",
            "keystore",
            "WebCrypto",
            "logging",
            "print(",
            "resolve(",
            "resolver",
            "provider",
            "filesystem",
            "database",
            "refresh(",
            "reload(",
        ):
            self.assertNotIn(forbidden, text)

    def test_snapshot_exposes_only_constructor_key_lookup_and_binding_decision(self):
        tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
        snapshot = next(
            node
            for node in tree.body
            if isinstance(node, ast.ClassDef)
            and node.name == "MarketplaceAuthenticationVerificationMethodSnapshot"
        )
        methods = [
            node.name
            for node in snapshot.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        ]
        self.assertEqual(methods, ["__init__", "verification_key_bytes", "verify"])
        for forbidden in ("add", "update", "delete", "refresh", "reload", "rotate"):
            self.assertNotIn(forbidden, methods)

    def test_snapshot_is_unselected_by_auth_runtime_web_and_android(self):
        for path in UNSELECTED_ENTRY_POINTS:
            self.assertTrue(path.is_file(), str(path))
            text = path.read_text(encoding="utf-8")
            self.assertNotIn("auth_verification_method_snapshot", text, str(path))
            self.assertNotIn("MarketplaceAuthenticationVerificationMethodSnapshot", text, str(path))
            self.assertNotIn("AuthenticationVerificationMethodEvidence", text, str(path))

    def test_dependency_workflow_repository_audit_and_olp_pin_remain_reviewed(self):
        pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
        project = pyproject["project"]
        self.assertEqual(project["dependencies"], [])
        self.assertEqual(
            project["optional-dependencies"],
            {
                "postgres": ["psycopg[binary]==3.3.5"],
                "local-server": ["uvicorn==0.52.4", "click==8.5.0", "h11==0.16.0"],
                "auth-verify": ["cryptography==50.0.1"],
            },
        )

        workflow = (ROOT / ".github" / "workflows" / "conformance.yml").read_text(encoding="utf-8")
        exact_install = (
            '& $env:MARKETPLACE_CI_PYTHON -m pip install --disable-pip-version-check "cryptography==50.0.1"'
        )
        self.assertEqual(workflow.count(exact_install), 1)
        self.assertIn("runs-on: [self-hosted, Windows, X64, marketplace-ci]", workflow)
        self.assertIn("permissions:\n  contents: read", workflow)
        self.assertEqual(workflow.count("persist-credentials: false"), 2)

        repository_audit = (ROOT / "tools" / "repository_audit.py").read_text(encoding="utf-8")
        self.assertIn('*repo_root.glob("src/**/*.py")', repository_audit)
        self.assertEqual(
            (ROOT / "conformance" / "olp-source-pin.txt").read_text(encoding="ascii").strip(),
            "41b768e50b6cb9cc8e516ad7b6c40969f9ed7b6c",
        )

    def test_wheel_gate_requires_new_snapshot_module(self):
        package_gate = (ROOT / "tools" / "package_artifact_gate.py").read_text(encoding="utf-8")
        package_tests = (ROOT / "tests" / "test_package_artifact_gate.py").read_text(encoding="utf-8")
        member = "marketplace/application/auth_verification_method_snapshot.py"
        self.assertEqual(package_gate.count(f'\"{member}\"'), 1)
        self.assertGreaterEqual(package_tests.count(member), 2)
        self.assertIn("test_missing_auth_verification_method_snapshot_member_is_rejected", package_tests)

    def test_document_records_exact_high_risk_scope_and_rollback_boundary(self):
        self.assertTrue(DOC.is_file())
        text = DOC.read_text(encoding="utf-8")
        for marker in (
            "MARKETPLACE_APPLICATION_AUTH_VERIFICATION_METHOD_SNAPSHOT_V1",
            "9721f352d3cb4a065e72ed01d8bc968aa17330ac",
            "Issue #280",
            "HIGH",
            "256",
            "[valid_from, valid_until)",
            "same snapshot instance",
            "no controller inference",
            "no external resolver",
            "no private-key",
            "no runtime activation",
            "source-only rollback",
            "tools/package_artifact_gate.py",
            "tests/test_package_artifact_gate.py",
        ):
            self.assertIn(marker, text)


if __name__ == "__main__":
    unittest.main()
