from __future__ import annotations

import base64
import hashlib
import json
from pathlib import Path
import unittest

from marketplace.application.auth import (
    AUTH_PROOF_DOMAIN,
    AUTH_PROOF_PURPOSE,
    MarketplaceApplicationAuthService,
    VerifiedAuthenticationProof,
)
from marketplace.application.auth_challenge import (
    encode_marketplace_auth_challenge,
    parse_marketplace_auth_challenge,
)
from marketplace.application.auth_session_http import (
    AUTH_REQUEST_MAX_BYTES,
    MAX_ACTIVE_SESSIONS,
    MAX_ACTIVE_SESSIONS_PER_PRINCIPAL,
    MAX_OUTSTANDING_CHALLENGES,
    MAX_OUTSTANDING_CHALLENGES_PER_BINDING,
    MAX_PROOF_JSON_BYTES,
    MarketplaceAuthenticationSessionHttpAdapter,
)
from marketplace.application.http import ApplicationHttpRequest

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs" / "m17-5d-session-establishment.md"
PRINCIPAL = "did:example:alice"
METHOD = "did:example:alice#key-1"
CHALLENGE = bytes(range(32))
TOKEN = bytes(range(32, 64))


class AllowBinding:
    def verify(self, *, principal: str, verification_method: str, at_time: int) -> bool:
        return principal == PRINCIPAL and verification_method == METHOD and at_time >= 0


class MaterialSource:
    def __init__(self, *, challenge: bytes = CHALLENGE, token: bytes = TOKEN) -> None:
        self.challenge = challenge
        self.token = token
        self.challenge_calls = 0
        self.token_calls = 0

    def challenge_bytes(self) -> bytes:
        self.challenge_calls += 1
        return self.challenge

    def session_token_bytes(self) -> bytes:
        self.token_calls += 1
        return self.token


class ProofVerifier:
    def __init__(self, *, valid: bool = True) -> None:
        self.valid = valid
        self.calls = 0

    def verify(self, proof_document: object) -> VerifiedAuthenticationProof:
        self.calls += 1
        return VerifiedAuthenticationProof(
            challenge_sha256=hashlib.sha256(CHALLENGE).digest(),
            domain=AUTH_PROOF_DOMAIN,
            proof_purpose=AUTH_PROOF_PURPOSE,
            verification_method=METHOD,
            cryptographically_valid=self.valid,
        )


def request(method: str, path: str, document: object | None = None) -> ApplicationHttpRequest:
    if document is None:
        body = b""
        content_type = None
    else:
        body = json.dumps(document, sort_keys=True, separators=(",", ":")).encode("utf-8")
        content_type = "application/json"
    return ApplicationHttpRequest(method, path, (), content_type, body)


def decode(response) -> dict[str, object]:
    return json.loads(response.body.decode("utf-8"))


def make_adapter(*, material=None, verifier=None):
    source = material or MaterialSource()
    proof_verifier = verifier or ProofVerifier()
    auth = MarketplaceApplicationAuthService(principal_binding_verifier=AllowBinding())
    adapter = MarketplaceAuthenticationSessionHttpAdapter(
        auth=auth,
        material_source=source,
        proof_verifier=proof_verifier,
    )
    return adapter, auth, source, proof_verifier


def establish(adapter, *, now: int = 100):
    challenge_response = adapter.handle(
        request("POST", "/api/auth/challenges", {"principal": PRINCIPAL, "verification_method": METHOD}),
        session_token=None,
        session_invalid=False,
        now=now,
    )
    challenge = decode(challenge_response)["challenge"]
    session_response = adapter.handle(
        request("POST", "/api/auth/sessions", {"challenge": challenge, "proof": {"synthetic": True}}),
        session_token=None,
        session_invalid=False,
        now=now + 1,
    )
    return challenge_response, session_response


