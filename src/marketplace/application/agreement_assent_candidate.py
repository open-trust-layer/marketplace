"""Read-only resolution of exact Agreement candidate source identities."""
from __future__ import annotations

from typing import Any, Callable

from .agreement_candidate import AgreementCandidateBuildResult


ProposalReader = Callable[[str], Any | None]
ProposalPredicate = Callable[[Any], bool]
ProposalParentExtractor = Callable[[Any], tuple[str, ...]]
AgreementCandidateAuthor = Callable[..., AgreementCandidateBuildResult]


class AgreementAssentCandidateResolutionError(RuntimeError):
    """Stable non-reflective candidate-resolution failure."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def _fail(code: str, message: str) -> None:
    raise AgreementAssentCandidateResolutionError(code, message) from None


def _record_id(value: object) -> str:
    if type(value) is not str or not value or len(value) > 512:
        raise ValueError("record identity is invalid")
    if any(ord(char) < 33 or ord(char) > 126 or char in "/?#" for char in value):
        raise ValueError("record identity is invalid")
    return value


class MarketplaceAgreementAssentCandidateResolutionService:
    """Resolve Proposal parent Listing and build one exact unpublished candidate."""

    def __init__(
        self,
        *,
        read_proposal: ProposalReader,
        is_proposal_record: ProposalPredicate,
        proposal_parent_ids: ProposalParentExtractor,
        build_candidate: AgreementCandidateAuthor,
    ) -> None:
        for name, value in (
            ("read_proposal", read_proposal),
            ("is_proposal_record", is_proposal_record),
            ("proposal_parent_ids", proposal_parent_ids),
            ("build_candidate", build_candidate),
        ):
            if not callable(value):
                raise TypeError(f"{name} MUST be callable")
        self._read_proposal = read_proposal
        self._is_proposal_record = is_proposal_record
        self._proposal_parent_ids = proposal_parent_ids
        self._build_candidate = build_candidate

    def resolve(
        self,
        *,
        proposal_record_id: str,
        acceptance_record_id: str,
    ) -> AgreementCandidateBuildResult:
        try:
            proposal_id = _record_id(proposal_record_id)
            acceptance_id = _record_id(acceptance_record_id)
        except ValueError:
            _fail(
                "AGREEMENT_ASSENT_CANDIDATE_REQUEST_INVALID",
                "Agreement assent candidate request is invalid",
            )

        try:
            proposal = self._read_proposal(proposal_id)
        except Exception:
            _fail(
                "AGREEMENT_ASSENT_CANDIDATE_PROPOSAL_UNAVAILABLE",
                "Proposal could not be resolved",
            )
        if proposal is None:
            _fail(
                "AGREEMENT_ASSENT_CANDIDATE_PROPOSAL_NOT_FOUND",
                "Proposal was not found",
            )

        try:
            is_proposal = self._is_proposal_record(proposal)
        except Exception:
            _fail(
                "AGREEMENT_ASSENT_CANDIDATE_PROPOSAL_INVALID",
                "target record is not a valid Proposal",
            )
        if type(is_proposal) is not bool or not is_proposal:
            _fail(
                "AGREEMENT_ASSENT_CANDIDATE_PROPOSAL_INVALID",
                "target record is not a valid Proposal",
            )

        try:
            parents = self._proposal_parent_ids(proposal)
        except Exception:
            _fail(
                "AGREEMENT_ASSENT_CANDIDATE_PARENT_INVALID",
                "Proposal parent binding is invalid",
            )
        if type(parents) is not tuple or len(parents) != 1:
            _fail(
                "AGREEMENT_ASSENT_CANDIDATE_PARENT_INVALID",
                "Proposal MUST have exactly one parent Listing",
            )
        try:
            listing_id = _record_id(parents[0])
        except Exception:
            _fail(
                "AGREEMENT_ASSENT_CANDIDATE_PARENT_INVALID",
                "Proposal parent binding is invalid",
            )

        try:
            result = self._build_candidate(
                listing_record_id=listing_id,
                proposal_record_id=proposal_id,
                acceptance_record_id=acceptance_id,
            )
        except Exception:
            _fail(
                "AGREEMENT_ASSENT_CANDIDATE_BUILD_FAILED",
                "Agreement candidate could not be built from exact source evidence",
            )
        if (
            type(result) is not AgreementCandidateBuildResult
            or result.listing_record_id != listing_id
            or result.proposal_record_id != proposal_id
            or result.acceptance_record_id != acceptance_id
            or result.published is not False
            or result.formation_evidence != "NOT_EVALUATED"
        ):
            _fail(
                "AGREEMENT_ASSENT_CANDIDATE_RESULT_INVALID",
                "Agreement candidate result is invalid",
            )
        return result


__all__ = [
    "AgreementAssentCandidateResolutionError",
    "AgreementCandidateAuthor",
    "MarketplaceAgreementAssentCandidateResolutionService",
    "ProposalParentExtractor",
    "ProposalPredicate",
    "ProposalReader",
]
