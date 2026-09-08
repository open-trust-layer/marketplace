from __future__ import annotations

import ast
from pathlib import Path
import tomllib
import unittest


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src" / "marketplace" / "application" / "auth_verification_method_evidence.py"
DOC = ROOT / "docs" / "m17-5l-auth-verification-method-evidence.md"

UNSELECTED_ENTRY_POINTS = (
    ROOT / "src" / "marketplace" / "application" / "__init__.py",
    ROOT / "src" / "marketplace" / "application" / "auth.py",
    ROOT / "src" / "marketplace" / "application" / "auth_verifier_ed25519.py",
    ROOT / "src" / "marketplace" / "application" / "auth_verification_method_snapshot.py",
    ROOT / "src" / "marketplace" / "application" / "auth_session_asgi.py",
    ROOT / "tools" / "marketplace_localhost.py",
    ROOT / "web" / "index.html",
    ROOT / "web" / "app.js",
    ROOT / "web" / "client_session.js",
    ROOT / "android" / "app" / "src" / "main" / "java" / "org" / "opentrustlayer" / "marketplace" / "MainActivity.kt",
    ROOT / "android" / "app" / "src" / "main" / "java" / "org" / "opentrustlayer" / "marketplace" / "MarketplaceClientSession.kt",
)


class M17AuthVerificationMethodEvidenceArtifactTests(unittest.TestCase):
    def test_source_import_boundary_is_stdlib_plus_existing_snapshot_only(self):
        tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
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
                "auth_verification_method_snapshot",
                "base64",
                "dataclasses",
                "hashlib",
                "json",
                "re",
                "typing",
            },
        )
        text = SOURCE.read_text(encoding="utf-8")
        self.assertEqual(text.count("hashlib.sha256("), 1)
        self.assertNotIn("cryptography", text)
        self.assertNotIn("Ed25519PrivateKey", text)

    def test_source_has_no_acquisition_resolution_io_persistence_or_signing_authority(self):
        text = SOURCE.read_text(encoding="utf-8")
        for forbidden in (
            "socket",
            "subprocess",
            "requests",
            "httpx",
            "urllib",
            "os.environ",
            "pathlib",
            "psycopg",
            "keyring",
            "open(",
            "read_text(",
            "write_text(",
            "print(",
            "logging",
            "private_key",
            "sign_authentication_proof",
            "Ed25519PrivateKey",
            "WebCrypto",
        ):
            self.assertNotIn(forbidden, text)

    def test_source_exposes_no_refresh_retry_or_network_provider_surface(self):
        tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
        methods = [node.name for node in ast.walk(tree) if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))]
        for forbidden in ("refresh", "reload", "retry", "fetch", "resolve", "download", "request"):
            self.assertNotIn(forbidden, methods)

    def test_evidence_intake_is_unselected_by_runtime_web_and_android(self):
        for path in UNSELECTED_ENTRY_POINTS:
            self.assertTrue(path.is_file(), str(path))
            text = path.read_text(encoding="utf-8")
            self.assertNotIn("auth_verification_method_evidence", text, str(path))
            self.assertNotIn("MarketplaceAuthenticationVerificationMethodEvidenceEnvelope", text, str(path))
            self.assertNotIn("materialize_marketplace_authentication_verification_method_snapshot", text, str(path))

    def test_dependency_workflow_repository_audit_and_olp_pin_remain_reviewed(self):
        project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
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
        self.assertIn("runs-on: [self-hosted, Windows, X64, marketplace-ci]", workflow)
        self.assertEqual(workflow.count("persist-credentials: false"), 2)
        repository_audit = (ROOT / "tools" / "repository_audit.py").read_text(encoding="utf-8")
        self.assertIn('*repo_root.glob("src/**/*.py")', repository_audit)
        self.assertEqual(
            (ROOT / "conformance" / "olp-source-pin.txt").read_text(encoding="ascii").strip(),
            "41b768e50b6cb9cc8e516ad7b6c40969f9ed7b6c",
        )

    def test_wheel_gate_requires_new_evidence_module(self):
        package_gate = (ROOT / "tools" / "package_artifact_gate.py").read_text(encoding="utf-8")
        package_tests = (ROOT / "tests" / "test_package_artifact_gate.py").read_text(encoding="utf-8")
        member = "marketplace/application/auth_verification_method_evidence.py"
        self.assertEqual(package_gate.count(f'\"{member}\"'), 1)
        self.assertGreaterEqual(package_tests.count(member), 2)
        self.assertIn("test_missing_auth_verification_method_evidence_member_is_rejected", package_tests)

    def test_document_records_exact_high_risk_scope_and_non_authority(self):
        text = DOC.read_text(encoding="utf-8")
        for marker in (
            "MARKETPLACE_APPLICATION_AUTH_VERIFICATION_METHOD_EVIDENCE_BUNDLE_V1",
            "8edd7c0d2e199e2a3d27de24f2946620b078406c",
            "Issue #282",
            "HIGH",
            "512 KiB",
            "16 KiB",
            "24-hour",
            "mkp1_",
            "digest",
            "authority",
            "no concrete trust verifier",
            "no network",
            "no runtime activation",
            "source-only rollback",
        ):
            self.assertIn(marker, text)


if __name__ == "__main__":
    unittest.main()
