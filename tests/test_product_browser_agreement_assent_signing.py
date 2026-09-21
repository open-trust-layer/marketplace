from __future__ import annotations

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / "web" / "app.js").read_text(encoding="utf-8")
INDEX = (ROOT / "web" / "index.html").read_text(encoding="utf-8")
CLIENT = (ROOT / "web" / "agreement_assent_client.js").read_text(encoding="utf-8")
DOC = ROOT / "docs" / "product-browser-agreement-assent-signing.md"


class ProductBrowserAgreementAssentSigningTests(unittest.TestCase):
    def test_surface_starts_fail_closed(self) -> None:
        self.assertIn(
            'id="agreement-assent-status" class="muted" aria-live="polite"',
            INDEX,
        )
        self.assertIn(
            'id="sign-agreement-assent" type="button" disabled',
            INDEX,
        )
        render_start = APP.index("function renderAgreementFormationHandoff(record)")
        render_end = APP.index("async function checkSelectedAgreementFormation()", render_start)
        render = APP[render_start:render_end]
        self.assertIn("signAgreementAssentButton.disabled = true", render)

    def test_signing_requires_exact_acceptance_bound_reviewed_status(self) -> None:
        render_start = APP.index("function renderAgreementFormationHandoff(record)")
        render_end = APP.index("async function checkSelectedAgreementFormation()", render_start)
        render = APP[render_start:render_end]
        for marker in (
            "proposalAcceptanceEvidence(proposalId)",
            "state.agreementFormationResults.get(proposalId)",
            "state.agreementFormationAcceptanceIds.get(proposalId) !== acceptance.recordId",
            "!result.requiredPrincipals.includes(principal)",
            "result.coveredPrincipals.includes(principal)",
            "!result.missingPrincipals.includes(principal)",
            "state.agreementAssentPending.has(proposalId)",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, render)
        self.assertIn("signAgreementAssentButton.disabled = false", render)

    def test_only_explicit_sign_button_invokes_sign_and_submit(self) -> None:
        self.assertEqual(APP.count(".signAndSubmit("), 1)
        self.assertEqual(
            APP.count('signAgreementAssentButton.addEventListener("click"'),
            1,
        )
        start = APP.index("async function signSelectedAgreementAssent()")
        end = APP.index("function renderDetail()", start)
        handler = APP[start:end]
        self.assertIn("authBootstrap.agreementAssentClient()", handler)
        self.assertIn(
            "state.agreementFormationAcceptanceIds.get(proposalId) !== acceptance.recordId",
            handler,
        )
        self.assertIn("formation.requiredPrincipals.includes(principal)", handler)
        self.assertIn("formation.coveredPrincipals.includes(principal)", handler)
        self.assertIn("formation.missingPrincipals.includes(principal)", handler)
        self.assertIn(
            "client.signAndSubmit(\n      proposalId,\n      acceptance.recordId,\n      formation.agreementRecordId,\n    )",
            handler,
        )
        self.assertNotIn(".formationStatus(", handler)
        self.assertNotIn("createAgreementAssentSignature(", handler)

    def test_client_checks_expected_candidate_before_signer(self) -> None:
        start = CLIENT.index("async function signAndSubmit")
        end = CLIENT.index(
            "return Object.freeze({ prepare, formationStatus, signAndSubmit })",
            start,
        )
        block = CLIENT[start:end]
        mismatch = block.index(
            "preparation.agreementRecordId !== expectedAgreementRecordId"
        )
        signer = block.index("createAgreementAssentSignature(")
        self.assertLess(mismatch, signer)
        self.assertIn('"AGREEMENT_ASSENT_AGREEMENT_MISMATCH"', block)

    def test_success_keeps_only_bounded_result_and_disables_repeat_signing(self) -> None:
        self.assertIn("state.agreementAssentResults.set(proposalId, result)", APP)
        self.assertIn("state.agreementAssentErrors.set(proposalId", APP)
        self.assertIn("state.agreementAssentPending.add(proposalId)", APP)
        self.assertIn("state.agreementAssentPending.delete(proposalId)", APP)
        render_start = APP.index("function renderAgreementFormationHandoff(record)")
        render_end = APP.index("async function checkSelectedAgreementFormation()", render_start)
        render = APP[render_start:render_end]
        submitted = render.index("const submitted = state.agreementAssentResults.get(proposalId)")
        enable = render.index("signAgreementAssentButton.disabled = false")
        self.assertLess(submitted, enable)

    def test_auth_and_acceptance_changes_invalidate_signing_state(self) -> None:
        self.assertGreaterEqual(APP.count("state.agreementAssentResults.clear()"), 2)
        self.assertGreaterEqual(APP.count("state.agreementAssentErrors.clear()"), 2)
        self.assertGreaterEqual(APP.count("state.agreementAssentPending.clear()"), 2)
        acceptance_start = APP.index("async function acceptSelectedProposal()")
        acceptance_end = APP.index("function renderAgreementFormationHandoff(record)", acceptance_start)
        acceptance = APP[acceptance_start:acceptance_end]
        self.assertIn("state.agreementFormationResults.delete(proposalId)", acceptance)
        self.assertIn("state.agreementFormationAcceptanceIds.delete(proposalId)", acceptance)
        self.assertIn("state.agreementAssentResults.delete(proposalId)", acceptance)

    def test_no_browser_persistence_background_or_publication_selection(self) -> None:
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
        signing_start = APP.index("async function signSelectedAgreementAssent()")
        signing_end = APP.index("function renderDetail()", signing_start)
        signing = APP[signing_start:signing_end].lower()
        for forbidden in (
            "publishagreement",
            "payment",
            "settlement",
            "fulfillment",
            "agreementpublication",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, signing)

    def test_document_freezes_explicit_high_risk_boundary(self) -> None:
        self.assertTrue(DOC.is_file())
        text = DOC.read_text(encoding="utf-8")
        for marker in (
            "HIGH source capability selection",
            "explicit human click",
            "required missing party",
            "same exact acceptance Record Identity",
            "expectedAgreementRecordId",
            "AGREEMENT_ASSENT_AGREEMENT_MISMATCH",
            "No signature is created on that mismatch",
            "Agreement assent evidence is not Agreement publication",
            "memory-only",
            "source-only",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, text)


if __name__ == "__main__":
    unittest.main()
