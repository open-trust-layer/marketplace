from __future__ import annotations

import unittest

from marketplace.application.agreement_candidate import AgreementCandidateBuildResult
from marketplace.application.agreement_formation import AgreementFormationEvaluationResult
from marketplace.application.agreement_publication import (
    AgreementPublicationPreflightError,
    MarketplaceAgreementPublicationPreflightService,
)


AGREEMENT_ID = "r1_test-agreement"
SELLER = "urn:marketplace:test:seller"
BUYER = "urn:marketplace:test:buyer"
OUTSIDER = "urn:marketplace:test:outsider"
RECORD = object()


def _candidate(*, record_id: str = AGREEMENT_ID) -> AgreementCandidateBuildResult:
    return AgreementCandidateBuildResult(
        record=RECORD,
        record_id=record_id,
        listing_record_id="r1_listing",
        proposal_record_id="r1_proposal",
        acceptance_record_id="r1_acceptance",
    )


def _formation(
    *,
    agreement_record_id: str = AGREEMENT_ID,
    sufficient: bool = True,
) -> AgreementFormationEvaluationResult:
    if sufficient:
        covered = (BUYER, SELLER)
        missing = ()
        status = "EVIDENCE_SUFFICIENT_FOR_PROFILE"
    else:
        covered = (SELLER,)
        missing = (BUYER,)
        status = "EVIDENCE_INCOMPLETE"
    return AgreementFormationEvaluationResult(
        agreement_record_id=agreement_record_id,
        formation_evidence=status,
        required_principals=(BUYER, SELLER),
        covered_principals=covered,
        missing_principals=missing,
    )


class ProductAgreementPublicationPreflightTests(unittest.TestCase):
    def _service(self, *, identity: str = AGREEMENT_ID):
        return MarketplaceAgreementPublicationPreflightService(
            record_identity=lambda _record: identity
        )

    def test_party_with_complete_formation_evidence_satisfies_preconditions(self) -> None:
        result = self._service().review(
            candidate=_candidate(),
            formation=_formation(),
            actor_principal=SELLER,
        )
        self.assertTrue(result.preconditions_satisfied)
        self.assertEqual(result.reason, "PRECONDITIONS_SATISFIED")
        self.assertFalse(result.publishes_agreement)
        self.assertFalse(result.authorizes_side_effects)

    def test_outsider_never_satisfies_publication_preconditions(self) -> None:
        result = self._service().review(
            candidate=_candidate(),
            formation=_formation(),
            actor_principal=OUTSIDER,
        )
        self.assertFalse(result.preconditions_satisfied)
        self.assertEqual(result.reason, "ACTOR_NOT_AGREEMENT_PARTY")

    def test_incomplete_formation_evidence_fails_closed(self) -> None:
        result = self._service().review(
            candidate=_candidate(),
            formation=_formation(sufficient=False),
            actor_principal=SELLER,
        )
        self.assertFalse(result.preconditions_satisfied)
        self.assertEqual(result.reason, "FORMATION_EVIDENCE_INCOMPLETE")

    def test_formation_for_another_agreement_is_rejected(self) -> None:
        with self.assertRaises(AgreementPublicationPreflightError) as caught:
            self._service().review(
                candidate=_candidate(),
                formation=_formation(agreement_record_id="r1_other-agreement"),
                actor_principal=SELLER,
            )
        self.assertEqual(caught.exception.code, "AGREEMENT_PUBLICATION_BINDING_MISMATCH")

    def test_candidate_record_identity_is_reverified(self) -> None:
        with self.assertRaises(AgreementPublicationPreflightError) as caught:
            self._service(identity="r1_different").review(
                candidate=_candidate(),
                formation=_formation(),
                actor_principal=SELLER,
            )
        self.assertEqual(caught.exception.code, "AGREEMENT_PUBLICATION_IDENTITY_MISMATCH")

    def test_inconsistent_sufficient_formation_result_is_rejected(self) -> None:
        hostile = AgreementFormationEvaluationResult(
            agreement_record_id=AGREEMENT_ID,
            formation_evidence="EVIDENCE_SUFFICIENT_FOR_PROFILE",
            required_principals=(BUYER, SELLER),
            covered_principals=(SELLER,),
            missing_principals=(BUYER,),
        )
        with self.assertRaises(AgreementPublicationPreflightError) as caught:
            self._service().review(
                candidate=_candidate(),
                formation=hostile,
                actor_principal=SELLER,
            )
        self.assertEqual(caught.exception.code, "AGREEMENT_PUBLICATION_FORMATION_INVALID")


if __name__ == "__main__":
    unittest.main()
