from __future__ import annotations

import hashlib
import json
import unittest

from marketplace.application.agreement_assent import MarketplaceAgreementAssentProofService
from marketplace.application.agreement_assent_candidate import (
    MarketplaceAgreementAssentCandidateResolutionService,
)
from marketplace.application.agreement_assent_coordination import (
    MemoryAgreementAssentCoordinationStore,
    MarketplaceAgreementAssentCoordinationService,
    PreparedAgreementAssent,
)
from marketplace.application.agreement_assent_formation import (
    MarketplaceAgreementAssentFormationService,
)
from marketplace.application.agreement_assent_http import (
    MarketplaceAuthenticatedAgreementAssentHttpAdapter,
)
from marketplace.application.agreement_assent_workflow import (
    MarketplaceAgreementAssentWorkflowService,
)
from marketplace.application.agreement_candidate import AgreementCandidateBuildResult
from marketplace.application.agreement_formation import (
    MarketplaceAgreementFormationEvaluationService,
)
from marketplace.application.agreement_publication import (
    MarketplaceAgreementPublicationPreflightService,
)
from marketplace.application.agreement_publication_http import (
    MarketplaceAuthenticatedAgreementPublicationHttpAdapter,
)
from marketplace.application.agreement_publication_write import (
    MarketplaceAgreementPublicationService,
)
from marketplace.application.auth import (
    AUTH_PROOF_DOMAIN,
    AUTH_PROOF_PURPOSE,
    AuthenticatedProductListingAuthoringService,
    AuthenticatedProposalAuthoringService,
    MarketplaceApplicationAuthService,
    VerifiedAuthenticationProof,
)
from marketplace.application.auth_http import MarketplaceAuthenticatedApplicationHttpAdapter
from marketplace.application.auth_verification_method_snapshot import (
    AuthenticationVerificationMethodEvidence,
    MarketplaceAuthenticationVerificationMethodSnapshot,
)
from marketplace.application.http import ApplicationHttpRequest, MarketplaceApplicationHttpAdapter
from marketplace.application.postgres_state import (
    ApplicationStatePutResult,
    ExpiryResult,
    PreparedApplicationRecord,
    StoreDisposition,
)
from marketplace.application.state import MarketplaceApplicationStateService


TOKEN = bytes(range(32))
SELLER = "did:example:seller"
BUYER = "did:example:buyer"
SELLER_METHOD = "did:example:seller#key-1"
BUYER_METHOD = "did:example:buyer#key-1"
PROPOSAL = "r1_" + "P" * 43
LISTING = "r1_" + "L" * 43
ACCEPTANCE = "r1_" + "A" * 43
AGREEMENT = "r1_" + "G" * 43


class AllowBinding:
    def verify(self, *, principal: str, verification_method: str, at_time: int) -> bool:
        return (
            principal == SELLER
            and verification_method == SELLER_METHOD
            and at_time >= 0
        )


class FakeApi:
    def list_intents(self, *, cursor=None, limit=64):
        from marketplace.application.api import IntentIndexPage

        return IntentIndexPage(("r-root",), None)

    def create_intent(self, _record):
        return ApplicationStatePutResult(StoreDisposition.STORED, 7)

    def respond_to_intent(self, _parent_record_id, _record):
        return ApplicationStatePutResult(StoreDisposition.STORED, 8)

    def get_intent(self, _record_id):
        return None

    def list_responses(self, _parent_record_id, *, limit=64):
        return ()

    def sync_watermark(self):
        return 0


class RecordingListingAuthoring:
    def create_product_listing(self, _fields):
        return ApplicationStatePutResult(StoreDisposition.STORED, 9)


class RecordingProposalAuthoring:
    def create_buyer_request_proposal(self, _draft):
        return ApplicationStatePutResult(StoreDisposition.STORED, 10)


class RecordingStateStore:
    def __init__(self):
        self.puts = []

    def initialize(self):
        return ExpiryResult((), ())

    def put(self, prepared):
        self.puts.append(prepared)
        return ApplicationStatePutResult(StoreDisposition.STORED, 31)


