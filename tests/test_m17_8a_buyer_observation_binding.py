"""M17.8A: buyer observation is local, transaction-bound and reset on drift."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "web" / "app.js"
DOC = ROOT / "docs" / "m17-8a-buyer-auth-observation-binding.md"


class M178ABuyerObservationBindingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = APP.read_text(encoding="utf-8")

    def test_observation_is_bound_to_actual_selected_record_and_session(self):
        src = self.source
        segment = src[
            src.index("function currentBuyerAuthenticationObservationContext()"):
            src.index("function buyerAuthenticationObservationIsCurrent()")
        ]
        for token in (
            "state.selectedId === null || state.responseParentId === null",
            "proposalResponseSummary(state.selectedRecord)",
            "productListingSummary(state.records.get(state.responseParentId))",
            "authBootstrap.state()",
            "!auth.active",
            "auth.principal !== listing.sellerPrincipal",
            "proposal.buyerPrincipal === listing.sellerPrincipal",
            "proposalId: state.selectedId",
            "listingRecordId: state.responseParentId",
            "sellerPrincipal: listing.sellerPrincipal",
            "buyerPrincipal: proposal.buyerPrincipal",
        ):
            with self.subTest(token=token):
                self.assertIn(token, segment)

    def test_changed_transaction_fail_closes_and_unchecks_checkbox(self):
        src = self.source
        segment = src[
            src.index("function buyerAuthenticationObservationIsCurrent()"):
            src.index("function authenticatedFlightEvidenceInputs()")
        ]
        for token in (
            "currentBuyerAuthenticationObservationContext()",
            "current.proposalId === stored.proposalId",
            "current.listingRecordId === stored.listingRecordId",
            "current.sellerPrincipal === stored.sellerPrincipal",
            "current.buyerPrincipal === stored.buyerPrincipal",
            "buyerAuthenticationObservation = null;",
            "evidenceBuyerAuthObservedInput.checked = false;",
            "clearAuthenticatedFlightEvidenceDocument();",
            "return false;",
        ):
            with self.subTest(token=token):
                self.assertIn(token, segment)
        self.assertLess(
            segment.index("buyerAuthenticationObservation = null;"),
            segment.index("evidenceBuyerAuthObservedInput.checked = false;"),
        )

    def test_preview_async_boundary_and_export_recheck_current_observation(self):
        src = self.source
        preview = src[
            src.index("function renderAuthenticatedFlightEvidencePreview()"):
            src.index("async function publishSelectedAgreement()")
        ]
        self.assertIn("buyerAuthenticationObservationIsCurrent();", preview)
        self.assertIn("!buyerAuthenticationObservationIsCurrent() ||", preview)
        self.assertIn("const buyerAuthenticated = evidenceBuyerAuthObservedInput.checked === true;", preview)
        export = src[
            src.index("function authenticatedFlightEvidenceDocumentIsCurrent()"):
            src.index("function downloadAuthenticatedFlightEvidence()")
        ]
        self.assertIn("buyerAuthenticationObservationIsCurrent() &&", export)
        self.assertIn("const current = authenticatedFlightEvidenceInputs();", export)

    def test_buyer_checkbox_event_captures_in_memory_context_only(self):
        src = self.source
        handler = src[
            src.index("function recordBuyerAuthenticationObservation()"):
            src.index("authPrincipalInput.addEventListener", src.index("function recordBuyerAuthenticationObservation()"))
        ]
        for token in (
            "currentBuyerAuthenticationObservationContext()",
            "buyerAuthenticationObservation =",
            "if (buyerAuthenticationObservation === null) evidenceBuyerAuthObservedInput.checked = false;",
            "clearAuthenticatedFlightEvidenceDocument();",
            "renderAuthenticatedFlightEvidencePreview();",
            'evidenceBuyerAuthObservedInput.addEventListener("input", recordBuyerAuthenticationObservation);',
            'evidenceBuyerAuthObservedInput.addEventListener("change", recordBuyerAuthenticationObservation);',
        ):
            with self.subTest(token=token):
                self.assertIn(token, handler)
        for forbidden in ("fetch(", "localStorage", "sessionStorage", "indexedDB", "clipboard",
                          "createObjectURL", "WebSocket", "setTimeout", "postgres", "privateKey"):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden.lower(), handler.lower())

    def test_document_preserves_manual_attestation_boundary(self):
        text = DOC.read_text(encoding="utf-8")
        for token in (
            "MARKETPLACE_BUYER_AUTH_OBSERVATION_BINDING_V1",
            "manual observation",
            "different Proposal",
            "same seller session",
            "not cryptographic evidence",
            "not live-runtime acceptance",
            "no server call",
        ):
            with self.subTest(token=token):
                self.assertIn(token, text)


if __name__ == "__main__":
    unittest.main()
