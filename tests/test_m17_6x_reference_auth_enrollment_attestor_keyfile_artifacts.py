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
    / "auth_enrollment_attestor_keyfile_v1.py"
)
TESTS = (
    ROOT
    / "tests"
    / "test_m17_6x_reference_auth_enrollment_attestor_keyfile.py"
)
ARTIFACTS = (
    ROOT
    / "tests"
    / "test_m17_6x_reference_auth_enrollment_attestor_keyfile_artifacts.py"
)
DOC = ROOT / "docs" / "m17-6x-reference-auth-enrollment-attestor-keyfile.md"
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
    ROOT
    / "src"
    / "marketplace"
    / "reference"
    / "auth_enrollment_runtime_uvicorn_v1.py",
    ROOT / "tools" / "marketplace_localhost.py",
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


class M176XReferenceAuthenticationEnrollmentAttestorKeyfileArtifactTests(
    unittest.TestCase
):
    def test_exact_m17_6x_artifacts_exist(self) -> None:
        for path in (SOURCE, TESTS, ARTIFACTS, DOC, PACKAGE_GATE, PACKAGE_TESTS):
            self.assertTrue(path.is_file(), str(path))

    def test_source_imports_only_filesystem_primitives_and_exact_t(self) -> None:
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
                "os",
                "stat",
                "typing",
                "auth_enrollment_attestor_ed25519_v1",
            },
        )

    def test_source_has_one_fixed_filename_one_open_and_exact_bounded_read(
        self,
    ) -> None:
        text = SOURCE.read_text(encoding="utf-8")
        self.assertEqual(
            text.count('"authentication-enrollment-ed25519.key"'),
            1,
        )
        self.assertEqual(text.count('open(path, "rb")'), 1)
        self.assertIn("handle.read(maximum + 1)", text)
        self.assertIn(
            "maximum = REFERENCE_AUTH_ENROLLMENT_ED25519_PRIVATE_KEY_BYTES",
            text,
        )
        self.assertEqual(
            text.count(
                "MarketplaceReferenceAuthenticationEnrollmentEd25519Attestor("
            ),
            1,
        )
        self.assertIn("private_key_bytes=private_key_bytes", text)
        self.assertIn("return attestor", text)

    def test_source_has_no_alternate_secret_source_generation_or_persistence(
        self,
    ) -> None:
        text = SOURCE.read_text(encoding="utf-8")
        for marker in (
            "os.environ",
            "getenv(",
            "expanduser",
            "glob",
            "Path(",
            "socket",
            "subprocess",
            "requests",
            "httpx",
            "urlopen",
            "psycopg",
            "sqlite",
            "keyring",
            "keystore",
            "vault",
            "HSM",
            "secrets",
            "random",
            "urandom",
            "generate",
            "derive",
            "export",
            "serialize",
            ".sign(",
            "logging.",
            "print(",
            '"wb"',
            '"ab"',
            "chmod",
            "chown",
            "unlink",
            "remove(",
            "rename(",
            "replace(",
        ):
            self.assertNotIn(marker, text)

    def test_existing_u_v_w_entrypoints_web_and_android_do_not_select_x(
        self,
    ) -> None:
        for path in NONSELECTING:
            self.assertTrue(path.is_file(), str(path))
            text = path.read_text(encoding="utf-8")
            self.assertNotIn("auth_enrollment_attestor_keyfile_v1", text, str(path))
            self.assertNotIn(
                "load_reference_authentication_enrollment_ed25519_attestor",
                text,
                str(path),
            )
            self.assertNotIn(
                "authentication-enrollment-ed25519.key",
                text,
                str(path),
            )

    def test_package_controls_require_x_reference_module(self) -> None:
        gate = PACKAGE_GATE.read_text(encoding="utf-8")
        tests = PACKAGE_TESTS.read_text(encoding="utf-8")
        member = "marketplace/reference/auth_enrollment_attestor_keyfile_v1.py"
        self.assertEqual(gate.count(f'"{member}"'), 1)
        self.assertGreaterEqual(tests.count(member), 2)

    def test_document_records_custody_nonselection_and_no_zeroization_claim(
        self,
    ) -> None:
        text = DOC.read_text(encoding="utf-8")
        for marker in (
            "MARKETPLACE_REFERENCE_AUTHENTICATION_ENROLLMENT_ED25519_KEYFILE_V1",
            "HIGH security/privacy",
            "authentication-enrollment-ed25519.key",
            "exactly 32 bytes",
            "synthetic non-secret",
            "immutable-byte zeroization is not claimed",
            "unselected",
            "Moon Company",
            "source-only rollback",
        ):
            self.assertIn(marker, text)


if __name__ == "__main__":
    unittest.main()