def decode_record(body: bytes):
    return json.loads(body.decode("utf-8"))


def encode_record(record: object) -> bytes:
    return json.dumps(record, sort_keys=True, separators=(",", ":")).encode("utf-8")


def make_active_auth() -> MarketplaceApplicationAuthService:
    auth = MarketplaceApplicationAuthService(principal_binding_verifier=AllowBinding())
    challenge = b"c" * 32
    auth.register_challenge(
        challenge=challenge,
        principal=SELLER,
        verification_method=SELLER_METHOD,
        now=100,
    )
    proof = VerifiedAuthenticationProof(
        challenge_sha256=hashlib.sha256(challenge).digest(),
        domain=AUTH_PROOF_DOMAIN,
        proof_purpose=AUTH_PROOF_PURPOSE,
        verification_method=SELLER_METHOD,
        cryptographically_valid=True,
    )
    auth.authenticate_challenge(
        challenge=challenge,
        proof=proof,
        session_token=TOKEN,
        now=101,
    )
    return auth


def _json(body):
    return json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _decode_carrier(value):
    if type(value) is not dict or frozenset(value) != {"bytes"}:
        raise ValueError("carrier invalid")
    return bytes.fromhex(value["bytes"])


def _encode_carrier(value):
    return {"bytes": value.hex()}


