from __future__ import annotations

import base64
import hashlib
import json
import unittest

from marketplace.application.auth import (
    AUTH_PROOF_DOMAIN,
    AUTH_PROOF_PURPOSE,
    MarketplaceApplicationAuthService,
    VerifiedAuthenticationProof,
)
from marketplace.application.auth_enrollment_http import (
    AUTH_ENROLLMENT_ATTESTATION_PREFIX,
    AUTH_ENROLLMENT_CLAIMS_PREFIX,
    AUTH_ENROLLMENT_EVIDENCE_ROUTE,
    AUTH_ENROLLMENT_NONCE_PREFIX,
    AUTH_ENROLLMENT_NONCE_ROUTE,
    EVIDENCE_RESPONSE_TYPE,
    MarketplaceAuthenticationEnrollmentHttpAdapter,
    NONCE_RESPONSE_TYPE,
    PROFILE_NAME,
    WEB_PROPOSAL_PROFILE,
    WEB_PROPOSAL_TYPE,
)
from marketplace.application.auth_enrollment_nonce import (
    MarketplaceAuthenticationEnrollmentNonceAuthority,
)
from marketplace.application.auth_verification_method_evidence import (
    decode_marketplace_authentication_verification_method_evidence_claims,
)
from marketplace.application.http import ApplicationHttpRequest


AUTHORITY = "https://authority.example/auth-enrollment"
PRINCIPAL = "did:example:alice"
METHOD = "did:example:alice#key-1"
OTHER_PRINCIPAL = "did:example:bob"
OTHER_METHOD = "did:example:bob#key-1"
KEY_BYTES = bytes(range(32))
KEY_PAYLOAD = base64.urlsafe_b64encode(KEY_BYTES).rstrip(b"=").decode("ascii")
PUBLIC_KEY = "mkp1_" + KEY_PAYLOAD
SESSION_TOKEN = b"t" * 32
LEASE_SECONDS = 600
NONCE = b"n" * 32


class AllowBinding:
    def verify(self, **_kwargs) -> bool:
        return True


class SequenceMaterialSource:
    def __init__(self, values: list[object]) -> None:
        self.values = list(values)
        self.calls = 0

    def enrollment_nonce_bytes(self):
        self.calls += 1
        if not self.values:
            raise RuntimeError("sensitive material exhaustion")
        value = self.values.pop(0)
        if isinstance(value, BaseException):
            raise value
        return value


class RecordingPolicy:
    def __init__(self, result: object = True) -> None:
        self.result = result
        self.calls = 0

    def approve_authentication_enrollment(self, **_kwargs):
        self.calls += 1
        return self.result


class RecordingAttestor:
    def __init__(self, result: bytes = b"s" * 64, *, raises: bool = False) -> None:
        self.result = result
        self.raises = raises
        self.calls = 0

    def attest_authentication_enrollment(self, _transcript: bytes) -> bytes:
        self.calls += 1
        if self.raises:
            raise RuntimeError("sensitive signer detail")
        return self.result


def authenticated_service(
    *,
    principal: str = PRINCIPAL,
    method: str = METHOD,
    token: bytes = SESSION_TOKEN,
) -> MarketplaceApplicationAuthService:
    auth = MarketplaceApplicationAuthService(principal_binding_verifier=AllowBinding())
    challenge = hashlib.sha256((principal + method).encode("utf-8")).digest()
    auth.register_challenge(
        challenge=challenge,
        principal=principal,
        verification_method=method,
        now=100,
    )
    attempt = auth.begin_challenge_attempt(challenge=challenge, now=100)
    proof = VerifiedAuthenticationProof(
        challenge_sha256=hashlib.sha256(challenge).digest(),
        domain=AUTH_PROOF_DOMAIN,
        proof_purpose=AUTH_PROOF_PURPOSE,
        verification_method=method,
        cryptographically_valid=True,
    )
    auth.authenticate_challenge_attempt(
        attempt=attempt,
        proof=proof,
        session_token=token,
        now=100,
    )
    return auth


def proposal_document(
    *,
    principal: str = PRINCIPAL,
    method: str = METHOD,
    public_key: str = PUBLIC_KEY,
) -> dict[str, object]:
    return {
        "profile": WEB_PROPOSAL_PROFILE,
        "type": WEB_PROPOSAL_TYPE,
        "principal": principal,
        "verificationMethod": method,
        "publicKey": public_key,
    }


