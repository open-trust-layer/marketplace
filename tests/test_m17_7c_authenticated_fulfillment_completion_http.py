from __future__ import annotations

import hashlib
import json
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
from marketplace.application.fulfillment_completion_http import (
    PROFILE_NAME,
    MarketplaceAuthenticatedFulfillmentCompletionHttpAdapter,
)
from marketplace.application.fulfillment_completion_publication import (
    CLAIMED_COMPLETE_PERFORMANCE,
    COMMITMENT_ACCEPTANCE,
    COMMITMENT_COMPLETION,
    FulfillmentCompletionPublicationError,
    FulfillmentEvidencePublicationResult,
    MarketplaceFulfillmentCompletionPublicationService,
)
from marketplace.application.http import ApplicationHttpRequest, ApplicationHttpResponse
from marketplace.application.postgres_state import StoreDisposition


TOKEN = bytes(range(32))
SELLER = "did:example:seller"
METHOD = "did:example:seller#key-1"
AGREEMENT = "r1_" + "G" * 43
EVENT = "r1_" + "E" * 43
COMMITMENT = "seller-delivery"


class AllowBinding:
    def verify(self, *, principal: str, verification_method: str, at_time: int) -> bool:
        return (
            principal == SELLER
            and verification_method == METHOD
            and at_time >= 0
        )


def make_active_auth() -> MarketplaceApplicationAuthService:
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


