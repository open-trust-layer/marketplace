from __future__ import annotations

import ast
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src" / "marketplace" / "reference" / "auth_enrollment_nonce_authority_v1.py"
TESTS = ROOT / "tests" / "test_m17_6q_reference_auth_enrollment_nonce_authority.py"
ARTIFACTS = ROOT / "tests" / "test_m17_6q_reference_auth_enrollment_nonce_authority_artifacts.py"
DOC = ROOT / "docs" / "m17-6q-reference-auth-enrollment-nonce-authority.md"
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


class M176QReferenceAuthenticationEnrollmentNonceAuthorityArtifactTests(unittest.TestCase):
    def test_exact_m17_6q_artifacts_exist(self) -> None:
        for path in (SOURCE, TESTS, ARTIFACTS, DOC, PACKAGE_GATE, PACKAGE_TESTS):
            self.assertTrue(path.is_file(), str(path))

    def test_source_imports_only_composition_dependencies_and_no_entropy_primitive(self) -> None:
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
                "typing",
                "application.auth_enrollment_nonce",
                "auth_enrollment_nonce_material_v1",
            },
        )
        self.assertNotIn("secrets", text)
        self.assertNotIn("token_bytes", text)
        self.assertIn(
            '"MARKETPLACE_REFERENCE_AUTHENTICATION_ENROLLMENT_NONCE_AUTHORITY_V1"',
            text,
        )

    def test_source_constructs_exactly_one_p_source_and_one_h_authority(self) -> None:
        text = SOURCE.read_text(encoding="utf-8")
        tree = ast.parse(text)
        calls = [
            node.func.id
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id
            in {
                "MarketplaceReferenceAuthenticationEnrollmentNonceMaterialSource",
                "MarketplaceAuthenticationEnrollmentNonceAuthority",
            }
        ]
        self.assertEqual(
            calls.count(
                "MarketplaceReferenceAuthenticationEnrollmentNonceMaterialSource"
            ),
            1,
        )
        self.assertEqual(
            calls.count("MarketplaceAuthenticationEnrollmentNonceAuthority"),
            1,
        )
        for marker in (
            "self.nonce_authority._nonce_bytes",
            "self.material_source",
            "self.nonce_authority._outstanding != {}",
            "self.nonce_authority._spent != {}",
        ):
            self.assertIn(marker, text)

    def test_source_has_no_runtime_persistence_policy_signing_or_external_io(self) -> None:
        text = SOURCE.read_text(encoding="utf-8")
        for marker in (
            "run_marketplace_authentication_enrollment_foreground",
            "UvicornLoopbackServerProvider",
            "socket",
            "open(",
            "Path(",
            "os.environ",
            "getenv(",
            "subprocess",
            "psycopg",
            "sqlite",
            "AuthenticationEnrollmentApprovalPolicy",
            "AuthenticationEnrollmentAuthorityAttestor",
            "private_key",
            "Ed25519PrivateKey",
            "http",
            "asgi",
        ):
            self.assertNotIn(marker, text)

    def test_existing_launch_runtime_web_and_android_do_not_select_q(self) -> None:
        for path in NONSELECTING:
            self.assertTrue(path.is_file(), str(path))
            text = path.read_text(encoding="utf-8")
            self.assertNotIn("auth_enrollment_nonce_authority_v1", text, str(path))
            self.assertNotIn(
                "build_reference_authentication_enrollment_nonce_authority",
                text,
                str(path),
            )
            self.assertNotIn(
                "MARKETPLACE_REFERENCE_AUTHENTICATION_ENROLLMENT_NONCE_AUTHORITY_V1",
                text,
                str(path),
            )

    def test_package_controls_require_new_reference_module(self) -> None:
        gate = PACKAGE_GATE.read_text(encoding="utf-8")
        tests = PACKAGE_TESTS.read_text(encoding="utf-8")
        member = "marketplace/reference/auth_enrollment_nonce_authority_v1.py"
        self.assertEqual(gate.count(f'"{member}"'), 1)
        self.assertGreaterEqual(tests.count(member), 2)

    def test_document_records_zero_entropy_unselected_moon_and_rollback_boundaries(self) -> None:
        text = DOC.read_text(encoding="utf-8")
        for marker in (
            "MARKETPLACE_REFERENCE_AUTHENTICATION_ENROLLMENT_NONCE_AUTHORITY_V1",
            "HIGH security/privacy",
            "zero entropy",
            "P → H",
            "unselected",
            "Moon Company",
            "source-only rollback",
        ):
            self.assertIn(marker, text)


if __name__ == "__main__":
    unittest.main()