def request(
    path: str,
    document: object,
    *,
    method: str = "POST",
    content_type: str | None = "application/json",
    query: tuple[tuple[str, str], ...] = (),
) -> ApplicationHttpRequest:
    body = (
        document
        if type(document) is bytes
        else json.dumps(
            document,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    )
    return ApplicationHttpRequest(
        method=method,
        path=path,
        query=query,
        content_type=content_type,
        body=body,
    )


def response_document(response) -> dict[str, object]:
    return json.loads(response.body.decode("utf-8"))


def decode_carrier(value: str, prefix: str) -> bytes:
    assert value.startswith(prefix)
    payload = value[len(prefix):]
    padding = "=" * ((4 - len(payload) % 4) % 4)
    return base64.urlsafe_b64decode((payload + padding).encode("ascii"))


def adapter(
    *,
    auth: MarketplaceApplicationAuthService | None = None,
    source: SequenceMaterialSource | None = None,
    policy: RecordingPolicy | None = None,
    attestor: RecordingAttestor | None = None,
):
    resolved_auth = auth or authenticated_service()
    resolved_source = source or SequenceMaterialSource([NONCE])
    nonce_authority = MarketplaceAuthenticationEnrollmentNonceAuthority(
        material_source=resolved_source
    )
    resolved_policy = policy or RecordingPolicy()
    resolved_attestor = attestor or RecordingAttestor()
    http = MarketplaceAuthenticationEnrollmentHttpAdapter(
        auth=resolved_auth,
        nonce_authority=nonce_authority,
        policy=resolved_policy,
        attestor=resolved_attestor,
        authority=AUTHORITY,
        evidence_lease_seconds=LEASE_SECONDS,
    )
    return (
        http,
        resolved_auth,
        resolved_source,
        nonce_authority,
        resolved_policy,
        resolved_attestor,
    )


class M176IAuthenticationEnrollmentHttpTests(unittest.TestCase):
    def test_profile_routes_and_response_types_are_exact(self) -> None:
        self.assertEqual(PROFILE_NAME, "MARKETPLACE_APPLICATION_AUTH_ENROLLMENT_HTTP_V1")
        self.assertEqual(
            AUTH_ENROLLMENT_NONCE_ROUTE,
            "/api/authentication-enrollment/nonces",
        )
        self.assertEqual(
            AUTH_ENROLLMENT_EVIDENCE_ROUTE,
            "/api/authentication-enrollment/evidence",
        )
        self.assertEqual(NONCE_RESPONSE_TYPE, "MarketplaceAuthenticationEnrollmentNonce")
        self.assertEqual(
            EVIDENCE_RESPONSE_TYPE,
            "MarketplaceAuthenticationVerificationMethodEvidenceEnvelope",
        )

    def test_unknown_route_and_wrong_method_are_bounded(self) -> None:
        http, *_ = adapter()
        unknown = http.handle(
            request("/api/other", {}),
            session_token=None,
            session_invalid=False,
            now=101,
        )
        self.assertEqual(unknown.status_code, 404)
        wrong_method = http.handle(
            request(AUTH_ENROLLMENT_NONCE_ROUTE, {}, method="GET"),
            session_token=SESSION_TOKEN,
            session_invalid=False,
            now=101,
        )
        self.assertEqual(wrong_method.status_code, 405)
        self.assertIn(("Allow", "POST"), wrong_method.headers)

    def test_authentication_is_required_before_request_parsing(self) -> None:
        http, *_ = adapter()
        malformed = request(AUTH_ENROLLMENT_NONCE_ROUTE, b"{not-json")
        missing = http.handle(
            malformed,
            session_token=None,
            session_invalid=False,
            now=101,
        )
        self.assertEqual(missing.status_code, 401)
        self.assertEqual(response_document(missing)["error"]["code"], "AUTH_REQUIRED")
        invalid = http.handle(
            malformed,
            session_token=b"x" * 31,
            session_invalid=False,
            now=101,
        )
        self.assertEqual(invalid.status_code, 401)
        self.assertEqual(
            response_document(invalid)["error"]["code"],
            "AUTH_SESSION_INVALID",
        )

    def test_nonce_issuance_authorizes_exact_principal_and_returns_canonical_carrier(self) -> None:
        http, auth, source, nonce_authority, policy, attestor = adapter()
        response = http.handle(
            request(
                AUTH_ENROLLMENT_NONCE_ROUTE,
                {
                    "profile": PROFILE_NAME,
                    "proposal": proposal_document(),
                },
            ),
            session_token=SESSION_TOKEN,
            session_invalid=False,
            now=101,
        )
        self.assertEqual(response.status_code, 201)
        self.assertIn(("Cache-Control", "no-store"), response.headers)
        body = response_document(response)
        self.assertEqual(
            frozenset(body),
            frozenset({"expiresAt", "issuedAt", "nonce", "profile", "type"}),
        )
        self.assertEqual(body["profile"], PROFILE_NAME)
        self.assertEqual(body["type"], NONCE_RESPONSE_TYPE)
        self.assertEqual(body["issuedAt"], 101)
        self.assertEqual(body["expiresAt"], 221)
        self.assertEqual(decode_carrier(body["nonce"], AUTH_ENROLLMENT_NONCE_PREFIX), NONCE)
        self.assertEqual(source.calls, 1)
        self.assertEqual(policy.calls, 0)
        self.assertEqual(attestor.calls, 0)
        view = auth.validate_session(session_token=SESSION_TOKEN, now=101)
        self.assertEqual(view.last_used_at, 101)
        self.assertEqual(len(nonce_authority._outstanding), 1)

    def test_nonce_issuance_principal_mismatch_fails_before_material_acquisition(self) -> None:
        source = SequenceMaterialSource([NONCE])
        http, _, _, _, policy, attestor = adapter(source=source)
        response = http.handle(
            request(
                AUTH_ENROLLMENT_NONCE_ROUTE,
                {
                    "profile": PROFILE_NAME,
                    "proposal": proposal_document(
                        principal=OTHER_PRINCIPAL,
                        method=OTHER_METHOD,
                    ),
                },
            ),
            session_token=SESSION_TOKEN,
            session_invalid=False,
            now=101,
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            response_document(response)["error"]["code"],
            "AUTH_PRINCIPAL_MISMATCH",
        )
        self.assertEqual(source.calls, 0)
        self.assertEqual(policy.calls, 0)
        self.assertEqual(attestor.calls, 0)

    def test_client_cannot_supply_authority_or_lease(self) -> None:
        source = SequenceMaterialSource([NONCE])
        http, *_ = adapter(source=source)
        for extra in (
            {"authority": "https://evil.example/authority"},
            {"leaseSeconds": 86400},
        ):
            document = {
                "profile": PROFILE_NAME,
                "proposal": proposal_document(),
                **extra,
            }
            with self.subTest(extra=extra):
                response = http.handle(
                    request(AUTH_ENROLLMENT_NONCE_ROUTE, document),
                    session_token=SESSION_TOKEN,
                    session_invalid=False,
                    now=101,
                )
                self.assertEqual(response.status_code, 400)
        self.assertEqual(source.calls, 0)

    def test_malformed_proposal_query_and_content_type_fail_without_nonce_issue(self) -> None:
        cases = (
            request(
                AUTH_ENROLLMENT_NONCE_ROUTE,
                {"profile": PROFILE_NAME, "proposal": {"profile": WEB_PROPOSAL_PROFILE}},
            ),
            request(
                AUTH_ENROLLMENT_NONCE_ROUTE,
                {"profile": PROFILE_NAME, "proposal": proposal_document()},
                query=(("x", "1"),),
            ),
            request(
                AUTH_ENROLLMENT_NONCE_ROUTE,
                {"profile": PROFILE_NAME, "proposal": proposal_document()},
                content_type="text/plain",
            ),
        )
        for index, req in enumerate(cases):
            source = SequenceMaterialSource([NONCE])
            http, *_ = adapter(source=source)
            with self.subTest(index=index):
                response = http.handle(
                    req,
                    session_token=SESSION_TOKEN,
                    session_invalid=False,
                    now=101,
                )
                self.assertIn(response.status_code, {400, 415})
                self.assertEqual(source.calls, 0)

    def test_successful_enrollment_preserves_exact_evidence_bytes_in_carriers(self) -> None:
        policy = RecordingPolicy()
        attestor = RecordingAttestor()
        http, auth, _, _, _, _ = adapter(policy=policy, attestor=attestor)

        nonce_response = http.handle(
            request(
                AUTH_ENROLLMENT_NONCE_ROUTE,
                {"profile": PROFILE_NAME, "proposal": proposal_document()},
            ),
            session_token=SESSION_TOKEN,
            session_invalid=False,
            now=101,
        )
        nonce_text = response_document(nonce_response)["nonce"]

        evidence_response = http.handle(
            request(
                AUTH_ENROLLMENT_EVIDENCE_ROUTE,
                {
                    "profile": PROFILE_NAME,
                    "proposal": proposal_document(),
                    "nonce": nonce_text,
                },
            ),
            session_token=SESSION_TOKEN,
            session_invalid=False,
            now=102,
        )
        self.assertEqual(evidence_response.status_code, 201)
        body = response_document(evidence_response)
        self.assertEqual(
            frozenset(body),
            frozenset({"attestation", "claims", "profile", "type"}),
        )
        self.assertEqual(body["profile"], PROFILE_NAME)
        self.assertEqual(body["type"], EVIDENCE_RESPONSE_TYPE)
        claims_json = decode_carrier(body["claims"], AUTH_ENROLLMENT_CLAIMS_PREFIX)
        attestation_bytes = decode_carrier(
            body["attestation"],
            AUTH_ENROLLMENT_ATTESTATION_PREFIX,
        )
        self.assertEqual(attestation_bytes, b"s" * 64)
        claims = decode_marketplace_authentication_verification_method_evidence_claims(
            claims_json
        )
        self.assertEqual(claims.authority, AUTHORITY)
        self.assertEqual(claims.issued_at, 102)
        self.assertEqual(claims.expires_at, 702)
        self.assertEqual(claims.entries[0].controller_principal, PRINCIPAL)
        self.assertEqual(claims.entries[0].verification_method, METHOD)
        self.assertEqual(claims.entries[0].public_key, KEY_BYTES)
        self.assertEqual(policy.calls, 1)
        self.assertEqual(attestor.calls, 1)
        self.assertEqual(
            auth.validate_session(session_token=SESSION_TOKEN, now=102).last_used_at,
            102,
        )

    def test_replay_returns_stable_conflict_without_second_policy_or_attestor_call(self) -> None:
        policy = RecordingPolicy()
        attestor = RecordingAttestor()
        http, *_ = adapter(policy=policy, attestor=attestor)
        nonce_response = http.handle(
            request(
                AUTH_ENROLLMENT_NONCE_ROUTE,
                {"profile": PROFILE_NAME, "proposal": proposal_document()},
            ),
            session_token=SESSION_TOKEN,
            session_invalid=False,
            now=101,
        )
        nonce_text = response_document(nonce_response)["nonce"]
        enrollment_request = request(
            AUTH_ENROLLMENT_EVIDENCE_ROUTE,
            {
                "profile": PROFILE_NAME,
                "proposal": proposal_document(),
                "nonce": nonce_text,
            },
        )
        first = http.handle(
            enrollment_request,
            session_token=SESSION_TOKEN,
            session_invalid=False,
            now=102,
        )
        second = http.handle(
            enrollment_request,
            session_token=SESSION_TOKEN,
            session_invalid=False,
            now=103,
        )
        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 409)
        self.assertEqual(
            response_document(second)["error"]["code"],
            "AUTH_ENROLLMENT_UNAVAILABLE",
        )
        self.assertEqual(policy.calls, 1)
        self.assertEqual(attestor.calls, 1)

    def test_malformed_nonce_does_not_burn_valid_nonce(self) -> None:
        policy = RecordingPolicy()
        attestor = RecordingAttestor()
        http, *_ = adapter(policy=policy, attestor=attestor)
        nonce_response = http.handle(
            request(
                AUTH_ENROLLMENT_NONCE_ROUTE,
                {"profile": PROFILE_NAME, "proposal": proposal_document()},
            ),
            session_token=SESSION_TOKEN,
            session_invalid=False,
            now=101,
        )
        nonce_text = response_document(nonce_response)["nonce"]
        malformed = http.handle(
            request(
                AUTH_ENROLLMENT_EVIDENCE_ROUTE,
                {
                    "profile": PROFILE_NAME,
                    "proposal": proposal_document(),
                    "nonce": "mken1_bad",
                },
            ),
            session_token=SESSION_TOKEN,
            session_invalid=False,
            now=102,
        )
        self.assertEqual(malformed.status_code, 400)
        good = http.handle(
            request(
                AUTH_ENROLLMENT_EVIDENCE_ROUTE,
                {
                    "profile": PROFILE_NAME,
                    "proposal": proposal_document(),
                    "nonce": nonce_text,
                },
            ),
            session_token=SESSION_TOKEN,
            session_invalid=False,
            now=102,
        )
        self.assertEqual(good.status_code, 201)
        self.assertEqual(policy.calls, 1)
        self.assertEqual(attestor.calls, 1)

    def test_policy_rejection_burns_nonce_and_hides_policy_cause(self) -> None:
        policy = RecordingPolicy(False)
        attestor = RecordingAttestor()
        http, *_ = adapter(policy=policy, attestor=attestor)
        nonce_response = http.handle(
            request(
                AUTH_ENROLLMENT_NONCE_ROUTE,
                {"profile": PROFILE_NAME, "proposal": proposal_document()},
            ),
            session_token=SESSION_TOKEN,
            session_invalid=False,
            now=101,
        )
        nonce_text = response_document(nonce_response)["nonce"]
        enrollment = request(
            AUTH_ENROLLMENT_EVIDENCE_ROUTE,
            {
                "profile": PROFILE_NAME,
                "proposal": proposal_document(),
                "nonce": nonce_text,
            },
        )
        first = http.handle(
            enrollment,
            session_token=SESSION_TOKEN,
            session_invalid=False,
            now=102,
        )
        second = http.handle(
            enrollment,
            session_token=SESSION_TOKEN,
            session_invalid=False,
            now=103,
        )
        for response in (first, second):
            self.assertEqual(response.status_code, 409)
            text = response.body.decode("utf-8")
            self.assertNotIn("policy", text.lower())
            self.assertNotIn("nonce", text.lower())
        self.assertEqual(policy.calls, 1)
        self.assertEqual(attestor.calls, 0)

    def test_evidence_principal_mismatch_returns_403_without_burning_nonce(self) -> None:
        source = SequenceMaterialSource([NONCE])
        auth = authenticated_service()
        nonce_authority = MarketplaceAuthenticationEnrollmentNonceAuthority(
            material_source=source
        )
        nonce_authority.issue_authentication_enrollment_nonce(
            principal=OTHER_PRINCIPAL,
            verification_method=OTHER_METHOD,
            public_key=PUBLIC_KEY,
            authority=AUTHORITY,
            evidence_lease_seconds=LEASE_SECONDS,
            now=101,
        )
        http = MarketplaceAuthenticationEnrollmentHttpAdapter(
            auth=auth,
            nonce_authority=nonce_authority,
            policy=RecordingPolicy(),
            attestor=RecordingAttestor(),
            authority=AUTHORITY,
            evidence_lease_seconds=LEASE_SECONDS,
        )
        nonce_text = AUTH_ENROLLMENT_NONCE_PREFIX + base64.urlsafe_b64encode(
            NONCE
        ).rstrip(b"=").decode("ascii")
        mismatch = http.handle(
            request(
                AUTH_ENROLLMENT_EVIDENCE_ROUTE,
                {
                    "profile": PROFILE_NAME,
                    "proposal": proposal_document(
                        principal=OTHER_PRINCIPAL,
                        method=OTHER_METHOD,
                    ),
                    "nonce": nonce_text,
                },
            ),
            session_token=SESSION_TOKEN,
            session_invalid=False,
            now=102,
        )
        self.assertEqual(mismatch.status_code, 403)
        self.assertIs(
            nonce_authority.consume_authentication_enrollment_nonce(
                nonce=NONCE,
                principal=OTHER_PRINCIPAL,
                verification_method=OTHER_METHOD,
                public_key=PUBLIC_KEY,
                authority=AUTHORITY,
                issued_at=102,
                expires_at=702,
            ),
            True,
        )

    def test_nonce_material_failure_is_stable_and_nonreflective(self) -> None:
        source = SequenceMaterialSource(
            [RuntimeError("sensitive material-source detail")]
        )
        http, *_ = adapter(source=source)
        response = http.handle(
            request(
                AUTH_ENROLLMENT_NONCE_ROUTE,
                {"profile": PROFILE_NAME, "proposal": proposal_document()},
            ),
            session_token=SESSION_TOKEN,
            session_invalid=False,
            now=101,
        )
        self.assertEqual(response.status_code, 503)
        text = response.body.decode("utf-8")
        self.assertIn("AUTH_ENROLLMENT_NONCE_UNAVAILABLE", text)
        self.assertNotIn("sensitive", text)
        self.assertNotIn(PRINCIPAL, text)


if __name__ == "__main__":
    unittest.main()
