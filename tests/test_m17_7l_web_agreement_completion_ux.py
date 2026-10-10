from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "web" / "app.js"
INDEX = ROOT / "web" / "index.html"
DOC = ROOT / "docs" / "m17-7l-web-agreement-completion-ux.md"


class M177LWebAgreementCompletionUxTests(unittest.TestCase):
    def test_exact_controls_exist_and_are_explicit_clicks(self) -> None:
        index = INDEX.read_text(encoding="utf-8")
        app = APP.read_text(encoding="utf-8")
        for marker in (
            'id="agreement-publication-completion-handoff"',
            'id="publish-agreement"',
            'id="claim-delivery-complete"',
            'id="agreement-publication-status"',
            'id="fulfillment-completion-status"',
        ):
            self.assertIn(marker, index)
        self.assertIn(
            'publishAgreementButton.addEventListener("click", () => void publishSelectedAgreement())',
            app,
        )
        self.assertIn(
            'claimDeliveryCompleteButton.addEventListener("click", () => void claimSelectedDeliveryComplete())',
            app,
        )

    def test_publication_is_formation_and_covered_party_gated(self) -> None:
        text = APP.read_text(encoding="utf-8")
        start = text.index("async function publishSelectedAgreement()")
        end = text.index("async function claimSelectedDeliveryComplete()", start)
        block = text[start:end]
        for marker in (
            'formation.formationEvidence !== "EVIDENCE_SUFFICIENT_FOR_PROFILE"',
            "formation.missingPrincipals.length !== 0",
            "!authSnapshot.active",
            "!formation.requiredPrincipals.includes(authSnapshot.principal)",
            "!formation.coveredPrincipals.includes(authSnapshot.principal)",
            "authBootstrap.agreementPublicationClient()",
            "client.publishAgreement(",
            "acceptance.recordId",
            "formation.agreementRecordId",
            'throw stableClientError("AGREEMENT_PUBLICATION_AGREEMENT_MISMATCH")',
        ):
            self.assertIn(marker, block)
        self.assertEqual(block.count("client.publishAgreement("), 1)

    def test_completion_is_exact_seller_delivery_claim(self) -> None:
        text = APP.read_text(encoding="utf-8")
        start = text.index("async function claimSelectedDeliveryComplete()")
        end = text.index("async function resolveSelectedProposalAcceptance()", start)
        block = text[start:end]
        for marker in (
            'const SELLER_DELIVERY_COMMITMENT_ID = "seller-delivery"',
            'const CLAIMED_COMPLETE_PERFORMANCE = "CLAIMED_COMPLETE_PERFORMANCE"',
        ):
            self.assertIn(marker, text)
        for marker in (
            "publication === undefined",
            "parentListing === null",
            "!authSnapshot.active",
            "authSnapshot.principal !== parentListing.sellerPrincipal",
            "authBootstrap.fulfillmentCompletionClient()",
            "client.publishEvidence(",
            "SELLER_DELIVERY_COMMITMENT_ID",
            "CLAIMED_COMPLETE_PERFORMANCE",
            "result.agreementRecordId !== publication.agreementRecordId",
            "result.commitmentId !== SELLER_DELIVERY_COMMITMENT_ID",
            "result.evidenceKind !== CLAIMED_COMPLETE_PERFORMANCE",
        ):
            self.assertIn(marker, block)
        self.assertEqual(block.count("client.publishEvidence("), 1)

    def test_rendering_does_not_publish_or_complete_automatically(self) -> None:
        text = APP.read_text(encoding="utf-8")
        start = text.index("function renderAgreementPublicationCompletionHandoff(record)")
        end = text.index("async function publishSelectedAgreement()", start)
        block = text[start:end]
        self.assertNotIn("publishAgreement(", block)
        self.assertNotIn("publishEvidence(", block)
        self.assertNotIn("agreementPublicationClient()", block)
        self.assertNotIn("fulfillmentCompletionClient()", block)

    def test_downstream_page_state_is_memory_only_and_cleared_on_refresh(self) -> None:
        text = APP.read_text(encoding="utf-8")
        self.assertIn("function clearAgreementPublicationCompletionState(", text)
        self.assertGreaterEqual(
            text.count("clearAgreementPublicationCompletionState("),
            5,
        )
        lower = text.lower()
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
            "retry",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, lower)

    def test_user_copy_preserves_attributable_evidence_boundary(self) -> None:
        index = INDEX.read_text(encoding="utf-8")
        app = APP.read_text(encoding="utf-8")
        doc = DOC.read_text(encoding="utf-8")
        self.assertIn(
            "Completion creates seller-attributed evidence only. It does not prove universal truth or trigger payment or settlement.",
            index,
        )
        for marker in (
            '"fulfillment.note"',
            '"fulfillment.published"',
            "not universal truth",
        ):
            self.assertIn(marker, app)
        for marker in (
            "attributable seller-authored claim",
            "not:",
            "buyer acceptance",
            "payment authorization",
            "settlement authorization",
            "source-only / Web rollback",
        ):
            self.assertIn(marker, doc)

    def test_bilingual_copy_covers_new_static_and_dynamic_surface(self) -> None:
        text = APP.read_text(encoding="utf-8")
        for key in (
            "agreementPublication.eyebrow",
            "agreementPublication.title",
            "agreementPublication.button",
            "agreementPublication.ready",
            "agreementPublication.published",
            "fulfillment.button",
            "fulfillment.note",
            "fulfillment.ready",
            "fulfillment.published",
        ):
            self.assertIn(f'"{key}": [', text)


if __name__ == "__main__":
    unittest.main()
