from __future__ import annotations

import ast
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src" / "marketplace" / "reference" / "auth_enrollment_approval_policy_v1.py"
TESTS = ROOT / "tests" / "test_m17_6r_reference_auth_enrollment_approval_policy.py"
ARTIFACTS = ROOT / "tests" / "test_m17_6r_reference_auth_enrollment_approval_policy_artifacts.py"
DOC = ROOT / "docs" / "m17-6r-reference-auth-enrollment-approval-policy.md"
PACKAGE_GATE = ROOT / "tools" / "package_artifact_gate.py"
PACKAGE_TESTS = ROOT / "tests" / "test_package_artifact_gate.py"

NONSELECTING = (
    ROOT / "src" / "marketplace" / "reference" / "auth_enrollment_launch_v1.py",
    ROOT / "src" / "marketplace" / "reference" / "auth_enrollment_nonce_authority_v1.py",
    ROOT / "src" / "marketplace" / "application" / "auth_enrollment_runtime_server.py",
    ROOT / "src" / "marketplace" / "application" / "uvicorn_provider.py",
    ROOT / "web" / "auth_bootstrap.js",
    ROOT / "android" / "app" / "src" / "main" / "java" / "org" / "opentrustlayer" / "marketplace" / "MainActivity.kt",
)


class M176RReferenceAuthenticationEnrollmentApprovalPolicyArtifactTests(unittest.TestCase):
    def test_exact_m17_6r_artifacts_exist(self) -> None:
        for path in (SOURCE, TESTS, ARTIFACTS, DOC, PACKAGE_GATE, PACKAGE_TESTS):
            self.assertTrue(path.is_file(), str(path))

    def test_source_imports_only_reviewed_validation_dependencies(self) -> None:
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
                "application.auth_enrollment_authority",
                "application.auth_verification_method_evidence",
            },
        )
        self.assertIn(
            '"MARKETPLACE_REFERENCE_AUTHENTICATION_ENROLLMENT_APPROVAL_POLICY_V1"',
            text,
        )
        self.assertIn(
            "REFERENCE_AUTH_ENROLLMENT_APPROVAL_MAX_BINDINGS: Final = AUTH_EVIDENCE_MAX_ENTRIES",
            text,
        )

    def test_source_uses_exact_match_only_and_no_normalization(self) -> None:
        text = SOURCE.read_text(encoding="utf-8")
        for marker in (
            "binding.principal == principal",
            "binding.verification_method == verification_method",
            "binding.public_key == public_key",
            "binding.authority == authority",
            "return True",
            "return False",
        ):
            self.assertIn(marker, text)
        for marker in (
            ".lower(",
            ".upper(",
            ".casefold(",
            ".strip(",
            ".startswith(",
            ".endswith(",
            "fnmatch",
            "wildcard",
        ):
            self.assertNotIn(marker, text)

    def test_source_has_no_attestor_signer_nonce_runtime_configuration_or_external_io(self) -> None:
        text = SOURCE.read_text(encoding="utf-8")
        for marker in (
            "AuthenticationEnrollmentAuthorityAttestor",
            "attest_authentication_enrollment",
            "Ed25519PrivateKey",
            "private_key",
            "auth_enrollment_nonce",
            "secrets",
            "token_bytes",
            "time.",
            "datetime",
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
        ):
            self.assertNotIn(marker, text)

    def test_existing_launch_nonce_runtime_web_and_android_do_not_select_r(self) -> None:
        for path in NONSELECTING:
            self.assertTrue(path.is_file(), str(path))
            text = path.read_text(encoding="utf-8")
            self.assertNotIn("auth_enrollment_approval_policy_v1", text, str(path))
            self.assertNotIn(
                "MarketplaceReferenceAuthenticationEnrollmentApprovalPolicy",
                text,
                str(path),
            )
            self.assertNotIn(
                "MARKETPLACE_REFERENCE_AUTHENTICATION_ENROLLMENT_APPROVAL_POLICY_V1",
                text,
                str(path),
            )

    def test_package_controls_require_new_reference_module(self) -> None:
        gate = PACKAGE_GATE.read_text(encoding="utf-8")
        tests = PACKAGE_TESTS.read_text(encoding="utf-8")
        member = "marketplace/reference/auth_enrollment_approval_policy_v1.py"
        self.assertEqual(gate.count(f'"{member}"'), 1)
        self.assertGreaterEqual(tests.count(member), 2)

    def test_document_records_exact_match_nonselection_moon_and_rollback_boundaries(self) -> None:
        text = DOC.read_text(encoding="utf-8")
        for marker in (
            "MARKETPLACE_REFERENCE_AUTHENTICATION_ENROLLMENT_APPROVAL_POLICY_V1",
            "HIGH security/privacy",
            "exact-match",
            "256",
            "unselected",
            "Moon Company",
            "source-only rollback",
        ):
            self.assertIn(marker, text)


if __name__ == "__main__":
    unittest.main()
