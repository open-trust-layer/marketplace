from __future__ import annotations

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "web" / "fulfillment_completion_client.js"
SESSION = ROOT / "web" / "client_session.js"
BOOTSTRAP = ROOT / "web" / "auth_bootstrap.js"
APP = ROOT / "web" / "app.js"
INDEX = ROOT / "web" / "index.html"
SITE_HOST = ROOT / "src" / "marketplace" / "application" / "site_host.py"
LOCALHOST = ROOT / "tools" / "marketplace_localhost.py"
DOC = ROOT / "docs" / "m17-7i-web-fulfillment-completion-client.md"


class M177IWebFulfillmentCompletionClientTests(unittest.TestCase):
    def test_exact_profile_route_and_request_shape(self) -> None:
        text = SOURCE.read_text(encoding="utf-8")
        self.assertIn(
            '"MARKETPLACE_WEB_FULFILLMENT_COMPLETION_CLIENT_V1"',
            text,
        )
        self.assertIn(
            '"/api/agreements/" + encodeURIComponent(agreementRecordId)',
            text,
        )
        self.assertIn(
            '"/commitments/" + encodeURIComponent(commitmentId) + "/completion-evidence"',
            text,
        )
        self.assertIn('authorizationFor("POST", path)', text)
        self.assertIn('method: "POST"', text)
        self.assertIn('"Content-Type": "application/json"', text)
        self.assertIn(
            "JSON.stringify({ evidence_kind: evidenceKind })",
            text,
        )

    def test_request_cannot_supply_issuer_or_authority_fields(self) -> None:
        text = SOURCE.read_text(encoding="utf-8")
        start = text.index("async function publishEvidence(")
        body_start = text.index("const body = JSON.stringify(", start)
        body_end = text.index("let response;", body_start)
        request_body = text[body_start:body_end]
        self.assertIn(
            "JSON.stringify({ evidence_kind: evidenceKind })",
            request_body,
        )
        for forbidden in (
            "issuer:",
            "principal:",
            "verification_method:",
            "public_key:",
            "trust:",
            "outcome:",
            "target:",
            "agreement_record_id:",
            "commitment_id:",
            "change_seq:",
            "disposition:",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, request_body)

    def test_exact_reviewed_evidence_kind_set(self) -> None:
        text = SOURCE.read_text(encoding="utf-8")
        for marker in (
            '"CLAIMED_COMPLETE_PERFORMANCE"',
            '"COMMITMENT_ACCEPTANCE"',
            '"COMMITMENT_COMPLETION"',
        ):
            self.assertIn(marker, text)
        self.assertIn("EVIDENCE_KINDS.has(value)", text)

    def test_success_response_rebinds_request_and_status_to_disposition(self) -> None:
        text = SOURCE.read_text(encoding="utf-8")
        for marker in (
            '"agreement_record_id"',
            '"change_seq"',
            '"commitment_id"',
            '"disposition"',
            '"evidence_kind"',
            '"record_id"',
            "agreementRecordId !== expectedAgreementRecordId",
            "commitmentId !== expectedCommitmentId",
            "evidenceKind !== expectedEvidenceKind",
            'value.disposition === "STORED" && status !== 201',
            'value.disposition === "DUPLICATE" && status !== 200',
            "Number.isSafeInteger(value.change_seq)",
        ):
            self.assertIn(marker, text)

    def test_client_is_selected_only_by_reviewed_authenticated_bundle(self) -> None:
        marker = "fulfillment_completion_client.js"
        self.assertTrue(SOURCE.is_file())
        self.assertIn(marker, SITE_HOST.read_text(encoding="utf-8"))
        self.assertIn(marker, LOCALHOST.read_text(encoding="utf-8"))
        self.assertEqual(
            BOOTSTRAP.read_text(encoding="utf-8").count(f'from "./{marker}"'),
            1,
        )
        self.assertNotIn(marker, APP.read_text(encoding="utf-8"))
        self.assertNotIn(marker, INDEX.read_text(encoding="utf-8"))
        route_marker = "completion-evidence"
        self.assertIn(route_marker, SESSION.read_text(encoding="utf-8"))
        self.assertNotIn(route_marker, APP.read_text(encoding="utf-8"))
        self.assertNotIn(route_marker, INDEX.read_text(encoding="utf-8"))

    def test_no_persistence_background_retry_signing_or_fulfillment_evaluation(self) -> None:
        text = SOURCE.read_text(encoding="utf-8").lower()
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
            "privatekey",
            ".sign(",
            "evaluate_commitment_fulfillment",
            "payment",
            "settlement",
        ):
            self.assertNotIn(forbidden, text)

    def test_document_records_unselected_semantic_boundary(self) -> None:
        text = DOC.read_text(encoding="utf-8")
        for marker in (
            "MARKETPLACE_WEB_FULFILLMENT_COMPLETION_CLIENT_V1",
            "MODERATE authenticated Web transport",
            "intentionally unusable from the active browser",
            "STORED",
            "HTTP 201",
            "DUPLICATE",
            "HTTP 200",
            "does not establish universal completion",
            "source-only rollback",
        ):
            self.assertIn(marker, text)


if __name__ == "__main__":
    unittest.main()
