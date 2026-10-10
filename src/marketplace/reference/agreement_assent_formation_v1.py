"""Reference re-verification bridge from retained assent to formation evidence."""
from __future__ import annotations

from olp import verify_proof
from olp.model.verification import (
    ResolutionProvenance,
    ResolvedVerificationMethod,
    Status,
)

from ..application.agreement_assent import VerifiedAgreementAssent
from ..application.agreement_assent_coordination import PreparedAgreementAssent
from .agreement_assent_coordination_v1 import (
    decode_prepared_product_agreement_assent_proof,
)
from .agreement_assent_v1 import (
    AGREEMENT_ASSENT_PROOF_PURPOSE,
    VerifiedAgreementAssentProof,
)
from .agreement_candidate_v1 import agreement_candidate_record_id
from .agreement_formation_v1 import AssentEvidence


class AgreementAssentFormationProfileError(ValueError):
    """Stable reference failure for retained-assent formation projection."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def _fail(code: str, message: str) -> None:
    raise AgreementAssentFormationProfileError(code, message) from None


def reverify_prepared_product_agreement_assent(
    agreement: object,
    prepared: PreparedAgreementAssent,
    public_key: bytes,
) -> VerifiedAgreementAssentProof:
    """Reverify stored public proof bytes against the exact current Agreement."""
    if type(prepared) is not PreparedAgreementAssent:
        _fail(
            "AGREEMENT_ASSENT_PREPARED_EVIDENCE_INVALID",
            "retained Agreement assent evidence is invalid",
        )
    if type(public_key) is not bytes or len(public_key) != 32:
        _fail(
            "AGREEMENT_ASSENT_METHOD_INVALID",
            "Agreement assent verification material is invalid",
        )
    try:
        agreement_record_id = agreement_candidate_record_id(agreement)
    except Exception:
        _fail(
            "AGREEMENT_ASSENT_CANDIDATE_INVALID",
            "Agreement assent formation requires a valid Agreement candidate",
        )
    if agreement_record_id != prepared.agreement_record_id:
        _fail(
            "AGREEMENT_ASSENT_BINDING_MISMATCH",
            "retained Agreement assent targets another Agreement",
        )

    try:
        proof = decode_prepared_product_agreement_assent_proof(prepared)
        resolved = ResolvedVerificationMethod(
            prepared.verification_method,
            "Ed25519",
            public_key,
            ResolutionProvenance.LOCAL_STORE,
        )
        result = verify_proof(
            agreement,
            proof,
            resolved_method=resolved,
            expected_purpose=AGREEMENT_ASSENT_PROOF_PURPOSE,
        )
    except AgreementAssentFormationProfileError:
        raise
    except Exception:
        _fail(
            "AGREEMENT_ASSENT_PROOF_INVALID",
            "retained Agreement assent proof could not be verified",
        )

    accepted = (
        result.conformance == Status.CONFORMING
        and result.record_binding == Status.VALID
        and result.version_support == Status.SUPPORTED
        and result.cryptosuite_support == Status.SUPPORTED
        and result.commitment_algorithm_support == Status.SUPPORTED
        and result.critical_extension_status == Status.UNDERSTOOD
        and result.verification_method_resolution == Status.RESOLVED
        and result.verification_method_compatibility == Status.COMPATIBLE
        and result.cryptographic_validity == Status.VALID
        and result.purpose_status == Status.MATCH
    )
    if not accepted:
        _fail(
            "AGREEMENT_ASSENT_PROOF_INVALID",
            "retained Agreement assent proof failed current verification",
        )
    return VerifiedAgreementAssentProof(
        proof=proof,
        resolved_method=resolved,
    )


def build_product_agreement_formation_evidence_from_verified_assent(
    verified: VerifiedAgreementAssent,
    expected_public_key: bytes,
) -> AssentEvidence:
    """Project an application-trusted verified assent into #360 evidence."""
    if type(verified) is not VerifiedAgreementAssent:
        _fail(
            "AGREEMENT_ASSENT_VERIFIED_RESULT_INVALID",
            "formation evidence requires an exact verified Agreement assent",
        )
    if type(expected_public_key) is not bytes or len(expected_public_key) != 32:
        _fail(
            "AGREEMENT_ASSENT_METHOD_INVALID",
            "Agreement assent verification material is invalid",
        )
    if type(verified.proof) is not VerifiedAgreementAssentProof:
        _fail(
            "AGREEMENT_ASSENT_VERIFIED_RESULT_INVALID",
            "formation evidence requires exact verified proof evidence",
        )

    proof = verified.proof.proof
    resolved = verified.proof.resolved_method
    if (
        proof.verificationMethod != verified.verification_method
        or resolved.identifier != verified.verification_method
        or resolved.key_type != "Ed25519"
        or resolved.public_key != expected_public_key
        or resolved.provenance != ResolutionProvenance.LOCAL_STORE
    ):
        _fail(
            "AGREEMENT_ASSENT_VERIFIED_RESULT_MISMATCH",
            "verified Agreement assent does not match current trusted method evidence",
        )

    try:
        return AssentEvidence(
            principal=verified.principal,
            proof=proof,
            resolved_method=resolved,
            attribution_accepted=True,
        )
    except Exception:
        _fail(
            "AGREEMENT_ASSENT_FORMATION_EVIDENCE_INVALID",
            "verified Agreement assent could not become formation evidence",
        )


__all__ = [
    "AgreementAssentFormationProfileError",
    "build_product_agreement_formation_evidence_from_verified_assent",
    "reverify_prepared_product_agreement_assent",
]
