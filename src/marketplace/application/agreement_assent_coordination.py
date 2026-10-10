"""Bounded coordination semantics for verified Agreement assent evidence."""
from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Callable, Final, Protocol

from ..runtime.contracts import StoreDisposition
from .agreement_assent import VerifiedAgreementAssent


AGREEMENT_ASSENT_COORDINATION_RETENTION_CLASS: Final = (
    "MARKETPLACE_AGREEMENT_ASSENT_COORDINATION_MVP"
)
DEFAULT_AGREEMENT_ASSENT_RETENTION_SECONDS: Final = 30 * 24 * 60 * 60
MAX_AGREEMENT_ASSENT_RETENTION_SECONDS: Final = DEFAULT_AGREEMENT_ASSENT_RETENTION_SECONDS
MAX_AGREEMENT_ASSENT_PROOF_BYTES: Final = 16 * 1024
MAX_AGREEMENT_ASSENT_COORDINATION_ENTRIES: Final = 4096
MAX_AGREEMENT_ASSENT_EXPIRY_BATCH: Final = 256
MAX_AGREEMENT_ASSENT_PARTIES: Final = 16
AGREEMENT_ASSENT_PROOF_IDENTITY_BYTES: Final = 32
_URI_MAX_BYTES: Final = 2048
_RECORD_ID = re.compile(r"^r1_[A-Za-z0-9_-]{43}$")
_URI = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:[^\s]+$")


