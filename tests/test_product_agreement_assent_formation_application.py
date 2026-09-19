from __future__ import annotations

import unittest

from marketplace.application.agreement_assent import VerifiedAgreementAssent
from marketplace.application.agreement_assent_coordination import (
    MemoryAgreementAssentCoordinationStore,
    MarketplaceAgreementAssentCoordinationService,
    PreparedAgreementAssent,
)
from marketplace.application.agreement_assent_formation import (
    AgreementAssentFormationError,
    MarketplaceAgreementAssentFormationService,
)
from marketplace.application.agreement_candidate import AgreementCandidateBuildResult
from marketplace.application.agreement_formation import (
    MarketplaceAgreementFormationEvaluationService,
)
from marketplace.application.auth_verification_method_snapshot import (
    AuthenticationVerificationMethodEvidence,
    MarketplaceAuthenticationVerificationMethodSnapshot,
)


AGREEMENT = "r1_" + "A" * 43
BUYER = "urn:marketplace:test:buyer"
SELLER = "urn:marketplace:test:seller"
BUYER_METHOD = "urn:marketplace:test:buyer-key"
SELLER_METHOD = "urn:marketplace:test:seller-key"
BUYER_KEY = b"\x11" * 32
SELLER_KEY = b"\x22" * 32


def candidate() -> AgreementCandidateBuildResult:
    return AgreementCandidateBuildResult(
        record=object(),
        record_id=AGREEMENT,
        listing_record_id="r1_" + "L" * 43,
        proposal_record_id="r1_" + "P" * 43,
        acceptance_record_id="r1_" + "C" * 43,
    )


def snapshot(*, seller_valid_until: int | None = None):
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
                valid_until=seller_valid_until,
            ),
        ]
    )


def prepared(principal: str, method: str, marker: int) -> PreparedAgreementAssent:
    return PreparedAgreementAssent(
        agreement_record_id=AGREEMENT,
        principal=principal,
        verification_method=method,
        proof_identity=bytes([marker]) * 32,
        proof_bytes=bytes([marker]),
    )


def coordination(values: tuple[PreparedAgreementAssent, ...]):
    lookup = {(value.principal, value.verification_method): value for value in values}
    store = MemoryAgreementAssentCoordinationStore(clock=lambda: 200)
    service = MarketplaceAgreementAssentCoordinationService(
        store=store,
        prepare_verified_assent=lambda verified: lookup[
            (verified.principal, verified.verification_method)
        ],
    )
    service.initialize()
    for value in values:
        service.accept(
            VerifiedAgreementAssent(
                agreement_record_id=AGREEMENT,
                principal=value.principal,
                verification_method=value.verification_method,
                proof=object(),
            )
        )
    return service


def formation_service():
    def evaluate(_agreement, evidence):
        covered = tuple(sorted(evidence))
        required = (BUYER, SELLER)
        missing = tuple(value for value in required if value not in covered)
        return {
            "agreement": AGREEMENT,
            "formation_evidence": (
                "EVIDENCE_SUFFICIENT_FOR_PROFILE"
                if not missing
                else "EVIDENCE_INCOMPLETE"
            ),
            "required_principals": list(required),
            "covered_principals": list(covered),
            "missing_principals": list(missing),
            "legal_enforceability": "NOT_EVALUATED",
            "universal_truth": False,
            "publishes_agreement": False,
            "authorizes_side_effects": False,
        }

    return MarketplaceAgreementFormationEvaluationService(evaluate=evaluate)


class ProductAgreementAssentFormationApplicationTests(unittest.TestCase):
    def service(self, values, *, methods=None, reverify=None, evidence_builder=None):
        calls = []

        def default_reverify(_record, value, key):
            calls.append(("reverify", value.principal, key))
            return object()

        def default_evidence(verified, key):
            calls.append(("evidence", verified.principal, key))
            return verified.principal

        return (
            MarketplaceAgreementAssentFormationService(
                coordination=coordination(tuple(values)),
                verification_methods=methods or snapshot(),
                formation=formation_service(),
                record_identity=lambda _record: AGREEMENT,
                reverify_prepared_proof=reverify or default_reverify,
                build_formation_evidence=evidence_builder or default_evidence,
            ),
            calls,
        )

    def test_complete_current_evidence_reaches_existing_formation_evaluator(self):
        service, calls = self.service(
            (
                prepared(BUYER, BUYER_METHOD, 1),
                prepared(SELLER, SELLER_METHOD, 2),
            )
        )
        result = service.evaluate(candidate=candidate(), at_time=200)
        self.assertEqual(result.formation_evidence, "EVIDENCE_SUFFICIENT_FOR_PROFILE")
        self.assertEqual(result.covered_principals, (BUYER, SELLER))
        self.assertEqual(
            [entry[0] for entry in calls],
            ["reverify", "evidence", "reverify", "evidence"],
        )

    def test_expired_method_is_not_promoted_and_result_stays_incomplete(self):
        service, calls = self.service(
            (
                prepared(BUYER, BUYER_METHOD, 1),
                prepared(SELLER, SELLER_METHOD, 2),
            ),
            methods=snapshot(seller_valid_until=200),
        )
        result = service.evaluate(candidate=candidate(), at_time=200)
        self.assertEqual(result.formation_evidence, "EVIDENCE_INCOMPLETE")
        self.assertEqual(result.covered_principals, (BUYER,))
        self.assertEqual(result.missing_principals, (SELLER,))
        self.assertFalse(any(entry[1] == SELLER for entry in calls))

    def test_candidate_identity_mismatch_fails_before_evidence_read(self):
        service, _ = self.service(())
        service._record_identity = lambda _record: "r1_" + "Z" * 43
        with self.assertRaises(AgreementAssentFormationError) as caught:
            service.evaluate(candidate=candidate(), at_time=200)
        self.assertEqual(
            caught.exception.code,
            "AGREEMENT_ASSENT_FORMATION_IDENTITY_MISMATCH",
        )

    def test_corrupt_retained_proof_reverification_is_hard_failure(self):
        def fail(*_args):
            raise RuntimeError("stored proof corruption")

        service, _ = self.service(
            (prepared(BUYER, BUYER_METHOD, 1),),
            reverify=fail,
        )
        with self.assertRaises(AgreementAssentFormationError) as caught:
            service.evaluate(candidate=candidate(), at_time=200)
        self.assertEqual(
            caught.exception.code,
            "AGREEMENT_ASSENT_FORMATION_REVERIFICATION_FAILED",
        )
        self.assertNotIn("stored proof corruption", str(caught.exception))

    def test_evidence_builder_failure_is_stable_and_nonreflective(self):
        def fail(*_args):
            raise RuntimeError("attribution provider detail")

        service, _ = self.service(
            (prepared(BUYER, BUYER_METHOD, 1),),
            evidence_builder=fail,
        )
        with self.assertRaises(AgreementAssentFormationError) as caught:
            service.evaluate(candidate=candidate(), at_time=200)
        self.assertEqual(
            caught.exception.code,
            "AGREEMENT_ASSENT_FORMATION_EVIDENCE_BUILD_FAILED",
        )
        self.assertNotIn("attribution provider detail", str(caught.exception))

    def test_invalid_time_is_rejected_before_trust_evaluation(self):
        service, _ = self.service(())
        with self.assertRaises(AgreementAssentFormationError) as caught:
            service.evaluate(candidate=candidate(), at_time=True)
        self.assertEqual(
            caught.exception.code,
            "AGREEMENT_ASSENT_FORMATION_REQUEST_INVALID",
        )


if __name__ == "__main__":
    unittest.main()
