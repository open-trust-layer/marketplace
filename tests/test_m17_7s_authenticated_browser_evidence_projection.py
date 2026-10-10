from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "web" / "authenticated_local_flight_evidence.js"
VALIDATOR = ROOT / "tools" / "marketplace_authenticated_local_flight_evidence.py"
SITE_HOST = ROOT / "src" / "marketplace" / "application" / "site_host.py"
LOCALHOST = ROOT / "tools" / "marketplace_localhost.py"
DOC = ROOT / "docs" / "m17-7s-authenticated-browser-evidence-projection.md"


class M177SAuthenticatedBrowserEvidenceProjectionTests(unittest.TestCase):
    def test_projection_uses_exact_r_profile_and_semantics(self) -> None:
        source = SOURCE.read_text(encoding="utf-8")
        validator = VALIDATOR.read_text(encoding="utf-8")
        for marker in (
            "MARKETPLACE_AUTHENTICATED_LOCAL_FLIGHT_EVIDENCE_V1",
            "127.0.0.1",
            "EVIDENCE_SUFFICIENT_FOR_PROFILE",
            "seller-delivery",
            "CLAIMED_COMPLETE_PERFORMANCE",
            "STORED",
            "DUPLICATE",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, source)
                self.assertIn(marker, validator)

    def test_output_keys_match_strict_validator_contract(self) -> None:
        source = SOURCE.read_text(encoding="utf-8")
        for marker in (
            "profile: PROFILE",
            "main_commit: mainCommit",
            "ci_run_number: ciRunNumber",
            "runtime_host: LOOPBACK_HOST",
            "seller_authenticated: true",
            "buyer_authenticated: true",
            "listing_record_id: listing",
            "proposal_record_id: proposal",
            "acceptance_record_id: acceptance",
            "agreement_record_id: agreement",
            "formation_evidence: FORMATION_SUFFICIENT",
            "missing_principals: Object.freeze([])",
            "agreement_publication: Object.freeze({",
            "completion: Object.freeze({",
            "universal_truth: false",
            "payment_or_settlement_evaluated: false",
            "public_network_exposed: false",
            "public_deployment: false",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, source)

    def test_projection_rejects_partial_or_semantically_different_observations(self) -> None:
        source = SOURCE.read_text(encoding="utf-8")
        for marker in (
            "sellerAuthenticated !== true",
            "buyerAuthenticated !== true",
            "runtimeHost !== LOOPBACK_HOST",
            "formationValue.formationEvidence !== FORMATION_SUFFICIENT",
            "formationValue.missingPrincipals.length !== 0",
            "completionValue.commitmentId !== COMMITMENT_ID",
            "completionValue.evidenceKind !== EVIDENCE_KIND",
            "new Set(lifecycleIds).size !== lifecycleIds.length",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, source)

    def test_projection_is_delivered_by_existing_static_module_boundary(self) -> None:
        marker = "authenticated_local_flight_evidence.js"
        self.assertTrue(SOURCE.is_file())
        self.assertIn(marker, SITE_HOST.read_text(encoding="utf-8"))
        self.assertIn(marker, LOCALHOST.read_text(encoding="utf-8"))

    def test_projection_has_no_runtime_or_credential_surface(self) -> None:
        source = SOURCE.read_text(encoding="utf-8").lower()
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
            "privatekey",
            "session_token",
            "authorization",
            "bearer ",
            "postgres",
            "payment(",
            "settlement(",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, source)

    def test_document_keeps_projection_distinct_from_live_acceptance(self) -> None:
        text = " ".join(DOC.read_text(encoding="utf-8").split())
        for marker in (
            "MARKETPLACE_AUTHENTICATED_BROWSER_EVIDENCE_PROJECTION_V1",
            "pure Web projection",
            "does not infer missing observations",
            "exact `127.0.0.1`",
            "pure synchronous value projection",
            "not live-flight acceptance",
            "separately authorized post-P loopback browser flight",
            "Source-only rollback",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, text)


if __name__ == "__main__":
    unittest.main()
