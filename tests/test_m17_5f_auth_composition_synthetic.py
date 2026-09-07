from __future__ import annotations

import asyncio
import base64
import json
import re
import unittest

from marketplace.application.auth import (
    AuthenticatedProductListingAuthoringService,
    AuthenticatedProposalAuthoringService,
    MarketplaceApplicationAuthService,
)
from marketplace.application.auth_http import MarketplaceAuthenticatedApplicationHttpAdapter
from marketplace.application.auth_session_asgi import MarketplaceSessionEstablishmentAsgiHttpAdapter
from marketplace.application.auth_session_http import MarketplaceAuthenticationSessionHttpAdapter
from marketplace.application.http import MarketplaceApplicationHttpAdapter
from marketplace.application.listing import UNIT_ITEM
from marketplace.application.site_host import MarketplaceSiteHostAdapter
from tests.test_m17_5c_bearer_session_transport import (
    FakeApi,
    RecordingListingAuthoring,
    RecordingProposalAuthoring,
    decode_record,
    encode_record,
)
from tests.test_m17_5d_session_establishment import (
    CHALLENGE,
    METHOD,
    PRINCIPAL,
    TOKEN,
    AllowBinding,
    MaterialSource,
    ProofVerifier,
)
from tests.test_m17_5d_session_establishment_hardening import invoke, scope


TOKEN_TEXT = "mkt1_" + base64.urlsafe_b64encode(TOKEN).rstrip(b"=").decode("ascii")
TOKEN_RE = re.compile(r"^mkt1_[A-Za-z0-9_-]{43}$")
PRINCIPAL_RE = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:\S+$")


class SyntheticClientError(Exception):
    def __init__(self, code: str) -> None:
        super().__init__("synthetic Marketplace client operation failed")
        self.code = code


class Clock:
    def __init__(self, now: int = 100) -> None:
        self.now = now

    def __call__(self) -> int:
        return self.now


class InProcessTransport:
    """Test-only ASGI driver. It never opens a socket or selects runtime composition."""

    def __init__(self, adapter: MarketplaceSessionEstablishmentAsgiHttpAdapter) -> None:
        self.adapter = adapter
        self.calls: list[tuple[str, str, str | None, bytes]] = []

    def execute(
        self,
        method: str,
        path: str,
        *,
        body: bytes = b"",
        authorization: str | None = None,
    ) -> tuple[int, bytes]:
        headers: list[tuple[bytes, bytes]] = []
        if body:
            headers.extend(
                (
                    (b"content-type", b"application/json"),
                    (b"content-length", str(len(body)).encode("ascii")),
                )
            )
        if authorization is not None:
            headers.append((b"authorization", authorization.encode("ascii")))
        self.calls.append((method, path, authorization, body))
        sent = asyncio.run(
            invoke(
                self.adapter,
                scope(method=method, path=path, headers=tuple(headers)),
                body,
            )
        )
        return sent[0]["status"], sent[1]["body"]


