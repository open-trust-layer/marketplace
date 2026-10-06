from __future__ import annotations

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "web" / "agreement_publication_client.js"
SESSION = ROOT / "web" / "client_session.js"
BOOTSTRAP = ROOT / "web" / "auth_bootstrap.js"
APP = ROOT / "web" / "app.js"
INDEX = ROOT / "web" / "index.html"
SITE_HOST = ROOT / "src" / "marketplace" / "application" / "site_host.py"
LOCALHOST = ROOT / "tools" / "marketplace_localhost.py"
DOC = ROOT / "docs" / "m17-7j-web-agreement-publication-client.md"


class M177JWebAgreementPublicationClientTests(unittest.TestCase):
    def test_exact_profile_route_and_request_shape(self) -> None:
        text = SOURCE.read_text(encoding="utf-8")
        self.assertIn(
            '"MARKETPLACE_WEB_AGREEMENT_PUBLICATION_CLIENT_V1"',
            text,
        )
        self.assertIn(
            'const path = "/api/agreements/" + encodeURIComponent(proposalRecordId)',
            text,
        )
        self.assertIn('authorizationFor("POST", path)', text)
        self.assertIn('method: "POST"', text)
        self.assertIn('"Content-Type": "application/json"', text)
        self.assertIn(
            "acceptance_record_id: acceptanceRecordId",
            text,
        )

    def test_request_cannot_supply_actor_or_authority_fields(self) -> None:
        text = SOURCE.read_text(encoding="utf-8")
        for forbidden in (
            "principal:",
            "issuer:",
            "verification_method:",
            "public_key:",
            "trust:",
            "formation_evidence:",
            "legal_enforceability:",
            "disposition:",
            "change_seq:",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, text)

    def test_expected_agreement_identity_is_local_validation_only(self) -> None:
        text = SOURCE.read_text(encoding="utf-8")
        self.assertIn("expectedAgreementRecordIdValue", text)
        self.assertIn(
            "agreementRecordId !== expectedAgreementRecordId",
            text,
        )
        self.assertNotIn(
            "expected_agreement_record_id",
            text,
        )

    def test_success_response_is_exact_and_status_bound_to_disposition(self) -> None:
        text = SOURCE.read_text(encoding="utf-8")
        self.assertIn(
            '["agreement_record_id", "change_seq", "disposition"]',
            text,
        )
        for marker in (
            '["STORED", "DUPLICATE"]',
            "Number.isSafeInteger(value.change_seq)",
            'value.disposition === "STORED" && status !== 201',
            'value.disposition === "DUPLICATE" && status !== 200',
        ):
            self.assertIn(marker, text)

    def test_client_is_deliberately_unselected_and_route_not_authorized(self) -> None:
        marker = "agreement_publication_client.js"
        self.assertTrue(SOURCE.is_file())
        for path in (SESSION, BOOTSTRAP, APP, INDEX, SITE_HOST, LOCALHOST):
            self.assertTrue(path.is_file(), str(path))
            self.assertNotIn(marker, path.read_text(encoding="utf-8"), str(path))

        session = SESSION.read_text(encoding="utf-8")
        self.assertNotIn(
            'parts.length === 1',
            session[session.index("function reviewedAgreementAssentRoute"):
                    session.index("function reviewedAuthenticatedRoute")],
        )

    def test_no_persistence_background_signing_payment_or_truth_claim(self) -> None:
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
            "payment",
            "settlement",
            "legal_enforceability",
            "universal_truth",
        ):
            self.assertNotIn(forbidden, text)

    def test_document_records_unselected_publication_boundary(self) -> None:
        text = DOC.read_text(encoding="utf-8")
        for marker in (
            "MARKETPLACE_WEB_AGREEMENT_PUBLICATION_CLIENT_V1",
            "MODERATE authenticated Web transport",
            "required explicit step",
            "intentionally unusable from the active page",
            "STORED",
            "HTTP 201",
            "DUPLICATE",
            "HTTP 200",
            "does not itself establish performance",
            "source-only rollback",
        ):
            self.assertIn(marker, text)


if __name__ == "__main__":
    unittest.main()
