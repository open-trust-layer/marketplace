from __future__ import annotations

import unittest

from marketplace.application.agreement_assent import (
    MarketplaceAgreementAssentProofService,
)
from marketplace.application.agreement_assent_coordination import (
    MemoryAgreementAssentCoordinationStore,
    MarketplaceAgreementAssentCoordinationService,
    PreparedAgreementAssent,
)
from marketplace.application.agreement_assent_formation import (
    MarketplaceAgreementAssentFormationService,
)
from marketplace.application.agreement_assent_workflow import (
    AgreementAssentWorkflowError,
    MarketplaceAgreementAssentWorkflowService,
)
from marketplace.application.agreement_candidate import AgreementCandidateBuildResult
from marketplace.application.agreement_formation import (
    MarketplaceAgreementFormationEvaluationService,
)
from marketplace.application.auth_verification_method_snapshot import (
    AuthenticationVerificationMethodEvidence,
    MarketplaceAuthenticationVerificationMethodSnapshot,
)
from marketplace.runtime.contracts import StoreDisposition


AGREEMENT = "r1_" + "A" * 43
BUYER = "urn:marketplace:test:buyer"
SELLER = "urn:marketplace:test:seller"
BUYER_METHOD = "urn:marketplace:test:buyer-key"
SELLER_METHOD = "urn:marketplace:test:seller-key"
BUYER_KEY = b"\x11" * 32
SELLER_KEY = b"\x22" * 32
SIGNATURE = b"\x33" * 64


def candidate() -> AgreementCandidateBuildResult:
    return AgreementCandidateBuildResult(
        record=object(),
        record_id=AGREEMENT,
        listing_record_id="r1_" + "L" * 43,
        proposal_record_id="r1_" + "P" * 43,
        acceptance_record_id="r1_" + "C" * 43,
    )


def snapshot():
    return MarketplaceAuthenticationVerificationMethodSnapshot(
        [
            AuthenticationVerificationMethodEvidence(
                verification_method=BUYER_METHOD,
                controller_principal=BUYER,
                public_key=BUYER_KEY,
                valid_from=100,
                valid_until=400,
            ),
            AuthenticationVerificationMethodEvidence(
                verification_method=SELLER_METHOD,
                controller_principal=SELLER,
                public_key=SELLER_KEY,
                valid_from=100,
                valid_until=400,
            ),
        ]
    )


def services(*, initialize: bool = True):
    methods = snapshot()
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
    store = MemoryAgreementAssentCoordinationStore(clock=lambda: 200)
    coordination = MarketplaceAgreementAssentCoordinationService(
        store=store,
        prepare_verified_assent=lambda verified: PreparedAgreementAssent(
            agreement_record_id=verified.agreement_record_id,
            principal=verified.principal,
            verification_method=verified.verification_method,
            proof_identity=(
                b"\x11" * 32
                if verified.principal == BUYER
                else b"\x22" * 32
            ),
            proof_bytes=(
                b"buyer-proof"
                if verified.principal == BUYER
                else b"seller-proof"
            ),
        ),
    )
    if initialize:
        coordination.initialize()

    evaluator = MarketplaceAgreementFormationEvaluationService(
        evaluate=lambda _agreement, evidence: {
            "agreement": AGREEMENT,
            "formation_evidence": (
                "EVIDENCE_SUFFICIENT_FOR_PROFILE"
                if set(evidence) == {BUYER, SELLER}
                else "EVIDENCE_INCOMPLETE"
            ),
            "required_principals": [BUYER, SELLER],
            "covered_principals": sorted(evidence),
            "missing_principals": [
                principal
                for principal in (BUYER, SELLER)
                if principal not in evidence
            ],
            "legal_enforceability": "NOT_EVALUATED",
            "universal_truth": False,
            "publishes_agreement": False,
            "authorizes_side_effects": False,
        }
    )
    formation = MarketplaceAgreementAssentFormationService(
        coordination=coordination,
        verification_methods=methods,
        formation=evaluator,
        record_identity=lambda _record: AGREEMENT,
        reverify_prepared_proof=lambda _record, prepared, key: (
            prepared.principal,
            key,
        ),
        build_formation_evidence=lambda verified, _key: verified.principal,
    )
    workflow = MarketplaceAgreementAssentWorkflowService(
        proof=proof,
        coordination=coordination,
        formation=formation,
    )
    return workflow, coordination