def _json(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


class M177CAuthenticatedFulfillmentCompletionHttpTests(unittest.TestCase):
    def make_adapter(self):
        auth = make_active_auth()

        base = object.__new__(MarketplaceAuthenticatedAgreementPublicationHttpAdapter)
        delegated = []

        def handle_base(request, *, session_token, session_invalid, now):
            delegated.append((request.path, session_token, session_invalid, now))
            return ApplicationHttpResponse(299, "Delegated", (), b"")

        base.handle = handle_base

        publication = object.__new__(MarketplaceFulfillmentCompletionPublicationService)
        calls = []
        failures: dict[str, str] = {}

        def publish(kind: str, **kwargs):
            calls.append((kind, kwargs))
            code = failures.get(kind)
            if code is not None:
                raise FulfillmentCompletionPublicationError(code)
            return FulfillmentEvidencePublicationResult(
                record_id=EVENT,
                agreement_record_id=kwargs["agreement_record_id"],
                commitment_id=kwargs["commitment_id"],
                evidence_kind=kind,
                disposition=StoreDisposition.STORED,
                change_seq=41,
            )

        publication.publish_claimed_complete_performance = (
            lambda **kwargs: publish(CLAIMED_COMPLETE_PERFORMANCE, **kwargs)
        )
        publication.publish_commitment_acceptance = (
            lambda **kwargs: publish(COMMITMENT_ACCEPTANCE, **kwargs)
        )
        publication.publish_commitment_completion = (
            lambda **kwargs: publish(COMMITMENT_COMPLETION, **kwargs)
        )

        adapter = MarketplaceAuthenticatedFulfillmentCompletionHttpAdapter(
            base=base,
            auth=auth,
            publication=publication,
        )
        return adapter, auth, calls, failures, delegated

    @staticmethod
    def request(document, *, path=None, method="POST"):
        return ApplicationHttpRequest(
            method,
            path
            or f"/api/agreements/{AGREEMENT}/commitments/{COMMITMENT}/completion-evidence",
            (),
            "application/json",
            _json(document),
        )

    @staticmethod
    def document(response):
        return json.loads(response.body.decode("utf-8"))

    def test_profile_is_exact(self) -> None:
        self.assertEqual(
            PROFILE_NAME,
            "MARKETPLACE_AUTHENTICATED_FULFILLMENT_COMPLETION_HTTP_V1",
        )

    def test_each_reviewed_kind_uses_authenticated_principal_and_one_service_call(self):
        for kind in (
            CLAIMED_COMPLETE_PERFORMANCE,
            COMMITMENT_ACCEPTANCE,
            COMMITMENT_COMPLETION,
        ):
            with self.subTest(kind=kind):
                adapter, auth, calls, _, _ = self.make_adapter()
                before = auth.validate_session(session_token=TOKEN, now=102)
                response = adapter.handle(
                    self.request({"evidence_kind": kind}),
                    session_token=TOKEN,
                    session_invalid=False,
                    now=102,
                )
                after = auth.validate_session(session_token=TOKEN, now=102)

                self.assertEqual(response.status_code, 201)
                self.assertEqual(
                    self.document(response),
                    {
                        "agreement_record_id": AGREEMENT,
                        "change_seq": 41,
                        "commitment_id": COMMITMENT,
                        "disposition": "STORED",
                        "evidence_kind": kind,
                        "record_id": EVENT,
                    },
                )
                self.assertEqual(
                    calls,
                    [
                        (
                            kind,
                            {
                                "agreement_record_id": AGREEMENT,
                                "commitment_id": COMMITMENT,
                                "issuer": SELLER,
                            },
                        )
                    ],
                )
                self.assertEqual(before.last_used_at, 101)
                self.assertEqual(after.last_used_at, 102)

    def test_unauthenticated_request_is_zero_publication(self):
        adapter, _, calls, _, _ = self.make_adapter()
        response = adapter.handle(
            self.request({"evidence_kind": COMMITMENT_COMPLETION}),
            session_token=None,
            session_invalid=False,
            now=102,
        )
        self.assertEqual(response.status_code, 401)
        self.assertEqual(calls, [])

    def test_caller_cannot_supply_issuer_or_other_authority_fields(self):
        adapter, _, calls, _, _ = self.make_adapter()
        response = adapter.handle(
            self.request(
                {
                    "evidence_kind": COMMITMENT_COMPLETION,
                    "issuer": "did:example:attacker",
                }
            ),
            session_token=TOKEN,
            session_invalid=False,
            now=102,
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            self.document(response)["error"]["code"],
            "FULFILLMENT_PUBLICATION_REQUEST_INVALID",
        )
        self.assertEqual(calls, [])

    def test_unsupported_evidence_kind_is_rejected_before_publication(self):
        adapter, _, calls, _, _ = self.make_adapter()
        response = adapter.handle(
            self.request({"evidence_kind": "UNREVIEWED"}),
            session_token=TOKEN,
            session_invalid=False,
            now=102,
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(calls, [])

    def test_service_failures_are_bounded(self):
        cases = (
            ("FULFILLMENT_PUBLICATION_AGREEMENT_NOT_FOUND", 404),
            ("FULFILLMENT_PUBLICATION_AGREEMENT_UNAVAILABLE", 503),
            ("FULFILLMENT_PUBLICATION_BUILD_FAILED", 409),
            ("FULFILLMENT_PUBLICATION_BINDING_MISMATCH", 500),
            ("FULFILLMENT_PUBLICATION_IDENTITY_FAILED", 500),
            ("FULFILLMENT_PUBLICATION_WRITE_FAILED", 503),
        )
        for code, status in cases:
            with self.subTest(code=code):
                adapter, _, calls, failures, _ = self.make_adapter()
                failures[COMMITMENT_COMPLETION] = code
                response = adapter.handle(
                    self.request({"evidence_kind": COMMITMENT_COMPLETION}),
                    session_token=TOKEN,
                    session_invalid=False,
                    now=102,
                )
                self.assertEqual(response.status_code, status)
                self.assertEqual(self.document(response)["error"]["code"], code)
                self.assertEqual(len(calls), 1)

    def test_non_m17_7c_path_delegates_unchanged(self):
        adapter, _, calls, _, delegated = self.make_adapter()
        response = adapter.handle(
            self.request(
                {"acceptance_record_id": "r1_" + "A" * 43},
                path="/api/agreements/r1_" + "P" * 43,
            ),
            session_token=TOKEN,
            session_invalid=False,
            now=102,
        )
        self.assertEqual(response.status_code, 299)
        self.assertEqual(calls, [])
        self.assertEqual(len(delegated), 1)

    def test_method_and_content_type_are_bounded_before_publication(self):
        adapter, _, calls, _, _ = self.make_adapter()
        response = adapter.handle(
            self.request(
                {"evidence_kind": COMMITMENT_COMPLETION},
                method="GET",
            ),
            session_token=TOKEN,
            session_invalid=False,
            now=102,
        )
        self.assertEqual(response.status_code, 405)
        self.assertEqual(calls, [])

        request = ApplicationHttpRequest(
            "POST",
            f"/api/agreements/{AGREEMENT}/commitments/{COMMITMENT}/completion-evidence",
            (),
            "text/plain",
            _json({"evidence_kind": COMMITMENT_COMPLETION}),
        )
        response = adapter.handle(
            request,
            session_token=TOKEN,
            session_invalid=False,
            now=102,
        )
        self.assertEqual(response.status_code, 415)
        self.assertEqual(calls, [])


if __name__ == "__main__":
    unittest.main()
