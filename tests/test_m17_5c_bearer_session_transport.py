from __future__ import annotations

import asyncio
import base64
import hashlib
import json
from pathlib import Path
import unittest

from marketplace.application.auth import (
    AUTH_PROOF_DOMAIN,
    AUTH_PROOF_PURPOSE,
    AuthenticatedProductListingAuthoringService,
    AuthenticatedProposalAuthoringService,
    MarketplaceApplicationAuthService,
    VerifiedAuthenticationProof,
)
from marketplace.application.asgi import (
    AsgiHttpAdapterError,
    MarketplaceAsgiHttpAdapter,
    MarketplaceBearerAsgiHttpAdapter,
)
from marketplace.application.bearer import (
    MarketplaceBearerTransportError,
    parse_marketplace_bearer_authorization,
)
from marketplace.application.http import (
    ApplicationHttpResponse,
    MarketplaceApplicationHttpAdapter,
    MarketplaceAuthenticatedApplicationHttpAdapter,
)
from marketplace.application.postgres_state import ApplicationStatePutResult, StoreDisposition
from marketplace.application.site_host import MarketplaceSiteHostAdapter
from marketplace.application.listing import ExactDecimal, ProductListingDraft, UNIT_ITEM
from marketplace.reference.application_record_v1 import marketplace_record_issuer_principal
from marketplace.reference.product_listing_v1 import build_product_listing_record


ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs" / "m17-5c-bearer-session-transport.md"
TOKEN = bytes(range(32))
OTHER_TOKEN = bytes(range(1, 33))
AUTH_VALUE = b"Bearer mkt1_" + base64.urlsafe_b64encode(TOKEN).rstrip(b"=")
PRINCIPAL = "did:example:seller"
METHOD = "did:example:seller#key-1"


class AllowBinding:
    def verify(self, *, principal: str, verification_method: str, at_time: int) -> bool:
        return principal == PRINCIPAL and verification_method == METHOD and at_time >= 0


class FakeApi:
    def __init__(self) -> None:
        self.calls: list[tuple[object, ...]] = []

    def list_intents(self, *, cursor=None, limit=64):
        from marketplace.application.api import IntentIndexPage
        return IntentIndexPage(("r-root",), None)
    def create_intent(self, record):
        self.calls.append(("create_intent", record))
        return ApplicationStatePutResult(StoreDisposition.STORED, 7)

    def respond_to_intent(self, parent_record_id, record):
        self.calls.append(("respond_to_intent", parent_record_id, record))
        return ApplicationStatePutResult(StoreDisposition.STORED, 8)

    def get_intent(self, record_id):
        return None

    def list_responses(self, parent_record_id, *, limit=64):
        return ()

    def sync_watermark(self):
        return 0


class RecordingListingAuthoring:
    def __init__(self) -> None:
        self.calls = []

    def create_product_listing(self, fields):
        self.calls.append(fields)
        return ApplicationStatePutResult(StoreDisposition.STORED, 9)


class RecordingProposalAuthoring:
    def __init__(self) -> None:
        self.calls = []
    def create_buyer_request_proposal(self, draft):
        self.calls.append(draft)
        return ApplicationStatePutResult(StoreDisposition.STORED, 10)


def decode_record(body: bytes):
    return json.loads(body.decode("utf-8"))


def encode_record(record: object) -> bytes:
    return json.dumps(record, sort_keys=True, separators=(",", ":")).encode("utf-8")


def make_active_auth() -> MarketplaceApplicationAuthService:
    auth = MarketplaceApplicationAuthService(principal_binding_verifier=AllowBinding())
    challenge = b"c" * 32
    auth.register_challenge(
        challenge=challenge,
        principal=PRINCIPAL,
        verification_method=METHOD,
        now=100,
    )
    proof = VerifiedAuthenticationProof(
        challenge_sha256=hashlib.sha256(challenge).digest(),
        domain=AUTH_PROOF_DOMAIN,
        proof_purpose=AUTH_PROOF_PURPOSE,
        verification_method=METHOD,
        cryptographically_valid=True,
    )
    auth.authenticate_challenge(
        challenge=challenge,
        proof=proof,
        session_token=TOKEN,
        now=101,
    )
    return auth


