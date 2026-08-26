from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from repository_audit import _REQUIRED_SECURITY_FILES, _audit_required_security_files


class FederationNetworkPolicyAuditTests(unittest.TestCase):
    def test_security_audit_requires_m25_runtime_module_and_documentation(self):
        self.assertEqual(
            set(_REQUIRED_SECURITY_FILES),
            {
                Path("src/marketplace/runtime/network_policy.py"),
                Path("docs/federation-egress-security.md"),
            },
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            findings: list[str] = []
            _audit_required_security_files(Path(temp_dir), findings)
            self.assertEqual(
                set(findings),
                {
                    "MISSING_SECURITY_FILE src/marketplace/runtime/network_policy.py",
                    "MISSING_SECURITY_FILE docs/federation-egress-security.md",
                },
            )

    def test_security_audit_accepts_complete_m25_artifact_set(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            for relative in _REQUIRED_SECURITY_FILES:
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("m25\n", encoding="utf-8")
            findings: list[str] = []
            _audit_required_security_files(root, findings)
            self.assertEqual(findings, [])


if __name__ == "__main__":
    unittest.main()
