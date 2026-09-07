from __future__ import annotations

import asyncio
import base64
import hashlib
import json
import unittest

from marketplace.application.api import IntentIndexPage
from marketplace.application.asgi import MarketplaceBearerAsgiHttpAdapter
from marketplace.application.auth import (
    AUTH_PROOF_DOMAIN,
    AUTH_PROOF_PURPOSE,
    ApplicationAuthError,
    AuthenticatedProductListingAuthoringService,
    AuthenticatedProposalAuthoringService,
    MarketplaceApplicationAuthService,
    VerifiedAuthenticationProof,
)
from marketplace.application.auth_http import MarketplaceAuthenticatedApplicationHttpAdapter
from marketplace.application.auth_session_asgi import MarketplaceSessionEstablishmentAsgiHttpAdapter
from marketplace.application.auth_session_http import AUTH_REQUEST_MAX_BYTES, MarketplaceAuthenticationSessionHttpAdapter
from marketplace.application.http import MarketplaceApplicationHttpAdapter
from marketplace.application.site_host import MarketplaceSiteHostAdapter
from tests.test_m17_5d_session_establishment import (
    CHALLENGE,
    METHOD,
    PRINCIPAL,
    TOKEN,
    AllowBinding,
    MaterialSource,
    ProofVerifier,
    decode,
    establish,
    make_adapter,
    request,
)


class NullApi:
    def list_intents(self, *, cursor=None, limit=64):
        return IntentIndexPage(("r-root",), None)


class NullWriter:
    def create_product_listing(self, fields):
        return object()

    def create_buyer_request_proposal(self, draft):
        return object()


def _decode_record(body: bytes):
    return json.loads(body.decode("utf-8"))


def _encode_record(record: object) -> bytes:
    return json.dumps(record, sort_keys=True, separators=(",", ":")).encode("utf-8")


def make_asgi_stack():
    source = MaterialSource()
    verifier = ProofVerifier()
    auth = MarketplaceApplicationAuthService(principal_binding_verifier=AllowBinding())
    writer = NullWriter()
    base = MarketplaceApplicationHttpAdapter(
        api=NullApi(),
        decode_record_json=_decode_record,
        encode_record_json=_encode_record,
        create_product_listing=writer.create_product_listing,
        create_proposal=writer.create_buyer_request_proposal,
    )
    protected = MarketplaceAuthenticatedApplicationHttpAdapter(
        base=base,
        auth=auth,
        product_listing_authoring=AuthenticatedProductListingAuthoringService(auth=auth, authoring=writer),
        proposal_authoring=AuthenticatedProposalAuthoringService(auth=auth, authoring=writer),
        decode_record_json=_decode_record,
        create_intent=lambda record: object(),
        respond_to_intent=lambda parent, record: object(),
        record_principal=lambda record: record["issuer"],
    )
    auth_http = MarketplaceAuthenticationSessionHttpAdapter(
        auth=auth,
        material_source=source,
        proof_verifier=verifier,
    )
    site = MarketplaceSiteHostAdapter(
        application_http=base,
        index_html=b"<html>Marketplace</html>",
        app_js=b"console.log('marketplace');",
        styles_css=b"body{}",
    )
    adapter = MarketplaceSessionEstablishmentAsgiHttpAdapter(
        site=site,
        marketplace_http=protected,
        auth_http=auth_http,
        now=lambda: 100,
    )
    return adapter, site, protected, auth, source, verifier


def scope(*, method="GET", path="/api/intents", headers=()):
    return {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": method,
        "scheme": "http",
        "path": path,
        "raw_path": path.encode("ascii"),
        "query_string": b"",
        "root_path": "",
        "headers": list(headers),
        "client": ("127.0.0.1", 12345),
        "server": ("127.0.0.1", 18080),
    }


async def invoke(adapter, request_scope, body=b""):
    pending = [{"type": "http.request", "body": body, "more_body": False}]
    sent = []

    async def receive():
        return pending.pop(0)

    async def send(message):
        sent.append(message)

    await adapter(request_scope, receive, send)
    return sent


def json_headers(body: bytes, *, authorization: bytes | None = None):
    values = [
        (b"content-type", b"application/json"),
        (b"content-length", str(len(body)).encode("ascii")),
    ]
    if authorization is not None:
        values.append((b"authorization", authorization))
    return tuple(values)


def response_document(sent):
    return json.loads(sent[1]["body"].decode("utf-8"))