class AgreementPublicationHttpTests(unittest.TestCase):
    def make_adapter(self, *, required=(SELLER, BUYER), covered=(SELLER, BUYER)):
        api = FakeApi()
        listing = RecordingListingAuthoring()
        proposal_authoring = RecordingProposalAuthoring()
        auth = make_active_auth()
        base = MarketplaceApplicationHttpAdapter(
            api=api,
            decode_record_json=decode_record,
            encode_record_json=encode_record,
            create_product_listing=listing.create_product_listing,
            create_proposal=proposal_authoring.create_buyer_request_proposal,
        )
        protected = MarketplaceAuthenticatedApplicationHttpAdapter(
            base=base,
            auth=auth,
            product_listing_authoring=AuthenticatedProductListingAuthoringService(
                auth=auth,
                authoring=listing,
            ),
            proposal_authoring=AuthenticatedProposalAuthoringService(
                auth=auth,
                authoring=proposal_authoring,
            ),
            decode_record_json=decode_record,
            create_intent=api.create_intent,
            respond_to_intent=api.respond_to_intent,
            record_principal=lambda record: record["issuer"],
        )

        candidate_reads = []

        def read_proposal(record_id):
            candidate_reads.append(record_id)
            return {"type": "proposal", "parents": (LISTING,)}

        def build_candidate(**kwargs):
            return AgreementCandidateBuildResult(
                record={"kind": "agreement"},
                record_id=AGREEMENT,
                listing_record_id=kwargs["listing_record_id"],
                proposal_record_id=kwargs["proposal_record_id"],
                acceptance_record_id=kwargs["acceptance_record_id"],
            )

        resolver = MarketplaceAgreementAssentCandidateResolutionService(
            read_proposal=read_proposal,
            is_proposal_record=lambda value: value["type"] == "proposal",
            proposal_parent_ids=lambda value: value["parents"],
            build_candidate=build_candidate,
        )

        methods = MarketplaceAuthenticationVerificationMethodSnapshot(
            [
                AuthenticationVerificationMethodEvidence(
                    verification_method=SELLER_METHOD,
                    controller_principal=SELLER,
                    public_key=b"\x11" * 32,
                    valid_from=100,
                    valid_until=400,
                ),
                AuthenticationVerificationMethodEvidence(
                    verification_method=BUYER_METHOD,
                    controller_principal=BUYER,
                    public_key=b"\x22" * 32,
                    valid_from=100,
                    valid_until=400,
                ),
            ]
        )
        proof = MarketplaceAgreementAssentProofService(
            verification_methods=methods,
            record_identity=lambda _record: AGREEMENT,
            build_signing_input=lambda _record, method: b"input:" + method.encode("ascii"),
            build_verified_proof=lambda _record, method, key, signature: (
                method,
                key,
                signature,
            ),
        )
        coordination_store = MemoryAgreementAssentCoordinationStore(clock=lambda: 102)
        coordination = MarketplaceAgreementAssentCoordinationService(
            store=coordination_store,
            prepare_verified_assent=lambda verified: PreparedAgreementAssent(
                agreement_record_id=verified.agreement_record_id,
                principal=verified.principal,
                verification_method=verified.verification_method,
                proof_identity=b"\x33" * 32,
                proof_bytes=b"verified-proof",
            ),
        )
        coordination.initialize()
        method_for = {SELLER: SELLER_METHOD, BUYER: BUYER_METHOD}
        for principal in covered:
            coordination_store.put(
                PreparedAgreementAssent(
                    agreement_record_id=AGREEMENT,
                    principal=principal,
                    verification_method=method_for[principal],
                    proof_identity=hashlib.sha256(principal.encode("utf-8")).digest(),
                    proof_bytes=("proof:" + principal).encode("utf-8"),
                )
            )

        def evaluate(_agreement, evidence):
            covered_now = tuple(value for value in required if value in evidence)
            missing = tuple(value for value in required if value not in covered_now)
            return {
                "agreement": AGREEMENT,
                "formation_evidence": (
                    "EVIDENCE_SUFFICIENT_FOR_PROFILE"
                    if not missing
                    else "EVIDENCE_INCOMPLETE"
                ),
                "required_principals": list(required),
                "covered_principals": list(covered_now),
                "missing_principals": list(missing),
                "legal_enforceability": "NOT_EVALUATED",
                "universal_truth": False,
                "publishes_agreement": False,
                "authorizes_side_effects": False,
            }

        formation = MarketplaceAgreementAssentFormationService(
            coordination=coordination,
            verification_methods=methods,
            formation=MarketplaceAgreementFormationEvaluationService(evaluate=evaluate),
            record_identity=lambda _record: AGREEMENT,
            reverify_prepared_proof=lambda *_args: object(),
            build_formation_evidence=lambda verified, _key: verified.principal,
        )
        workflow = MarketplaceAgreementAssentWorkflowService(
            proof=proof,
            coordination=coordination,
            formation=formation,
        )
        assent = MarketplaceAuthenticatedAgreementAssentHttpAdapter(
            base=protected,
            auth=auth,
            candidate_resolution=resolver,
            workflow=workflow,
            encode_signing_input=_encode_carrier,
            decode_signature=_decode_carrier,
        )

        state_store = RecordingStateStore()
        state = MarketplaceApplicationStateService(
            store=state_store,
            prepare_record=lambda _record: PreparedApplicationRecord(
                record_id=AGREEMENT,
                canonical_record=b'{"kind":"agreement"}',
            ),
            decode_record=lambda _raw: {"kind": "agreement"},
        )
        state.initialize()
        preflight = MarketplaceAgreementPublicationPreflightService(
            record_identity=lambda _record: AGREEMENT,
        )
        publication = MarketplaceAgreementPublicationService(
            state=state,
            record_identity=lambda _record: AGREEMENT,
        )
        adapter = MarketplaceAuthenticatedAgreementPublicationHttpAdapter(
            base=assent,
            auth=auth,
            candidate_resolution=resolver,
            workflow=workflow,
            preflight=preflight,
            publication=publication,
        )
        return adapter, auth, state_store, candidate_reads

    @staticmethod
    def request(document, *, method="POST", path=None):
        return ApplicationHttpRequest(
            method,
            path or f"/api/agreements/{PROPOSAL}",
            (),
            "application/json",
            _json(document),
        )

    @staticmethod
    def document(response):
        return json.loads(response.body.decode("utf-8"))

    def test_success_publishes_exactly_once_and_returns_bounded_metadata(self):
        adapter, auth, store, reads = self.make_adapter()
        before = auth.validate_session(session_token=TOKEN, now=102)
        response = adapter.handle(
            self.request({"acceptance_record_id": ACCEPTANCE}),
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
                "change_seq": 31,
                "disposition": "STORED",
            },
        )
        self.assertEqual(reads, [PROPOSAL])
        self.assertEqual(len(store.puts), 1)
        self.assertEqual(store.puts[0].record_id, AGREEMENT)
        self.assertEqual(before.last_used_at, 101)
        self.assertEqual(after.last_used_at, 102)

    def test_unauthenticated_request_is_zero_write_and_zero_resolution(self):
        adapter, _, store, reads = self.make_adapter()
        response = adapter.handle(
            self.request({"acceptance_record_id": ACCEPTANCE}),
            session_token=None,
            session_invalid=False,
            now=102,
        )
        self.assertEqual(response.status_code, 401)
        self.assertEqual(reads, [])
        self.assertEqual(store.puts, [])

    def test_caller_cannot_override_principal_key_trust_or_attribution(self):
        adapter, _, store, reads = self.make_adapter()
        response = adapter.handle(
            self.request(
                {
                    "acceptance_record_id": ACCEPTANCE,
                    "principal": "did:example:attacker",
                    "public_key": "attacker",
                    "attribution_accepted": True,
                }
            ),
            session_token=TOKEN,
            session_invalid=False,
            now=102,
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            self.document(response)["error"]["code"],
            "AGREEMENT_PUBLICATION_REQUEST_INVALID",
        )
        self.assertEqual(reads, [])
        self.assertEqual(store.puts, [])

    def test_incomplete_formation_is_zero_write_and_does_not_touch_session(self):
        adapter, auth, store, reads = self.make_adapter(covered=(SELLER,))
        before = auth.validate_session(session_token=TOKEN, now=102)
        response = adapter.handle(
            self.request({"acceptance_record_id": ACCEPTANCE}),
            session_token=TOKEN,
            session_invalid=False,
            now=102,
        )
        after = auth.validate_session(session_token=TOKEN, now=102)
        self.assertEqual(response.status_code, 409)
        self.assertEqual(
            self.document(response)["error"]["code"],
            "AGREEMENT_PUBLICATION_FORMATION_INCOMPLETE",
        )
        self.assertEqual(reads, [PROPOSAL])
        self.assertEqual(store.puts, [])
        self.assertEqual(before.last_used_at, after.last_used_at)

    def test_non_party_actor_is_zero_write(self):
        adapter, _, store, reads = self.make_adapter(
            required=(BUYER,),
            covered=(BUYER,),
        )
        response = adapter.handle(
            self.request({"acceptance_record_id": ACCEPTANCE}),
            session_token=TOKEN,
            session_invalid=False,
            now=102,
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            self.document(response)["error"]["code"],
            "AGREEMENT_PUBLICATION_PARTY_REQUIRED",
        )
        self.assertEqual(reads, [PROPOSAL])
        self.assertEqual(store.puts, [])

    def test_route_requires_explicit_exact_acceptance_identity(self):
        adapter, _, store, reads = self.make_adapter()
        response = adapter.handle(
            self.request({}),
            session_token=TOKEN,
            session_invalid=False,
            now=102,
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(reads, [])
        self.assertEqual(store.puts, [])

    def test_assent_subroute_still_delegates_to_existing_adapter(self):
        adapter, _, store, reads = self.make_adapter()
        response = adapter.handle(
            self.request(
                {"acceptance_record_id": ACCEPTANCE},
                path=f"/api/agreements/{PROPOSAL}/assent/status",
            ),
            session_token=TOKEN,
            session_invalid=False,
            now=102,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(reads, [PROPOSAL])
        self.assertEqual(store.puts, [])


if __name__ == "__main__":
    unittest.main()
