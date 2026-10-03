from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "web" / "auth_enrollment_client.js"
TEXT = SOURCE.read_text(encoding="utf-8")


class M176AAWebAuthenticationEnrollmentClientContractTests(unittest.TestCase):
    def test_exact_profile_routes_and_server_types_are_frozen(self) -> None:
        for marker in (
            '"MARKETPLACE_WEB_AUTH_ENROLLMENT_CLIENT_V1"',
            '"MARKETPLACE_APPLICATION_AUTH_ENROLLMENT_HTTP_V1"',
            '"MARKETPLACE_WEB_AUTH_ED25519_ENROLLMENT_PROPOSAL_V1"',
            '"MarketplaceAuthenticationEnrollmentProposal"',
            '"MarketplaceAuthenticationEnrollmentNonce"',
            '"MarketplaceAuthenticationVerificationMethodEvidenceEnvelope"',
            '"/api/authentication-enrollment/nonces"',
            '"/api/authentication-enrollment/evidence"',
        ):
            self.assertIn(marker, TEXT)

    def test_proposal_shape_is_exact_public_only_and_uri_bounded(self) -> None:
        start = TEXT.index("function reviewedProposal")
        end = TEXT.index("function reviewedConfiguration", start)
        block = TEXT[start:end]
        self.assertIn(
            'exactKeys(value, ["profile", "type", "principal", "verificationMethod", "publicKey"])',
            block,
        )
        self.assertIn("value.profile !== PROPOSAL_PROFILE", block)
        self.assertIn("value.type !== PROPOSAL_TYPE", block)
        self.assertIn("reviewedUri(value.principal)", block)
        self.assertIn("reviewedUri(value.verificationMethod)", block)
        self.assertIn("PUBLIC_KEY_PREFIX", block)
        for marker in (
            "privateKey", "private_key", "seed", "mnemonic", "passphrase",
            "authority", "issuedAt", "expiresAt", "attestation",
        ):
            self.assertNotIn(marker, block)

    def test_client_requires_active_principal_match_before_network(self) -> None:
        start = TEXT.index("async function enrollAuthenticationProposal")
        end = TEXT.index("return Object.freeze({ enrollAuthenticationProposal })", start)
        block = TEXT[start:end]
        proposal_at = block.index("reviewedProposal(proposalValue)")
        principal_at = block.index("reviewed.session.requirePrincipal()")
        mismatch_at = block.index("principal !== proposal.principal")
        nonce_at = block.index("postAuthenticatedJson(")
        self.assertLess(proposal_at, principal_at)
        self.assertLess(principal_at, mismatch_at)
        self.assertLess(mismatch_at, nonce_at)
        self.assertIn('stableEnrollmentClientError("AUTH_REQUIRED")', block)
        self.assertIn('stableEnrollmentClientError("AUTH_PRINCIPAL_MISMATCH")', block)

    def test_exact_nonce_then_evidence_requests_and_nonce_stays_internal(self) -> None:
        start = TEXT.index("async function enrollAuthenticationProposal")
        end = TEXT.index("return Object.freeze({ enrollAuthenticationProposal })", start)
        block = TEXT[start:end]
        self.assertEqual(block.count("postAuthenticatedJson("), 2)
        nonce_at = block.index("NONCE_ROUTE")
        evidence_at = block.index("EVIDENCE_ROUTE")
        self.assertLess(nonce_at, evidence_at)
        self.assertIn("{ profile: SERVER_PROFILE, proposal }", block)
        self.assertIn("nonce: nonceResponse.nonce", block)
        self.assertIn("return evidenceResponse", block)
        returned = TEXT[TEXT.index("return Object.freeze({", TEXT.index("function reviewedEvidenceResponse")):
                        TEXT.index("});", TEXT.index("function reviewedEvidenceResponse"))]
        self.assertIn("claims,", returned)
        self.assertIn("attestation,", returned)
        self.assertNotIn("nonce", returned)

    def test_transport_is_exact_authenticated_json_post_without_credentials(self) -> None:
        start = TEXT.index("async function postAuthenticatedJson")
        end = TEXT.index("function reviewedNonceResponse", start)
        block = TEXT[start:end]
        for marker in (
            'authorizationFor("POST", path)',
            'method: "POST"',
            'Accept: "application/json"',
            '"Content-Type": "application/json"',
            "Authorization: authorization",
            'credentials: "omit"',
            'cache: "no-store"',
            'redirect: "error"',
            'referrerPolicy: "no-referrer"',
        ):
            self.assertIn(marker, block)
        self.assertEqual(block.count("reviewed.fetchImpl("), 1)
        self.assertNotIn("retry", block.lower())

    def test_nonce_and_evidence_responses_are_exact_and_bounded(self) -> None:
        nonce_start = TEXT.index("function reviewedNonceResponse")
        evidence_start = TEXT.index("function reviewedEvidenceResponse", nonce_start)
        nonce = TEXT[nonce_start:evidence_start]
        evidence_end = TEXT.index("function createMarketplaceWebAuthEnrollmentClient", evidence_start)
        evidence = TEXT[evidence_start:evidence_end]
        self.assertIn(
            'exactKeys(value, ["expiresAt", "issuedAt", "nonce", "profile", "type"])',
            nonce,
        )
        self.assertIn("Number.isSafeInteger(value.issuedAt)", nonce)
        self.assertIn("value.expiresAt <= value.issuedAt", nonce)
        self.assertIn("NONCE_PREFIX", nonce)
        self.assertIn(
            'exactKeys(value, ["attestation", "claims", "profile", "type"])',
            evidence,
        )
        self.assertIn("CLAIMS_PREFIX", evidence)
        self.assertIn("ATTESTATION_PREFIX", evidence)
        self.assertIn("const MAX_RESPONSE_BYTES = 768 * 1024", TEXT)
        self.assertIn("const MAX_CLAIMS_PAYLOAD_CHARS = 699051", TEXT)
        self.assertIn("const MAX_ATTESTATION_PAYLOAD_CHARS = 21846", TEXT)

    def test_server_errors_are_bounded_and_session_invalidation_is_delegated(self) -> None:
        start = TEXT.index("async function decodeJsonResponse")
        end = TEXT.index("async function postAuthenticatedJson", start)
        block = TEXT[start:end]
        self.assertIn("SERVER_ERROR_CODE.test(serverCode)", block)
        self.assertIn('"AUTH_ENROLLMENT_HTTP_FAILED"', block)
        self.assertIn("session.invalidateForServerCode(code)", block)
        self.assertIn('"APPLICATION_HTTP_TRANSPORT_FAILED"', TEXT)
        self.assertNotIn("console.", TEXT)


if __name__ == "__main__":
    unittest.main()
