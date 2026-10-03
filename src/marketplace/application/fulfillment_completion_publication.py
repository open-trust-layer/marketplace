"""M17.7B unselected application publication of reviewed fulfillment evidence."""
from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any, Callable, Final

from .postgres_state import ApplicationStatePutResult, StoreDisposition
from .state import MarketplaceApplicationStateService


PROFILE_NAME: Final = "MARKETPLACE_APPLICATION_FULFILLMENT_COMPLETION_PUBLICATION_V1"

CLAIMED_COMPLETE_PERFORMANCE: Final = "CLAIMED_COMPLETE_PERFORMANCE"
COMMITMENT_ACCEPTANCE: Final = "COMMITMENT_ACCEPTANCE"
COMMITMENT_COMPLETION: Final = "COMMITMENT_COMPLETION"

_EVIDENCE_KINDS = frozenset(
    {
        CLAIMED_COMPLETE_PERFORMANCE,
        COMMITMENT_ACCEPTANCE,
        COMMITMENT_COMPLETION,
    }
)
_MAX_RECORD_ID_CHARS: Final = 512
_MAX_URI_BYTES: Final = 2048
_LOCAL_ID_RE = re.compile(r"^[A-Za-z][A-Za-z0-9._-]{0,63}$")
_URI_RE = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:[^\s]+$")
_ERROR_MESSAGE: Final = "Marketplace fulfillment completion publication failed"

FulfillmentEvidenceBuilder = Callable[..., Any]
FulfillmentEvidenceTargetExtractor = Callable[[Any], tuple[str, str]]
RecordIdentityExtractor = Callable[[Any], str]


class FulfillmentCompletionPublicationError(RuntimeError):
    """Stable non-reflective M17.7B publication failure."""

    def __init__(self, code: str) -> None:
        super().__init__(_ERROR_MESSAGE)
        self.code = code


def _fail(code: str) -> None:
    raise FulfillmentCompletionPublicationError(code) from None


def _record_id(value: object) -> str:
    if type(value) is not str or not value or len(value) > _MAX_RECORD_ID_CHARS:
        raise ValueError("record identity is invalid")
    if any(ord(char) < 33 or ord(char) > 126 or char in "/?#" for char in value):
        raise ValueError("record identity is invalid")
    return value


def _commitment_id(value: object) -> str:
    if type(value) is not str or _LOCAL_ID_RE.fullmatch(value) is None:
        raise ValueError("commitment id is invalid")
    return value


def _principal(value: object) -> str:
    if type(value) is not str or not value:
        raise ValueError("issuer principal is invalid")
    try:
        encoded = value.encode("utf-8", "strict")
    except UnicodeEncodeError as exc:
        raise ValueError("issuer principal is invalid") from exc
    if len(encoded) > _MAX_URI_BYTES or _URI_RE.fullmatch(value) is None:
        raise ValueError("issuer principal is invalid")
    return value


@dataclass(frozen=True, slots=True)
class FulfillmentEvidencePublicationResult:
    record_id: str
    agreement_record_id: str
    commitment_id: str
    evidence_kind: str
    disposition: StoreDisposition
    change_seq: int | None

    def __post_init__(self) -> None:
        _record_id(self.record_id)
        _record_id(self.agreement_record_id)
        _commitment_id(self.commitment_id)
        if self.evidence_kind not in _EVIDENCE_KINDS:
            raise ValueError("evidence_kind is outside the reviewed M17.7B set")
        if type(self.disposition) is not StoreDisposition:
            raise TypeError("disposition MUST be exact StoreDisposition")
        if self.change_seq is not None and (
            type(self.change_seq) is not int or self.change_seq < 1
        ):
            raise ValueError("change_seq MUST be a positive exact integer when present")

    def to_document(self) -> dict[str, object]:
        return {
            "agreement_record_id": self.agreement_record_id,
            "change_seq": self.change_seq,
            "commitment_id": self.commitment_id,
            "disposition": self.disposition.value,
            "evidence_kind": self.evidence_kind,
            "record_id": self.record_id,
        }


