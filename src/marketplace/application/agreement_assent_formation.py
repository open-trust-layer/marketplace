"""Read-only aggregation of retained Agreement assent into formation evidence."""
from __future__ import annotations

from typing import Any, Callable

from .agreement_assent import VerifiedAgreementAssent
from .agreement_assent_coordination import (
    MarketplaceAgreementAssentCoordinationService,
    PreparedAgreementAssent,
)
from .agreement_candidate import AgreementCandidateBuildResult
from .agreement_formation import (
    AgreementFormationEvaluationResult,
    MarketplaceAgreementFormationEvaluationService,
)
from .auth_verification_method_snapshot import (
    MarketplaceAuthenticationVerificationMethodSnapshot,
)


AgreementRecordIdentity = Callable[[Any], str]
PreparedAgreementAssentReverifier = Callable[
    [Any, PreparedAgreementAssent, bytes],
    Any,
]
FormationEvidenceBuilder = Callable[[VerifiedAgreementAssent, bytes], Any]


class AgreementAssentFormationError(RuntimeError):
    """Stable non-reflective aggregation failure."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def _fail(code: str, message: str) -> None:
    raise AgreementAssentFormationError(code, message) from None


def _time(value: object) -> int:
    if type(value) is not int or isinstance(value, bool) or value < 0:
        raise ValueError("evaluation time is invalid")
    return value


class MarketplaceAgreementAssentFormationService:
    """Re-establish trust in retained assent before running formation evaluation."""

    def __init__(
        self,
        *,
        coordination: MarketplaceAgreementAssentCoordinationService,
        verification_methods: MarketplaceAuthenticationVerificationMethodSnapshot,
        formation: MarketplaceAgreementFormationEvaluationService,
        record_identity: AgreementRecordIdentity,
        reverify_prepared_proof: PreparedAgreementAssentReverifier,
        build_formation_evidence: FormationEvidenceBuilder,
    ) -> None:
        if type(coordination) is not MarketplaceAgreementAssentCoordinationService:
            raise TypeError(
                "coordination MUST be exact MarketplaceAgreementAssentCoordinationService"
            )
        if type(verification_methods) is not MarketplaceAuthenticationVerificationMethodSnapshot:
            raise TypeError(
                "verification_methods MUST be exact MarketplaceAuthenticationVerificationMethodSnapshot"
            )
        if type(formation) is not MarketplaceAgreementFormationEvaluationService:
            raise TypeError(
                "formation MUST be exact MarketplaceAgreementFormationEvaluationService"
            )
        if not callable(record_identity):
            raise TypeError("record_identity MUST be callable")
        if not callable(reverify_prepared_proof):
            raise TypeError("reverify_prepared_proof MUST be callable")
        if not callable(build_formation_evidence):
            raise TypeError("build_formation_evidence MUST be callable")
        self._coordination = coordination
        self._verification_methods = verification_methods
        self._formation = formation
        self._record_identity = record_identity
        self._reverify_prepared_proof = reverify_prepared_proof
        self._build_formation_evidence = build_formation_evidence

    def _candidate_identity(self, candidate: AgreementCandidateBuildResult) -> str:
        if type(candidate) is not AgreementCandidateBuildResult:
            _fail(
                "AGREEMENT_ASSENT_FORMATION_CANDIDATE_INVALID",
                "Agreement assent formation requires an exact candidate result",
            )
        try:
            derived = self._record_identity(candidate.record)
        except Exception:
            _fail(
                "AGREEMENT_ASSENT_FORMATION_IDENTITY_FAILED",
                "Agreement candidate identity could not be derived",
            )
        if type(derived) is not str or derived != candidate.record_id:
            _fail(
                "AGREEMENT_ASSENT_FORMATION_IDENTITY_MISMATCH",
                "Agreement candidate identity does not match the reviewed result",
            )
        return derived

    def evaluate(
        self,
        *,
        candidate: AgreementCandidateBuildResult,
        at_time: int,
    ) -> AgreementFormationEvaluationResult:
        agreement_record_id = self._candidate_identity(candidate)
        try:
            reviewed_time = _time(at_time)
        except ValueError:
            _fail(
                "AGREEMENT_ASSENT_FORMATION_REQUEST_INVALID",
                "Agreement assent formation request is invalid",
            )

        try:
            retained = self._coordination.for_agreement(agreement_record_id)
        except Exception:
            _fail(
                "AGREEMENT_ASSENT_FORMATION_EVIDENCE_UNAVAILABLE",
                "retained Agreement assent evidence is unavailable",
            )

        evidence: list[Any] = []
        for prepared in retained:
            if type(prepared) is not PreparedAgreementAssent:
                _fail(
                    "AGREEMENT_ASSENT_FORMATION_EVIDENCE_INVALID",
                    "retained Agreement assent evidence is invalid",
                )
            if prepared.agreement_record_id != agreement_record_id:
                _fail(
                    "AGREEMENT_ASSENT_FORMATION_BINDING_MISMATCH",
                    "retained Agreement assent targets another Agreement",
                )

            try:
                bound = self._verification_methods.verify(
                    principal=prepared.principal,
                    verification_method=prepared.verification_method,
                    at_time=reviewed_time,
                )
            except Exception:
                bound = False
            if bound is not True:
                continue

            try:
                public_key = self._verification_methods.verification_key_bytes(
                    prepared.verification_method
                )
            except Exception:
                continue
            if type(public_key) is not bytes or len(public_key) != 32:
                continue

            try:
                proof = self._reverify_prepared_proof(
                    candidate.record,
                    prepared,
                    public_key,
                )
            except Exception:
                _fail(
                    "AGREEMENT_ASSENT_FORMATION_REVERIFICATION_FAILED",
                    "retained Agreement assent proof could not be reverified",
                )
            if proof is None:
                _fail(
                    "AGREEMENT_ASSENT_FORMATION_REVERIFICATION_FAILED",
                    "retained Agreement assent proof could not be reverified",
                )

            try:
                verified = VerifiedAgreementAssent(
                    agreement_record_id=agreement_record_id,
                    principal=prepared.principal,
                    verification_method=prepared.verification_method,
                    proof=proof,
                )
                observation = self._build_formation_evidence(
                    verified,
                    public_key,
                )
            except Exception:
                _fail(
                    "AGREEMENT_ASSENT_FORMATION_EVIDENCE_BUILD_FAILED",
                    "reverified Agreement assent could not become formation evidence",
                )
            if observation is None:
                _fail(
                    "AGREEMENT_ASSENT_FORMATION_EVIDENCE_BUILD_FAILED",
                    "reverified Agreement assent could not become formation evidence",
                )
            evidence.append(observation)

        try:
            result = self._formation.evaluate(
                agreement=candidate.record,
                evidence=tuple(evidence),
            )
        except Exception:
            _fail(
                "AGREEMENT_ASSENT_FORMATION_EVALUATION_FAILED",
                "Agreement formation evidence could not be evaluated",
            )
        if (
            type(result) is not AgreementFormationEvaluationResult
            or result.agreement_record_id != agreement_record_id
        ):
            _fail(
                "AGREEMENT_ASSENT_FORMATION_RESULT_INVALID",
                "Agreement formation evaluator returned an invalid result",
            )
        return result


__all__ = [
    "AgreementAssentFormationError",
    "AgreementRecordIdentity",
    "FormationEvidenceBuilder",
    "MarketplaceAgreementAssentFormationService",
    "PreparedAgreementAssentReverifier",
]