def proof_for(challenge: bytes, *, valid: bool = True) -> VerifiedAuthenticationProof:
    return VerifiedAuthenticationProof(
        challenge_sha256=hashlib.sha256(challenge).digest(),
        domain=AUTH_PROOF_DOMAIN,
        proof_purpose=AUTH_PROOF_PURPOSE,
        verification_method=METHOD,
        cryptographically_valid=valid,
    )


class RaisingVerifier:
    def __init__(self) -> None:
        self.calls = 0

    def verify(self, proof_document: object):
        self.calls += 1
        raise RuntimeError("sensitive verifier detail")


class RejectBinding:
    def verify(self, *, principal: str, verification_method: str, at_time: int) -> bool:
        return False


class RaisingBinding:
    def verify(self, *, principal: str, verification_method: str, at_time: int) -> bool:
        raise RuntimeError("sensitive binding detail")


class SequenceMaterial:
    def __init__(self, challenges: list[bytes], tokens: list[bytes]) -> None:
        self._challenges = list(challenges)
        self._tokens = list(tokens)
        self.challenge_calls = 0
        self.token_calls = 0

    def challenge_bytes(self) -> bytes:
        self.challenge_calls += 1
        return self._challenges.pop(0)

    def session_token_bytes(self) -> bytes:
        self.token_calls += 1
        return self._tokens.pop(0)


class SequenceVerifier:
    def __init__(self, challenges: list[bytes]) -> None:
        self._challenges = list(challenges)
        self.calls = 0

    def verify(self, proof_document: object) -> VerifiedAuthenticationProof:
        challenge = self._challenges[self.calls]
        self.calls += 1
        return proof_for(challenge)


