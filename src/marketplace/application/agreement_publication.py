"""Pure preflight for a future protected Agreement publication write."""
from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any, Callable

from .agreement_candidate import AgreementCandidateBuildResult
from .agreement_formation import AgreementFormationEvaluationResult


_URI_RE = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:[^\s]+$")
_MAX_URI_BYTES = 2048

RecordIdentityExtractor = Callable[[Any], str]


class AgreementPublicationPreflightError(RuntimeError):
    """Stable fail-closed publication-preflight failure."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def _fail(code: str, message: str) -> None:
    raise AgreementPublicationPreflightError(code, message) from None


def _principal(value: object) -> str:
    if type(value) is not str or not value:
        raise ValueError("principal is invalid")
    try:
        encoded = value.encode("utf-8", "strict")
    except UnicodeEncodeError as exc:
        raise ValueError("principal is invalid") from exc
    if len(encoded) > _MAX_URI_BYTES or _URI_RE.fullmatch(value) is None:
        raise ValueError("principal is invalid")
    return value


@dataclass(frozen=True, slots=True)
class AgreementPublicationPreflightResult:
    agreement_record_id: str
    actor_principal: str
    formation_evidence: str
    required_principals: tuple[str, ...]
    preconditions_satisfied: bool
    reason: str
    publishes_agreement: bool = False
    authorizes_side_effects: bool = False

    def __post_init__(self) -> None:
        if type(self.agreement_record_id) is not str or not self.agreement_record_id:
            raise ValueError("agreement_record_id MUST be non-empty exact text")
        _principal(self.actor_principal)
        if self.formation_evidence not in {
            "EVIDENCE_SUFFICIENT_FOR_PROFILE",
            "EVIDENCE_INCOMPLETE",
        }:
            raise ValueError("formation_evidence is outside the reviewed profile")
        if type(self.required_principals) is not tuple or not self.required_principals:
            raise ValueError("required_principals MUST be a non-empty exact tuple")
        for principal in self.required_principals:
            _principal(principal)
        if type(self.preconditions_satisfied) is not bool:
            raise TypeError("preconditions_satisfied MUST be exact bool")
        if type(self.reason) is not str or not self.reason:
            raise ValueError("reason MUST be non-empty exact text")
        if self.publishes_agreement is not False:
            raise ValueError("preflight MUST NOT publish Agreement")
        if self.authorizes_side_effects is not False:
            raise ValueError("preflight MUST NOT authorize side effects")

    def to_document(self) -> dict[str, object]:
        return {
            "agreement_record_id": self.agreement_record_id,
            "actor_principal": self.actor_principal,
            "formation_evidence": self.formation_evidence,
            "required_principals": list(self.required_principals),
            "preconditions_satisfied": self.preconditions_satisfied,
            "reason": self.reason,
            "publishes_agreement": False,
            "authorizes_side_effects": False,
        }


class MarketplaceAgreementPublicationPreflightService:
    """Review publication preconditions without mutating application state."""

    def __init__(self, *, record_identity: RecordIdentityExtractor) -> None:
        if not callable(record_identity):
            raise TypeError("record_identity MUST be callable")
        self._record_identity = record_identity

    def review(
        self,
        *,
        candidate: AgreementCandidateBuildResult,
        formation: AgreementFormationEvaluationResult,
        actor_principal: str,
    ) -> AgreementPublicationPreflightResult:
        if type(candidate) is not AgreementCandidateBuildResult:
            _fail("AGREEMENT_PUBLICATION_CANDIDATE_INVALID", "Agreement candidate is invalid")
        if type(formation) is not AgreementFormationEvaluationResult:
            _fail("AGREEMENT_PUBLICATION_FORMATION_INVALID", "Agreement formation result is invalid")
        try:
            actor = _principal(actor_principal)
        except ValueError:
            _fail("AGREEMENT_PUBLICATION_REQUEST_INVALID", "publication preflight request is invalid")

        try:
            derived_id = self._record_identity(candidate.record)
        except Exception:
            _fail("AGREEMENT_PUBLICATION_IDENTITY_FAILED", "Agreement candidate identity could not be verified")
        if type(derived_id) is not str or derived_id != candidate.record_id:
            _fail("AGREEMENT_PUBLICATION_IDENTITY_MISMATCH", "Agreement candidate identity changed")
        if formation.agreement_record_id != candidate.record_id:
            _fail("AGREEMENT_PUBLICATION_BINDING_MISMATCH", "formation evidence targets another Agreement")

        required = formation.required_principals
        covered = formation.covered_principals
        missing = formation.missing_principals
        if len(set(required)) != len(required):
            _fail("AGREEMENT_PUBLICATION_FORMATION_INVALID", "required principal set is invalid")
        if len(set(covered)) != len(covered) or len(set(missing)) != len(missing):
            _fail("AGREEMENT_PUBLICATION_FORMATION_INVALID", "formation coverage is invalid")
        required_set = set(required)
        covered_set = set(covered)
        missing_set = set(missing)
        if (
            not covered_set.issubset(required_set)
            or missing_set != required_set - covered_set
            or (
                formation.formation_evidence == "EVIDENCE_SUFFICIENT_FOR_PROFILE"
                and missing_set
            )
            or (
                formation.formation_evidence == "EVIDENCE_INCOMPLETE"
                and not missing_set
            )
        ):
            _fail("AGREEMENT_PUBLICATION_FORMATION_INVALID", "formation evidence is internally inconsistent")

        if actor not in required_set:
            satisfied = False
            reason = "ACTOR_NOT_AGREEMENT_PARTY"
        elif formation.formation_evidence != "EVIDENCE_SUFFICIENT_FOR_PROFILE":
            satisfied = False
            reason = "FORMATION_EVIDENCE_INCOMPLETE"
        elif actor not in covered_set:
            satisfied = False
            reason = "ACTOR_ASSENT_NOT_COVERED"
        else:
            satisfied = True
            reason = "PRECONDITIONS_SATISFIED"

        try:
            return AgreementPublicationPreflightResult(
                agreement_record_id=candidate.record_id,
                actor_principal=actor,
                formation_evidence=formation.formation_evidence,
                required_principals=required,
                preconditions_satisfied=satisfied,
                reason=reason,
            )
        except Exception:
            _fail("AGREEMENT_PUBLICATION_RESULT_INVALID", "publication preflight result is invalid")


__all__ = [
    "AgreementPublicationPreflightError",
    "AgreementPublicationPreflightResult",
    "MarketplaceAgreementPublicationPreflightService",
    "RecordIdentityExtractor",
]
