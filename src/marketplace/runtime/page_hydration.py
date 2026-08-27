"""Bounded sequential hydration of one already-supplied M8 federation page.

Milestone 28 coordinates the accepted M24 page validator/ingest path and M27
single-Record retrieval boundary. It deliberately adds no socket/TLS/URL client,
parallelism, retry, cursor following, endpoint discovery, or durable cache.
"""
from __future__ import annotations

import math
import time
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from itertools import islice
from typing import Any, Final, Protocol

from .federation import (
    FederationPageOutcome,
    OfflineFederationService,
    PreparedFederationExchange,
    ValidatedFederationPage,
)
from .network_policy import FederationEndpointAuthorization
from .record_retrieval import RetrievedRecordTransportResult

DEFAULT_MAX_HYDRATED_RECORDS: Final = 16
MAX_HYDRATED_RECORDS: Final = 64
DEFAULT_PAGE_HYDRATION_TIMEOUT_SECONDS: Final = 60.0
MAX_PAGE_HYDRATION_TIMEOUT_SECONDS: Final = 300.0


class FederationPageHydrationError(RuntimeError):
    """Fail-closed M28 page-hydration error with stable local reason code."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def _fail(code: str, message: str) -> None:
    raise FederationPageHydrationError(code, message)


def _nested_code(exc: BaseException) -> str:
    code = getattr(exc, "code", None)
    return code if isinstance(code, str) and code else type(exc).__name__


def _finite_clock_value(value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        _fail("INVALID_MONOTONIC_CLOCK", "page hydration monotonic clock MUST return a finite number")
    normalized = float(value)
    if not math.isfinite(normalized):
        _fail("INVALID_MONOTONIC_CLOCK", "page hydration monotonic clock MUST return a finite number")
    return normalized


def _exact_int(value: object, expected: int) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value == expected


class RecordTargetRetriever(Protocol):
    """M27-compatible preflight + one-shot retrieval boundary."""

    def preflight(
        self,
        *,
        endpoint: str,
        authorization: FederationEndpointAuthorization,
        expected_record_identity: str,
    ) -> None: ...

    def retrieve(
        self,
        *,
        endpoint: str,
        authorization: FederationEndpointAuthorization,
        expected_record_identity: str,
    ) -> RetrievedRecordTransportResult: ...


class RetrievedRecordValueVerifier(Protocol):
    """Return a Record value only after exact M27 identity/semantic verification."""

    def __call__(
        self,
        envelope: Any,
        *,
        expected_record_identity: str,
    ) -> Any: ...


@dataclass(frozen=True)
class PageHydrationLimits:
    max_records: int = DEFAULT_MAX_HYDRATED_RECORDS
    total_timeout_seconds: float = DEFAULT_PAGE_HYDRATION_TIMEOUT_SECONDS

    def __post_init__(self) -> None:
        if (
            isinstance(self.max_records, bool)
            or not isinstance(self.max_records, int)
            or not 1 <= self.max_records <= MAX_HYDRATED_RECORDS
        ):
            raise ValueError(f"max_records MUST be within 1..{MAX_HYDRATED_RECORDS}")
        if (
            isinstance(self.total_timeout_seconds, bool)
            or not isinstance(self.total_timeout_seconds, (int, float))
            or not math.isfinite(float(self.total_timeout_seconds))
            or not 0 < float(self.total_timeout_seconds) <= MAX_PAGE_HYDRATION_TIMEOUT_SECONDS
        ):
            raise ValueError(
                "total_timeout_seconds MUST be finite and within "
                f"(0, {MAX_PAGE_HYDRATION_TIMEOUT_SECONDS}]"
            )


@dataclass(frozen=True)
class RecordHydrationTarget:
    """Explicit operator/caller-supplied exact target for one page Record identity."""

    record_id: str
    endpoint: str
    authorization: FederationEndpointAuthorization

    def __post_init__(self) -> None:
        if not isinstance(self.record_id, str) or not self.record_id:
            raise ValueError("record_id MUST be non-empty text")
        if not isinstance(self.endpoint, str) or not self.endpoint:
            raise ValueError("endpoint MUST be non-empty text")
        if not isinstance(self.authorization, FederationEndpointAuthorization):
            raise TypeError("authorization MUST be FederationEndpointAuthorization")


@dataclass(frozen=True)
class FederationPageHydrationOutcome:
    """Operational M28 outcome wrapping the authoritative M24 local page outcome."""

    page_outcome: FederationPageOutcome
    hydrated_record_ids: tuple[str, ...]
    retrieval_attempts: int
    record_transport_was_invoked: bool
    retries_performed: int = 0
    parallel_retrieval: bool = False
    cursor_automatically_followed: bool = False
    proofs_verified: bool = False
    establishes_truth: bool = False
    establishes_authorization: bool = False
    creates_agreement: bool = False


class BoundedFederationPageHydrator:
    """Hydrate one bounded page sequentially, then invoke M24 once with all Records."""

    def __init__(
        self,
        *,
        federation_service: OfflineFederationService,
        record_retriever: RecordTargetRetriever,
        verify_record_value: RetrievedRecordValueVerifier,
        limits: PageHydrationLimits | None = None,
        monotonic_clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if not isinstance(federation_service, OfflineFederationService):
            raise TypeError("federation_service MUST be OfflineFederationService")
        if not callable(getattr(record_retriever, "preflight", None)):
            raise TypeError("record_retriever MUST provide callable preflight")
        if not callable(getattr(record_retriever, "retrieve", None)):
            raise TypeError("record_retriever MUST provide callable retrieve")
        if not callable(verify_record_value):
            raise TypeError("verify_record_value MUST be callable")
        if not callable(monotonic_clock):
            raise TypeError("monotonic_clock MUST be callable")
        self._federation = federation_service
        self._retriever = record_retriever
        self._verify_record_value = verify_record_value
        self._limits = limits or PageHydrationLimits()
        self._monotonic = monotonic_clock

    @property
    def limits(self) -> PageHydrationLimits:
        return self._limits

    def _clock(self) -> float:
        try:
            value = self._monotonic()
        except Exception as exc:
            _fail("MONOTONIC_CLOCK_FAILED", f"page hydration monotonic clock failed: {type(exc).__name__}")
        return _finite_clock_value(value)

    def _check_budget(self, start: float) -> None:
        now = self._clock()
        if now < start:
            _fail("MONOTONIC_CLOCK_ROLLBACK", "page hydration monotonic clock moved backwards")
        if now - start >= self._limits.total_timeout_seconds:
            _fail("PAGE_HYDRATION_TIMEOUT", "page hydration time budget is exhausted")

    def _bounded_targets(self, targets: Iterable[RecordHydrationTarget]) -> tuple[RecordHydrationTarget, ...]:
        try:
            values = tuple(islice(targets, self._limits.max_records + 1))
        except TypeError:
            _fail("INVALID_HYDRATION_TARGETS", "hydration targets MUST be iterable")
        if len(values) > self._limits.max_records:
            _fail("HYDRATION_TARGET_LIMIT_EXCEEDED", "hydration target count exceeds configured bound")
        for target in values:
            if not isinstance(target, RecordHydrationTarget):
                _fail("INVALID_HYDRATION_TARGET", "hydration targets MUST be RecordHydrationTarget values")
        return values

    def _target_map(
        self,
        validated: ValidatedFederationPage,
        targets: Iterable[RecordHydrationTarget],
    ) -> dict[str, RecordHydrationTarget]:
        if len(validated.record_ids) > self._limits.max_records:
            _fail(
                "HYDRATION_PAGE_LIMIT_EXCEEDED",
                "validated page Record count exceeds configured hydration bound",
            )
        values = self._bounded_targets(targets)
        by_id: dict[str, RecordHydrationTarget] = {}
        endpoints: set[str] = set()
        for target in values:
            if target.record_id in by_id:
                _fail("DUPLICATE_HYDRATION_TARGET", "hydration targets repeat a Record identity")
            if target.endpoint in endpoints:
                _fail(
                    "DUPLICATE_HYDRATION_ENDPOINT",
                    "distinct hydration targets MUST NOT reuse one exact endpoint",
                )
            by_id[target.record_id] = target
            endpoints.add(target.endpoint)

        expected = set(validated.record_ids)
        supplied = set(by_id)
        if supplied != expected or len(by_id) != len(validated.record_ids):
            missing = tuple(sorted(expected - supplied))
            unexpected = tuple(sorted(supplied - expected))
            _fail(
                "HYDRATION_TARGET_SET_MISMATCH",
                f"hydration targets do not exactly match page Record IDs; missing={missing}, unexpected={unexpected}",
            )
        return by_id

    @staticmethod
    def _validate_transport_result(
        result: Any,
        *,
        expected_record_identity: str,
    ) -> RetrievedRecordTransportResult:
        if not isinstance(result, RetrievedRecordTransportResult):
            _fail("INVALID_RETRIEVAL_RESULT", "M27 retriever MUST return RetrievedRecordTransportResult")
        if result.expected_record_identity != expected_record_identity:
            _fail("RETRIEVAL_IDENTITY_BINDING_MISMATCH", "retrieval result is bound to the wrong Record identity")
        if not _exact_int(result.http_status, 200):
            _fail("INVALID_RETRIEVAL_RESULT", "retrieval result MUST report exact integer HTTP status 200")
        if (
            isinstance(result.response_body_bytes, bool)
            or not isinstance(result.response_body_bytes, int)
            or result.response_body_bytes < 1
        ):
            _fail("INVALID_RETRIEVAL_RESULT", "retrieval result response byte count is invalid")
        if not isinstance(result.selected_address, str) or not result.selected_address:
            _fail("INVALID_RETRIEVAL_RESULT", "retrieval result selected address is invalid")
        if not isinstance(result.tls_server_hostname, str) or not result.tls_server_hostname:
            _fail("INVALID_RETRIEVAL_RESULT", "retrieval result TLS hostname is invalid")
        if not _exact_int(result.connection_attempts, 1):
            _fail("RETRIEVAL_ATTEMPT_INVARIANT", "each hydrated Record MUST have exactly one connection attempt")
        if not _exact_int(result.redirects_followed, 0) or not _exact_int(result.retries_performed, 0):
            _fail("RETRIEVAL_REPLAY_INVARIANT", "M28 forbids redirects and retries")
        if result.proxy_used is not False or result.credentials_used is not False:
            _fail("RETRIEVAL_AMBIENT_AUTHORITY_INVARIANT", "M28 forbids proxy or credential use")
        for name in (
            "identity_verified",
            "marketplace_semantics_verified",
            "proofs_verified",
            "establishes_truth",
            "establishes_authorization",
            "automatically_ingested",
        ):
            if getattr(result, name) is not False:
                _fail(
                    "RETRIEVAL_AUTHORITY_INVARIANT",
                    f"M27 transport result MUST keep {name}=false",
                )
        envelope = result.response_envelope
        if (
            not isinstance(envelope, tuple)
            or len(envelope) != 4
            or envelope[0] != "OLP-TRANSPORT"
            or not _exact_int(envelope[1], 1)
            or envelope[2] != "record"
        ):
            _fail("INVALID_RETRIEVAL_RESULT", "M27 retrieval result contains invalid Record envelope shape")
        return result

    def hydrate_and_accept(
        self,
        prepared: PreparedFederationExchange,
        response_envelope: Sequence[Any],
        targets: Iterable[RecordHydrationTarget],
    ) -> FederationPageHydrationOutcome:
        """Hydrate one validated finite page and invoke M24 only after all Records verify."""
        start = self._clock()
        validated = self._federation.validate_page(prepared, response_envelope)
        self._check_budget(start)
        by_id = self._target_map(validated, targets)
        self._check_budget(start)

        # Reject every statically/current-time invalid target before the first
        # DNS lookup. M27 retrieve() repeats these checks and still revalidates
        # authorization after fresh DNS, so this preflight grants no future use.
        for record_id in validated.record_ids:
            self._check_budget(start)
            target = by_id[record_id]
            try:
                self._retriever.preflight(
                    endpoint=target.endpoint,
                    authorization=target.authorization,
                    expected_record_identity=record_id,
                )
            except Exception as exc:
                _fail(
                    "HYDRATION_TARGET_PREFLIGHT_FAILED",
                    f"Record target preflight failed for {record_id}: {_nested_code(exc)}",
                )
            self._check_budget(start)

        verified_records: list[Any] = []
        attempts = 0
        for record_id in validated.record_ids:
            self._check_budget(start)
            target = by_id[record_id]
            attempts += 1
            try:
                raw_result = self._retriever.retrieve(
                    endpoint=target.endpoint,
                    authorization=target.authorization,
                    expected_record_identity=record_id,
                )
            except Exception as exc:
                _fail(
                    "HYDRATION_RETRIEVAL_FAILED",
                    f"Record retrieval failed for {record_id}: {_nested_code(exc)}",
                )
            self._check_budget(start)
            result = self._validate_transport_result(
                raw_result,
                expected_record_identity=record_id,
            )
            try:
                record = self._verify_record_value(
                    result.response_envelope,
                    expected_record_identity=record_id,
                )
            except Exception as exc:
                _fail(
                    "HYDRATION_RECORD_VERIFICATION_FAILED",
                    f"Record verification failed for {record_id}: {_nested_code(exc)}",
                )
            verified_records.append(record)
            self._check_budget(start)

        # Re-run the same M24 page binding at the point of storage. Any response
        # mutation or verifier identity drift therefore fails before M24's first
        # repository mutation. No partial page ingest occurs before this call.
        # Local repository failures during this final existing M24 ingest are not
        # claimed transactional or reversible by M28.
        try:
            page_outcome = self._federation.accept_page(
                prepared,
                response_envelope,
                verified_records,
            )
        except Exception as exc:
            _fail(
                "HYDRATION_FINAL_PAGE_ACCEPTANCE_FAILED",
                f"final M24 page acceptance failed: {_nested_code(exc)}",
            )

        return FederationPageHydrationOutcome(
            page_outcome=page_outcome,
            hydrated_record_ids=page_outcome.record_ids,
            retrieval_attempts=attempts,
            record_transport_was_invoked=attempts > 0,
        )
