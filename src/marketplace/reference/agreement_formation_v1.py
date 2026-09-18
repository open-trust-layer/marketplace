"""Reference evaluation of detached assent evidence for product Agreements.

This module verifies evidence for the Marketplace agreement-formation profile.
It does not create proofs, publish records, or evaluate legal enforceability.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from olp import RecordV1, verify_proof
from olp.encoding.record_identity import record_identity_text
from olp.model.proof import OLPProof
from olp.model.verification import ResolvedVerificationMethod, Status

from .agreement_candidate_v1 import AGREEMENT_FORMATION_PROFILE
from .record_v1 import TYPE_AGREEMENT, validate_market_record


MAX_ASSENT_EVIDENCE = 16


class AgreementFormationProfileError(ValueError):
    """Stable product Agreement-formation evaluation failure."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def _fail(code: str, message: str) -> None:
    raise AgreementFormationProfileError(code, message) from None


def _principal(value: object) -> str:
    if type(value) is not str or not value or len(value) > 512:
        raise ValueError("principal MUST be bounded non-empty exact text")
    if any(ord(char) < 33 or ord(char) > 126 for char in value):
        raise ValueError("principal MUST contain visible ASCII only")
    return value


@dataclass(frozen=True, slots=True)
class AssentEvidence:
    """One detached proof observation attributed to one asserted principal."""

    principal: str
    proof: OLPProof
    resolved_method: ResolvedVerificationMethod | None
    attribution_accepted: bool

    def __post_init__(self) -> None:
        _principal(self.principal)
        if type(self.proof) is not OLPProof:
            raise TypeError("proof MUST be exact OLPProof")
        if self.resolved_method is not None and type(self.resolved_method) is not ResolvedVerificationMethod:
            raise TypeError("resolved_method MUST be exact ResolvedVerificationMethod or None")
        if type(self.attribution_accepted) is not bool:
            raise TypeError("attribution_accepted MUST be exact bool")


def _proof_satisfies_assent(
    agreement: RecordV1,
    evidence: AssentEvidence,
    *,
    evaluation_time: datetime | None,
) -> tuple[bool, dict[str, str]]:
    result = verify_proof(
        agreement,
        evidence.proof,
        resolved_method=evidence.resolved_method,
        expected_purpose="assertion",
        evaluation_time=evaluation_time,
    )
    dimensions = {
        "record_binding": str(result.record_binding),
        "version_support": str(result.version_support),
        "cryptosuite_support": str(result.cryptosuite_support),
        "commitment_algorithm_support": str(result.commitment_algorithm_support),
        "critical_extension_status": str(result.critical_extension_status),
        "cryptographic_validity": str(result.cryptographic_validity),
        "purpose_status": str(result.purpose_status),
        "verification_method_resolution": str(result.verification_method_resolution),
        "verification_method_compatibility": str(result.verification_method_compatibility),
        "temporal_status": str(result.temporal_status),
        "attribution": "ACCEPTED" if evidence.attribution_accepted else "NOT_ACCEPTED",
    }
    accepted = (
        result.conformance == Status.CONFORMING
        and result.version_support == Status.SUPPORTED
        and result.cryptosuite_support == Status.SUPPORTED
        and result.commitment_algorithm_support == Status.SUPPORTED
        and result.critical_extension_status == Status.UNDERSTOOD
        and result.record_binding == Status.VALID
        and result.cryptographic_validity == Status.VALID
        and result.purpose_status == Status.MATCH
        and result.verification_method_resolution == Status.RESOLVED
        and result.verification_method_compatibility == Status.COMPATIBLE
        and evidence.attribution_accepted
    )
    return accepted, dimensions


def evaluate_product_agreement_formation(
    agreement: object,
    evidence: tuple[AssentEvidence, ...],
    *,
    evaluation_time: datetime | None = None,
) -> dict[str, Any]:
    """Evaluate bounded detached assent evidence without publishing the Agreement."""
    if type(agreement) is not RecordV1:
        _fail("AGREEMENT_REQUIRED", "formation evaluation requires exact RecordV1")
    try:
        validate_market_record(agreement)
    except Exception:
        _fail("AGREEMENT_INVALID", "formation evaluation requires a valid Marketplace record")
    if agreement.type != TYPE_AGREEMENT:
        _fail("AGREEMENT_REQUIRED", "formation evaluation requires MarketAgreement")
    if AGREEMENT_FORMATION_PROFILE not in agreement.profiles:
        _fail("FORMATION_PROFILE_REQUIRED", "MarketAgreement MUST declare agreement-formation-v1")
    if type(evidence) is not tuple:
        _fail("ASSENT_EVIDENCE_INVALID", "assent evidence MUST be an exact tuple")
    if len(evidence) > MAX_ASSENT_EVIDENCE:
        _fail("ASSENT_EVIDENCE_LIMIT_EXCEEDED", "too many assent evidence observations")
    if evaluation_time is not None and type(evaluation_time) is not datetime:
        _fail("EVALUATION_TIME_INVALID", "evaluation_time MUST be exact datetime or None")

    required = tuple(
        sorted(
            {_principal(party["principal"]) for party in agreement.content["parties"]},
            key=lambda value: value.encode("utf-8"),
        )
    )
    covered: set[str] = set()
    extraneous: set[str] = set()
    observations: list[dict[str, Any]] = []

    for item in evidence:
        if type(item) is not AssentEvidence:
            _fail("ASSENT_EVIDENCE_INVALID", "every observation MUST be exact AssentEvidence")
        if item.principal not in required:
            extraneous.add(item.principal)
        try:
            accepted, dimensions = _proof_satisfies_assent(
                agreement,
                item,
                evaluation_time=evaluation_time,
            )
        except Exception:
            accepted = False
            dimensions = {
                "verification": "REJECTED",
                "attribution": "ACCEPTED" if item.attribution_accepted else "NOT_ACCEPTED",
            }
        if accepted and item.principal in required:
            covered.add(item.principal)
        observations.append(
            {
                "principal": item.principal,
                "verification_method": item.proof.verificationMethod,
                "accepted_for_coverage": accepted and item.principal in required,
                "dimensions": dimensions,
            }
        )

    missing = tuple(principal for principal in required if principal not in covered)
    return {
        "profile": AGREEMENT_FORMATION_PROFILE,
        "agreement": record_identity_text(agreement),
        "required_principals": list(required),
        "covered_principals": sorted(covered, key=lambda value: value.encode("utf-8")),
        "missing_principals": list(missing),
        "extraneous_principals": sorted(extraneous, key=lambda value: value.encode("utf-8")),
        "observations": observations,
        "formation_evidence": (
            "EVIDENCE_SUFFICIENT_FOR_PROFILE" if not missing else "EVIDENCE_INCOMPLETE"
        ),
        "legal_enforceability": "NOT_EVALUATED",
        "universal_truth": False,
        "publishes_agreement": False,
        "authorizes_side_effects": False,
    }


__all__ = [
    "AgreementFormationProfileError",
    "AssentEvidence",
    "MAX_ASSENT_EVIDENCE",
    "evaluate_product_agreement_formation",
]
