from __future__ import annotations

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "web" / "agreement_assent_client.js"
TEXT = SOURCE.read_text(encoding="utf-8")


class ProductWebAgreementAssentClientContractTests(unittest.TestCase):
    def test_exact_profile_and_routes_are_frozen(self) -> None:
        self.assertIn(
            '"MARKETPLACE_WEB_AGREEMENT_ASSENT_CLIENT_V1"',
            TEXT,
        )
        self.assertIn('"/api/agreements/" + encodeURIComponent(proposalRecordId)', TEXT)
        self.assertIn('"/assent/preparation"', TEXT)
        self.assertIn('"/assent"', TEXT)

    def test_request_authority_is_limited_to_acceptance_and_signature(self) -> None:
        for marker in (
            "{ acceptance_record_id: acceptanceRecordId }",
            "acceptance_record_id: acceptanceRecordId",
            "signature: encodeOjveBytes",
        ):
            self.assertIn(marker, TEXT)
        for forbidden in (
            "principal:",
            "verification_method:",
            "public_key:",
            "attribution",
            "listing_record_id:",
            "agreement_record_id:",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, TEXT)

    def test_ojve_carrier_is_exact_and_canonical(self) -> None:
        for marker in (
            'exactKeys(value, ["$olp", "v"])',
            'value.$olp !== "bytes"',
            'return Object.freeze({ $olp: "bytes", v: encodeBase64Url(value) });',
            'value.length % 4 === 1',
            'value.includes("=")',
            "bits !== 0 && buffer !== 0",
        ):
            self.assertIn(marker, TEXT)
        self.assertNotIn("atob(", TEXT)
        self.assertNotIn("btoa(", TEXT)

    def test_bearer_is_obtained_only_from_session_route_policy(self) -> None:
        self.assertIn('session.authorizationFor("POST", path)', TEXT)
        self.assertIn("Authorization: authorization", TEXT)
        self.assertNotIn("sessionToken", TEXT)
        self.assertNotIn("bearerToken", TEXT)

    def test_signer_receives_only_method_and_copied_signing_bytes(self) -> None:
        start = TEXT.index("async function signAndSubmit")
        end = TEXT.index(
            "return Object.freeze({ prepare, formationStatus, signAndSubmit })",
            start,
        )
        block = TEXT[start:end]
        self.assertEqual(block.count("createAgreementAssentSignature("), 1)
        self.assertIn("verificationMethod: preparation.verificationMethod", block)
        self.assertIn("signingInput: Uint8Array.from(preparation.signingInput)", block)
        self.assertIn("signature.length !== SIGNATURE_BYTES", block)

    def test_formation_status_is_read_only_and_coverage_consistent(self) -> None:
        for marker in (
            '"/assent/status"'.replace("\\/", "/"),
            "reviewedFormationStatusResponse",
            "requiredPrincipals.length === 0",
            "covered.size + missing.size !== required.size",
            'value.legal_enforceability !== "NOT_EVALUATED"',
            "value.universal_truth !== false",
            'value.formation_evidence === "EVIDENCE_SUFFICIENT_FOR_PROFILE"',
            "missing.size === 0",
        ):
            self.assertIn(marker, TEXT)
        start = TEXT.index("async function formationStatus")
        end = TEXT.index("async function signAndSubmit", start)
        block = TEXT[start:end]
        self.assertNotIn("createAgreementAssentSignature", block)
        self.assertNotIn("signature:", block)

    def test_success_response_cannot_claim_publication_or_side_effects(self) -> None:
        self.assertIn("value.publishes_agreement !== false", TEXT)
        self.assertIn("value.authorizes_side_effects !== false", TEXT)
        self.assertIn("publishesAgreement: false", TEXT)
        self.assertIn("authorizesSideEffects: false", TEXT)


if __name__ == "__main__":
    unittest.main()
