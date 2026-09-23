"""Transport-neutral authoring seam for unpublished Agreement candidates."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from .state import MarketplaceApplicationStateService


AgreementCandidateBuilder = Callable[[Any, Any, Any], Any]
RecordIdentityExtractor = Callable[[Any], str]


class AgreementCandidateAuthoringError(RuntimeError):
    """Stable Agreement-candidate authoring failure without reflected payloads."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def _fail(code: str, message: str) -> None:
    raise AgreementCandidateAuthoringError(code, message) from None


def _record_id(value: object, *, name: str) -> str:
    if type(value) is not str or not value or len(value) > 512:
        raise ValueError(f"{name} is invalid")
    if any(ord(char) < 33 or ord(char) > 126 or char in "/?#" for char in value):
        raise ValueError(f"{name} is invalid")
    return value


@dataclass(frozen=True, slots=True)
class AgreementCandidateBuildResult:
    record: Any
    record_id: str
    listing_record_id: str
    proposal_record_id: str
    acceptance_record_id: str
    published: bool = False
    formation_evidence: str = "NOT_EVALUATED"

    def __post_init__(self) -> None:
        _record_id(self.record_id, name="record_id")
        _record_id(self.listing_record_id, name="listing_record_id")
        _record_id(self.proposal_record_id, name="proposal_record_id")
        _record_id(self.acceptance_record_id, name="acceptance_record_id")
        if self.published is not False:
            raise ValueError("Agreement candidate result MUST remain unpublished")
        if self.formation_evidence != "NOT_EVALUATED":
            raise ValueError("Agreement candidate formation MUST remain unevaluated")

    def to_document(self) -> dict[str, object]:
        return {
            "record_id": self.record_id,
            "source_records": {
                "listing": self.listing_record_id,
                "proposal": self.proposal_record_id,
                "proposal_acceptance": self.acceptance_record_id,
            },
            "published": False,
            "formation_evidence": "NOT_EVALUATED",
        }


class MarketplaceAgreementCandidateAuthoringService:
    """Resolve exact source evidence and build, but never publish, an Agreement."""

    def __init__(
        self,
        *,
        state: MarketplaceApplicationStateService,
        build_record: AgreementCandidateBuilder,
        record_identity: RecordIdentityExtractor,
    ) -> None:
        if type(state) is not MarketplaceApplicationStateService:
            raise TypeError("state MUST be exact MarketplaceApplicationStateService")
        if not callable(build_record):
            raise TypeError("build_record MUST be callable")
        if not callable(record_identity):
            raise TypeError("record_identity MUST be callable")
        self._state = state
        self._build_record = build_record
        self._record_identity = record_identity

    def _resolve(self, record_id: str, *, role: str) -> Any:
        try:
            reviewed_id = _record_id(record_id, name=f"{role}_record_id")
        except ValueError:
            _fail("AGREEMENT_CANDIDATE_REQUEST_INVALID", "Agreement candidate request is invalid")
        try:
            value = self._state.peek(reviewed_id)
        except Exception:
            _fail("AGREEMENT_CANDIDATE_SOURCE_UNAVAILABLE", f"{role} source record could not be resolved")
        if value is None:
            _fail("AGREEMENT_CANDIDATE_SOURCE_NOT_FOUND", f"{role} source record was not found")
        return value

    def build_candidate(
        self,
        *,
        listing_record_id: str,
        proposal_record_id: str,
        acceptance_record_id: str,
    ) -> AgreementCandidateBuildResult:
        listing = self._resolve(listing_record_id, role="listing")
        proposal = self._resolve(proposal_record_id, role="proposal")
        acceptance = self._resolve(acceptance_record_id, role="acceptance")
        try:
            record = self._build_record(listing, proposal, acceptance)
        except Exception:
            _fail("AGREEMENT_CANDIDATE_BUILD_FAILED", "Agreement candidate could not be built")
        try:
            candidate_id = _record_id(self._record_identity(record), name="record_id")
        except Exception:
            _fail("AGREEMENT_CANDIDATE_IDENTITY_FAILED", "Agreement candidate identity could not be derived")
        try:
            return AgreementCandidateBuildResult(
                record=record,
                record_id=candidate_id,
                listing_record_id=listing_record_id,
                proposal_record_id=proposal_record_id,
                acceptance_record_id=acceptance_record_id,
            )
        except Exception:
            _fail("AGREEMENT_CANDIDATE_RESULT_INVALID", "Agreement candidate result is invalid")


__all__ = [
    "AgreementCandidateAuthoringError",
    "AgreementCandidateBuildResult",
    "AgreementCandidateBuilder",
    "MarketplaceAgreementCandidateAuthoringService",
    "RecordIdentityExtractor",
]