def make_stack():
    api = FakeApi()
    listing = RecordingListingAuthoring()
    proposal = RecordingProposalAuthoring()
    auth = make_active_auth()
    base = MarketplaceApplicationHttpAdapter(
        api=api,
        decode_record_json=decode_record,
        encode_record_json=encode_record,
        create_product_listing=listing.create_product_listing,
        create_proposal=proposal.create_buyer_request_proposal,
    )
    guarded_listing = AuthenticatedProductListingAuthoringService(auth=auth, authoring=listing)
    guarded_proposal = AuthenticatedProposalAuthoringService(auth=auth, authoring=proposal)
    protected = MarketplaceAuthenticatedApplicationHttpAdapter(
        base=base,
        auth=auth,
        product_listing_authoring=guarded_listing,
        proposal_authoring=guarded_proposal,
        record_principal=lambda record: record["issuer"],
    )
    site = MarketplaceSiteHostAdapter(
        application_http=base,
        index_html=b"<html>Marketplace</html>",
        app_js=b"console.log('marketplace');",
        styles_css=b"body{}",
    )
    adapter = MarketplaceBearerAsgiHttpAdapter(
        site=site,
        application_http=protected,
        now=lambda: 102,
    )
    return adapter, api, listing, proposal


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


def response_document(sent):
    return json.loads(sent[1]["body"].decode("utf-8"))


def json_headers(body: bytes, *, authorization: bytes | None = None):
    values = [
        (b"content-type", b"application/json"),
        (b"content-length", str(len(body)).encode("ascii")),
    ]
    if authorization is not None:
        values.append((b"authorization", authorization))
    return tuple(values)


