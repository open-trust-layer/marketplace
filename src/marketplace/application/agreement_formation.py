"""Transport-neutral application seam for Agreement formation evidence evaluation."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable


FormationEvaluator = Callable[[Any, tuple[Any, ...]], dict[str, Any]]


class AgreementFormationEvaluationError(RuntimeError):
    """Stable non-reflective application failure for formation evaluation."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def _fail(code: str, message: str) -> None:
    raise AgreementFormationEvaluationError(code, message) from None


@dataclass(frozen=True, slots=True)
class AgreementFormationEvaluationResult:
    agreement_record_id: str
    formation_evidence: str
    required_principals: tuple[str, ...]
    covered_principals: tuple[str, ...]
    missing_principals: tuple[str, ...]
    legal_enforceability: str = "NOT_EVALUATED"
    universal_truth: bool = False
    publishes_agreement: bool = False
    authorizes_side_effects: bool = False

    def __post_init__(self) -> None:
        if type(self.agreement_record_id) is not str or not self.agreement_record_id:
            raise ValueError("agreement_record_id MUST be non-empty exact text")
        if self.formation_evidence not in {
            "EVIDENCE_SUFFICIENT_FOR_PROFILE",
            "EVIDENCE_INCOMPLETE",
        }:
            raise ValueError("formation_evidence is outside the reviewed product profile")
        for values in (
            self.required_principals,
            self.covered_principals,
            self.missing_principals,
        ):
            if type(values) is not tuple or any(type(value) is not str or not value for value in values):
                raise ValueError("principal collections MUST be exact non-empty-text tuples")
        if self.legal_enforceability != "NOT_EVALUATED":
            raise ValueError("legal enforceability MUST remain unevaluated")
        if self.universal_truth is not False:
            raise ValueError("formation result MUST NOT claim universal truth")
        if self.publishes_agreement is not False:
            raise ValueError("formation evaluation MUST NOT publish Agreement")
        if self.authorizes_side_effects is not False:
            raise ValueError("formation evaluation MUST NOT authorize side effects")

    def to_document(self) -> dict[str, object]:
        return {
            "agreement_record_id": self.agreement_record_id,
            "formation_evidence": self.formation_evidence,
            "required_principals": list(self.required_principals),
            "covered_principals": list(self.covered_principals),
            "missing_principals": list(self.missing_principals),
            "legal_enforceability": "NOT_EVALUATED",
            "universal_truth": False,
            "publishes_agreement": False,
            "authorizes_side_effects": False,
        }


class MarketplaceAgreementFormationEvaluationService:
    """Evaluate injected assent evidence without creating proofs or mutating state."""

    def __init__(self, *, evaluate: FormationEvaluator) -> None:
        if not callable(evaluate):
            raise TypeError("evaluate MUST be callable")
        self._evaluate = evaluate

    def evaluate(
        self,
        *,
        agreement: Any,
        evidence: tuple[Any, ...],
    ) -> AgreementFormationEvaluationResult:
        if type(evidence) is not tuple:
            _fail("AGREEMENT_FORMATION_REQUEST_INVALID", "formation evidence request is invalid")
        try:
            document = self._evaluate(agreement, evidence)
        except Exception:
            _fail("AGREEMENT_FORMATION_EVALUATION_FAILED", "Agreement formation evidence could not be evaluated")
        if type(document) is not dict:
            _fail("AGREEMENT_FORMATION_RESULT_INVALID", "formation evaluator returned an invalid result")
        try:
            return AgreementFormationEvaluationResult(
                agreement_record_id=document["agreement"],
                formation_evidence=document["formation_evidence"],
                required_principals=tuple(document["required_principals"]),
                covered_principals=tuple(document["covered_principals"]),
                missing_principals=tuple(document["missing_principals"]),
                legal_enforceability=document["legal_enforceability"],
                universal_truth=document["universal_truth"],
                publishes_agreement=document["publishes_agreement"],
                authorizes_side_effects=document["authorizes_side_effects"],
            )
        except Exception:
            _fail("AGREEMENT_FORMATION_RESULT_INVALID", "formation evaluator returned an invalid result")


__all__ = [
    "AgreementFormationEvaluationError",
    "AgreementFormationEvaluationResult",
    "FormationEvaluator",
    "MarketplaceAgreementFormationEvaluationService",
]
