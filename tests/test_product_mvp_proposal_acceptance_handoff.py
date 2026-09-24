import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = (ROOT / "web" / "index.html").read_text(encoding="utf-8")
APP = (ROOT / "web" / "app.js").read_text(encoding="utf-8")


class ProductMvpProposalAcceptanceHandoffTests(unittest.TestCase):
    def test_handoff_surface_is_visible_but_fail_closed(self) -> None:
        for marker in (
            'id="proposal-acceptance-handoff"',
            'id="proposal-acceptance-status"',
            'id="proposal-acceptance-seller"',
            'id="proposal-acceptance-parent"',
            'id="proposal-acceptance-proposal"',
        ):
            self.assertIn(marker, INDEX)
        self.assertIn('id="accept-proposal" type="button" disabled', INDEX)

    def test_selected_proposal_binds_exact_parent_and_seller(self) -> None:
        start = APP.index("function renderProposalAcceptanceHandoff(record)")
        end = APP.index("function renderDetail()", start)
        body = APP[start:end]
        self.assertIn("proposalResponseSummary(record)", body)
        self.assertIn("state.responseParentId", body)
        self.assertIn("productListingSummary(state.records.get(parentId))", body)
        self.assertIn("parentListing.sellerPrincipal", body)
        self.assertIn("state.selectedId", body)

    def test_handoff_enables_only_exact_authenticated_seller(self) -> None:
        start = APP.index("function renderProposalAcceptanceHandoff(record)")
        end = APP.index("function renderDetail()", start)
        body = APP[start:end]
        self.assertIn("acceptProposalButton.disabled = true", body)
        self.assertIn("authBootstrap.state()", body)
        self.assertIn("authSnapshot.principal !== parentListing.sellerPrincipal", body)
        self.assertIn('i18n.t("acceptance.authMismatch")', body)
        self.assertIn("acceptProposalButton.disabled = false", body)

    def test_acceptance_requires_explicit_click_and_keeps_exact_result_in_memory(self) -> None:
        self.assertIn(
            'acceptProposalButton.addEventListener("click", () => void acceptSelectedProposal())',
            APP,
        )
        start = APP.index("async function acceptSelectedProposal()")
        end = APP.index("function renderDetail()", start)
        body = APP[start:end]
        self.assertIn("authBootstrap.proposalAcceptanceClient()", body)
        self.assertIn("client.acceptProposal(proposalId)", body)
        self.assertIn("state.proposalAcceptanceResults.set(proposalId, result)", body)
        self.assertNotIn("agreementAssentClient()", body)
        self.assertNotIn("signAndSubmit(", body)

    def test_handoff_explains_authentication_boundary_bilingually(self) -> None:
        self.assertIn('"acceptance.authRequired"', APP)
        self.assertIn("Authentication required. No seller acceptance has been published.", APP)
        self.assertIn("\\u0422\\u0440\\u0435\\u0431\\u0443\\u0435\\u0442\\u0441\\u044f ", APP)
        self.assertIn('"acceptance.parentUnavailable"', APP)
        self.assertIn('"acceptance.button"', APP)


if __name__ == "__main__":
    unittest.main()
