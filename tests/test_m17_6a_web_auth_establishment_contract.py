from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "web" / "auth_establishment.js"
TEXT = SOURCE.read_text(encoding="utf-8")


class M176AWebAuthEstablishmentContractTests(unittest.TestCase):
    def test_exact_reviewed_profile_and_wire_constants(self) -> None:
        for marker in (
            '"MARKETPLACE_WEB_AUTH_SESSION_ESTABLISHMENT_V1"',
            '"https://open-trust-layer.github.io/marketplace/application-auth/v1"',
            '"MarketplaceAuthenticationProof"',
            '"https://open-trust-layer.github.io/marketplace/application-auth/eddsa-ed25519-v1"',
            'const AUTH_PURPOSE = "assertion"',
            '/^mkc1_[A-Za-z0-9_-]{43}$/',
            '/^mkt1_[A-Za-z0-9_-]{43}$/',
            '/^mks1_[A-Za-z0-9_-]{86}$/',
            "const MAX_AUTH_BODY_BYTES = 64 * 1024",
            "const MAX_PROOF_JSON_BYTES = 48 * 1024",
        ):
            self.assertIn(marker, TEXT)

    def test_establishment_is_exact_challenge_proof_session_sequence(self) -> None:
        start = TEXT.index("async function establishSession")
        end = TEXT.index("return Object.freeze({ establishSession })", start)
        block = TEXT[start:end]
        self.assertEqual(block.count('"/api/auth/challenges"'), 1)
        self.assertEqual(block.count('"/api/auth/sessions"'), 1)
        self.assertEqual(block.count("proofProvider.createAuthenticationProof("), 1)
        self.assertEqual(block.count("session.adoptEstablishedSession("), 1)
        challenge = block.index('"/api/auth/challenges"')
        sign = block.index("proofProvider.createAuthenticationProof(")
        session = block.index('"/api/auth/sessions"')
        adopt = block.index("session.adoptEstablishedSession(")
        self.assertLess(challenge, sign)
        self.assertLess(sign, session)
        self.assertLess(session, adopt)

    def test_challenge_and_session_requests_are_bearer_negative(self) -> None:
        start = TEXT.index("async function postJson")
        end = TEXT.index("function createMarketplaceWebAuthEstablishment", start)
        block = TEXT[start:end]
        self.assertIn('credentials: "omit"', block)
        self.assertIn('redirect: "error"', block)
        self.assertIn('referrerPolicy: "no-referrer"', block)
        self.assertNotIn("Authorization", block)

    def test_proof_is_bound_to_exact_server_challenge_and_method(self) -> None:
        self.assertIn("value.verificationMethod !== verificationMethod", TEXT)
        self.assertIn("value.challenge !== challenge", TEXT)
        self.assertIn("value.domain !== AUTH_DOMAIN", TEXT)
        self.assertIn("value.proofPurpose !== AUTH_PURPOSE", TEXT)
        self.assertIn("!PROOF_VALUE.test(value.proofValue)", TEXT)

    def test_session_mismatch_fails_before_adoption_and_token_is_not_returned(self) -> None:
        self.assertIn("value.principal !== principal", TEXT)
        self.assertIn("value.verification_method !== verificationMethod", TEXT)
        self.assertIn("!SESSION_TOKEN.test(value.session_token)", TEXT)
        returned = TEXT[TEXT.index("return Object.freeze({", TEXT.index("session.adoptEstablishedSession")):]
        self.assertNotIn("session_token", returned.split("});", 1)[0])


if __name__ == "__main__":
    unittest.main()
