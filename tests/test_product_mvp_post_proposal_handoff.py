from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "web" / "app.js"


class MarketplaceMvpPostProposalHandoffTests(unittest.TestCase):
    def _block(self):
        text = APP.read_text(encoding="utf-8")
        start = text.index("async function createProposal")
        end = text.index("function reviewedMvpText", start)
        return text[start:end]

    def test_proposal_acceptance_is_not_reclassified_when_refresh_fails(self):
        block = self._block()
        self.assertIn('"proposal.refreshFailed"', block)
        self.assertIn('"warning"', block)
        self.assertLess(block.index("await apiFetch"), block.index("await fullResync"))
        self.assertIn("return;", block)
        self.assertIn('"proposal.failed"', block)

    def test_successful_refresh_keeps_exact_parent_selected(self):
        block = self._block()
        self.assertIn("if (state.records.has(parentId))", block)
        self.assertIn("selectIntent(parentId);", block)
        self.assertIn('"proposal.acceptedRefreshed"', block)
        self.assertNotIn("selectIntent(createdId)", block)

    def test_missing_parent_after_refresh_is_warning_not_write_failure(self):
        block = self._block()
        self.assertIn('"proposal.parentGone"', block)
        self.assertEqual(block.count("await apiFetch("), 1)
        self.assertEqual(block.count("await fullResync();"), 1)


if __name__ == "__main__":
    unittest.main()