class SyntheticMemorySessionClient:
    """Test-only mirror of the reviewed M17.5E memory-session transport contract."""

    def __init__(self, transport: InProcessTransport) -> None:
        self.transport = transport
        self._token: str | None = None
        self._principal: str | None = None

    @property
    def active(self) -> bool:
        return self._token is not None

    def __repr__(self) -> str:
        return f"SyntheticMemorySessionClient(active={self.active})"

    def adopt_established_session(self, *, principal: str, session_token: str) -> None:
        if PRINCIPAL_RE.fullmatch(principal) is None or TOKEN_RE.fullmatch(session_token) is None:
            raise SyntheticClientError("AUTH_SESSION_INVALID")
        self._principal = principal
        self._token = session_token

    def clear(self) -> None:
        self._token = None
        self._principal = None

    def require_principal(self) -> str:
        if self._token is None or self._principal is None:
            raise SyntheticClientError("AUTH_REQUIRED")
        return self._principal

    @staticmethod
    def _authenticated_route(method: str, path: str) -> bool:
        if method == "GET":
            return path == "/api/auth/session"
        if method != "POST":
            return False
        if path in ("/api/auth/logout", "/api/product-listings", "/api/intents"):
            return True
        if not path.startswith("/api/intents/"):
            return False
        parts = path.removeprefix("/api/intents/").split("/")
        if len(parts) != 2 or not parts[0] or "?" in parts[0] or "#" in parts[0]:
            return False
        return parts[1] in ("responses", "proposals")

    def _authorization_for(self, method: str, path: str) -> str | None:
        if not self._authenticated_route(method, path):
            return None
        if self._token is None:
            raise SyntheticClientError("AUTH_REQUIRED")
        return f"Bearer {self._token}"

    def _decode(self, status: int, body: bytes) -> dict[str, object]:
        document = json.loads(body.decode("utf-8")) if body else {}
        if 200 <= status <= 299:
            return document
        error = document.get("error") if isinstance(document, dict) else None
        code = error.get("code") if isinstance(error, dict) else None
        stable_code = code if isinstance(code, str) else f"HTTP_{status}"
        if stable_code == "AUTH_SESSION_INVALID":
            self.clear()
        raise SyntheticClientError(stable_code)

    def request(self, method: str, path: str, *, document: object | None = None) -> dict[str, object]:
        body = (
            b""
            if document is None
            else json.dumps(document, sort_keys=True, separators=(",", ":")).encode("utf-8")
        )
        authorization = self._authorization_for(method, path)
        status, response_body = self.transport.execute(
            method,
            path,
            body=body,
            authorization=authorization,
        )
        return self._decode(status, response_body)

    def establish(self) -> dict[str, object]:
        challenge = self.request(
            "POST",
            "/api/auth/challenges",
            document={"principal": PRINCIPAL, "verification_method": METHOD},
        )
        session = self.request(
            "POST",
            "/api/auth/sessions",
            document={"challenge": challenge["challenge"], "proof": {"synthetic": True}},
        )
        token = session.get("session_token")
        principal = session.get("principal")
        if not isinstance(token, str) or not isinstance(principal, str):
            raise SyntheticClientError("AUTH_SESSION_INVALID")
        self.adopt_established_session(principal=principal, session_token=token)
        return session

    def list_intents(self) -> dict[str, object]:
        return self.request("GET", "/api/intents")

    def inspect_session(self) -> dict[str, object]:
        return self.request("GET", "/api/auth/session")

    def create_product_listing(self, fields: dict[str, object]) -> dict[str, object]:
        if "seller_principal" in fields:
            raise SyntheticClientError("AUTH_PRINCIPAL_MISMATCH")
        document = dict(fields)
        document["seller_principal"] = self.require_principal()
        return self.request("POST", "/api/product-listings", document=document)

    def create_proposal(self, parent_id: str, fields: dict[str, object]) -> dict[str, object]:
        if "buyer_principal" in fields:
            raise SyntheticClientError("AUTH_PRINCIPAL_MISMATCH")
        document = dict(fields)
        document["buyer_principal"] = self.require_principal()
        return self.request("POST", f"/api/intents/{parent_id}/proposals", document=document)

    def create_raw_intent(self, record: dict[str, object]) -> dict[str, object]:
        if record.get("issuer") != self.require_principal():
            raise SyntheticClientError("AUTH_PRINCIPAL_MISMATCH")
        return self.request("POST", "/api/intents", document=record)

    def logout(self) -> dict[str, object]:
        if self._token is None:
            raise SyntheticClientError("AUTH_REQUIRED")
        authorization = f"Bearer {self._token}"
        self.clear()
        status, response_body = self.transport.execute(
            "POST",
            "/api/auth/logout",
            authorization=authorization,
        )
        return self._decode(status, response_body)


class FailingLogoutTransport:
    def __init__(self, client: SyntheticMemorySessionClient) -> None:
        self.client = client
        self.calls = 0

    def execute(self, method: str, path: str, *, body: bytes = b"", authorization: str | None = None):
        self.calls += 1
        if method != "POST" or path != "/api/auth/logout":
            raise AssertionError("unexpected synthetic transport call")
        if self.client.active:
            raise AssertionError("logout transport was attempted before local clear")
        raise RuntimeError("synthetic transport failure")


