"""Reference serialization for verified Agreement assent coordination evidence."""
from __future__ import annotations

from olp.constants import MANDATORY_CRYPTOSUITE, PROOF_TYPE, PROOF_VERSION
from olp.encoding.proof_identity import proof_identity
from olp.model.proof import OLPProof, RecordCommitment

from ..application.agreement_assent import VerifiedAgreementAssent
from ..application.agreement_assent_coordination import PreparedAgreementAssent
from .agreement_assent_v1 import (
    AGREEMENT_ASSENT_PROOF_PURPOSE,
    VerifiedAgreementAssentProof,
)
from .transport_json_v1 import (
    decode_transport_envelope_json,
    encode_transport_envelope_json,
)


PROOF_MESSAGE_TYPE = "proof"
_PROOF_PAYLOAD_KEYS = frozenset(
    {
        "type",
        "version",
        "cryptosuite",
        "proofPurpose",
        "verificationMethod",
        "recordCommitment",
        "proofValue",
        "critical",
        "extensions",
    }
)


class AgreementAssentCoordinationProfileError(ValueError):
    """Stable reference boundary failure for stored assent evidence."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def _fail(code: str, message: str) -> None:
    raise AgreementAssentCoordinationProfileError(code, message) from None


def _review_minimal_proof(proof: OLPProof, verification_method: str) -> None:
    if type(proof) is not OLPProof:
        _fail(
            "AGREEMENT_ASSENT_PROOF_INVALID",
            "stored Agreement assent requires an exact OLP proof",
        )
    try:
        proof.validate_structure()
    except Exception:
        _fail(
            "AGREEMENT_ASSENT_PROOF_INVALID",
            "stored Agreement assent proof is invalid",
        )
    if (
        proof.type != PROOF_TYPE
        or proof.version != PROOF_VERSION
        or proof.cryptosuite != MANDATORY_CRYPTOSUITE
        or proof.proofPurpose != AGREEMENT_ASSENT_PROOF_PURPOSE
        or proof.verificationMethod != verification_method
        or proof.created is not None
        or proof.expires is not None
        or proof.domain is not None
        or proof.challenge is not None
        or proof.nonce is not None
        or proof.critical != ()
        or dict(proof.extensions) != {}
    ):
        _fail(
            "AGREEMENT_ASSENT_PROOF_PROFILE_MISMATCH",
            "stored Agreement assent proof is outside the reviewed profile",
        )


def _payload(proof: OLPProof) -> dict[str, object]:
    return {
        "type": proof.type,
        "version": proof.version,
        "cryptosuite": proof.cryptosuite,
        "proofPurpose": proof.proofPurpose,
        "verificationMethod": proof.verificationMethod,
        "recordCommitment": proof.recordCommitment.proof_input_value(),
        "proofValue": proof.proofValue,
        "critical": (),
        "extensions": {},
    }


def build_prepared_product_agreement_assent(
    verified: VerifiedAgreementAssent,
) -> PreparedAgreementAssent:
    """Serialize one trusted application result into bounded public proof bytes."""
    if type(verified) is not VerifiedAgreementAssent:
        _fail(
            "AGREEMENT_ASSENT_VERIFIED_RESULT_INVALID",
            "Agreement assent preparation requires an exact verified result",
        )
    if type(verified.proof) is not VerifiedAgreementAssentProof:
        _fail(
            "AGREEMENT_ASSENT_VERIFIED_RESULT_INVALID",
            "Agreement assent preparation requires exact verified proof evidence",
        )
    proof = verified.proof.proof
    _review_minimal_proof(proof, verified.verification_method)
    try:
        identity = proof_identity(proof)
        body = encode_transport_envelope_json(
            ("OLP-TRANSPORT", 1, PROOF_MESSAGE_TYPE, _payload(proof))
        )
        return PreparedAgreementAssent(
            agreement_record_id=verified.agreement_record_id,
            principal=verified.principal,
            verification_method=verified.verification_method,
            proof_identity=identity,
            proof_bytes=body,
        )
    except AgreementAssentCoordinationProfileError:
        raise
    except Exception:
        _fail(
            "AGREEMENT_ASSENT_SERIALIZATION_FAILED",
            "Agreement assent proof could not be serialized safely",
        )


def decode_prepared_product_agreement_assent_proof(
    prepared: PreparedAgreementAssent,
) -> OLPProof:
    """Decode stored public proof bytes and re-check exact identity and method."""
    if type(prepared) is not PreparedAgreementAssent:
        _fail(
            "AGREEMENT_ASSENT_PREPARED_EVIDENCE_INVALID",
            "stored Agreement assent evidence is invalid",
        )
    try:
        envelope = decode_transport_envelope_json(prepared.proof_bytes)
    except Exception:
        _fail(
            "AGREEMENT_ASSENT_SERIALIZATION_INVALID",
            "stored Agreement assent proof encoding is invalid",
        )
    if (
        type(envelope) is not tuple
        or len(envelope) != 4
        or envelope[:3] != ("OLP-TRANSPORT", 1, PROOF_MESSAGE_TYPE)
        or type(envelope[3]) is not dict
        or frozenset(envelope[3]) != _PROOF_PAYLOAD_KEYS
    ):
        _fail(
            "AGREEMENT_ASSENT_SERIALIZATION_INVALID",
            "stored Agreement assent proof envelope is invalid",
        )
    payload = envelope[3]
    commitment = payload["recordCommitment"]
    if (
        type(commitment) is not tuple
        or len(commitment) != 2
        or type(commitment[0]) is not int
        or isinstance(commitment[0], bool)
        or type(commitment[1]) is not bytes
        or not commitment[1]
        or payload["critical"] != ()
        or payload["extensions"] != {}
    ):
        _fail(
            "AGREEMENT_ASSENT_SERIALIZATION_INVALID",
            "stored Agreement assent proof payload is invalid",
        )
    try:
        proof = OLPProof(
            type=payload["type"],
            version=payload["version"],
            cryptosuite=payload["cryptosuite"],
            proofPurpose=payload["proofPurpose"],
            verificationMethod=payload["verificationMethod"],
            recordCommitment=RecordCommitment(commitment[0], commitment[1]),
            proofValue=payload["proofValue"],
            critical=(),
            extensions={},
        )
        _review_minimal_proof(proof, prepared.verification_method)
        if proof_identity(proof) != prepared.proof_identity:
            _fail(
                "AGREEMENT_ASSENT_PROOF_IDENTITY_MISMATCH",
                "stored Agreement assent proof identity does not match its key",
            )
        return proof
    except AgreementAssentCoordinationProfileError:
        raise
    except Exception:
        _fail(
            "AGREEMENT_ASSENT_SERIALIZATION_INVALID",
            "stored Agreement assent proof payload is invalid",
        )


__all__ = [
    "AgreementAssentCoordinationProfileError",
    "PROOF_MESSAGE_TYPE",
    "build_prepared_product_agreement_assent",
    "decode_prepared_product_agreement_assent_proof",
]