class M17SessionEstablishmentTests(unittest.TestCase):
    def test_exact_challenge_carrier_round_trip(self):
        encoded = encode_marketplace_auth_challenge(CHALLENGE)
        self.assertEqual(len(encoded), 48)
        self.assertTrue(encoded.startswith("mkc1_"))
        self.assertEqual(parse_marketplace_auth_challenge(encoded), CHALLENGE)

    def test_challenge_endpoint_returns_exact_public_contract(self):
        adapter, _, source, _ = make_adapter()
        response = adapter.handle(
            request("POST", "/api/auth/challenges", {"principal": PRINCIPAL, "verification_method": METHOD}),
            session_token=None,
            session_invalid=False,
            now=100,
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(
            decode(response),
            {
                "challenge": encode_marketplace_auth_challenge(CHALLENGE),
                "domain": AUTH_PROOF_DOMAIN,
                "expires_in_seconds": 120,
                "proof_purpose": AUTH_PROOF_PURPOSE,
            },
        )
        self.assertEqual(source.challenge_calls, 1)
        self.assertEqual(source.token_calls, 0)

    def test_session_endpoint_returns_token_once_and_uses_one_verifier_call(self):
        adapter, _, source, verifier = make_adapter()
        _, response = establish(adapter)
        self.assertEqual(response.status_code, 201)
        document = decode(response)
        expected_token = "mkt1_" + base64.urlsafe_b64encode(TOKEN).rstrip(b"=").decode("ascii")
        self.assertEqual(document["session_token"], expected_token)
        self.assertEqual(document["principal"], PRINCIPAL)
        self.assertEqual(document["verification_method"], METHOD)
        self.assertEqual(document["idle_timeout_seconds"], 1800)
        self.assertEqual(document["absolute_timeout_seconds"], 28800)
        self.assertEqual(source.challenge_calls, 1)
        self.assertEqual(source.token_calls, 1)
        self.assertEqual(verifier.calls, 1)

    def test_session_inspection_is_non_touching_and_logout_revokes(self):
        adapter, _, _, _ = make_adapter()
        establish(adapter)
        response = adapter.handle(
            request("GET", "/api/auth/session"),
            session_token=TOKEN,
            session_invalid=False,
            now=120,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(decode(response)["last_used_at"], 101)
        logout = adapter.handle(
            request("POST", "/api/auth/logout"),
            session_token=TOKEN,
            session_invalid=False,
            now=121,
        )
        self.assertEqual(logout.status_code, 200)
        self.assertEqual(decode(logout), {"status": "REVOKED"})

        invalid = adapter.handle(
            request("GET", "/api/auth/session"),
            session_token=TOKEN,
            session_invalid=False,
            now=122,
        )
        self.assertEqual(invalid.status_code, 401)
        self.assertEqual(decode(invalid)["error"]["code"], "AUTH_SESSION_INVALID")

    def test_invalid_proof_consumes_challenge_and_is_not_retried(self):
        verifier = ProofVerifier(valid=False)
        adapter, _, source, verifier = make_adapter(verifier=verifier)
        challenge_response = adapter.handle(
            request("POST", "/api/auth/challenges", {"principal": PRINCIPAL, "verification_method": METHOD}),
            session_token=None,
            session_invalid=False,
            now=100,
        )
        document = {"challenge": decode(challenge_response)["challenge"], "proof": {"bad": True}}
        first = adapter.handle(request("POST", "/api/auth/sessions", document), session_token=None, session_invalid=False, now=101)
        second = adapter.handle(request("POST", "/api/auth/sessions", document), session_token=None, session_invalid=False, now=102)
        self.assertEqual(first.status_code, 401)
        self.assertEqual(decode(first)["error"]["code"], "AUTH_PROOF_INVALID")
        self.assertEqual(second.status_code, 401)
        self.assertEqual(decode(second)["error"]["code"], "AUTH_CHALLENGE_INVALID")
        self.assertEqual(verifier.calls, 1)
        self.assertEqual(source.token_calls, 1)

    def test_missing_or_invalid_bearer_uses_stable_session_failures(self):
        adapter, _, _, _ = make_adapter()
        missing = adapter.handle(
            request("GET", "/api/auth/session"),
            session_token=None,
            session_invalid=False,
            now=100,
        )
        malformed = adapter.handle(
            request("GET", "/api/auth/session"),
            session_token=None,
            session_invalid=True,
            now=100,
        )
        self.assertEqual((missing.status_code, decode(missing)["error"]["code"]), (401, "AUTH_REQUIRED"))
        self.assertEqual((malformed.status_code, decode(malformed)["error"]["code"]), (401, "AUTH_SESSION_INVALID"))

    def test_auth_request_and_proof_bounds_fail_closed(self):
        adapter, _, _, _ = make_adapter()
        oversized = ApplicationHttpRequest(
            "POST", "/api/auth/challenges", (), "application/json", b"{" + b"x" * AUTH_REQUEST_MAX_BYTES
        )
        response = adapter.handle(oversized, session_token=None, session_invalid=False, now=100)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(decode(response)["error"]["code"], "AUTH_REQUEST_INVALID")
        self.assertEqual(MAX_PROOF_JSON_BYTES, 48 * 1024)

    def test_capacity_constants_are_exact_approved_ceilings(self):
        self.assertEqual(MAX_OUTSTANDING_CHALLENGES, 128)
        self.assertEqual(MAX_OUTSTANDING_CHALLENGES_PER_BINDING, 4)
        self.assertEqual(MAX_ACTIVE_SESSIONS, 256)
        self.assertEqual(MAX_ACTIVE_SESSIONS_PER_PRINCIPAL, 8)

    def test_m17_5d_document_records_source_only_boundary(self):
        self.assertTrue(DOC.is_file())
        text = DOC.read_text(encoding="utf-8")
        for marker in (
            "MARKETPLACE_APPLICATION_SESSION_ESTABLISHMENT_V1",
            "CredentialMaterialSource",
            "AuthenticationProofVerifier",
            "64 KiB",
            "48 KiB",
            "AUTH_CAPACITY_EXCEEDED",
            "no runtime activation",
            "no credential persistence",
        ):
            self.assertIn(marker, text)


if __name__ == "__main__":
    unittest.main()
