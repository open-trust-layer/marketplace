from __future__ import annotations

import asyncio
import base64
import hashlib
import json
from pathlib import Path
import unittest

from marketplace.application.agreement_publication_http import (
    MarketplaceAuthenticatedAgreementPublicationHttpAdapter,
)
from marketplace.application.auth import (
    AUTH_PROOF_DOMAIN,
    AUTH_PROOF_PURPOSE,
    MarketplaceApplicationAuthService,
    VerifiedAuthenticationProof,
)
from marketplace.application.auth_session_asgi import (
    MarketplaceSessionEstablishmentAsgiHttpAdapter,
)
from marketplace.application.auth_session_http import (
    MarketplaceAuthenticationSessionHttpAdapter,
)
from marketplace.application.fulfillment_completion_http import (
    MarketplaceAuthenticatedFulfillmentCompletionHttpAdapter,
)
from marketplace.application.fulfillment_completion_publication import (
    CLAIMED_COMPLETE_PERFORMANCE,
    FulfillmentEvidencePublicationResult,
    MarketplaceFulfillmentCompletionPublicationService,
)
from marketplace.application.http import _json_response
from marketplace.application.postgres_state import StoreDisposition
from marketplace.application.site_host import MarketplaceSiteHostAdapter


ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "web" / "app.js"
INDEX = ROOT / "web" / "index.html"
BOOTSTRAP = ROOT / "web" / "auth_bootstrap.js"
SESSION = ROOT / "web" / "client_session.js"
SITE_HOST = ROOT / "src" / "marketplace" / "application" / "site_host.py"
LOCALHOST = ROOT / "tools" / "marketplace_localhost.py"
DOC = ROOT / "docs" / "m17-7m-authenticated-completion-flight-acceptance.md"

TOKEN = bytes(range(32))
AUTH_VALUE = b"Bearer mkt1_" + base64.urlsafe_b64encode(TOKEN).rstrip(b"=")
SELLER = "did:example:seller"
METHOD = "did:example:seller#key-1"
AGREEMENT = "r1_" + "G" * 43
PROPOSAL = "r1_" + "P" * 43
ACCEPTANCE = "r1_" + "A" * 43
EVENT = "r1_" + "E" * 43
COMMITMENT = "seller-delivery"


class AllowBinding:
    def verify(self, *, principal: str, verification_method: str, at_time: int) -> bool:
        return (
            principal == SELLER
            and verification_method == METHOD
            and at_time >= 0
        )


