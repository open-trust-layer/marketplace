"""Transport-neutral orchestration for Agreement assent preparation and intake."""
from __future__ import annotations

from dataclasses import dataclass

from ..runtime.contracts import StoreDisposition
from .agreement_assent import (
    AgreementAssentSigningPreparation,
    MarketplaceAgreementAssentProofService,
    VerifiedAgreementAssent,
)
from .agreement_assent_coordination import (
    AgreementAssentPutResult,
    MarketplaceAgreementAssentCoordinationService,
)
from .agreement_assent_formation import MarketplaceAgreementAssentFormationService
from .agreement_candidate import AgreementCandidateBuildResult
from .agreement_formation import AgreementFormationEvaluationResult


class AgreementAssentWorkflowError(RuntimeError):
    """Stable non-reflective Agreement-assent workflow failure."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def _fail(code: str, message: str) -> None:
    raise AgreementAssentWorkflowError(code, message) from None


@dataclass(frozen=True, slots=True)
class AgreementAssentSubmissionResult:
    agreement_record_id: str
    principal: str
    verification_method: str
    disposition: StoreDisposition
    accepted_at: int
    expires_at: int
    publishes_agreement: bool = False
    authorizes_side_effects: bool = False

    def __post_init__(self) -> None:
        for value in (
            self.agreement_record_id,
            self.principal,
            self.verification_method,
        ):
            if type(value) is not str or not value:
                raise ValueError("Agreement assent submission binding is invalid")
        if type(self.disposition) is not StoreDisposition:
            raise TypeError("disposition MUST be exact StoreDisposition")
        if (
            type(self.accepted_at) is not int
            or isinstance(self.accepted_at, bool)
            or type(self.expires_at) is not int
            or isinstance(self.expires_at, bool)
            or self.accepted_at < 0
            or self.expires_at <= self.accepted_at
        ):
            raise ValueError("Agreement assent retention timestamps are invalid")
        if self.publishes_agreement is not False:
            raise ValueError("assent submission MUST NOT publish Agreement")
        if self.authorizes_side_effects is not False:
            raise ValueError("assent submission MUST NOT authorize side effects")


class MarketplaceAgreementAssentWorkflowService:
    """Compose reviewed assent services without adding hidden lifecycle actions."""

    def __init__(
        self,
        *,
        proof: MarketplaceAgreementAssentProofService,
        coordination: MarketplaceAgreementAssentCoordinationService,
        formation: MarketplaceAgreementAssentFormationService,
    ) -> None:
        if type(proof) is not MarketplaceAgreementAssentProofService:
            raise TypeError("proof MUST be exact MarketplaceAgreementAssentProofService")
        if type(coordination) is not MarketplaceAgreementAssentCoordinationService:
            raise TypeError(
                "coordination MUST be exact MarketplaceAgreementAssentCoordinationService"
            )
        if type(formation) is not MarketplaceAgreementAssentFormationService:
            raise TypeError(
                "formation MUST be exact MarketplaceAgreementAssentFormationService"
            )
        self._proof = proof
        self._coordination = coordination
        self._formation = formation

    def prepare(
        self,
        *,
        candidate: AgreementCandidateBuildResult,
        principal: str,
        verification_method: str,
        at_time: int,
    ) -> AgreementAssentSigningPreparation:
        if type(candidate) is not AgreementCandidateBuildResult:
            _fail(
                "AGREEMENT_ASSENT_WORKFLOW_CANDIDATE_INVALID",
                "Agreement assent workflow requires an exact candidate result",
            )
        try:
            result = self._proof.prepare(
                candidate=candidate,
                principal=principal,
                verification_method=verification_method,
                at_time=at_time,
            )
        except Exception:
            _fail(
                "AGREEMENT_ASSENT_WORKFLOW_PREPARATION_FAILED",
                "Agreement assent signing preparation failed",
            )
        if (
            type(result) is not AgreementAssentSigningPreparation
            or result.agreement_record_id != candidate.record_id
        ):
            _fail(
                "AGREEMENT_ASSENT_WORKFLOW_PREPARATION_INVALID",
                "Agreement assent signing preparation is invalid",
            )
        return result

    def submit(
        self,
        *,
        candidate: AgreementCandidateBuildResult,
        preparation: AgreementAssentSigningPreparation,
        signature: bytes,
        at_time: int,
    ) -> AgreementAssentSubmissionResult:
        if type(candidate) is not AgreementCandidateBuildResult:
            _fail(
                "AGREEMENT_ASSENT_WORKFLOW_CANDIDATE_INVALID",
                "Agreement assent workflow requires an exact candidate result",
            )
        if type(preparation) is not AgreementAssentSigningPreparation:
            _fail(
                "AGREEMENT_ASSENT_WORKFLOW_PREPARATION_INVALID",
                "Agreement assent signing preparation is invalid",
            )
        try:
            verified = self._proof.finalize(
                candidate=candidate,
                preparation=preparation,
                signature=signature,
                at_time=at_time,
            )
        except Exception:
            _fail(
                "AGREEMENT_ASSENT_WORKFLOW_VERIFICATION_FAILED",
                "Agreement assent signature verification failed",
            )
        if (
            type(verified) is not VerifiedAgreementAssent
            or verified.agreement_record_id != candidate.record_id
            or verified.principal != preparation.principal
            or verified.verification_method != preparation.verification_method
        ):
            _fail(
                "AGREEMENT_ASSENT_WORKFLOW_VERIFICATION_INVALID",
                "verified Agreement assent binding is invalid",
            )

        try:
            stored = self._coordination.accept(verified)
        except Exception:
            _fail(
                "AGREEMENT_ASSENT_WORKFLOW_STORE_FAILED",
                "verified Agreement assent could not be retained",
            )
        if type(stored) is not AgreementAssentPutResult:
            _fail(
                "AGREEMENT_ASSENT_WORKFLOW_STORE_INVALID",
                "Agreement assent coordination result is invalid",
            )

        try:
            return AgreementAssentSubmissionResult(
                agreement_record_id=verified.agreement_record_id,
                principal=verified.principal,
                verification_method=verified.verification_method,
                disposition=stored.disposition,
                accepted_at=stored.accepted_at,
                expires_at=stored.expires_at,
            )
        except Exception:
            _fail(
                "AGREEMENT_ASSENT_WORKFLOW_RESULT_INVALID",
                "Agreement assent submission result is invalid",
            )

    def formation_status(
        self,
        *,
        candidate: AgreementCandidateBuildResult,
        at_time: int,
    ) -> AgreementFormationEvaluationResult:
        if type(candidate) is not AgreementCandidateBuildResult:
            _fail(
                "AGREEMENT_ASSENT_WORKFLOW_CANDIDATE_INVALID",
                "Agreement assent workflow requires an exact candidate result",
            )
        try:
            result = self._formation.evaluate(
                candidate=candidate,
                at_time=at_time,
            )
        except Exception:
            _fail(
                "AGREEMENT_ASSENT_WORKFLOW_FORMATION_FAILED",
                "Agreement formation status could not be evaluated",
            )
        if (
            type(result) is not AgreementFormationEvaluationResult
            or result.agreement_record_id != candidate.record_id
        ):
            _fail(
                "AGREEMENT_ASSENT_WORKFLOW_FORMATION_INVALID",
                "Agreement formation status is invalid",
            )
        return result


__all__ = [
    "AgreementAssentSubmissionResult",
    "AgreementAssentWorkflowError",
    "MarketplaceAgreementAssentWorkflowService",
]
