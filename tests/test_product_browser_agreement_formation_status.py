from __future__ import annotations

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
INDEX = (ROOT / "web" / "index.html").read_text(encoding="utf-8")
APP = (ROOT / "web" / "app.js").read_text(encoding="utf-8")
DOC = ROOT / "docs" / "product-browser-agreement-formation-status.md"


class ProductBrowserAgreementFormationStatusTests(unittest.TestCase):
    def test_status_surface_is_visible_only_in_proposal_detail_and_signing_starts_disabled(self) -> None:
        for marker in (
            'id="agreement-formation-handoff"',
            'id="agreement-formation-status"',
            'id="agreement-formation-agreement"',
            'id="agreement-formation-evidence"',
            'id="agreement-formation-covered"',
            'id="agreement-formation-missing"',
        ):
            self.assertIn(marker, INDEX)
        self.assertIn('id="check-agreement-formation" type="button" disabled', INDEX)
        self.assertIn('id="sign-agreement-assent" type="button" disabled', INDEX)

    def test_status_requires_exact_page_memory_acceptance(self) -> None:
        start = APP.index("function renderAgreementFormationHandoff(record)")
        end = APP.index("async function checkSelectedAgreementFormation()", start)
        body = APP[start:end]
        self.assertIn("proposalResponseSummary(record)", body)
        self.assertIn("state.proposalAcceptanceResults.get(proposalId)", body)
        self.assertIn("authBootstrap.state()", body)
        self.assertIn("checkAgreementFormationButton.disabled = false", body)
        self.assertIn("signAgreementAssentButton.disabled = true", body)

    def test_only_explicit_status_button_calls_formation_status(self) -> None:
        self.assertIn(
            'checkAgreementFormationButton.addEventListener("click", () => void checkSelectedAgreementFormation())',
            APP,
        )
        start = APP.index("async function checkSelectedAgreementFormation()")
        end = APP.index("async function signSelectedAgreementAssent()", start)
        body = APP[start:end]
        self.assertIn("authBootstrap.agreementAssentClient()", body)
        self.assertIn("client.formationStatus(proposalId, acceptance.recordId)", body)
        self.assertIn("state.agreementFormationResults.set(proposalId, result)", body)
        self.assertNotIn("client.prepare(", body)
        self.assertNotIn("signAndSubmit(", body)
        self.assertNotIn("createAgreementAssentSignature(", body)

    def test_party_status_is_cleared_on_auth_lifecycle_and_before_refresh(self) -> None:
        self.assertGreaterEqual(APP.count("state.agreementFormationResults.clear()"), 2)
        self.assertGreaterEqual(APP.count("state.agreementFormationErrors.clear()"), 2)
        self.assertGreaterEqual(APP.count("state.agreementFormationPending.clear()"), 2)
        start = APP.index("async function checkSelectedAgreementFormation()")
        end = APP.index("function renderDetail()", start)
        body = APP[start:end]
        self.assertIn("state.agreementFormationResults.delete(proposalId)", body)

    def test_formation_status_handler_itself_never_signs(self) -> None:
        start = APP.index("async function checkSelectedAgreementFormation()")
        end = APP.index("async function signSelectedAgreementAssent()", start)
        body = APP[start:end]
        self.assertNotIn("signAndSubmit(", body)
        self.assertNotIn("createAgreementAssentSignature(", body)

    def test_status_result_is_memory_only_and_bounded_to_reviewed_fields(self) -> None:
        for marker in (
            "agreementRecordId",
            "formationEvidence",
            "coveredPrincipals",
            "missingPrincipals",
        ):
            self.assertIn(marker, APP)
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
            self.assertNotIn(forbidden, lower)

    def test_document_records_read_only_and_no_signing_boundary(self) -> None:
        self.assertTrue(DOC.is_file())
        text = DOC.read_text(encoding="utf-8")
        for marker in (
            "read-only",
            "exact acceptance Record Identity",
            "explicit user click",
            "formationStatus",
            "No signing occurs inside the formation-status",
            "no Agreement publication",
            "memory-only",
            "source-only rollback",
        ):
            self.assertIn(marker, text)


if __name__ == "__main__":
    unittest.main()
