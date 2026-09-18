"""Transport-neutral application seam for Agreement assent proof preparation."""
from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any, Callable, Final

from .agreement_candidate import AgreementCandidateBuildResult
from .auth_verification_method_snapshot import (
    MarketplaceAuthenticationVerificationMethodSnapshot,
)


MAX_AGREEMENT_ASSENT_SIGNING_INPUT_BYTES: Final = 4096
ED25519_SIGNATURE_BYTES: Final = 64
_URI_MAX_BYTES: Final = 2048
_URI_RE = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:[^\s]+$")

AgreementRecordIdentity = Callable[[Any], str]
AgreementAssentSigningInputBuilder = Callable[[Any, str], bytes]
AgreementAssentEvidenceBuilder = Callable[[Any, str, str, bytes, bytes], Any]


class AgreementAssentError(RuntimeError):
    """Stable non-reflective failure for Agreement assent preparation/verification."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def _fail(code: str, message: str) -> None:
    raise AgreementAssentError(code, message) from None


def _record_id(value: object) -> str:
    if type(value) is not str or not value or len(value) > 512:
        raise ValueError("Agreement identity is invalid")
    if any(ord(char) < 33 or ord(char) > 126 or char in "/?#" for char in value):
        raise ValueError("Agreement identity is invalid")
    return value


def _uri(value: object) -> str:
    if type(value) is not str or not value:
        raise ValueError("URI is invalid")
    try:
        raw = value.encode("utf-8", "strict")
    except UnicodeEncodeError:
        raise ValueError("URI is invalid") from None
    if len(raw) > _URI_MAX_BYTES or _URI_RE.fullmatch(value) is None:
        raise ValueError("URI is invalid")
    return value


def _time(value: object) -> int:
    if type(value) is not int or isinstance(value, bool) or value < 0:
        raise ValueError("evaluation time is invalid")
    return value


@dataclass(frozen=True, slots=True)
class AgreementAssentSigningPreparation:
    agreement_record_id: str
    principal: str
    verification_method: str
    signing_input: bytes

    def __post_init__(self) -> None:
        _record_id(self.agreement_record_id)
        _uri(self.principal)
        _uri(self.verification_method)
        if type(self.signing_input) is not bytes:
            raise TypeError("signing_input MUST be exact bytes")
        if not (1 <= len(self.signing_input) <= MAX_AGREEMENT_ASSENT_SIGNING_INPUT_BYTES):
            raise ValueError("signing_input is outside the reviewed byte bound")


@dataclass(frozen=True, slots=True)
class VerifiedAgreementAssent:
    agreement_record_id: str
    principal: str
    verification_method: str
    evidence: Any

    def __post_init__(self) -> None:
        _record_id(self.agreement_record_id)
        _uri(self.principal)
        _uri(self.verification_method)
        if self.evidence is None:
            raise ValueError("verified Agreement assent evidence MUST be present")


class MarketplaceAgreementAssentProofService:
    """Prepare and finalize one verified party assent without persistence."""

    def __init__(
        self,
        *,
        verification_methods: MarketplaceAuthenticationVerificationMethodSnapshot,
        record_identity: AgreementRecordIdentity,
        build_signing_input: AgreementAssentSigningInputBuilder,
        build_verified_evidence: AgreementAssentEvidenceBuilder,
    ) -> None:
        if type(verification_methods) is not MarketplaceAuthenticationVerificationMethodSnapshot:
            raise TypeError(
                "verification_methods MUST be exact MarketplaceAuthenticationVerificationMethodSnapshot"
            )
        if not callable(record_identity):
            raise TypeError("record_identity MUST be callable")
        if not callable(build_signing_input):
            raise TypeError("build_signing_input MUST be callable")
        if not callable(build_verified_evidence):
            raise TypeError("build_verified_evidence MUST be callable")
        self._verification_methods = verification_methods
        self._record_identity = record_identity
        self._build_signing_input = build_signing_input
        self._build_verified_evidence = build_verified_evidence

    def _candidate_identity(self, candidate: AgreementCandidateBuildResult) -> str:
        if type(candidate) is not AgreementCandidateBuildResult:
            _fail(
                "AGREEMENT_ASSENT_CANDIDATE_INVALID",
                "Agreement assent requires an exact Agreement candidate result",
            )
        try:
            derived = _record_id(self._record_identity(candidate.record))
        except Exception:
            _fail(
                "AGREEMENT_ASSENT_IDENTITY_FAILED",
                "Agreement candidate identity could not be derived",
            )
        if derived != candidate.record_id:
            _fail(
                "AGREEMENT_ASSENT_IDENTITY_MISMATCH",
                "Agreement candidate identity does not match the reviewed result",
            )
        return derived

    def prepare(
        self,
        *,
        candidate: AgreementCandidateBuildResult,
        principal: str,
        verification_method: str,
        at_time: int,
    ) -> AgreementAssentSigningPreparation:
        agreement_record_id = self._candidate_identity(candidate)
        try:
            reviewed_principal = _uri(principal)
        except ValueError:
            _fail(
                "AGREEMENT_ASSENT_PRINCIPAL_INVALID",
                "Agreement assent principal is invalid",
            )
        try:
            reviewed_method = _uri(verification_method)
        except ValueError:
            _fail(
                "AGREEMENT_ASSENT_METHOD_INVALID",
                "Agreement assent verification method is invalid",
            )
        try:
            reviewed_time = _time(at_time)
        except ValueError:
            _fail(
                "AGREEMENT_ASSENT_PREPARATION_INVALID",
                "Agreement assent preparation is invalid",
            )

        try:
            bound = self._verification_methods.verify(
                principal=reviewed_principal,
                verification_method=reviewed_method,
                at_time=reviewed_time,
            )
        except Exception:
            _fail(
                "AGREEMENT_ASSENT_METHOD_UNAVAILABLE",
                "Agreement assent verification-method evidence is unavailable",
            )
        if bound is not True:
            _fail(
                "AGREEMENT_ASSENT_PRINCIPAL_MISMATCH",
                "Agreement assent principal is not bound to the verification method",
            )

        try:
            signing_input = self._build_signing_input(candidate.record, reviewed_method)
        except Exception:
            _fail(
                "AGREEMENT_ASSENT_PREPARATION_INVALID",
                "Agreement assent signing input could not be prepared",
            )
        if (
            type(signing_input) is not bytes
            or not (1 <= len(signing_input) <= MAX_AGREEMENT_ASSENT_SIGNING_INPUT_BYTES)
        ):
            _fail(
                "AGREEMENT_ASSENT_PREPARATION_INVALID",
                "Agreement assent signing input is invalid",
            )
        try:
            return AgreementAssentSigningPreparation(
                agreement_record_id=agreement_record_id,
                principal=reviewed_principal,
                verification_method=reviewed_method,
                signing_input=signing_input,
            )
        except Exception:
            _fail(
                "AGREEMENT_ASSENT_PREPARATION_INVALID",
                "Agreement assent preparation is invalid",
            )

    def finalize(
        self,
        *,
        candidate: AgreementCandidateBuildResult,
        preparation: AgreementAssentSigningPreparation,
        signature: bytes,
        at_time: int,
    ) -> VerifiedAgreementAssent:
        if type(preparation) is not AgreementAssentSigningPreparation:
            _fail(
                "AGREEMENT_ASSENT_PREPARATION_INVALID",
                "Agreement assent preparation is invalid",
            )
        if type(signature) is not bytes or len(signature) != ED25519_SIGNATURE_BYTES:
            _fail(
                "AGREEMENT_ASSENT_SIGNATURE_INVALID",
                "Agreement assent signature is invalid",
            )

        current = self.prepare(
            candidate=candidate,
            principal=preparation.principal,
            verification_method=preparation.verification_method,
            at_time=at_time,
        )
        if current != preparation:
            _fail(
                "AGREEMENT_ASSENT_PREPARATION_INVALID",
                "Agreement assent preparation no longer matches the reviewed candidate",
            )

        try:
            public_key = self._verification_methods.verification_key_bytes(
                current.verification_method
            )
        except Exception:
            _fail(
                "AGREEMENT_ASSENT_METHOD_UNAVAILABLE",
                "Agreement assent verification-method evidence is unavailable",
            )
        if type(public_key) is not bytes or len(public_key) != 32:
            _fail(
                "AGREEMENT_ASSENT_METHOD_UNAVAILABLE",
                "Agreement assent verification-method evidence is unavailable",
            )

        try:
            evidence = self._build_verified_evidence(
                candidate.record,
                current.principal,
                current.verification_method,
                public_key,
                signature,
            )
        except Exception:
            _fail(
                "AGREEMENT_ASSENT_VERIFICATION_FAILED",
                "Agreement assent proof verification failed",
            )
        if evidence is None:
            _fail(
                "AGREEMENT_ASSENT_PROOF_INVALID",
                "Agreement assent proof is invalid",
            )
        try:
            return VerifiedAgreementAssent(
                agreement_record_id=current.agreement_record_id,
                principal=current.principal,
                verification_method=current.verification_method,
                evidence=evidence,
            )
        except Exception:
            _fail(
                "AGREEMENT_ASSENT_PROOF_INVALID",
                "Agreement assent proof is invalid",
            )


__all__ = [
    "AgreementAssentError",
    "AgreementAssentEvidenceBuilder",
    "AgreementAssentSigningInputBuilder",
    "AgreementAssentSigningPreparation",
    "AgreementRecordIdentity",
    "ED25519_SIGNATURE_BYTES",
    "MAX_AGREEMENT_ASSENT_SIGNING_INPUT_BYTES",
    "MarketplaceAgreementAssentProofService",
    "VerifiedAgreementAssent",
]
