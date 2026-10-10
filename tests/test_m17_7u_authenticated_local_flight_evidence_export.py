from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "web" / "app.js"
INDEX = ROOT / "web" / "index.html"
DOC = ROOT / "docs" / "m17-7u-authenticated-local-flight-evidence-export.md"


class M177UAuthenticatedLocalFlightEvidenceExportTests(unittest.TestCase):
    def test_page_exposes_separate_explicit_download_control(self) -> None:
        text = INDEX.read_text(encoding="utf-8")
        for marker in (
            'id="download-authenticated-flight-evidence"',
            'type="button"',
            "Download evidence JSON",
            "Preview stays memory-only unless you explicitly download this non-secret JSON.",
            "No clipboard, upload, payment, deployment, or public-network action occurs.",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, text)

    def test_export_is_disabled_until_a_current_prepared_document_exists(self) -> None:
        text = APP.read_text(encoding="utf-8")
        for marker in (
            "let authenticatedFlightEvidenceDocument = null;",
            "authenticatedFlightEvidenceDocument = null;",
            "downloadAuthenticatedFlightEvidenceButton.disabled = true;",
            "authenticatedFlightEvidenceDocument = documentValue;",
            "downloadAuthenticatedFlightEvidenceButton.disabled = false;",
            "downloadAuthenticatedFlightEvidenceButton.disabled = !authenticatedFlightEvidenceDocumentIsCurrent();",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, text)

    def test_currentness_rechecks_metadata_lifecycle_and_reviewed_boundaries(self) -> None:
        text = APP.read_text(encoding="utf-8")
        start = text.index("function authenticatedFlightEvidenceDocumentIsCurrent()")
        end = text.index("function downloadAuthenticatedFlightEvidence()", start)
        block = text[start:end]
        for marker in (
            'location.hostname === "127.0.0.1"',
            "documentValue.main_commit === evidenceMainCommitInput.value.trim()",
            "documentValue.ci_run_number === Number(evidenceCiRunNumberInput.value)",
            "evidenceBuyerAuthObservedInput.checked === true",
            "documentValue.listing_record_id === current.listingRecordId",
            "documentValue.proposal_record_id === current.proposalId",
            "documentValue.acceptance_record_id === current.acceptance.recordId",
            "documentValue.agreement_record_id === current.formation.agreementRecordId",
            "publication?.agreement_record_id === current.publication.agreementRecordId",
            "publication?.disposition === current.publication.disposition",
            "publication?.change_seq === current.publication.changeSeq",
            "completion?.record_id === current.completion.recordId",
            "completion?.agreement_record_id === current.completion.agreementRecordId",
            "completion?.commitment_id === current.completion.commitmentId",
            "completion?.evidence_kind === current.completion.evidenceKind",
            "completion?.disposition === current.completion.disposition",
            "completion?.change_seq === current.completion.changeSeq",
            "documentValue.universal_truth === false",
            "documentValue.payment_or_settlement_evaluated === false",
            "documentValue.public_network_exposed === false",
            "documentValue.public_deployment === false",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, block)

    def test_export_uses_exact_prepared_object_and_stable_utf8_json_file(self) -> None:
        text = APP.read_text(encoding="utf-8")
        start = text.index("function downloadAuthenticatedFlightEvidence()")
        end = text.index("async function resolveSelectedProposalAcceptance()", start)
        block = text[start:end]
        for marker in (
            "authenticatedFlightEvidenceDocumentIsCurrent()",
            "clearAuthenticatedFlightEvidenceDocument();",
            '"marketplace-authenticated-local-flight-evidence.json"',
            "JSON.stringify(authenticatedFlightEvidenceDocument, null, 2)",
            'type: "application/json;charset=utf-8"',
            "URL.createObjectURL(blob)",
            'document.createElement("a")',
            "anchor.download = filename",
            "anchor.click();",
            "anchor.remove();",
            "URL.revokeObjectURL(objectUrl);",
            '"evidence.downloaded"',
            '"evidence.exportStale"',
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, block)

    def test_export_runs_only_from_the_explicit_button_handler(self) -> None:
        text = APP.read_text(encoding="utf-8")
        self.assertEqual(text.count("function downloadAuthenticatedFlightEvidence()"), 1)
        self.assertIn(
            'downloadAuthenticatedFlightEvidenceButton.addEventListener("click", downloadAuthenticatedFlightEvidence);',
            text,
        )
        self.assertEqual(text.count("downloadAuthenticatedFlightEvidence();"), 0)

    def test_export_surface_has_no_network_storage_clipboard_or_background_authority(self) -> None:
        text = APP.read_text(encoding="utf-8")
        start = text.index("function downloadAuthenticatedFlightEvidence()")
        end = text.index("async function resolveSelectedProposalAcceptance()", start)
        block = text[start:end].lower()
        for forbidden in (
            "fetch(",
            "xmlhttprequest",
            "websocket",
            "eventsource",
            "localstorage",
            "sessionstorage",
            "indexeddb",
            "document.cookie",
            "serviceworker",
            "settimeout",
            "setinterval",
            "worker(",
            "broadcastchannel",
            "clipboard",
            "authorization",
            "bearer ",
            "privatekey",
            "postgres",
            "payment(",
            "settlement(",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, block)

    def test_document_records_local_file_and_acceptance_boundaries(self) -> None:
        text = " ".join(DOC.read_text(encoding="utf-8").split())
        for marker in (
            "MARKETPLACE_AUTHENTICATED_LOCAL_FLIGHT_EVIDENCE_EXPORT_V1",
            "one separate, explicit browser action",
            "marketplace-authenticated-local-flight-evidence.json",
            "application/json;charset=utf-8",
            "No value is reconstructed from rendered HTML text",
            "object URL is revoked",
            "no automatic download",
            "not itself live-flight acceptance",
            "Source-only rollback",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, text)


if __name__ == "__main__":
    unittest.main()
