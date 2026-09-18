"""Protected application-state publication of one preflight-approved Agreement."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from .agreement_candidate import AgreementCandidateBuildResult
from .agreement_publication import AgreementPublicationPreflightResult
from .postgres_state import ApplicationStatePutResult, StoreDisposition
from .state import MarketplaceApplicationStateService


RecordIdentityExtractor = Callable[[Any], str]


class AgreementPublicationWriteError(RuntimeError):
    """Stable fail-closed Agreement publication write failure."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def _fail(code: str, message: str) -> None:
    raise AgreementPublicationWriteError(code, message) from None


def _record_id(value: object) -> str:
    if type(value) is not str or not value or len(value) > 512:
        raise ValueError("record_id is invalid")
    if any(ord(char) < 33 or ord(char) > 126 or char in "/?#" for char in value):
        raise ValueError("record_id is invalid")
    return value


@dataclass(frozen=True, slots=True)
class AgreementPublicationResult:
    record_id: str
    disposition: StoreDisposition
    change_seq: int | None

    def __post_init__(self) -> None:
        _record_id(self.record_id)
        if type(self.disposition) is not StoreDisposition:
            raise TypeError("disposition MUST be exact StoreDisposition")
        if self.change_seq is not None and (
            type(self.change_seq) is not int or self.change_seq < 1
        ):
            raise ValueError("change_seq MUST be a positive exact integer when present")

    def to_document(self) -> dict[str, object]:
        return {
            "record_id": self.record_id,
            "disposition": self.disposition.value,
            "change_seq": self.change_seq,
        }


class MarketplaceAgreementPublicationService:
    """Publish one exact Agreement only after a canonical positive preflight."""

    def __init__(
        self,
        *,
        state: MarketplaceApplicationStateService,
        record_identity: RecordIdentityExtractor,
    ) -> None:
        if type(state) is not MarketplaceApplicationStateService:
            raise TypeError("state MUST be exact MarketplaceApplicationStateService")
        if not callable(record_identity):
            raise TypeError("record_identity MUST be callable")
        self._state = state
        self._record_identity = record_identity

    def publish(
        self,
        *,
        candidate: AgreementCandidateBuildResult,
        preflight: AgreementPublicationPreflightResult,
    ) -> AgreementPublicationResult:
        if type(candidate) is not AgreementCandidateBuildResult:
            _fail("AGREEMENT_PUBLICATION_CANDIDATE_INVALID", "Agreement candidate is invalid")
        if type(preflight) is not AgreementPublicationPreflightResult:
            _fail("AGREEMENT_PUBLICATION_PREFLIGHT_INVALID", "publication preflight is invalid")

        try:
            candidate_id = _record_id(candidate.record_id)
            derived_id = _record_id(self._record_identity(candidate.record))
        except Exception:
            _fail("AGREEMENT_PUBLICATION_IDENTITY_FAILED", "Agreement identity could not be verified")
        if derived_id != candidate_id:
            _fail("AGREEMENT_PUBLICATION_IDENTITY_MISMATCH", "Agreement candidate identity changed")
        if preflight.agreement_record_id != candidate_id:
            _fail("AGREEMENT_PUBLICATION_BINDING_MISMATCH", "publication preflight targets another Agreement")

        required = preflight.required_principals
        if (
            not preflight.preconditions_satisfied
            or preflight.reason != "PRECONDITIONS_SATISFIED"
            or preflight.formation_evidence != "EVIDENCE_SUFFICIENT_FOR_PROFILE"
            or preflight.actor_principal not in required
            or preflight.publishes_agreement is not False
            or preflight.authorizes_side_effects is not False
        ):
            _fail(
                "AGREEMENT_PUBLICATION_PREFLIGHT_NOT_SATISFIED",
                "Agreement publication preconditions are not satisfied",
            )

        try:
            put = self._state.publish(candidate.record)
        except Exception:
            _fail("AGREEMENT_PUBLICATION_WRITE_FAILED", "Agreement could not be published")
        if type(put) is not ApplicationStatePutResult:
            _fail("AGREEMENT_PUBLICATION_WRITE_FAILED", "Agreement publication returned an invalid result")

        try:
            return AgreementPublicationResult(
                record_id=candidate_id,
                disposition=put.disposition,
                change_seq=put.change_seq,
            )
        except Exception:
            _fail("AGREEMENT_PUBLICATION_WRITE_FAILED", "Agreement publication returned an invalid result")


__all__ = [
    "AgreementPublicationResult",
    "AgreementPublicationWriteError",
    "MarketplaceAgreementPublicationService",
    "RecordIdentityExtractor",
]
