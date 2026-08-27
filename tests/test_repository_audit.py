from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from repository_audit import (
    _REQUIRED_GOVERNANCE_FILES,
    _REQUIRED_REFERENCE_FILES,
    _REQUIRED_SECURITY_FILES,
    _REFERENCE_WRAPPERS,
    _audit_packaging,
    _audit_python,
    _audit_reference_adapter_layout,
    _audit_required_governance_files,
    _audit_required_security_files,
    _read_utf8,
)

_VALID_PYPROJECT = """[build-system]
requires = [\"setuptools==80.9.0\"]
build-backend = \"setuptools.build_meta\"

[project]
name = \"open-layer-marketplace\"
version = \"0.0.1.dev0\"
description = \"Experimental runtime\"
requires-python = \">=3.11\"
license = \"Apache-2.0\"
dependencies = []

[tool.setuptools.packages.find]
where = [\"src\"]
include = [\"marketplace*\"]
"""


class RepositoryAuditTests(unittest.TestCase):
    def test_utf8_bom_python_source_is_accepted_like_python_itself(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "module.py"
            path.write_bytes(b"\xef\xbb\xbfanswer = 42\n")
            findings: list[str] = []
            text = _read_utf8(path, findings)
            self.assertEqual(text, "answer = 42\n")
            self.assertEqual(findings, [])
            assert text is not None
            _audit_python(path, text, findings)
            self.assertEqual(findings, [])

    def test_governance_audit_reports_missing_required_files(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            findings: list[str] = []
            _audit_required_governance_files(Path(temp_dir), findings)
            expected = {
                f"MISSING_GOVERNANCE_FILE {path.as_posix()}"
                for path in _REQUIRED_GOVERNANCE_FILES
            }
            self.assertEqual(set(findings), expected)

    def test_governance_audit_accepts_complete_required_file_set(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            for relative_path in _REQUIRED_GOVERNANCE_FILES:
                path = root / relative_path
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("policy\n", encoding="utf-8")
            findings: list[str] = []
            _audit_required_governance_files(root, findings)
            self.assertEqual(findings, [])

    def test_security_audit_requires_m25_through_m28_runtime_reference_and_docs(self):
        expected = {
            Path("src/marketplace/runtime/network_policy.py"),
            Path("docs/federation-egress-security.md"),
            Path("src/marketplace/runtime/https_transport.py"),
            Path("src/marketplace/reference/transport_json_v1.py"),
            Path("docs/authorized-https-federation-transport.md"),
            Path("src/marketplace/runtime/record_retrieval.py"),
            Path("src/marketplace/reference/record_retrieval_v1.py"),
            Path("docs/immutable-record-retrieval.md"),
            Path("src/marketplace/runtime/page_hydration.py"),
            Path("docs/bounded-federation-page-hydration.md"),
        }
        self.assertTrue(expected.issubset(set(_REQUIRED_SECURITY_FILES)))

        with tempfile.TemporaryDirectory() as temp_dir:
            findings: list[str] = []
            _audit_required_security_files(Path(temp_dir), findings)
            expected_findings = {
                f"MISSING_SECURITY_FILE {path.as_posix()}"
                for path in _REQUIRED_SECURITY_FILES
            }
            self.assertEqual(set(findings), expected_findings)

    def test_security_audit_accepts_complete_required_file_set(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            for relative_path in _REQUIRED_SECURITY_FILES:
                path = root / relative_path
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("security boundary\n", encoding="utf-8")
            findings: list[str] = []
            _audit_required_security_files(root, findings)
            self.assertEqual(findings, [])

    def test_reference_layout_includes_packaged_m8_and_m27_reusable_verifier_surface(self):
        self.assertIn(Path("src/marketplace/reference/federation_v1.py"), _REQUIRED_REFERENCE_FILES)
        self.assertIn(Path("src/marketplace/reference/transport_json_v1.py"), _REQUIRED_REFERENCE_FILES)
        self.assertIn(Path("src/marketplace/reference/record_retrieval_v1.py"), _REQUIRED_REFERENCE_FILES)
        self.assertIn(Path("tools/marketplace_federation_v1.py"), _REQUIRED_REFERENCE_FILES)
        self.assertIn(Path("tools/marketplace_federation_v1.py"), _REFERENCE_WRAPPERS)

    def test_reference_layout_requires_packaged_sources_and_tool_wrappers(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            findings: list[str] = []
            _audit_reference_adapter_layout(Path(temp_dir), findings)
            expected = {
                f"MISSING_REFERENCE_ADAPTER_FILE {path.as_posix()}"
                for path in _REQUIRED_REFERENCE_FILES
            }
            self.assertEqual(set(findings), expected)

    def test_reference_layout_accepts_thin_delegating_wrappers(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            for relative_path in _REQUIRED_REFERENCE_FILES:
                path = root / relative_path
                path.parent.mkdir(parents=True, exist_ok=True)
                if relative_path.parts[0] == "tools":
                    path.write_text("from marketplace.reference import record_v1\n", encoding="utf-8")
                else:
                    path.write_text("pass\n", encoding="utf-8")
            findings: list[str] = []
            _audit_reference_adapter_layout(root, findings)
            self.assertEqual(findings, [])

    def test_packaging_audit_accepts_distribution_boundary(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "pyproject.toml").write_text(_VALID_PYPROJECT, encoding="utf-8")
            findings: list[str] = []
            _audit_packaging(root, findings)
            self.assertEqual(findings, [])

    def test_packaging_audit_rejects_unreviewed_build_backend_version(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            text = _VALID_PYPROJECT.replace("setuptools==80.9.0", "setuptools>=77")
            (root / "pyproject.toml").write_text(text, encoding="utf-8")
            findings: list[str] = []
            _audit_packaging(root, findings)
            self.assertIn(
                "PYPROJECT_BUILD_REQUIRES MUST equal ['setuptools==80.9.0']",
                findings,
            )

    def test_packaging_audit_rejects_runtime_dependency(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            text = _VALID_PYPROJECT.replace("dependencies = []", "dependencies = [\"requests>=2\"]")
            (root / "pyproject.toml").write_text(text, encoding="utf-8")
            findings: list[str] = []
            _audit_packaging(root, findings)
            self.assertIn(
                "PYPROJECT_RUNTIME_DEPENDENCIES base runtime dependencies MUST remain an empty array",
                findings,
            )

    def test_packaging_audit_rejects_public_index_optional_dependency(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            text = _VALID_PYPROJECT.replace(
                "dependencies = []\n",
                "dependencies = []\n\n[project.optional-dependencies]\nreference = [\"open-layer-protocol==0.0.6.dev0\"]\n",
            )
            (root / "pyproject.toml").write_text(text, encoding="utf-8")
            findings: list[str] = []
            _audit_packaging(root, findings)
            self.assertIn(
                "PYPROJECT_OPTIONAL_DEPENDENCIES public-index optional dependencies are not permitted",
                findings,
            )

    def test_packaging_audit_rejects_console_entry_point(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            text = _VALID_PYPROJECT.replace(
                "dependencies = []\n",
                "dependencies = []\n\n[project.scripts]\nmarketplace-server = \"marketplace.server:main\"\n",
            )
            (root / "pyproject.toml").write_text(text, encoding="utf-8")
            findings: list[str] = []
            _audit_packaging(root, findings)
            self.assertIn(
                "PYPROJECT_SCRIPTS runtime console scripts are not permitted",
                findings,
            )

    def test_packaging_audit_rejects_package_root_outside_src(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            text = _VALID_PYPROJECT.replace('where = ["src"]', 'where = ["."]')
            (root / "pyproject.toml").write_text(text, encoding="utf-8")
            findings: list[str] = []
            _audit_packaging(root, findings)
            self.assertIn(
                "PYPROJECT_PACKAGE_ROOT package discovery MUST use where = ['src']",
                findings,
            )

    def test_packaging_audit_rejects_stable_version(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            text = _VALID_PYPROJECT.replace('version = "0.0.1.dev0"', 'version = "1.0.0"')
            (root / "pyproject.toml").write_text(text, encoding="utf-8")
            findings: list[str] = []
            _audit_packaging(root, findings)
            self.assertIn(
                "PYPROJECT_VERSION MUST be an experimental 0.0.N.devN version",
                findings,
            )


if __name__ == "__main__":
    unittest.main()
