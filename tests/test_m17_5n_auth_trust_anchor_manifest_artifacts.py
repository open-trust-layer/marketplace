from __future__ import annotations

import ast
from pathlib import Path
import tomllib
import unittest


ROOT = Path(__file__).resolve().parents[1]
SOURCE = (
    ROOT
    / "src"
    / "marketplace"
    / "application"
    / "auth_trust_anchor_manifest.py"
)
DOC = ROOT / "docs" / "m17-5n-auth-trust-anchor-manifest.md"

UNSELECTED_ENTRY_POINTS = (
    ROOT / "src" / "marketplace" / "application" / "__init__.py",
    ROOT / "src" / "marketplace" / "application" / "auth.py",
    ROOT / "src" / "marketplace" / "application" / "auth_session_asgi.py",
    ROOT / "src" / "marketplace" / "application" / "asgi.py",
    ROOT / "src" / "marketplace" / "runtime" / "composition.py",
    ROOT / "tools" / "marketplace_localhost.py",
    ROOT / "web" / "index.html",
    ROOT / "web" / "app.js",
    ROOT / "web" / "client_session.js",
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
    ROOT
    / "android"
    / "app"
    / "src"
    / "main"
    / "java"
    / "org"
    / "opentrustlayer"
    / "marketplace"
    / "MarketplaceClientSession.kt",
)


class M17AuthTrustAnchorManifestArtifactTests(unittest.TestCase):
    def test_source_imports_only_canonical_json_and_existing_m_l_contracts(self):
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
                "dataclasses",
                "json",
                "typing",
                "auth_evidence_trust_ed25519",
                "auth_verification_method_evidence",
            },
        )
        for forbidden in (
            "cryptography",
            "olp.crypto",
            "Ed25519PrivateKey",
            "private_key",
            "seed",
            "mnemonic",
            "passphrase",
            "def sign(",
            "secrets",
            "random",
            "keyring",
            "keystore",
        ):
            self.assertNotIn(forbidden, text)

    def test_source_has_no_acquisition_persistence_refresh_or_runtime_authority(self):
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
            "open(",
            "read_text(",
            "write_text(",
            "logging",
            "print(",
            "threading",
            "asyncio",
        ):
            self.assertNotIn(forbidden, text)
        tree = ast.parse(text)
        method_names = {
            node.name
            for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        }
        for forbidden_method in (
            "refresh",
            "reload",
            "retry",
            "fetch",
            "resolve",
            "download",
            "request",
            "replace",
            "rotate",
            "revoke",
        ):
            self.assertNotIn(forbidden_method, method_names)

    def test_dependency_workflow_and_package_boundary_are_unchanged(self):
        project = tomllib.loads(
            (ROOT / "pyproject.toml").read_text(encoding="utf-8")
        )["project"]
        self.assertEqual(project["dependencies"], [])
        self.assertEqual(
            project["optional-dependencies"]["auth-verify"],
            ["cryptography==50.0.1"],
        )
        workflow = (
            ROOT / ".github" / "workflows" / "conformance.yml"
        ).read_text(encoding="utf-8")
        exact_install = (
            '& $env:MARKETPLACE_CI_PYTHON -m pip install '
            '--disable-pip-version-check "cryptography==50.0.1"'
        )
        self.assertEqual(workflow.count(exact_install), 1)

        package_gate = (
            ROOT / "tools" / "package_artifact_gate.py"
        ).read_text(encoding="utf-8")
        package_tests = (
            ROOT / "tests" / "test_package_artifact_gate.py"
        ).read_text(encoding="utf-8")
        member = "marketplace/application/auth_trust_anchor_manifest.py"
        self.assertEqual(package_gate.count(f'"{member}"'), 1)
        self.assertGreaterEqual(package_tests.count(member), 2)
        self.assertIn(
            "test_missing_auth_trust_anchor_manifest_member_is_rejected",
            package_tests,
        )

    def test_manifest_intake_is_unselected_everywhere(self):
        for path in UNSELECTED_ENTRY_POINTS:
            self.assertTrue(path.is_file(), str(path))
            text = path.read_text(encoding="utf-8")
            self.assertNotIn("auth_trust_anchor_manifest", text, str(path))
            self.assertNotIn(
                "materialize_marketplace_authentication_evidence_trust_anchor_snapshot",
                text,
                str(path),
            )
            self.assertNotIn(
                "MARKETPLACE_APPLICATION_AUTH_TRUST_ANCHOR_MANIFEST_V1",
                text,
                str(path),
            )

    def test_predecessor_m_and_l_do_not_select_n(self):
        for path in (
            ROOT
            / "src"
            / "marketplace"
            / "application"
            / "auth_evidence_trust_ed25519.py",
            ROOT
            / "src"
            / "marketplace"
            / "application"
            / "auth_verification_method_evidence.py",
        ):
            text = path.read_text(encoding="utf-8")
            self.assertNotIn("auth_trust_anchor_manifest", text)

    def test_document_records_high_risk_six_file_scope_and_non_authority(self):
        text = DOC.read_text(encoding="utf-8")
        for marker in (
            "MARKETPLACE_APPLICATION_AUTH_TRUST_ANCHOR_MANIFEST_V1",
            "88450b90efe8869c5d697b66c880117ee315982d",
            "Issue #286",
            "HIGH",
            "256 KiB",
            "1..64",
            "mkp1_",
            "six-file",
            "no filesystem",
            "no network",
            "no persistence",
            "no runtime activation",
            "source-only rollback",
        ):
            self.assertIn(marker, text)


if __name__ == "__main__":
    unittest.main()
