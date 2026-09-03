from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
README = ROOT / "README.md"
DOC = ROOT / "docs" / "m17-1k-product-status-reconciliation.md"


class M17ProductStatusReconciliationTests(unittest.TestCase):
    def test_current_status_reports_application_foundation(self):
        text = README.read_text(encoding="utf-8-sig")
        first_status = next(line for line in text.splitlines() if line.startswith("**Project status:**"))
        self.assertIn("application-foundation implementation", first_status)
        self.assertNotIn("pre-implementation", first_status)

    def test_readme_records_m17_1a_through_j_without_production_claim(self):
        text = README.read_text(encoding="utf-8-sig")
        for marker in ("M17.1A", "M17.1B", "M17.1C", "M17.1D", "M17.1E", "M17.1F", "M17.1G", "M17.1H", "M17.1I", "M17.1J"):
            self.assertIn(marker, text)
        for marker in ("not a production deployment", "no live PostgreSQL activation", "no network/server activation", "Android build remains unproven"):
            self.assertIn(marker, text)

    def test_historical_preimplementation_claim_is_time_scoped(self):
        text = README.read_text(encoding="utf-8-sig")
        self.assertIn("At Milestone 12, the Marketplace remained experimental/pre-implementation:", text)

    def test_reconciliation_document_preserves_historical_context(self):
        self.assertTrue(DOC.is_file())
        text = DOC.read_text(encoding="utf-8-sig")
        self.assertIn("historical milestone context", text)
        self.assertIn("current repository status", text)
        self.assertIn("no new runtime authority", text)


if __name__ == "__main__":
    unittest.main()
