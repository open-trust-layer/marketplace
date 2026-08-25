from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from repository_audit import _audit_python, _read_utf8


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


if __name__ == "__main__":
    unittest.main()