def make_stack():
    source = MaterialSource(challenge=CHALLENGE, token=TOKEN)
    verifier = ProofVerifier()
    auth = MarketplaceApplicationAuthService(principal_binding_verifier=AllowBinding())
    api = FakeApi()
    listing = RecordingListingAuthoring()
    proposal = RecordingProposalAuthoring()
    base = MarketplaceApplicationHttpAdapter(
        api=api,
        decode_record_json=decode_record,
        encode_record_json=encode_record,
        create_product_listing=listing.create_product_listing,
        create_proposal=proposal.create_buyer_request_proposal,
    )
    protected = MarketplaceAuthenticatedApplicationHttpAdapter(
        base=base,
        auth=auth,
        product_listing_authoring=AuthenticatedProductListingAuthoringService(auth=auth, authoring=listing),
        proposal_authoring=AuthenticatedProposalAuthoringService(auth=auth, authoring=proposal),
        decode_record_json=decode_record,
        create_intent=api.create_intent,
        respond_to_intent=api.respond_to_intent,
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
    clock = Clock()
    adapter = MarketplaceSessionEstablishmentAsgiHttpAdapter(
        site=site,
        marketplace_http=protected,
        auth_http=auth_http,
        now=clock,
    )
    transport = InProcessTransport(adapter)
    client = SyntheticMemorySessionClient(transport)
    return client, transport, auth, source, verifier, api, listing, proposal, clock


def listing_fields() -> dict[str, object]:
    return {
        "subject_uri": "urn:example:item:m17-5f",
        "title": "synthetic item",
        "description": "deterministic fixture",
        "consideration_coefficient": 1,
        "consideration_scale": 0,
        "currency_code": "EUR",
        "quantity_coefficient": 1,
        "quantity_scale": 0,
        "unit_uri": UNIT_ITEM,
        "latitude_e6": 1,
        "longitude_e6": 1,
    }


def proposal_fields() -> dict[str, object]:
    return {
        "subject_uri": "urn:example:item:m17-5f",
        "action_uri": "https://example.test/actions/synthetic-buy",
    }


class M175FSyntheticAuthCompositionTests(unittest.TestCase):
    def test_challenge_session_inspection_and_anonymous_read_compose_end_to_end(self):
        client, transport, _, source, verifier, api, _, _, clock = make_stack()
        session = client.establish()
        self.assertEqual(session["session_token"], TOKEN_TEXT)
        self.assertEqual(session["principal"], PRINCIPAL)
        self.assertTrue(client.active)
        self.assertEqual(source.challenge_calls, 1)
        self.assertEqual(source.token_calls, 1)
        self.assertEqual(verifier.calls, 1)

        clock.now = 120
        inspected = client.inspect_session()
        self.assertEqual(inspected["principal"], PRINCIPAL)
        self.assertEqual(inspected["verification_method"], METHOD)
        self.assertEqual(inspected["last_used_at"], 100)
        self.assertNotIn("session_token", inspected)
        self.assertNotIn("challenge", inspected)
        self.assertNotIn("proof", inspected)

        anonymous = client.list_intents()
        self.assertEqual(anonymous["record_ids"], ["r-root"])
        self.assertEqual(api.calls, [])
        self.assertIsNone(transport.calls[-1][2])
        self.assertEqual(transport.calls[-1][:2], ("GET", "/api/intents"))

    def test_structured_writes_derive_exact_session_principal(self):
        client, _, _, _, _, _, listing, proposal, _ = make_stack()
        client.establish()
        listing_result = client.create_product_listing(listing_fields())
        proposal_result = client.create_proposal("r-parent", proposal_fields())
        self.assertEqual(listing_result, {"change_seq": 9, "disposition": "STORED"})
        self.assertEqual(proposal_result, {"change_seq": 10, "disposition": "STORED"})
        self.assertEqual(listing.calls[0].seller_principal, PRINCIPAL)
        self.assertEqual(proposal.calls[0].buyer_principal, PRINCIPAL)

    def test_missing_local_session_and_principal_override_fail_before_dispatch(self):
        client, transport, _, _, _, _, _, _, _ = make_stack()
        with self.assertRaises(SyntheticClientError) as missing:
            client.create_product_listing(listing_fields())
        self.assertEqual(missing.exception.code, "AUTH_REQUIRED")
        self.assertEqual(transport.calls, [])

        client.establish()
        before = len(transport.calls)
        hostile = listing_fields()
        hostile["seller_principal"] = "did:example:other"
        with self.assertRaises(SyntheticClientError) as override:
            client.create_product_listing(hostile)
        self.assertEqual(override.exception.code, "AUTH_PRINCIPAL_MISMATCH")
        self.assertEqual(len(transport.calls), before)

    def test_raw_issuer_mismatch_fails_before_server_dispatch(self):
        client, transport, _, _, _, api, _, _, _ = make_stack()
        client.establish()
        before = len(transport.calls)
        with self.assertRaises(SyntheticClientError) as mismatch:
            client.create_raw_intent({"issuer": "did:example:other", "kind": "synthetic"})
        self.assertEqual(mismatch.exception.code, "AUTH_PRINCIPAL_MISMATCH")
        self.assertEqual(len(transport.calls), before)
        self.assertEqual(api.calls, [])

    def test_server_session_invalidation_clears_local_memory_session(self):
        client, transport, _, _, _, _, _, _, _ = make_stack()
        client.establish()
        authorization = f"Bearer {TOKEN_TEXT}"
        status, _ = transport.execute("POST", "/api/auth/logout", authorization=authorization)
        self.assertEqual(status, 200)
        self.assertTrue(client.active)

        with self.assertRaises(SyntheticClientError) as invalid:
            client.inspect_session()
        self.assertEqual(invalid.exception.code, "AUTH_SESSION_INVALID")
        self.assertFalse(client.active)

    def test_logout_is_local_first_single_attempt_and_never_restores_session(self):
        client, _, _, _, _, _, _, _, _ = make_stack()
        client.adopt_established_session(principal=PRINCIPAL, session_token=TOKEN_TEXT)
        failing = FailingLogoutTransport(client)
        client.transport = failing  # test-only transport substitution; no runtime composition change.
        with self.assertRaises(RuntimeError):
            client.logout()
        self.assertEqual(failing.calls, 1)
        self.assertFalse(client.active)
        self.assertNotIn(TOKEN_TEXT, repr(client))

    def test_new_client_instance_has_no_credential_recovery(self):
        client, transport, _, _, _, _, _, _, _ = make_stack()
        client.establish()
        self.assertTrue(client.active)
        restarted = SyntheticMemorySessionClient(transport)
        self.assertFalse(restarted.active)
        with self.assertRaises(SyntheticClientError) as missing:
            restarted.inspect_session()
        self.assertEqual(missing.exception.code, "AUTH_REQUIRED")


if __name__ == "__main__":
    unittest.main()