class AgreementAssentCoordinationError(RuntimeError):
    """Stable non-reflective coordination failure."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


class AgreementAssentCoordinationCollisionError(AgreementAssentCoordinationError):
    def __init__(self) -> None:
        super().__init__(
            "AGREEMENT_ASSENT_COLLISION",
            "Agreement assent key is already bound to different verified evidence",
        )


def _record_id(value: object) -> str:
    if type(value) is not str or _RECORD_ID.fullmatch(value) is None:
        raise ValueError("agreement_record_id MUST be canonical Record Identity text")
    return value


def _uri(value: object) -> str:
    if type(value) is not str or not value:
        raise ValueError("URI MUST be non-empty exact text")
    try:
        raw = value.encode("utf-8", "strict")
    except UnicodeEncodeError:
        raise ValueError("URI MUST be valid UTF-8") from None
    if len(raw) > _URI_MAX_BYTES or _URI.fullmatch(value) is None:
        raise ValueError("URI is outside the reviewed profile")
    return value


def _time(value: object) -> int:
    if type(value) is not int or isinstance(value, bool) or value < 0:
        raise ValueError("time MUST be a non-negative exact integer")
    return value


@dataclass(frozen=True, slots=True)
class PreparedAgreementAssent:
    """Canonical public evidence ready for coordination retention."""

    agreement_record_id: str
    principal: str
    verification_method: str
    proof_identity: bytes
    proof_bytes: bytes

    def __post_init__(self) -> None:
        _record_id(self.agreement_record_id)
        _uri(self.principal)
        _uri(self.verification_method)
        if (
            type(self.proof_identity) is not bytes
            or len(self.proof_identity) != AGREEMENT_ASSENT_PROOF_IDENTITY_BYTES
        ):
            raise ValueError("proof_identity MUST be exact 32 bytes")
        if type(self.proof_bytes) is not bytes:
            raise TypeError("proof_bytes MUST be exact bytes")
        if not (1 <= len(self.proof_bytes) <= MAX_AGREEMENT_ASSENT_PROOF_BYTES):
            raise ValueError("proof_bytes are outside the reviewed byte bound")


@dataclass(frozen=True, slots=True)
class AgreementAssentPutResult:
    disposition: StoreDisposition
    accepted_at: int
    expires_at: int

    def __post_init__(self) -> None:
        if type(self.disposition) is not StoreDisposition:
            raise TypeError("disposition MUST be exact StoreDisposition")
        start = _time(self.accepted_at)
        end = _time(self.expires_at)
        if end <= start:
            raise ValueError("expires_at MUST be later than accepted_at")


@dataclass(frozen=True, slots=True)
class AgreementAssentExpiryResult:
    expired_keys: tuple[tuple[str, str], ...]

    def __post_init__(self) -> None:
        if type(self.expired_keys) is not tuple:
            raise TypeError("expired_keys MUST be an exact tuple")
        for key in self.expired_keys:
            if type(key) is not tuple or len(key) != 2:
                raise TypeError("expired key MUST be an exact pair")
            _record_id(key[0])
            _uri(key[1])


class AgreementAssentCoordinationStore(Protocol):
    retention_class: str

    @property
    def retention_seconds(self) -> int: ...

    def initialize(self) -> AgreementAssentExpiryResult: ...
    def put(self, prepared: PreparedAgreementAssent) -> AgreementAssentPutResult: ...
    def peek(self, agreement_record_id: str, principal: str) -> PreparedAgreementAssent | None: ...
    def list_for_agreement(
        self,
        agreement_record_id: str,
        *,
        limit: int,
    ) -> tuple[PreparedAgreementAssent, ...]: ...
    def expire_due(self) -> AgreementAssentExpiryResult: ...


Clock = Callable[[], int]
AgreementAssentPreparer = Callable[[VerifiedAgreementAssent], PreparedAgreementAssent]


@dataclass(frozen=True, slots=True)
class _StoredAgreementAssent:
    prepared: PreparedAgreementAssent
    accepted_at: int
    expires_at: int


class MemoryAgreementAssentCoordinationStore:
    """Deterministic reference store for coordination semantics, not durability."""

    retention_class = AGREEMENT_ASSENT_COORDINATION_RETENTION_CLASS

    def __init__(
        self,
        *,
        clock: Clock,
        retention_seconds: int = DEFAULT_AGREEMENT_ASSENT_RETENTION_SECONDS,
        max_entries: int = MAX_AGREEMENT_ASSENT_COORDINATION_ENTRIES,
    ) -> None:
        if not callable(clock):
            raise TypeError("clock MUST be callable")
        if (
            type(retention_seconds) is not int
            or isinstance(retention_seconds, bool)
            or not 1 <= retention_seconds <= MAX_AGREEMENT_ASSENT_RETENTION_SECONDS
        ):
            raise ValueError("retention_seconds MUST be an exact integer within 30 days")
        if (
            type(max_entries) is not int
            or isinstance(max_entries, bool)
            or not 1 <= max_entries <= MAX_AGREEMENT_ASSENT_COORDINATION_ENTRIES
        ):
            raise ValueError("max_entries is outside the reviewed coordination bound")
        self._clock = clock
        self._retention_seconds = retention_seconds
        self._max_entries = max_entries
        self._entries: dict[tuple[str, str], _StoredAgreementAssent] = {}

    @property
    def retention_seconds(self) -> int:
        return self._retention_seconds

    def _now(self) -> int:
        try:
            return _time(self._clock())
        except Exception:
            raise AgreementAssentCoordinationError(
                "AGREEMENT_ASSENT_CLOCK_INVALID",
                "Agreement assent coordination clock is invalid",
            ) from None

    def _expire_due_at(self, now: int) -> AgreementAssentExpiryResult:
        due = tuple(
            key
            for key, stored in sorted(self._entries.items())
            if stored.expires_at <= now
        )[:MAX_AGREEMENT_ASSENT_EXPIRY_BATCH]
        for key in due:
            del self._entries[key]
        return AgreementAssentExpiryResult(due)

    def initialize(self) -> AgreementAssentExpiryResult:
        return self._expire_due_at(self._now())

    def put(self, prepared: PreparedAgreementAssent) -> AgreementAssentPutResult:
        if type(prepared) is not PreparedAgreementAssent:
            raise TypeError("prepared MUST be exact PreparedAgreementAssent")
        now = self._now()
        self._expire_due_at(now)
        key = (prepared.agreement_record_id, prepared.principal)
        existing = self._entries.get(key)
        if existing is not None:
            if existing.prepared == prepared:
                return AgreementAssentPutResult(
                    StoreDisposition.DUPLICATE,
                    existing.accepted_at,
                    existing.expires_at,
                )
            raise AgreementAssentCoordinationCollisionError()
        if len(self._entries) >= self._max_entries:
            raise AgreementAssentCoordinationError(
                "AGREEMENT_ASSENT_COORDINATION_CAPACITY_EXCEEDED",
                "Agreement assent coordination capacity is exhausted",
            )
        expires_at = now + self._retention_seconds
        self._entries[key] = _StoredAgreementAssent(prepared, now, expires_at)
        return AgreementAssentPutResult(StoreDisposition.STORED, now, expires_at)

    def peek(
        self,
        agreement_record_id: str,
        principal: str,
    ) -> PreparedAgreementAssent | None:
        key = (_record_id(agreement_record_id), _uri(principal))
        now = self._now()
        stored = self._entries.get(key)
        if stored is None or stored.expires_at <= now:
            return None
        return stored.prepared

    def list_for_agreement(
        self,
        agreement_record_id: str,
        *,
        limit: int = MAX_AGREEMENT_ASSENT_PARTIES,
    ) -> tuple[PreparedAgreementAssent, ...]:
        reviewed_id = _record_id(agreement_record_id)
        if (
            type(limit) is not int
            or isinstance(limit, bool)
            or not 1 <= limit <= MAX_AGREEMENT_ASSENT_PARTIES
        ):
            raise ValueError("limit is outside the reviewed party bound")
        now = self._now()
        values = tuple(
            stored.prepared
            for key, stored in sorted(
                self._entries.items(),
                key=lambda item: item[0][1].encode("utf-8"),
            )
            if key[0] == reviewed_id and stored.expires_at > now
        )
        if len(values) > limit:
            raise AgreementAssentCoordinationError(
                "AGREEMENT_ASSENT_EVIDENCE_LIMIT_EXCEEDED",
                "Agreement assent evidence exceeds the reviewed party bound",
            )
        return values

    def expire_due(self) -> AgreementAssentExpiryResult:
        return self._expire_due_at(self._now())


class MarketplaceAgreementAssentCoordinationService:
    """Accept verified assents into an injected bounded coordination store."""

    def __init__(
        self,
        *,
        store: AgreementAssentCoordinationStore,
        prepare_verified_assent: AgreementAssentPreparer,
    ) -> None:
        if not callable(prepare_verified_assent):
            raise TypeError("prepare_verified_assent MUST be callable")
        self._store = store
        self._prepare_verified_assent = prepare_verified_assent
        self._initialized = False

    def initialize(self) -> AgreementAssentExpiryResult:
        self._initialized = False
        result = self._store.initialize()
        if type(result) is not AgreementAssentExpiryResult:
            raise TypeError("coordination store initialize MUST return exact expiry result")
        self._initialized = True
        return result

    def _require_initialized(self) -> None:
        if not self._initialized:
            raise AgreementAssentCoordinationError(
                "AGREEMENT_ASSENT_COORDINATION_NOT_INITIALIZED",
                "Agreement assent coordination must be initialized before use",
            )

    def accept(self, verified: VerifiedAgreementAssent) -> AgreementAssentPutResult:
        self._require_initialized()
        if type(verified) is not VerifiedAgreementAssent:
            raise TypeError("verified MUST be exact VerifiedAgreementAssent")
        try:
            prepared = self._prepare_verified_assent(verified)
        except Exception:
            raise AgreementAssentCoordinationError(
                "AGREEMENT_ASSENT_PREPARATION_FAILED",
                "verified Agreement assent could not be prepared for coordination",
            ) from None
        if type(prepared) is not PreparedAgreementAssent:
            raise TypeError("prepare_verified_assent MUST return exact PreparedAgreementAssent")
        if (
            prepared.agreement_record_id != verified.agreement_record_id
            or prepared.principal != verified.principal
            or prepared.verification_method != verified.verification_method
        ):
            raise AgreementAssentCoordinationError(
                "AGREEMENT_ASSENT_PREPARATION_MISMATCH",
                "prepared Agreement assent does not match the verified binding",
            )
        result = self._store.put(prepared)
        if type(result) is not AgreementAssentPutResult:
            raise TypeError("coordination store put MUST return exact AgreementAssentPutResult")
        return result

    def peek(
        self,
        agreement_record_id: str,
        principal: str,
    ) -> PreparedAgreementAssent | None:
        self._require_initialized()
        result = self._store.peek(agreement_record_id, principal)
        if result is not None and type(result) is not PreparedAgreementAssent:
            raise TypeError("coordination store peek MUST return prepared assent or None")
        return result

    def for_agreement(
        self,
        agreement_record_id: str,
    ) -> tuple[PreparedAgreementAssent, ...]:
        self._require_initialized()
        result = self._store.list_for_agreement(
            agreement_record_id,
            limit=MAX_AGREEMENT_ASSENT_PARTIES,
        )
        if type(result) is not tuple or any(
            type(value) is not PreparedAgreementAssent for value in result
        ):
            raise TypeError("coordination store list MUST return exact prepared-assent tuple")
        return result

    def expire_due(self) -> AgreementAssentExpiryResult:
        self._require_initialized()
        result = self._store.expire_due()
        if type(result) is not AgreementAssentExpiryResult:
            raise TypeError("coordination store expire_due MUST return exact expiry result")
        return result


__all__ = [
    "AGREEMENT_ASSENT_COORDINATION_RETENTION_CLASS",
    "AGREEMENT_ASSENT_PROOF_IDENTITY_BYTES",
    "AgreementAssentCoordinationCollisionError",
    "AgreementAssentCoordinationError",
    "AgreementAssentCoordinationStore",
    "AgreementAssentExpiryResult",
    "AgreementAssentPreparer",
    "AgreementAssentPutResult",
    "DEFAULT_AGREEMENT_ASSENT_RETENTION_SECONDS",
    "MAX_AGREEMENT_ASSENT_COORDINATION_ENTRIES",
    "MAX_AGREEMENT_ASSENT_EXPIRY_BATCH",
    "MAX_AGREEMENT_ASSENT_PARTIES",
    "MAX_AGREEMENT_ASSENT_PROOF_BYTES",
    "MAX_AGREEMENT_ASSENT_RETENTION_SECONDS",
    "MemoryAgreementAssentCoordinationStore",
    "MarketplaceAgreementAssentCoordinationService",
    "PreparedAgreementAssent",
    "StoreDisposition",
]