class M17BearerSessionTransportTests(unittest.TestCase):
    def test_exact_bearer_grammar_decodes_32_byte_token(self):
        self.assertEqual(len(AUTH_VALUE), 55)
        self.assertEqual(parse_marketplace_bearer_authorization(AUTH_VALUE), TOKEN)
    def test_bearer_grammar_rejects_noncanonical_forms(self):
        payload = AUTH_VALUE.split(b"mkt1_", 1)[1]
        cases = (
            b"bearer mkt1_" + payload,
            b"Bearer  mkt1_" + payload,
            b"Bearer mkt2_" + payload,
            b"Bearer mkt1_" + payload + b"=",
            b"Bearer mkt1_" + payload[:-1],
            b"Bearer mkt1_" + payload[:-1] + b"+",
            b" Bearer mkt1_" + payload,
            b"Bearer mkt1_" + payload + b" ",
        )
        for value in cases:
            with self.subTest(value=value):
                with self.assertRaises(MarketplaceBearerTransportError):
                    parse_marketplace_bearer_authorization(value)

    def test_anonymous_read_remains_unchanged_without_credential(self):
        adapter, api, _, _ = make_stack()
        sent = asyncio.run(invoke(adapter, scope()))
        self.assertEqual(sent[0]["status"], 200)
        self.assertEqual(response_document(sent), {"next_cursor": None, "record_ids": ["r-root"]})
        self.assertEqual(api.calls, [])

    def test_bearer_on_anonymous_read_fails_closed(self):
        adapter, _, _, _ = make_stack()
        sent = asyncio.run(invoke(adapter, scope(headers=((b"authorization", AUTH_VALUE),))))
        self.assertEqual(sent[0]["status"], 401)
        self.assertEqual(response_document(sent)["error"]["code"], "AUTH_SESSION_INVALID")
    def test_each_protected_write_requires_bearer_before_authoring(self):
        cases = (
            ("/api/intents", b"{}"),
            ("/api/product-listings", b"{}"),
            ("/api/intents/r-parent/proposals", b"{}"),
            ("/api/intents/r-parent/responses", b"{}"),
        )
        for path, body in cases:
            with self.subTest(path=path):
                adapter, api, listing, proposal = make_stack()
                sent = asyncio.run(
                    invoke(adapter, scope(method="POST", path=path, headers=json_headers(body)), body)
                )
                self.assertEqual(sent[0]["status"], 401)
                self.assertEqual(response_document(sent)["error"]["code"], "AUTH_REQUIRED")
                self.assertEqual(api.calls, [])
                self.assertEqual(listing.calls, [])
                self.assertEqual(proposal.calls, [])

    def test_invalid_session_is_non_reflective_401(self):
        adapter, api, listing, _ = make_stack()
        body = product_listing_body(PRINCIPAL)
        bad = b"Bearer mkt1_" + base64.urlsafe_b64encode(OTHER_TOKEN).rstrip(b"=")
        sent = asyncio.run(
            invoke(adapter, scope(method="POST", path="/api/product-listings", headers=json_headers(body, authorization=bad)), body)
        )
        self.assertEqual(sent[0]["status"], 401)
        text = sent[1]["body"].decode("utf-8")
        self.assertIn("AUTH_SESSION_INVALID", text)
        self.assertNotIn(bad.decode("ascii"), text)
        self.assertEqual(api.calls, [])
        self.assertEqual(listing.calls, [])
    def test_structured_listing_uses_session_bound_principal(self):
        adapter, api, listing, _ = make_stack()
        body = product_listing_body(PRINCIPAL)
        sent = asyncio.run(
            invoke(adapter, scope(method="POST", path="/api/product-listings", headers=json_headers(body, authorization=AUTH_VALUE)), body)
        )
        self.assertEqual(sent[0]["status"], 201)
        self.assertEqual(response_document(sent), {"change_seq": 9, "disposition": "STORED"})
        self.assertEqual(len(listing.calls), 1)
        self.assertEqual(listing.calls[0].seller_principal, PRINCIPAL)
        self.assertEqual(api.calls, [])

    def test_structured_listing_principal_mismatch_is_403_before_write(self):
        adapter, api, listing, _ = make_stack()
        body = product_listing_body("did:example:other")
        sent = asyncio.run(
            invoke(adapter, scope(method="POST", path="/api/product-listings", headers=json_headers(body, authorization=AUTH_VALUE)), body)
        )
        self.assertEqual(sent[0]["status"], 403)
        self.assertEqual(response_document(sent)["error"]["code"], "AUTH_PRINCIPAL_MISMATCH")
        self.assertEqual(listing.calls, [])
        self.assertEqual(api.calls, [])

    def test_structured_proposal_uses_session_bound_principal(self):
        adapter, _, _, proposal = make_stack()
        body = proposal_body(PRINCIPAL)
        sent = asyncio.run(
            invoke(adapter, scope(method="POST", path="/api/intents/r-parent/proposals", headers=json_headers(body, authorization=AUTH_VALUE)), body)
        )
        self.assertEqual(sent[0]["status"], 201)
        self.assertEqual(len(proposal.calls), 1)
        self.assertEqual(proposal.calls[0].buyer_principal, PRINCIPAL)
    def test_raw_intent_and_response_require_exact_record_issuer(self):
        for path, call_name in (
            ("/api/intents", "create_intent"),
            ("/api/intents/r-parent/responses", "respond_to_intent"),
        ):
            with self.subTest(path=path):
                adapter, api, _, _ = make_stack()
                body = json.dumps({"issuer": PRINCIPAL, "kind": "synthetic"}, separators=(",", ":")).encode("utf-8")
                sent = asyncio.run(
                    invoke(adapter, scope(method="POST", path=path, headers=json_headers(body, authorization=AUTH_VALUE)), body)
                )
                self.assertEqual(sent[0]["status"], 201)
                self.assertEqual(api.calls[0][0], call_name)

    def test_raw_record_principal_mismatch_fails_before_api_write(self):
        adapter, api, _, _ = make_stack()
        body = b'{"issuer":"did:example:other","kind":"synthetic"}'
        sent = asyncio.run(
            invoke(adapter, scope(method="POST", path="/api/intents", headers=json_headers(body, authorization=AUTH_VALUE)), body)
        )
        self.assertEqual(sent[0]["status"], 403)
        self.assertEqual(response_document(sent)["error"]["code"], "AUTH_PRINCIPAL_MISMATCH")
        self.assertEqual(api.calls, [])

    def test_duplicate_authorization_and_cookie_paths_fail_closed(self):
        adapter, _, _, _ = make_stack()
        duplicate = ((b"authorization", AUTH_VALUE), (b"authorization", AUTH_VALUE))
        with self.assertRaises(AsgiHttpAdapterError):
            asyncio.run(invoke(adapter, scope(headers=duplicate)))
        for name in (b"cookie", b"proxy-authorization"):
            with self.subTest(name=name):
                with self.assertRaises(AsgiHttpAdapterError):
                    asyncio.run(invoke(adapter, scope(headers=((name, b"secret"),))))
    def test_legacy_asgi_adapter_remains_credential_negative(self):
        _, _, _, _ = make_stack()
        base = MarketplaceApplicationHttpAdapter(
            api=FakeApi(),
            decode_record_json=decode_record,
            encode_record_json=encode_record,
            create_product_listing=RecordingListingAuthoring().create_product_listing,
            create_proposal=RecordingProposalAuthoring().create_buyer_request_proposal,
        )
        site = MarketplaceSiteHostAdapter(
            application_http=base,
            index_html=b"<html>Marketplace</html>",
            app_js=b"console.log('marketplace');",
            styles_css=b"body{}",
        )
        adapter = MarketplaceAsgiHttpAdapter(site=site)
        with self.assertRaises(AsgiHttpAdapterError) as caught:
            asyncio.run(invoke(adapter, scope(headers=((b"authorization", AUTH_VALUE),))))
        self.assertEqual(caught.exception.code, "ASGI_SENSITIVE_HEADER_FORBIDDEN")

    def test_reference_record_issuer_extractor_is_exact(self):
        record = build_product_listing_record(
            ProductListingDraft(
                seller_principal=PRINCIPAL,
                subject_uri="urn:example:item:x",
                title="x",
                description="x",
                consideration=ExactDecimal(1, 0),
                currency_code="EUR",
                quantity=ExactDecimal(1, 0),
                unit_uri=UNIT_ITEM,
                latitude_e6=1,
                longitude_e6=1,
            )
        )
        self.assertEqual(marketplace_record_issuer_principal(record), PRINCIPAL)
    def test_malformed_bearer_is_mapped_to_stable_non_reflective_401(self):
        adapter, _, _, _ = make_stack()
        body = product_listing_body(PRINCIPAL)
        hostile = b"Bearer mkt1_not-a-secret-but-hostile"
        sent = asyncio.run(
            invoke(adapter, scope(method="POST", path="/api/product-listings", headers=json_headers(body, authorization=hostile)), body)
        )
        self.assertEqual(sent[0]["status"], 401)
        text = sent[1]["body"].decode("utf-8")
        self.assertIn("AUTH_SESSION_INVALID", text)
        self.assertNotIn(hostile.decode("ascii"), text)

    def test_m17_5c_document_records_source_only_security_boundary(self):
        self.assertTrue(DOC.is_file())
        document = DOC.read_text(encoding="utf-8")
        for marker in (
            "MARKETPLACE_APPLICATION_BEARER_V1",
            "request-lifetime only",
            "anonymous reads",
            "AUTH_REQUIRED",
            "AUTH_SESSION_INVALID",
            "AUTH_PRINCIPAL_MISMATCH",
            "no runtime activation",
            "no credential persistence",
        ):
            self.assertIn(marker, document)


def product_listing_body(principal: str) -> bytes:
    return json.dumps(
        {
            "seller_principal": principal,
            "subject_uri": "urn:example:item:x",
            "title": "x",
            "description": "x",
            "consideration_coefficient": 1,
            "consideration_scale": 0,
            "currency_code": "EUR",
            "quantity_coefficient": 1,
            "quantity_scale": 0,
            "unit_uri": UNIT_ITEM,
            "latitude_e6": 1,
            "longitude_e6": 1,
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def proposal_body(principal: str) -> bytes:
    return json.dumps(
        {
            "buyer_principal": principal,
            "subject_uri": "urn:example:item:x",
            "action_uri": "https://example.test/actions/buy",
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


if __name__ == "__main__":
    unittest.main()
