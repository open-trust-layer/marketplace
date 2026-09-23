from __future__ import annotations

import unittest

from marketplace.application.agreement_formation import (
    AgreementFormationEvaluationError,
    MarketplaceAgreementFormationEvaluationService,
)


AGREEMENT_ID = "r1_test-agreement"


def _document(*, status: str = "EVIDENCE_SUFFICIENT_FOR_PROFILE"):
    missing = [] if status == "EVIDENCE_SUFFICIENT_FOR_PROFILE" else ["urn:buyer"]
    covered = ["urn:buyer", "urn:seller"] if not missing else ["urn:seller"]
    return {
        "agreement": AGREEMENT_ID,
        "formation_evidence": status,
        "required_principals": ["urn:buyer", "urn:seller"],
        "covered_principals": covered,
        "missing_principals": missing,
        "legal_enforceability": "NOT_EVALUATED",
        "universal_truth": False,
        "publishes_agreement": False,
        "authorizes_side_effects": False,
    }


class ProductAgreementFormationApplicationTests(unittest.TestCase):
    def test_service_preserves_non_authority_boundaries(self) -> None:
        service = MarketplaceAgreementFormationEvaluationService(
            evaluate=lambda _agreement, _evidence: _document()
        )
        result = service.evaluate(agreement=object(), evidence=())
        self.assertEqual(result.formation_evidence, "EVIDENCE_SUFFICIENT_FOR_PROFILE")
        self.assertEqual(result.legal_enforceability, "NOT_EVALUATED")
        self.assertFalse(result.universal_truth)
        self.assertFalse(result.publishes_agreement)
        self.assertFalse(result.authorizes_side_effects)

    def test_incomplete_result_remains_non_authoritative(self) -> None:
        service = MarketplaceAgreementFormationEvaluationService(
            evaluate=lambda _agreement, _evidence: _document(status="EVIDENCE_INCOMPLETE")
        )
        result = service.evaluate(agreement=object(), evidence=())
        self.assertEqual(result.missing_principals, ("urn:buyer",))
        self.assertFalse(result.to_document()["publishes_agreement"])

    def test_evaluator_failure_is_stable_and_non_reflective(self) -> None:
        def fail(_agreement, _evidence):
            raise RuntimeError("sensitive verifier detail")

        service = MarketplaceAgreementFormationEvaluationService(evaluate=fail)
        with self.assertRaises(AgreementFormationEvaluationError) as caught:
            service.evaluate(agreement=object(), evidence=())
        self.assertEqual(caught.exception.code, "AGREEMENT_FORMATION_EVALUATION_FAILED")
        self.assertNotIn("sensitive verifier detail", str(caught.exception))

    def test_authority_promotion_from_evaluator_is_rejected(self) -> None:
        hostile = _document()
        hostile["authorizes_side_effects"] = True
        service = MarketplaceAgreementFormationEvaluationService(
            evaluate=lambda _agreement, _evidence: hostile
        )
        with self.assertRaises(AgreementFormationEvaluationError) as caught:
            service.evaluate(agreement=object(), evidence=())
        self.assertEqual(caught.exception.code, "AGREEMENT_FORMATION_RESULT_INVALID")


if __name__ == "__main__":
    unittest.main()
