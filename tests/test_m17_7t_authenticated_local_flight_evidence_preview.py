from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "web" / "app.js"
INDEX = ROOT / "web" / "index.html"
PROJECTION = ROOT / "web" / "authenticated_local_flight_evidence.js"
DOC = ROOT / "docs" / "m17-7t-authenticated-local-flight-evidence-preview.md"


class M177TAuthenticatedLocalFlightEvidencePreviewTests(unittest.TestCase):
    def test_page_exposes_explicit_memory_only_preview_controls(self) -> None:
        text = INDEX.read_text(encoding="utf-8")
        for marker in (
            'id="evidence-main-commit"',
            'id="evidence-ci-run-number"',
            'id="evidence-buyer-auth-observed"',
            'id="prepare-authenticated-flight-evidence"',
            'id="authenticated-flight-evidence-status"',
            'id="authenticated-flight-evidence-json"',
            "Prepare non-secret evidence preview",
            "Preview stays memory-only unless you explicitly download this non-secret JSON. No clipboard, upload, payment, deployment, or public-network action occurs.",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, text)

    def test_preview_derives_lifecycle_and_seller_state_but_requires_buyer_observation(self) -> None:
        text = APP.read_text(encoding="utf-8")
        for marker in (
            "state.responseParentId",
            "proposalAcceptanceEvidence(proposalId)",
            "state.agreementFormationResults.get(proposalId)",
            "state.agreementPublicationResults.get(proposalId)",
            "state.fulfillmentCompletionResults.get(proposalId)",
            "authSnapshot.principal !== parentListing.sellerPrincipal",
            'formation.formationEvidence !== "EVIDENCE_SUFFICIENT_FOR_PROFILE"',
            "formation.missingPrincipals.length !== 0",
            "evidenceBuyerAuthObservedInput.checked === true",
            "sellerAuthenticated: true",
            "const buyerAuthenticated = evidenceBuyerAuthObservedInput.checked === true;",
            "buyerAuthenticated,",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, text)

    def test_preview_requires_distinct_seller_buyer_and_formation_coverage(self) -> None:
        text = APP.read_text(encoding="utf-8")
        start = text.index("function authenticatedFlightEvidenceInputs()")
        end = text.index("function renderAuthenticatedFlightEvidencePreview()", start)
        block = text[start:end]
        for required in (
            "const proposal = proposalResponseSummary(state.selectedRecord);",
            "if (proposal === null) return null;",
            "authSnapshot.principal !== parentListing.sellerPrincipal",
            "proposal.buyerPrincipal === parentListing.sellerPrincipal",
            "!Array.isArray(formation.requiredPrincipals)",
            "!Array.isArray(formation.coveredPrincipals)",
            "!Array.isArray(formation.missingPrincipals)",
            "!formation.requiredPrincipals.includes(parentListing.sellerPrincipal)",
            "!formation.requiredPrincipals.includes(proposal.buyerPrincipal)",
            "!formation.coveredPrincipals.includes(parentListing.sellerPrincipal)",
            "!formation.coveredPrincipals.includes(proposal.buyerPrincipal)",
            "formation.missingPrincipals.length !== 0",
        ):
            with self.subTest(required=required):
                self.assertIn(required, block)
        self.assertLess(
            block.index("proposal.buyerPrincipal === parentListing.sellerPrincipal"),
            block.index("return {"),
        )

    def test_preview_preparation_and_download_reuse_two_party_guard(self) -> None:
        text = APP.read_text(encoding="utf-8")
        begin = text.index("function authenticatedFlightEvidenceInputs()")
        finish = text.index("async function publishSelectedAgreement()", begin)
        preview = text[begin:finish]
        self.assertIn("const observed = authenticatedFlightEvidenceInputs();", preview)
        self.assertIn("const current = authenticatedFlightEvidenceInputs();", preview)
        export_start = text.index("function authenticatedFlightEvidenceDocumentIsCurrent()")
        export_end = text.index("function downloadAuthenticatedFlightEvidence()", export_start)
        self.assertIn(
            "const current = authenticatedFlightEvidenceInputs();",
            text[export_start:export_end],
        )

    def test_preview_requires_exact_loopback_and_explicit_main_ci_metadata(self) -> None:
        text = APP.read_text(encoding="utf-8")
        for marker in (
            "/^[0-9a-f]{40}$/.test(evidenceMainCommitInput.value.trim())",
            "Number.isSafeInteger(ciRunNumber) && ciRunNumber > 0",
            'location.hostname !== "127.0.0.1"',
            "const mainCommit = evidenceMainCommitInput.value.trim();",
            "const ciRunNumber = Number(evidenceCiRunNumberInput.value);",
            "evidenceMainCommitInput.value.trim() !== mainCommit",
            "Number(evidenceCiRunNumberInput.value) !== ciRunNumber",
            "mainCommit,",
            "ciRunNumber,",
            "runtimeHost: location.hostname",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, text)

    def test_projection_is_selected_only_after_explicit_click_and_output_is_cleared(self) -> None:
        text = APP.read_text(encoding="utf-8")
        self.assertEqual(text.count('import("./authenticated_local_flight_evidence.js")'), 1)
        self.assertIn('prepareAuthenticatedFlightEvidenceButton.addEventListener("click", () => void prepareAuthenticatedFlightEvidence())', text)
        self.assertIn('authenticatedFlightEvidenceJson.textContent = "{}"', text)
        self.assertIn("clearAuthenticatedFlightEvidenceDocument();", text)
        self.assertIn("JSON.stringify(documentValue, null, 2)", text)

    def test_preview_preparation_does_not_perform_persistence_or_export_runtime_actions(self) -> None:
        block = APP.read_text(encoding="utf-8")
        start = block.index("function clearAuthenticatedFlightEvidenceDocument()")
        end = block.index("async function publishSelectedAgreement()", start)
        preview = block[start:end].lower()
        for forbidden in (
            "localstorage", "sessionstorage", "indexeddb", "document.cookie",
            "clipboard", "createobjecturl", "filesystem",
            "websocket", "eventsource", "settimeout", "setinterval", "fetch(",
            "authorization", "bearer ", "privatekey", "postgres", "payment(", "settlement(",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, preview)

    def test_document_preserves_manual_buyer_observation_and_acceptance_boundary(self) -> None:
        text = " ".join(DOC.read_text(encoding="utf-8").split())
        for marker in (
            "MARKETPLACE_AUTHENTICATED_LOCAL_FLIGHT_EVIDENCE_PREVIEW_V1",
            "does not infer a buyer session",
            "exact 127.0.0.1",
            "Prepare non-secret evidence preview",
            "preventing a stale document",
            "does not download, copy, persist, upload",
            "not itself a live-flight acceptance claim",
            "Source-only rollback",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, text)

    def test_projection_module_remains_the_strict_s_boundary(self) -> None:
        self.assertIn("MARKETPLACE_AUTHENTICATED_LOCAL_FLIGHT_EVIDENCE_V1", PROJECTION.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
