"""Reference OLP proof boundary for one product Agreement party assent."""
from __future__ import annotations

from dataclasses import dataclass

from olp import verify_proof
from olp.constants import (
    MANDATORY_CRYPTOSUITE,
    PROOF_TYPE,
    PROOF_VERSION,
    SHA256_COSE_ALGORITHM_ID,
)
from olp.crypto.commitments import record_commitment
from olp.encoding.proof_input import build_proof_input, encode_proof_input
from olp.model.proof import OLPProof
from olp.model.verification import (
    ResolutionProvenance,
    ResolvedVerificationMethod,
    Status,
)

from .agreement_candidate_v1 import agreement_candidate_record_id
AGREEMENT_ASSENT_PROOF_PURPOSE = "assertion"
ED25519_PUBLIC_KEY_BYTES = 32
ED25519_SIGNATURE_BYTES = 64


@dataclass(frozen=True, slots=True)
class VerifiedAgreementAssentProof:
    """Cryptographically verified OLP proof without application attribution."""

    proof: OLPProof
    resolved_method: ResolvedVerificationMethod

    def __post_init__(self) -> None:
        if type(self.proof) is not OLPProof:
            raise TypeError("proof MUST be exact OLPProof")
        if type(self.resolved_method) is not ResolvedVerificationMethod:
            raise TypeError("resolved_method MUST be exact ResolvedVerificationMethod")


class AgreementAssentProfileError(ValueError):
    """Stable reference-profile failure for Agreement assent proof processing."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def _fail(code: str, message: str) -> None:
    raise AgreementAssentProfileError(code, message) from None


def _candidate(record: object):
    try:
        agreement_candidate_record_id(record)
    except Exception:
        _fail(
            "AGREEMENT_ASSENT_CANDIDATE_INVALID",
            "Agreement assent requires a valid Agreement candidate",
        )
    return record


def build_product_agreement_assent_signing_input(
    agreement: object,
    verification_method: str,
) -> bytes:
    """Return exact OLP ProofInputV1 bytes for one Agreement assertion."""
    reviewed = _candidate(agreement)
    try:
        commitment = record_commitment(reviewed, SHA256_COSE_ALGORITHM_ID)
        proof_input = build_proof_input(
            cryptosuite=MANDATORY_CRYPTOSUITE,
            proof_purpose=AGREEMENT_ASSENT_PROOF_PURPOSE,
            verification_method=verification_method,
            record_commitment=commitment,
        )
        encoded = encode_proof_input(proof_input)
    except AgreementAssentProfileError:
        raise
    except Exception:
        _fail(
            "AGREEMENT_ASSENT_SIGNING_INPUT_INVALID",
            "Agreement assent signing input could not be built",
        )
    if type(encoded) is not bytes or not encoded:
        _fail(
            "AGREEMENT_ASSENT_SIGNING_INPUT_INVALID",
            "Agreement assent signing input is invalid",
        )
    return encoded


def build_verified_product_agreement_assent_proof(
    agreement: object,
    verification_method: str,
    public_key: bytes,
    signature: bytes,
) -> VerifiedAgreementAssentProof:
    """Verify one exact standard OLP proof without assigning party attribution."""
    reviewed = _candidate(agreement)
    if type(public_key) is not bytes or len(public_key) != ED25519_PUBLIC_KEY_BYTES:
        _fail(
            "AGREEMENT_ASSENT_METHOD_INVALID",
            "Agreement assent verification material is invalid",
        )
    if type(signature) is not bytes or len(signature) != ED25519_SIGNATURE_BYTES:
        _fail(
            "AGREEMENT_ASSENT_SIGNATURE_INVALID",
            "Agreement assent signature is invalid",
        )

    try:
        proof = OLPProof(
            type=PROOF_TYPE,
            version=PROOF_VERSION,
            cryptosuite=MANDATORY_CRYPTOSUITE,
            proofPurpose=AGREEMENT_ASSENT_PROOF_PURPOSE,
            verificationMethod=verification_method,
            recordCommitment=record_commitment(
                reviewed,
                SHA256_COSE_ALGORITHM_ID,
            ),
            proofValue=signature,
        )
        proof.validate_structure()
        resolved = ResolvedVerificationMethod(
            verification_method,
            "Ed25519",
            public_key,
            ResolutionProvenance.LOCAL_STORE,
        )
        result = verify_proof(
            reviewed,
            proof,
            resolved_method=resolved,
            expected_purpose=AGREEMENT_ASSENT_PROOF_PURPOSE,
        )
    except AgreementAssentProfileError:
        raise
    except Exception:
        _fail(
            "AGREEMENT_ASSENT_PROOF_INVALID",
            "Agreement assent proof could not be verified",
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
            "Agreement assent proof failed the reviewed verification profile",
        )

    try:
        return VerifiedAgreementAssentProof(
            proof=proof,
            resolved_method=resolved,
        )
    except Exception:
        _fail(
            "AGREEMENT_ASSENT_PROOF_INVALID",
            "Agreement assent proof result is invalid",
        )


__all__ = [
    "AGREEMENT_ASSENT_PROOF_PURPOSE",
    "AgreementAssentProfileError",
    "VerifiedAgreementAssentProof",
    "ED25519_PUBLIC_KEY_BYTES",
    "ED25519_SIGNATURE_BYTES",
    "build_product_agreement_assent_signing_input",
    "build_verified_product_agreement_assent_proof",
]