class M17SessionEstablishmentHardeningTests(unittest.TestCase):
    def test_explicit_asgi_seam_establishes_and_inspects_without_changing_anonymous_reads(self):
        adapter, _, _, _, _, _ = make_asgi_stack()
        challenge_body = json.dumps(
            {"principal": PRINCIPAL, "verification_method": METHOD},
            separators=(",", ":"),
        ).encode("utf-8")
        challenge_sent = asyncio.run(invoke(
            adapter,
            scope(method="POST", path="/api/auth/challenges", headers=json_headers(challenge_body)),
            challenge_body,
        ))
        self.assertEqual(challenge_sent[0]["status"], 201)
        challenge = response_document(challenge_sent)["challenge"]

        session_body = json.dumps(
            {"challenge": challenge, "proof": {"synthetic": True}},
            separators=(",", ":"),
        ).encode("utf-8")
        session_sent = asyncio.run(invoke(
            adapter,
            scope(method="POST", path="/api/auth/sessions", headers=json_headers(session_body)),
            session_body,
        ))
        self.assertEqual(session_sent[0]["status"], 201)
        token_text = response_document(session_sent)["session_token"]
        auth_value = f"Bearer {token_text}".encode("ascii")
        inspect_sent = asyncio.run(invoke(
            adapter,
            scope(path="/api/auth/session", headers=((b"authorization", auth_value),)),
        ))
        self.assertEqual(inspect_sent[0]["status"], 200)
        self.assertEqual(response_document(inspect_sent)["principal"], PRINCIPAL)

        anonymous = asyncio.run(invoke(adapter, scope(path="/api/intents")))
        self.assertEqual(anonymous[0]["status"], 200)
        self.assertEqual(response_document(anonymous)["record_ids"], ["r-root"])

    def test_existing_m17_5c_adapter_does_not_activate_session_establishment_routes(self):
        _, site, protected, _, _, _ = make_asgi_stack()
        legacy = MarketplaceBearerAsgiHttpAdapter(
            site=site,
            application_http=protected,
            now=lambda: 100,
        )
        body = json.dumps(
            {"principal": PRINCIPAL, "verification_method": METHOD},
            separators=(",", ":"),
        ).encode("utf-8")
        sent = asyncio.run(invoke(
            legacy,
            scope(method="POST", path="/api/auth/challenges", headers=json_headers(body)),
            body,
        ))
        self.assertEqual(sent[0]["status"], 404)

    def test_verifier_failure_consumes_challenge_once_without_reflection_or_retry(self):
        verifier = RaisingVerifier()
        adapter, _, source, _ = make_adapter(verifier=verifier)
        challenge_response = adapter.handle(
            request("POST", "/api/auth/challenges", {"principal": PRINCIPAL, "verification_method": METHOD}),
            session_token=None,
            session_invalid=False,
            now=100,
        )
        document = {"challenge": decode(challenge_response)["challenge"], "proof": {"synthetic": True}}
        first = adapter.handle(
            request("POST", "/api/auth/sessions", document),
            session_token=None,
            session_invalid=False,
            now=101,
        )
        second = adapter.handle(
            request("POST", "/api/auth/sessions", document),
            session_token=None,
            session_invalid=False,
            now=102,
        )
        self.assertEqual((first.status_code, decode(first)["error"]["code"]), (503, "AUTH_PROOF_VERIFIER_UNAVAILABLE"))
        self.assertNotIn("sensitive verifier detail", first.body.decode("utf-8"))
        self.assertEqual((second.status_code, decode(second)["error"]["code"]), (401, "AUTH_CHALLENGE_INVALID"))
        self.assertEqual(verifier.calls, 1)
        self.assertEqual(source.token_calls, 0)

    def test_challenge_material_collision_fails_closed_without_retry(self):
        adapter, _, source, _ = make_adapter()
        payload = {"principal": PRINCIPAL, "verification_method": METHOD}
        first = adapter.handle(
            request("POST", "/api/auth/challenges", payload),
            session_token=None,
            session_invalid=False,
            now=100,
        )
        second = adapter.handle(
            request("POST", "/api/auth/challenges", payload),
            session_token=None,
            session_invalid=False,
            now=101,
        )
        self.assertEqual(first.status_code, 201)
        self.assertEqual((second.status_code, decode(second)["error"]["code"]), (503, "AUTH_MATERIAL_UNAVAILABLE"))
        self.assertEqual(source.challenge_calls, 2)

    def test_binding_rejected_and_unavailable_have_distinct_stable_mappings(self):
        for binding, expected in (
            (RejectBinding(), (403, "AUTH_PRINCIPAL_BINDING_REJECTED")),
            (RaisingBinding(), (503, "AUTH_PRINCIPAL_BINDING_UNAVAILABLE")),
        ):
            with self.subTest(expected=expected):
                source = MaterialSource()
                verifier = ProofVerifier()
                auth = MarketplaceApplicationAuthService(principal_binding_verifier=binding)
                adapter = MarketplaceAuthenticationSessionHttpAdapter(
                    auth=auth,
                    material_source=source,
                    proof_verifier=verifier,
                )
                _, response = establish(adapter)
                self.assertEqual((response.status_code, decode(response)["error"]["code"]), expected)
                self.assertNotIn("sensitive binding detail", response.body.decode("utf-8"))

    def test_proof_depth_and_serialized_byte_bounds_fail_before_verifier(self):
        adapter, _, _, verifier = make_adapter()
        challenge_response = adapter.handle(
            request("POST", "/api/auth/challenges", {"principal": PRINCIPAL, "verification_method": METHOD}),
            session_token=None,
            session_invalid=False,
            now=100,
        )
        challenge = decode(challenge_response)["challenge"]
        deep: object = "leaf"
        for _ in range(9):
            deep = {"nested": deep}
        response = adapter.handle(
            request("POST", "/api/auth/sessions", {"challenge": challenge, "proof": deep}),
            session_token=None,
            session_invalid=False,
            now=101,
        )
        self.assertEqual((response.status_code, decode(response)["error"]["code"]), (400, "AUTH_REQUEST_INVALID"))
        self.assertEqual(verifier.calls, 0)

        adapter2, _, _, verifier2 = make_adapter()
        challenge2 = decode(adapter2.handle(
            request("POST", "/api/auth/challenges", {"principal": PRINCIPAL, "verification_method": METHOD}),
            session_token=None,
            session_invalid=False,
            now=100,
        ))["challenge"]
        oversized_proof = {"parts": ["x" * 8000 for _ in range(7)]}
        response2 = adapter2.handle(
            request("POST", "/api/auth/sessions", {"challenge": challenge2, "proof": oversized_proof}),
            session_token=None,
            session_invalid=False,
            now=101,
        )
        self.assertEqual((response2.status_code, decode(response2)["error"]["code"]), (400, "AUTH_REQUEST_INVALID"))
        self.assertEqual(verifier2.calls, 0)

    def test_challenge_capacity_purges_expired_state_before_decision(self):
        auth = MarketplaceApplicationAuthService(principal_binding_verifier=AllowBinding())
        for index in range(4):
            auth.register_challenge(
                challenge=index.to_bytes(32, "big"),
                principal=PRINCIPAL,
                verification_method=METHOD,
                now=0,
            )
        with self.assertRaises(ApplicationAuthError) as caught:
            auth.register_challenge(
                challenge=(9).to_bytes(32, "big"),
                principal=PRINCIPAL,
                verification_method=METHOD,
                now=1,
            )
        self.assertEqual(caught.exception.code, "AUTH_CAPACITY_EXCEEDED")
        auth.register_challenge(
            challenge=(10).to_bytes(32, "big"),
            principal=PRINCIPAL,
            verification_method=METHOD,
            now=120,
        )

    def test_session_capacity_purges_idle_expired_state_before_decision(self):
        auth = MarketplaceApplicationAuthService(principal_binding_verifier=AllowBinding())
        for index in range(8):
            challenge = (100 + index).to_bytes(32, "big")
            token = (200 + index).to_bytes(32, "big")
            now = index * 2
            auth.register_challenge(
                challenge=challenge,
                principal=PRINCIPAL,
                verification_method=METHOD,
                now=now,
            )
            auth.authenticate_challenge(
                challenge=challenge,
                proof=proof_for(challenge),
                session_token=token,
                now=now + 1,
            )
        blocked_challenge = (150).to_bytes(32, "big")
        auth.register_challenge(
            challenge=blocked_challenge,
            principal=PRINCIPAL,
            verification_method=METHOD,
            now=16,
        )
        with self.assertRaises(ApplicationAuthError) as caught:
            auth.authenticate_challenge(
                challenge=blocked_challenge,
                proof=proof_for(blocked_challenge),
                session_token=(250).to_bytes(32, "big"),
                now=17,
            )
        self.assertEqual(caught.exception.code, "AUTH_CAPACITY_EXCEEDED")
        fresh_challenge = (160).to_bytes(32, "big")
        auth.register_challenge(
            challenge=fresh_challenge,
            principal=PRINCIPAL,
            verification_method=METHOD,
            now=1816,
        )
        view = auth.authenticate_challenge(
            challenge=fresh_challenge,
            proof=proof_for(fresh_challenge),
            session_token=(260).to_bytes(32, "big"),
            now=1817,
        )
        self.assertEqual(view.principal, PRINCIPAL)

    def test_auth_asgi_enforces_64k_declared_body_before_receive(self):
        adapter, _, _, _, _, _ = make_asgi_stack()
        oversized = AUTH_REQUEST_MAX_BYTES + 1
        request_scope = scope(
            method="POST",
            path="/api/auth/challenges",
            headers=((b"content-type", b"application/json"), (b"content-length", str(oversized).encode("ascii"))),
        )
        sent = []
        receive_calls = 0

        async def receive():
            nonlocal receive_calls
            receive_calls += 1
            raise AssertionError("oversized auth body must fail before receive")

        async def send(message):
            sent.append(message)

        asyncio.run(adapter(request_scope, receive, send))
        self.assertEqual(receive_calls, 0)
        self.assertEqual(sent[0]["status"], 400)
        self.assertEqual(response_document(sent)["error"]["code"], "AUTH_REQUEST_INVALID")

    def test_static_site_does_not_consult_auth_clock(self):
        _, site, protected, auth, source, verifier = make_asgi_stack()
        auth_http = MarketplaceAuthenticationSessionHttpAdapter(
            auth=auth, material_source=source, proof_verifier=verifier
        )
        def poisoned_clock():
            raise RuntimeError("auth clock must not run for static site")
        adapter = MarketplaceSessionEstablishmentAsgiHttpAdapter(
            site=site, marketplace_http=protected, auth_http=auth_http, now=poisoned_clock
        )
        sent = asyncio.run(invoke(adapter, scope(path="/")))
        self.assertEqual(sent[0]["status"], 200)
        self.assertIn(b"Marketplace", sent[1]["body"])

    def test_expired_session_logout_is_invalid_not_success(self):
        adapter, _, _, _ = make_adapter()
        establish(adapter, now=100)
        response = adapter.handle(
            request("POST", "/api/auth/logout"),
            session_token=TOKEN,
            session_invalid=False,
            now=1901,
        )
        self.assertEqual((response.status_code, decode(response)["error"]["code"]), (401, "AUTH_SESSION_INVALID"))


if __name__ == "__main__":
    unittest.main()