class ProductAgreementAssentWorkflowTests(unittest.TestCase):
    def test_prepare_is_read_only_and_exactly_bound(self):
        workflow, coordination = services()
        result = workflow.prepare(
            candidate=candidate(),
            principal=BUYER,
            verification_method=BUYER_METHOD,
            at_time=200,
        )
        self.assertEqual(result.agreement_record_id, AGREEMENT)
        self.assertEqual(result.principal, BUYER)
        self.assertEqual(
            coordination.for_agreement(AGREEMENT),
            (),
        )

    def test_submit_verifies_then_stores_without_publication_authority(self):
        workflow, coordination = services()
        preparation = workflow.prepare(
            candidate=candidate(),
            principal=BUYER,
            verification_method=BUYER_METHOD,
            at_time=200,
        )
        result = workflow.submit(
            candidate=candidate(),
            preparation=preparation,
            signature=SIGNATURE,
            at_time=200,
        )
        self.assertEqual(result.disposition, StoreDisposition.STORED)
        self.assertEqual(result.agreement_record_id, AGREEMENT)
        self.assertEqual(result.principal, BUYER)
        self.assertFalse(result.publishes_agreement)
        self.assertFalse(result.authorizes_side_effects)
        self.assertIsNotNone(coordination.peek(AGREEMENT, BUYER))

    def test_duplicate_submit_is_idempotent_and_does_not_extend_expiry(self):
        workflow, _ = services()
        preparation = workflow.prepare(
            candidate=candidate(),
            principal=BUYER,
            verification_method=BUYER_METHOD,
            at_time=200,
        )
        first = workflow.submit(
            candidate=candidate(),
            preparation=preparation,
            signature=SIGNATURE,
            at_time=200,
        )
        second = workflow.submit(
            candidate=candidate(),
            preparation=preparation,
            signature=SIGNATURE,
            at_time=200,
        )
        self.assertEqual(first.disposition, StoreDisposition.STORED)
        self.assertEqual(second.disposition, StoreDisposition.DUPLICATE)
        self.assertEqual(first.accepted_at, second.accepted_at)
        self.assertEqual(first.expires_at, second.expires_at)

    def test_submit_does_not_hide_coordination_initialization(self):
        workflow, _ = services(initialize=False)
        preparation = workflow.prepare(
            candidate=candidate(),
            principal=BUYER,
            verification_method=BUYER_METHOD,
            at_time=200,
        )
        with self.assertRaises(AgreementAssentWorkflowError) as caught:
            workflow.submit(
                candidate=candidate(),
                preparation=preparation,
                signature=SIGNATURE,
                at_time=200,
            )
        self.assertEqual(
            caught.exception.code,
            "AGREEMENT_ASSENT_WORKFLOW_STORE_FAILED",
        )

    def test_formation_status_is_separate_and_read_only(self):
        workflow, coordination = services()
        for principal, method in (
            (BUYER, BUYER_METHOD),
            (SELLER, SELLER_METHOD),
        ):
            preparation = workflow.prepare(
                candidate=candidate(),
                principal=principal,
                verification_method=method,
                at_time=200,
            )
            workflow.submit(
                candidate=candidate(),
                preparation=preparation,
                signature=SIGNATURE,
                at_time=200,
            )
        before = coordination.for_agreement(AGREEMENT)
        status = workflow.formation_status(
            candidate=candidate(),
            at_time=200,
        )
        after = coordination.for_agreement(AGREEMENT)
        self.assertEqual(status.formation_evidence, "EVIDENCE_SUFFICIENT_FOR_PROFILE")
        self.assertEqual(before, after)
        self.assertFalse(status.publishes_agreement)
        self.assertFalse(status.authorizes_side_effects)

    def test_bad_signature_is_stable_and_does_not_store(self):
        workflow, coordination = services()
        preparation = workflow.prepare(
            candidate=candidate(),
            principal=BUYER,
            verification_method=BUYER_METHOD,
            at_time=200,
        )
        with self.assertRaises(AgreementAssentWorkflowError) as caught:
            workflow.submit(
                candidate=candidate(),
                preparation=preparation,
                signature=b"\x00" * 63,
                at_time=200,
            )
        self.assertEqual(
            caught.exception.code,
            "AGREEMENT_ASSENT_WORKFLOW_VERIFICATION_FAILED",
        )
        self.assertEqual(coordination.for_agreement(AGREEMENT), ())


if __name__ == "__main__":
    unittest.main()
