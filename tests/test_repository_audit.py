from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from repository_audit import (
    _REQUIRED_GOVERNANCE_FILES,
    _audit_python,
    _audit_required_governance_files,
    _read_utf8,
)


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


if __name__ == "__main__":
    unittest.main()
