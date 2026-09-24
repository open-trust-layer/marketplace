from __future__ import annotations

import unittest

from marketplace.application.agreement_assent_candidate import (
    AgreementAssentCandidateResolutionError,
    MarketplaceAgreementAssentCandidateResolutionService,
)
from marketplace.application.agreement_candidate import AgreementCandidateBuildResult


PROPOSAL = "r1_" + "P" * 43
LISTING = "r1_" + "L" * 43
ACCEPTANCE = "r1_" + "A" * 43
AGREEMENT = "r1_" + "G" * 43


def result(
    *,
    listing: str = LISTING,
    proposal: str = PROPOSAL,
    acceptance: str = ACCEPTANCE,
):
    return AgreementCandidateBuildResult(
        record=object(),
        record_id=AGREEMENT,
        listing_record_id=listing,
        proposal_record_id=proposal,
        acceptance_record_id=acceptance,
    )


class ProductAgreementAssentCandidateResolutionTests(unittest.TestCase):
    def make_service(self, *, proposal=None, parents=None, author=None):
        calls = []
        proposal_value = (
            {"type": "proposal", "parents": (LISTING,)}
            if proposal is None
            else proposal
        )

        def read(record_id):
            calls.append(("read", record_id))
            return proposal_value

        def build(**kwargs):
            calls.append(("build", kwargs))
            if author is not None:
                return author(**kwargs)
            return result(
                listing=kwargs["listing_record_id"],
                proposal=kwargs["proposal_record_id"],
                acceptance=kwargs["acceptance_record_id"],
            )

        service = MarketplaceAgreementAssentCandidateResolutionService(
            read_proposal=read,
            is_proposal_record=lambda value: value.get("type") == "proposal",
            proposal_parent_ids=(
                (lambda _value: parents)
                if parents is not None
                else (lambda value: value["parents"])
            ),
            build_candidate=build,
        )
        return service, calls

    def test_resolves_listing_only_from_exact_proposal_parent(self):
        service, calls = self.make_service()
        built = service.resolve(
            proposal_record_id=PROPOSAL,
            acceptance_record_id=ACCEPTANCE,
        )
        self.assertEqual(built.listing_record_id, LISTING)
        self.assertEqual(built.proposal_record_id, PROPOSAL)
        self.assertEqual(built.acceptance_record_id, ACCEPTANCE)
        self.assertEqual(calls[0], ("read", PROPOSAL))
        self.assertEqual(
            calls[1],
            (
                "build",
                {
                    "listing_record_id": LISTING,
                    "proposal_record_id": PROPOSAL,
                    "acceptance_record_id": ACCEPTANCE,
                },
            ),
        )

    def test_invalid_request_fails_before_proposal_read(self):
        service, calls = self.make_service()
        with self.assertRaises(AgreementAssentCandidateResolutionError) as caught:
            service.resolve(
                proposal_record_id="bad/id",
                acceptance_record_id=ACCEPTANCE,
            )
        self.assertEqual(
            caught.exception.code,
            "AGREEMENT_ASSENT_CANDIDATE_REQUEST_INVALID",
        )
        self.assertEqual(calls, [])

    def test_missing_proposal_fails_before_candidate_authoring(self):
        service, calls = self.make_service(proposal=None)
        service._read_proposal = lambda record_id: None
        with self.assertRaises(AgreementAssentCandidateResolutionError) as caught:
            service.resolve(
                proposal_record_id=PROPOSAL,
                acceptance_record_id=ACCEPTANCE,
            )
        self.assertEqual(
            caught.exception.code,
            "AGREEMENT_ASSENT_CANDIDATE_PROPOSAL_NOT_FOUND",
        )
        self.assertFalse(any(call[0] == "build" for call in calls))

    def test_multiple_parents_fail_closed_without_authoring(self):
        service, calls = self.make_service(parents=(LISTING, "r1_" + "X" * 43))
        with self.assertRaises(AgreementAssentCandidateResolutionError) as caught:
            service.resolve(
                proposal_record_id=PROPOSAL,
                acceptance_record_id=ACCEPTANCE,
            )
        self.assertEqual(
            caught.exception.code,
            "AGREEMENT_ASSENT_CANDIDATE_PARENT_INVALID",
        )
        self.assertFalse(any(call[0] == "build" for call in calls))

    def test_mismatched_authoring_result_is_rejected(self):
        service, _ = self.make_service(
            author=lambda **_kwargs: result(acceptance="r1_" + "Z" * 43)
        )
        with self.assertRaises(AgreementAssentCandidateResolutionError) as caught:
            service.resolve(
                proposal_record_id=PROPOSAL,
                acceptance_record_id=ACCEPTANCE,
            )
        self.assertEqual(
            caught.exception.code,
            "AGREEMENT_ASSENT_CANDIDATE_RESULT_INVALID",
        )

    def test_authoring_failure_is_stable_and_nonreflective(self):
        def fail(**_kwargs):
            raise RuntimeError("private source detail")

        service, _ = self.make_service(author=fail)
        with self.assertRaises(AgreementAssentCandidateResolutionError) as caught:
            service.resolve(
                proposal_record_id=PROPOSAL,
                acceptance_record_id=ACCEPTANCE,
            )
        self.assertEqual(
            caught.exception.code,
            "AGREEMENT_ASSENT_CANDIDATE_BUILD_FAILED",
        )
        self.assertNotIn("private source detail", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
