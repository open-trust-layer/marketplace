from pathlib import Path
import unittest

from marketplace.application.proposal import BuyerRequestProposalDraft
from marketplace.reference.proposal_v1 import build_buyer_request_proposal_record


ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "web" / "app.js"


class MarketplaceMvpResponseSummaryTests(unittest.TestCase):
    def test_reference_proposal_shape_is_summary_compatible(self):
        record = build_buyer_request_proposal_record(
            BuyerRequestProposalDraft(
                buyer_principal="urn:open-layer-marketplace:demo:buyer",
                subject_uri="urn:open-layer-marketplace:demo:item:city-bicycle",
                action_uri="urn:open-layer-marketplace:demo:action:buy",
                parent_record_id="r1_" + "A" * 43,
            )
        )
        self.assertTrue(any(profile.endswith("/profile/proposal-v1") for profile in record.profiles))
        self.assertEqual(record.content["issuer"]["principal"], "urn:open-layer-marketplace:demo:buyer")
        self.assertEqual(record.content["subjects"][0]["uri"], "urn:open-layer-marketplace:demo:item:city-bicycle")
        self.assertEqual(record.content["action"]["id"], "urn:open-layer-marketplace:demo:action:buy")
    def test_web_summary_is_fail_closed_and_uses_synced_records_only(self):
        text = APP.read_text(encoding="utf-8")
        self.assertIn('profile.endsWith("/profile/proposal-v1")', text)
        self.assertIn("const issuer = record.content?.issuer", text)
        self.assertIn("subjects.length !== 1", text)
        self.assertIn("buyerPrincipal: reviewedProposalUri(issuer.principal)", text)
        self.assertIn("subjectUri: reviewedProposalUri(subject.uri)", text)
        self.assertIn("actionUri: reviewedProposalUri(action.id)", text)
        block = text.split("async function renderResponses(recordId) {", 1)[1].split("\nfunction selectIntent", 1)[0]
        self.assertEqual(block.count("apiFetch("), 1)
        self.assertIn("proposalResponseSummary(state.records.get(id))", block)
        self.assertIn("if (summary === null)", block)
        self.assertIn("item.textContent = id", block)

    def test_readable_summary_uses_text_nodes_and_preserves_click_through(self):
        text = APP.read_text(encoding="utf-8")
        block = text.split("async function renderResponses(recordId) {", 1)[1].split("\nfunction selectIntent", 1)[0]
        self.assertIn('title.textContent = "Buyer Proposal"', block)
        self.assertIn("Buyer ${summary.buyerPrincipal}", block)
        self.assertIn("Subject ${summary.subjectUri}", block)
        self.assertIn("Action ${summary.actionUri}", block)
        self.assertIn("Record ${id}", block)
        self.assertIn('item.addEventListener("click", () => void inspectIntent(id))', block)
        self.assertNotIn("innerHTML", block)


if __name__ == "__main__":
    unittest.main()
