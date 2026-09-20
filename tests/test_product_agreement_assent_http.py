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
from marketplace.application.postgres_state import ApplicationStatePutResult, StoreDisposition


TOKEN = bytes(range(32))
PRINCIPAL = "did:example:seller"
METHOD = "did:example:seller#key-1"


class AllowBinding:
    def verify(self, *, principal: str, verification_method: str, at_time: int) -> bool:
        return principal == PRINCIPAL and verification_method == METHOD and at_time >= 0


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


PROPOSAL = "r1_" + "P" * 43
LISTING = "r1_" + "L" * 43
ACCEPTANCE = "r1_" + "A" * 43
AGREEMENT = "r1_" + "G" * 43
PUBLIC_KEY = b"\x11" * 32
SIGNATURE = b"\x44" * 64


def _json(body):
    return json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _decode_carrier(value):
    if type(value) is not dict or frozenset(value) != {"bytes"}:
        raise ValueError("carrier invalid")
    return bytes.fromhex(value["bytes"])


def _encode_carrier(value):
    return {"bytes": value.hex()}


class AgreementAssentHttpTests(unittest.TestCase):
    def make_adapter(self, *, required_principals=None):
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
        candidate_builds = []

        def read_proposal(record_id):
            candidate_reads.append(record_id)
            return {"type": "proposal", "parents": (LISTING,)}

        def build_candidate(**kwargs):
            candidate_builds.append(kwargs)
            return AgreementCandidateBuildResult(
                record=object(),
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
                    verification_method=METHOD,
                    controller_principal=PRINCIPAL,
                    public_key=PUBLIC_KEY,
                    valid_from=100,
                    valid_until=400,
                )
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
        store = MemoryAgreementAssentCoordinationStore(clock=lambda: 102)
        coordination = MarketplaceAgreementAssentCoordinationService(
            store=store,
            prepare_verified_assent=lambda verified: PreparedAgreementAssent(
                agreement_record_id=verified.agreement_record_id,
                principal=verified.principal,
                verification_method=verified.verification_method,
                proof_identity=b"\x22" * 32,
                proof_bytes=b"verified-proof",
            ),
        )
        coordination.initialize()
        required = tuple(
            required_principals
            if required_principals is not None
            else (PRINCIPAL, "did:example:other")
        )
        formation = MarketplaceAgreementAssentFormationService(
            coordination=coordination,
            verification_methods=methods,
            formation=MarketplaceAgreementFormationEvaluationService(
                evaluate=lambda _agreement, _evidence: {
                    "agreement": AGREEMENT,
                    "formation_evidence": "EVIDENCE_INCOMPLETE",
                    "required_principals": list(required),
                    "covered_principals": [],
                    "missing_principals": list(required),
                    "legal_enforceability": "NOT_EVALUATED",
                    "universal_truth": False,
                    "publishes_agreement": False,
                    "authorizes_side_effects": False,
                }
            ),
            record_identity=lambda _record: AGREEMENT,
            reverify_prepared_proof=lambda *_args: object(),
            build_formation_evidence=lambda *_args: object(),
        )
        workflow = MarketplaceAgreementAssentWorkflowService(
            proof=proof,
            coordination=coordination,
            formation=formation,
        )
        adapter = MarketplaceAuthenticatedAgreementAssentHttpAdapter(
            base=protected,
            auth=auth,
            candidate_resolution=resolver,
            workflow=workflow,
            encode_signing_input=_encode_carrier,
            decode_signature=_decode_carrier,
        )
        return adapter, auth, coordination, candidate_reads, candidate_builds

    @staticmethod
    def request(kind, document, *, method="POST"):
        if kind == "preparation":
            suffix = "/assent/preparation"
        elif kind == "status":
            suffix = "/assent/status"
        else:
            suffix = "/assent"
        return ApplicationHttpRequest(
            method,
            f"/api/agreements/{PROPOSAL}{suffix}",
            (),
            "application/json",
            _json(document),
        )

    @staticmethod
    def document(response):
        return json.loads(response.body.decode("utf-8"))

    def test_preparation_requires_auth_before_candidate_resolution(self):
        adapter, _, coordination, reads, _ = self.make_adapter()
        response = adapter.handle(
            self.request("preparation", {"acceptance_record_id": ACCEPTANCE}),
            session_token=None,
            session_invalid=False,
            now=102,
        )
        self.assertEqual(response.status_code, 401)
        self.assertEqual(reads, [])
        self.assertEqual(coordination.for_agreement(AGREEMENT), ())

    def test_preparation_derives_session_binding_and_is_read_only(self):
        adapter, auth, coordination, reads, builds = self.make_adapter()
        before = auth.validate_session(session_token=TOKEN, now=102)
        response = adapter.handle(
            self.request("preparation", {"acceptance_record_id": ACCEPTANCE}),
            session_token=TOKEN,
            session_invalid=False,
            now=102,
        )
        after = auth.validate_session(session_token=TOKEN, now=102)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(before.last_used_at, after.last_used_at)
        document = self.document(response)
        self.assertEqual(document["agreement_record_id"], AGREEMENT)
        self.assertEqual(document["verification_method"], METHOD)
        self.assertEqual(
            bytes.fromhex(document["proof_input"]["bytes"]),
            b"input:" + METHOD.encode("ascii"),
        )
        self.assertEqual(reads, [PROPOSAL])
        self.assertEqual(builds[0]["listing_record_id"], LISTING)
        self.assertEqual(builds[0]["acceptance_record_id"], ACCEPTANCE)
        self.assertEqual(coordination.for_agreement(AGREEMENT), ())

    def test_status_requires_auth_before_candidate_resolution(self):
        adapter, _, coordination, reads, _ = self.make_adapter()
        response = adapter.handle(
            self.request("status", {"acceptance_record_id": ACCEPTANCE}),
            session_token=None,
            session_invalid=False,
            now=102,
        )
        self.assertEqual(response.status_code, 401)
        self.assertEqual(reads, [])
        self.assertEqual(coordination.for_agreement(AGREEMENT), ())

    def test_status_is_party_only_read_only_and_session_touch_negative(self):
        adapter, auth, coordination, reads, builds = self.make_adapter()
        before = auth.validate_session(session_token=TOKEN, now=102)
        response = adapter.handle(
            self.request("status", {"acceptance_record_id": ACCEPTANCE}),
            session_token=TOKEN,
            session_invalid=False,
            now=102,
        )
        after = auth.validate_session(session_token=TOKEN, now=102)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(before.last_used_at, after.last_used_at)
        document = self.document(response)
        self.assertEqual(document["agreement_record_id"], AGREEMENT)
        self.assertEqual(document["formation_evidence"], "EVIDENCE_INCOMPLETE")
        self.assertEqual(
            document["required_principals"],
            [PRINCIPAL, "did:example:other"],
        )
        self.assertEqual(document["covered_principals"], [])
        self.assertEqual(
            document["missing_principals"],
            [PRINCIPAL, "did:example:other"],
        )
        self.assertEqual(document["legal_enforceability"], "NOT_EVALUATED")
        self.assertFalse(document["universal_truth"])
        self.assertFalse(document["publishes_agreement"])
        self.assertFalse(document["authorizes_side_effects"])
        self.assertEqual(reads, [PROPOSAL])
        self.assertEqual(builds[0]["acceptance_record_id"], ACCEPTANCE)
        self.assertEqual(coordination.for_agreement(AGREEMENT), ())

    def test_non_party_cannot_prepare_submit_or_read_status(self):
        cases = (
            ("preparation", {"acceptance_record_id": ACCEPTANCE}),
            (
                "submission",
                {
                    "acceptance_record_id": ACCEPTANCE,
                    "signature": {"bytes": SIGNATURE.hex()},
                },
            ),
            ("status", {"acceptance_record_id": ACCEPTANCE}),
        )
        for kind, document in cases:
            with self.subTest(kind=kind):
                adapter, auth, coordination, reads, _ = self.make_adapter(
                    required_principals=("did:example:other",)
                )
                before = auth.validate_session(session_token=TOKEN, now=102)
                response = adapter.handle(
                    self.request(kind, document),
                    session_token=TOKEN,
                    session_invalid=False,
                    now=102,
                )
                after = auth.validate_session(session_token=TOKEN, now=102)
                self.assertEqual(response.status_code, 403)
                self.assertEqual(
                    self.document(response)["error"]["code"],
                    "AGREEMENT_ASSENT_PARTY_REQUIRED",
                )
                self.assertEqual(before.last_used_at, after.last_used_at)
                self.assertEqual(reads, [PROPOSAL])
                self.assertEqual(coordination.for_agreement(AGREEMENT), ())

    def test_submission_reprepares_server_binding_and_stores_verified_assent(self):
        adapter, auth, coordination, reads, builds = self.make_adapter()
        response = adapter.handle(
            self.request(
                "submission",
                {
                    "acceptance_record_id": ACCEPTANCE,
                    "signature": {"bytes": SIGNATURE.hex()},
                },
            ),
            session_token=TOKEN,
            session_invalid=False,
            now=102,
        )
        self.assertEqual(response.status_code, 201)
        document = self.document(response)
        self.assertEqual(document["agreement_record_id"], AGREEMENT)
        self.assertEqual(document["disposition"], "STORED")
        self.assertFalse(document["publishes_agreement"])
        self.assertFalse(document["authorizes_side_effects"])
        self.assertEqual(reads, [PROPOSAL])
        self.assertEqual(builds[0]["listing_record_id"], LISTING)
        stored = coordination.peek(AGREEMENT, PRINCIPAL)
        self.assertIsNotNone(stored)
        self.assertEqual(stored.verification_method, METHOD)
        session = auth.validate_session(session_token=TOKEN, now=102)
        self.assertEqual(session.last_used_at, 102)

    def test_malformed_signature_is_rejected_before_candidate_resolution(self):
        adapter, _, coordination, reads, _ = self.make_adapter()
        response = adapter.handle(
            self.request(
                "submission",
                {
                    "acceptance_record_id": ACCEPTANCE,
                    "signature": {"bytes": "00"},
                },
            ),
            session_token=TOKEN,
            session_invalid=False,
            now=102,
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(reads, [])
        self.assertEqual(coordination.for_agreement(AGREEMENT), ())

    def test_caller_cannot_supply_principal_method_listing_or_signing_input(self):
        adapter, _, coordination, reads, _ = self.make_adapter()
        hostile = {
            "acceptance_record_id": ACCEPTANCE,
            "principal": "did:example:attacker",
            "verification_method": "did:example:attacker#key",
            "listing_record_id": "r1_" + "X" * 43,
        }
        response = adapter.handle(
            self.request("preparation", hostile),
            session_token=TOKEN,
            session_invalid=False,
            now=102,
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(reads, [])
        self.assertEqual(coordination.for_agreement(AGREEMENT), ())

    def test_nonmatching_route_delegates_to_existing_adapter(self):
        adapter, _, _, _, _ = self.make_adapter()
        response = adapter.handle(
            ApplicationHttpRequest("GET", "/api/intents", (), None, b""),
            session_token=None,
            session_invalid=False,
            now=102,
        )
        self.assertEqual(response.status_code, 200)

    def test_matching_route_is_post_only(self):
        adapter, _, _, reads, _ = self.make_adapter()
        response = adapter.handle(
            self.request(
                "preparation",
                {"acceptance_record_id": ACCEPTANCE},
                method="GET",
            ),
            session_token=None,
            session_invalid=False,
            now=102,
        )
        self.assertEqual(response.status_code, 405)
        self.assertIn(("Allow", "POST"), response.headers)
        self.assertEqual(reads, [])


if __name__ == "__main__":
    unittest.main()
