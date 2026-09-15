from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "web" / "app.js"


class MarketplaceMvpProposalParentBindingTests(unittest.TestCase):
    def create_proposal_block(self) -> str:
        text = APP.read_text(encoding="utf-8")
        return text.split("async function createProposal(event) {", 1)[1].split(
            "\nfunction reviewedMvpText", 1
        )[0]

    def detail_block(self) -> str:
        text = APP.read_text(encoding="utf-8")
        return text.split("function renderDetail() {", 1)[1].split(
            "\nfunction renderResponseItems", 1
        )[0]

    def test_proposal_button_requires_reviewed_product_listing_subject(self):
        block = self.detail_block()
        self.assertIn(
            "responseButton.disabled = selectedProductListingSubjectUri(record) === null",
            block,
        )
    def test_submission_requires_selected_listing_before_any_api_call(self):
        block = self.create_proposal_block()
        self.assertIn(
            "const parentSubjectUri = selectedProductListingSubjectUri(state.selectedRecord)",
            block,
        )
        self.assertIn('"proposal.selectListing"', block)
        self.assertLess(block.index("parentSubjectUri === null"), block.index("apiFetch("))

    def test_submission_binds_exact_subject_before_any_api_call(self):
        block = self.create_proposal_block()
        self.assertIn(
            'const submittedSubjectUri = reviewedProposalUri(byId("proposal-subject-uri").value)',
            block,
        )
        self.assertIn("submittedSubjectUri !== parentSubjectUri", block)
        self.assertIn('"proposal.subjectMismatch"', block)
        self.assertLess(block.index("submittedSubjectUri !== parentSubjectUri"), block.index("apiFetch("))

    def test_parent_binding_is_exact_not_normalized(self):
        block = self.create_proposal_block()
        self.assertIn("submittedSubjectUri !== parentSubjectUri", block)
        self.assertNotIn("toLowerCase", block)
        self.assertNotIn("toLocaleLowerCase", block)
        self.assertNotIn("normalize(", block)

    def test_parent_binding_messages_are_bilingual(self):
        text = APP.read_text(encoding="utf-8")
        self.assertIn("Select a product listing with one valid subject before creating a Proposal.", text)
        self.assertIn("Перед созданием предложения выберите объявление с одним корректным предметом.", text)
        self.assertIn("Proposal subject must exactly match the selected product listing subject {subjectUri}.", text)
        self.assertIn("Предмет предложения должен точно совпадать с предметом выбранного объявления {subjectUri}.", text)


if __name__ == "__main__":
    unittest.main()