def active_auth() -> MarketplaceApplicationAuthService:
    auth = MarketplaceApplicationAuthService(principal_binding_verifier=AllowBinding())
    challenge = b"c" * 32
    auth.register_challenge(
        challenge=challenge,
        principal=SELLER,
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


def json_body(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


def scope(*, path: str, body: bytes, authorization: bytes | None):
    headers = [
        (b"content-type", b"application/json"),
        (b"content-length", str(len(body)).encode("ascii")),
    ]
    if authorization is not None:
        headers.append((b"authorization", authorization))
    return {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "POST",
        "scheme": "http",
        "path": path,
        "raw_path": path.encode("ascii"),
        "query_string": b"",
        "root_path": "",
        "headers": headers,
        "client": ("127.0.0.1", 49152),
        "server": ("127.0.0.1", 18080),
    }


async def invoke(adapter, request_scope, body: bytes):
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


def final_asgi():
    auth = active_auth()

    base = object.__new__(MarketplaceAuthenticatedAgreementPublicationHttpAdapter)
    delegated = []

    def handle_base(request, *, session_token, session_invalid, now):
        delegated.append(
            {
                "path": request.path,
                "session_token": session_token,
                "session_invalid": session_invalid,
                "now": now,
            }
        )
        return _json_response(
            201,
            "Created",
            {
                "agreement_record_id": AGREEMENT,
                "change_seq": 40,
                "disposition": "STORED",
            },
        )

    base.handle = handle_base

    publication = object.__new__(MarketplaceFulfillmentCompletionPublicationService)
    calls = []

    def publish_claimed_complete_performance(**kwargs):
        calls.append(kwargs)
        return FulfillmentEvidencePublicationResult(
            record_id=EVENT,
            agreement_record_id=kwargs["agreement_record_id"],
            commitment_id=kwargs["commitment_id"],
            evidence_kind=CLAIMED_COMPLETE_PERFORMANCE,
            disposition=StoreDisposition.STORED,
            change_seq=41,
        )

    publication.publish_claimed_complete_performance = publish_claimed_complete_performance
    publication.publish_commitment_acceptance = lambda **_kwargs: (_ for _ in ()).throw(
        AssertionError("unexpected acceptance publication")
    )
    publication.publish_commitment_completion = lambda **_kwargs: (_ for _ in ()).throw(
        AssertionError("unexpected completion publication")
    )

    fulfillment = MarketplaceAuthenticatedFulfillmentCompletionHttpAdapter(
        base=base,
        auth=auth,
        publication=publication,
    )
    site = object.__new__(MarketplaceSiteHostAdapter)
    auth_http = object.__new__(MarketplaceAuthenticationSessionHttpAdapter)
    asgi = MarketplaceSessionEstablishmentAsgiHttpAdapter(
        site=site,
        marketplace_http=fulfillment,
        auth_http=auth_http,
        now=lambda: 102,
    )
    return asgi, calls, delegated


class M177MAuthenticatedCompletionFlightAcceptanceTests(unittest.TestCase):
    def test_final_asgi_publishes_exact_seller_claim_from_bearer_session(self) -> None:
        asgi, calls, delegated = final_asgi()
        body = json_body({"evidence_kind": CLAIMED_COMPLETE_PERFORMANCE})
        path = (
            f"/api/agreements/{AGREEMENT}/commitments/"
            f"{COMMITMENT}/completion-evidence"
        )

        sent = asyncio.run(
            invoke(
                asgi,
                scope(path=path, body=body, authorization=AUTH_VALUE),
                body,
            )
        )

        self.assertEqual(sent[0]["status"], 201)
        self.assertEqual(
            response_document(sent),
            {
                "agreement_record_id": AGREEMENT,
                "change_seq": 41,
                "commitment_id": COMMITMENT,
                "disposition": "STORED",
                "evidence_kind": CLAIMED_COMPLETE_PERFORMANCE,
                "record_id": EVENT,
            },
        )
        self.assertEqual(
            calls,
            [
                {
                    "agreement_record_id": AGREEMENT,
                    "commitment_id": COMMITMENT,
                    "issuer": SELLER,
                }
            ],
        )
        self.assertEqual(delegated, [])

    def test_unauthenticated_and_authority_injecting_completion_are_zero_publication(self) -> None:
        for authorization, document, expected_status in (
            (None, {"evidence_kind": CLAIMED_COMPLETE_PERFORMANCE}, 401),
            (
                AUTH_VALUE,
                {
                    "evidence_kind": CLAIMED_COMPLETE_PERFORMANCE,
                    "issuer": "did:example:attacker",
                },
                400,
            ),
        ):
            with self.subTest(authorization=authorization, document=document):
                asgi, calls, delegated = final_asgi()
                body = json_body(document)
                path = (
                    f"/api/agreements/{AGREEMENT}/commitments/"
                    f"{COMMITMENT}/completion-evidence"
                )
                sent = asyncio.run(
                    invoke(
                        asgi,
                        scope(path=path, body=body, authorization=authorization),
                        body,
                    )
                )
                self.assertEqual(sent[0]["status"], expected_status)
                self.assertEqual(calls, [])
                self.assertEqual(delegated, [])

    def test_same_final_asgi_preserves_agreement_publication_delegation(self) -> None:
        asgi, calls, delegated = final_asgi()
        body = json_body({"acceptance_record_id": ACCEPTANCE})
        path = f"/api/agreements/{PROPOSAL}"

        sent = asyncio.run(
            invoke(
                asgi,
                scope(path=path, body=body, authorization=AUTH_VALUE),
                body,
            )
        )

        self.assertEqual(sent[0]["status"], 201)
        self.assertEqual(
            response_document(sent)["agreement_record_id"],
            AGREEMENT,
        )
        self.assertEqual(calls, [])
        self.assertEqual(
            delegated,
            [
                {
                    "path": path,
                    "session_token": TOKEN,
                    "session_invalid": False,
                    "now": 102,
                }
            ],
        )

    def test_active_web_surface_requires_two_explicit_clicks(self) -> None:
        app = APP.read_text(encoding="utf-8")
        index = INDEX.read_text(encoding="utf-8")

        self.assertIn('id="publish-agreement" type="button" disabled', index)
        self.assertIn('id="claim-delivery-complete" type="button" disabled', index)
        self.assertIn(
            'publishAgreementButton.addEventListener("click", () => void publishSelectedAgreement())',
            app,
        )
        self.assertIn(
            'claimDeliveryCompleteButton.addEventListener("click", () => void claimSelectedDeliveryComplete())',
            app,
        )
        self.assertIn('const SELLER_DELIVERY_COMMITMENT_ID = "seller-delivery"', app)
        self.assertIn(
            'const CLAIMED_COMPLETE_PERFORMANCE = "CLAIMED_COMPLETE_PERFORMANCE"',
            app,
        )

        render_start = app.index(
            "function renderAgreementPublicationCompletionHandoff(record)"
        )
        publish_start = app.index("async function publishSelectedAgreement()", render_start)
        render = app[render_start:publish_start]
        self.assertNotIn("publishAgreement(", render)
        self.assertNotIn("publishEvidence(", render)

        publish_end = app.index(
            "async function claimSelectedDeliveryComplete()",
            publish_start,
        )
        publish = app[publish_start:publish_end]
        self.assertEqual(publish.count("client.publishAgreement("), 1)

        completion_start = publish_end
        completion_end = app.index(
            "async function resolveSelectedProposalAcceptance()",
            completion_start,
        )
        completion = app[completion_start:completion_end]
        self.assertEqual(completion.count("client.publishEvidence("), 1)
        self.assertIn(
            "authSnapshot.principal !== parentListing.sellerPrincipal",
            completion,
        )

    def test_reviewed_browser_modules_routes_and_localhost_mode_are_selected(self) -> None:
        bootstrap = BOOTSTRAP.read_text(encoding="utf-8")
        session = SESSION.read_text(encoding="utf-8")
        site_host = SITE_HOST.read_text(encoding="utf-8")
        localhost = LOCALHOST.read_text(encoding="utf-8")

        for marker in (
            "./agreement_publication_client.js",
            "./fulfillment_completion_client.js",
            "function agreementPublicationClient()",
            "function fulfillmentCompletionClient()",
        ):
            self.assertIn(marker, bootstrap)

        for marker in (
            "function reviewedAgreementPublicationRoute(path)",
            "function reviewedFulfillmentCompletionRoute(path)",
            '"completion-evidence"',
        ):
            self.assertIn(marker, session)

        for route in (
            "/agreement_publication_client.js",
            "/fulfillment_completion_client.js",
        ):
            self.assertIn(f'"{route}"', site_host)

        for marker in (
            "--execute-fulfillment-completion-localhost",
            "EXECUTE_FULFILLMENT_COMPLETION_AUTHENTICATED_MARKETPLACE_LOCALHOST_V1",
            "_run_fulfillment_completion_foreground",
        ):
            self.assertIn(marker, localhost)

    def test_semantic_and_operational_boundaries_remain_explicit(self) -> None:
        app = APP.read_text(encoding="utf-8")
        doc = " ".join(DOC.read_text(encoding="utf-8").split())
        self.assertIn("seller-attributed evidence only", app)
        self.assertIn("does not prove universal truth", app)
        self.assertIn("payment or settlement", app)
        for marker in (
            "the authenticated principal to be the only fulfillment issuer",
            "explicit user clicks",
            "no browser automation dependency",
            "no public-network exposure",
            "no payment or settlement authority",
            "acceptance-only rollback",
        ):
            self.assertIn(marker, doc)


if __name__ == "__main__":
    unittest.main()
