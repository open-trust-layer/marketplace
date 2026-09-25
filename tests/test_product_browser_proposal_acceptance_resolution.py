from __future__ import annotations

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / "web" / "app.js").read_text(encoding="utf-8")
INDEX = (ROOT / "web" / "index.html").read_text(encoding="utf-8")
CLIENT = (ROOT / "web" / "proposal_acceptance_client.js").read_text(encoding="utf-8")
SESSION = (ROOT / "web" / "client_session.js").read_text(encoding="utf-8")
DOC = ROOT / "docs" / "product-browser-proposal-acceptance-resolution.md"


class ProductBrowserProposalAcceptanceResolutionTests(unittest.TestCase):
    def test_control_starts_disabled_and_has_one_explicit_handler(self) -> None:
        self.assertIn(
            'id="resolve-proposal-acceptance" type="button" disabled',
            INDEX,
        )
        self.assertEqual(
            APP.count('resolveProposalAcceptanceButton.addEventListener("click"'),
            1,
        )
        self.assertEqual(APP.count("client.resolveAcceptance(proposalId)"), 1)

    def test_client_get_is_exact_and_response_is_bound_to_requested_proposal(self) -> None:
        start = CLIENT.index("async function resolveAcceptance")
        end = CLIENT.index("async function acceptProposal", start)
        block = CLIENT[start:end]
        self.assertIn('authorizationFor("GET", path)', block)
        self.assertIn('method: "GET"', block)
        self.assertNotIn('"Content-Type"', block)
        self.assertNotIn("body:", block)
        self.assertIn(
            'exactKeys(value, ["proposal_record_id", "record_id"])',
            CLIENT,
        )
        self.assertIn(
            "proposalRecordId !== expectedProposalRecordId",
            CLIENT,
        )

    def test_memory_session_authorizes_only_exact_acceptance_get_tail(self) -> None:
        start = SESSION.index("function reviewedAuthenticatedRoute")
        end = SESSION.index("class MarketplaceMemorySession", start)
        block = SESSION[start:end]
        self.assertIn('if (method === "GET")', block)
        self.assertIn('if (path === "/api/auth/session") return true', block)
        self.assertIn('return parts[1] === "acceptance"', block)
        self.assertIn('parts.length !== 2', block)
        self.assertIn('parts[0].includes("?") || parts[0].includes("#")', block)

    def test_resolution_is_explicit_read_only_and_cannot_publish(self) -> None:
        start = APP.index("async function resolveSelectedProposalAcceptance()")
        end = APP.index("async function checkSelectedAgreementFormation()", start)
        block = APP[start:end]
        self.assertIn("authBootstrap.proposalAcceptanceClient()", block)
        self.assertIn("client.resolveAcceptance(proposalId)", block)
        self.assertIn(
            "state.proposalAcceptanceResolutionResults.set(proposalId, result)",
            block,
        )
        self.assertNotIn("acceptProposal(", block)
        self.assertNotIn("signAndSubmit(", block)
        self.assertNotIn(".formationStatus(", block)

    def test_resolved_identity_can_feed_status_and_signing_without_relabeling(self) -> None:
        self.assertIn("function proposalAcceptanceEvidence(proposalId)", APP)
        self.assertIn(
            "return state.proposalAcceptanceResolutionResults.get(proposalId)",
            APP,
        )
        self.assertGreaterEqual(
            APP.count("const acceptance = proposalAcceptanceEvidence(proposalId)"),
            3,
        )
        self.assertIn(
            "state.agreementFormationAcceptanceIds.get(proposalId) !== acceptance.recordId",
            APP,
        )

    def test_auth_lifecycle_clears_party_gated_resolution_state(self) -> None:
        self.assertGreaterEqual(
            APP.count("state.proposalAcceptanceResolutionResults.clear()"),
            2,
        )
        self.assertGreaterEqual(
            APP.count("state.proposalAcceptanceResolutionErrors.clear()"),
            2,
        )
        self.assertGreaterEqual(
            APP.count("state.proposalAcceptanceResolutionPending.clear()"),
            2,
        )

    def test_no_persistence_background_or_automatic_resolution(self) -> None:
        lower = APP.lower()
        for forbidden in (
            "localstorage",
            "sessionstorage",
            "indexeddb",
            "document.cookie",
            "serviceworker",
            "setinterval",
            "settimeout",
            "websocket",
            "eventsource",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, lower)
        self.assertEqual(APP.count("resolveSelectedProposalAcceptance()"), 2)

    def test_document_records_party_gated_read_only_boundary(self) -> None:
        self.assertTrue(DOC.is_file())
        text = DOC.read_text(encoding="utf-8")
        for marker in (
            "LOW authenticated read-only product selection",
            "Resolve Proposal acceptance",
            "explicit browser action",
            "GET /api/intents/{proposal_record_id}/acceptance",
            "no body",
            "page-memory-only",
            "server-side resolver independently derives buyer + seller",
            "does not imply formation sufficiency or assent",
            "source-only",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, text)


if __name__ == "__main__":
    unittest.main()