class MarketplaceFulfillmentCompletionPublicationService:
    """Resolve, build, re-bind, identify, and publish one immutable evidence event."""

    def __init__(
        self,
        *,
        state: MarketplaceApplicationStateService,
        build_claimed_complete_performance: FulfillmentEvidenceBuilder,
        build_commitment_acceptance: FulfillmentEvidenceBuilder,
        build_commitment_completion: FulfillmentEvidenceBuilder,
        event_target: FulfillmentEvidenceTargetExtractor,
        record_identity: RecordIdentityExtractor,
    ) -> None:
        if type(state) is not MarketplaceApplicationStateService:
            raise TypeError("state MUST be exact MarketplaceApplicationStateService")
        for name, value in (
            ("build_claimed_complete_performance", build_claimed_complete_performance),
            ("build_commitment_acceptance", build_commitment_acceptance),
            ("build_commitment_completion", build_commitment_completion),
            ("event_target", event_target),
            ("record_identity", record_identity),
        ):
            if not callable(value):
                raise TypeError(f"{name} MUST be callable")
        self._state = state
        self._build_claimed_complete_performance = build_claimed_complete_performance
        self._build_commitment_acceptance = build_commitment_acceptance
        self._build_commitment_completion = build_commitment_completion
        self._event_target = event_target
        self._record_identity = record_identity

    def _publish(
        self,
        *,
        agreement_record_id: str,
        commitment_id: str,
        issuer: str,
        evidence_kind: str,
        builder: FulfillmentEvidenceBuilder,
    ) -> FulfillmentEvidencePublicationResult:
        try:
            agreement_id = _record_id(agreement_record_id)
            reviewed_commitment_id = _commitment_id(commitment_id)
            reviewed_issuer = _principal(issuer)
        except ValueError:
            _fail("FULFILLMENT_PUBLICATION_REQUEST_INVALID")

        try:
            agreement = self._state.peek(agreement_id)
        except Exception:
            _fail("FULFILLMENT_PUBLICATION_AGREEMENT_UNAVAILABLE")
        if agreement is None:
            _fail("FULFILLMENT_PUBLICATION_AGREEMENT_NOT_FOUND")

        try:
            event = builder(
                agreement=agreement,
                commitment_id=reviewed_commitment_id,
                issuer=reviewed_issuer,
            )
        except Exception:
            _fail("FULFILLMENT_PUBLICATION_BUILD_FAILED")

        try:
            target = self._event_target(event)
        except Exception:
            _fail("FULFILLMENT_PUBLICATION_BINDING_INVALID")
        if (
            type(target) is not tuple
            or len(target) != 2
            or type(target[0]) is not str
            or type(target[1]) is not str
        ):
            _fail("FULFILLMENT_PUBLICATION_BINDING_INVALID")
        try:
            target_agreement_id = _record_id(target[0])
            target_commitment_id = _commitment_id(target[1])
        except ValueError:
            _fail("FULFILLMENT_PUBLICATION_BINDING_INVALID")
        if (
            target_agreement_id != agreement_id
            or target_commitment_id != reviewed_commitment_id
        ):
            _fail("FULFILLMENT_PUBLICATION_BINDING_MISMATCH")

        try:
            event_id = _record_id(self._record_identity(event))
        except Exception:
            _fail("FULFILLMENT_PUBLICATION_IDENTITY_FAILED")

        try:
            put = self._state.publish(event)
        except Exception:
            _fail("FULFILLMENT_PUBLICATION_WRITE_FAILED")
        if type(put) is not ApplicationStatePutResult:
            _fail("FULFILLMENT_PUBLICATION_WRITE_FAILED")

        try:
            return FulfillmentEvidencePublicationResult(
                record_id=event_id,
                agreement_record_id=agreement_id,
                commitment_id=reviewed_commitment_id,
                evidence_kind=evidence_kind,
                disposition=put.disposition,
                change_seq=put.change_seq,
            )
        except Exception:
            _fail("FULFILLMENT_PUBLICATION_WRITE_FAILED")

    def publish_claimed_complete_performance(
        self,
        *,
        agreement_record_id: str,
        commitment_id: str,
        issuer: str,
    ) -> FulfillmentEvidencePublicationResult:
        return self._publish(
            agreement_record_id=agreement_record_id,
            commitment_id=commitment_id,
            issuer=issuer,
            evidence_kind=CLAIMED_COMPLETE_PERFORMANCE,
            builder=self._build_claimed_complete_performance,
        )

    def publish_commitment_acceptance(
        self,
        *,
        agreement_record_id: str,
        commitment_id: str,
        issuer: str,
    ) -> FulfillmentEvidencePublicationResult:
        return self._publish(
            agreement_record_id=agreement_record_id,
            commitment_id=commitment_id,
            issuer=issuer,
            evidence_kind=COMMITMENT_ACCEPTANCE,
            builder=self._build_commitment_acceptance,
        )

    def publish_commitment_completion(
        self,
        *,
        agreement_record_id: str,
        commitment_id: str,
        issuer: str,
    ) -> FulfillmentEvidencePublicationResult:
        return self._publish(
            agreement_record_id=agreement_record_id,
            commitment_id=commitment_id,
            issuer=issuer,
            evidence_kind=COMMITMENT_COMPLETION,
            builder=self._build_commitment_completion,
        )


__all__ = [
    "CLAIMED_COMPLETE_PERFORMANCE",
    "COMMITMENT_ACCEPTANCE",
    "COMMITMENT_COMPLETION",
    "FulfillmentCompletionPublicationError",
    "FulfillmentEvidenceBuilder",
    "FulfillmentEvidencePublicationResult",
    "FulfillmentEvidenceTargetExtractor",
    "MarketplaceFulfillmentCompletionPublicationService",
    "PROFILE_NAME",
    "RecordIdentityExtractor",
]
