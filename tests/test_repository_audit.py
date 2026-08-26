from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from repository_audit import (
    _REQUIRED_GOVERNANCE_FILES,
    _audit_packaging,
    _audit_python,
    _audit_required_governance_files,
    _read_utf8,
)

_VALID_PYPROJECT = """[build-system]
requires = [\"setuptools>=77\"]
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

    def test_packaging_audit_accepts_m21_distribution_boundary(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "pyproject.toml").write_text(_VALID_PYPROJECT, encoding="utf-8")
            findings: list[str] = []
            _audit_packaging(root, findings)
            self.assertEqual(findings, [])

    def test_packaging_audit_rejects_runtime_dependency(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            text = _VALID_PYPROJECT.replace("dependencies = []", "dependencies = [\"requests>=2\"]")
            (root / "pyproject.toml").write_text(text, encoding="utf-8")
            findings: list[str] = []
            _audit_packaging(root, findings)
            self.assertIn(
                "PYPROJECT_RUNTIME_DEPENDENCIES MUST remain an empty array in M21",
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
                "PYPROJECT_SCRIPTS runtime console scripts are not permitted in M21",
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
