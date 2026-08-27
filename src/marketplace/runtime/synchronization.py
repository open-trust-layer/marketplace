"""Strictly bounded sequential composition of existing federation runtime gates.

Milestone 31 composes M26 control exchange, M28 page hydration, M29 one-step
continuation planning, and M30 immutable prepared requests. This module adds no
socket/TLS/HTTP/DNS implementation, retry loop, endpoint discovery, background
work, or durable cursor/checkpoint state.

A cursor never grants transmission authority. Each possible control request
requires one caller-supplied finite ``FederationControlTarget`` slot, and every
actual exchange still revalidates its M25 authorization inside the M26 adapter.
"""
from __future__ import annotations

import math
import time
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from itertools import islice
from typing import Any, Final, Protocol

from .continuation import (
    CONTINUATION_PREPARED,
    ContinuationPlanOutcome,
    FederationContinuationPlanner,
)
from .federation import (
    FederationPageOutcome,
    OfflineFederationService,
    PreparedFederationExchange,
    ValidatedFederationPage,
)
from .https_transport import HttpsFederationExchangeResult
from .network_policy import FederationEndpointAuthorization
from .page_hydration import (
    BoundedFederationPageHydrator,
    FederationPageHydrationOutcome,
    RecordHydrationTarget,
)
from .prepared_integrity import detach_host_value, host_value_integrity_snapshot

DEFAULT_MAX_SYNCHRONIZATION_PAGES: Final = 4
MAX_SYNCHRONIZATION_PAGES: Final = 16
DEFAULT_MAX_SYNCHRONIZATION_RECORDS: Final = 64
MAX_SYNCHRONIZATION_RECORDS: Final = 256
DEFAULT_SYNCHRONIZATION_TIMEOUT_SECONDS: Final = 120.0
MAX_SYNCHRONIZATION_TIMEOUT_SECONDS: Final = 300.0

SYNC_FINAL_PAGE_ACCEPTED: Final = "FINAL_PAGE_ACCEPTED"
SYNC_STOPPED_PAGE_LIMIT: Final = "STOPPED_PAGE_LIMIT"
SYNC_STOPPED_CONTROL_TARGET_LIMIT: Final = "STOPPED_CONTROL_TARGET_LIMIT"
SYNC_STOPPED_TIME_LIMIT: Final = "STOPPED_TIME_LIMIT"


class FederationSynchronizationError(RuntimeError):
    """Fail-closed M31 orchestration error with stable local reason code."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def _fail(code: str, message: str) -> None:
    raise FederationSynchronizationError(code, message)


def _nested_code(exc: BaseException) -> str:
    code = getattr(exc, "code", None)
    return code if isinstance(code, str) and code else type(exc).__name__


def _exact_int(value: object, expected: int) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value == expected


def _finite_number(value: object, *, code: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        _fail(code, "synchronization monotonic clock MUST return a finite number")
    normalized = float(value)
    if not math.isfinite(normalized):
        _fail(code, "synchronization monotonic clock MUST return a finite number")
    return normalized


class FederationControlTransport(Protocol):
    """M26-compatible one-shot control exchange boundary."""

    def exchange(
        self,
        prepared: PreparedFederationExchange,
        *,
        endpoint: str,
        authorization: FederationEndpointAuthorization,
    ) -> HttpsFederationExchangeResult: ...


class PageRecordTargetProvider(Protocol):
    """Resolve exact M28 targets for one validated page without granting authority."""

    def __call__(
        self,
        record_ids: tuple[str, ...],
        *,
        page_number: int,
    ) -> Iterable[RecordHydrationTarget]: ...


@dataclass(frozen=True)
class FederationSynchronizationLimits:
    max_pages: int = DEFAULT_MAX_SYNCHRONIZATION_PAGES
    max_total_records: int = DEFAULT_MAX_SYNCHRONIZATION_RECORDS
    total_timeout_seconds: float = DEFAULT_SYNCHRONIZATION_TIMEOUT_SECONDS

    def __post_init__(self) -> None:
        if (
            isinstance(self.max_pages, bool)
            or not isinstance(self.max_pages, int)
            or not 1 <= self.max_pages <= MAX_SYNCHRONIZATION_PAGES
        ):
            raise ValueError(f"max_pages MUST be within 1..{MAX_SYNCHRONIZATION_PAGES}")
        if (
            isinstance(self.max_total_records, bool)
            or not isinstance(self.max_total_records, int)
            or not 1 <= self.max_total_records <= MAX_SYNCHRONIZATION_RECORDS
        ):
            raise ValueError(
                f"max_total_records MUST be within 1..{MAX_SYNCHRONIZATION_RECORDS}"
            )
        if (
            isinstance(self.total_timeout_seconds, bool)
            or not isinstance(self.total_timeout_seconds, (int, float))
            or not math.isfinite(float(self.total_timeout_seconds))
            or not 0 < float(self.total_timeout_seconds) <= MAX_SYNCHRONIZATION_TIMEOUT_SECONDS
        ):
            raise ValueError(
                "total_timeout_seconds MUST be finite and within "
                f"(0, {MAX_SYNCHRONIZATION_TIMEOUT_SECONDS}]"
            )


@dataclass(frozen=True)
class FederationControlTarget:
    """One explicit finite control-send slot; never synthesized from a cursor."""

    endpoint: str
    authorization: FederationEndpointAuthorization

    def __post_init__(self) -> None:
        if not isinstance(self.endpoint, str) or not self.endpoint:
            raise ValueError("endpoint MUST be non-empty text")
        if not isinstance(self.authorization, FederationEndpointAuthorization):
            raise TypeError("authorization MUST be FederationEndpointAuthorization")


@dataclass(frozen=True)
class FederationSynchronizationOutcome:
    """Bounded operational facts only; no semantic or protected-action authority."""

    disposition: str
    pages_accepted: int
    control_exchanges: int
    continuations_planned: int
    continuations_transmitted: int
    hydrated_record_count: int
    record_retrieval_attempts: int
    final_page_observed: bool
    last_source_completeness: str | None
    control_transport_was_invoked: bool
    record_transport_was_invoked: bool
    retries_performed: int = 0
    parallel_execution: bool = False
    background_execution: bool = False
    global_completeness: str = "UNKNOWN"
    absence_is_deletion_evidence: bool = False
    proofs_verified: bool = False
    establishes_truth: bool = False
    establishes_peer_trust: bool = False
    establishes_authorization: bool = False
    creates_agreement: bool = False
    authorizes_side_effects: bool = False


class BoundedFederationSynchronizationOrchestrator:
    """Synchronize a finite page sequence using only existing reviewed gates."""

    def __init__(
        self,
        *,
        federation_service: OfflineFederationService,
        control_transport: FederationControlTransport,
        page_hydrator: BoundedFederationPageHydrator,
        continuation_planner: FederationContinuationPlanner,
        record_target_provider: PageRecordTargetProvider,
        limits: FederationSynchronizationLimits | None = None,
        monotonic_clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if not isinstance(federation_service, OfflineFederationService):
            raise TypeError("federation_service MUST be OfflineFederationService")
        if not callable(getattr(control_transport, "exchange", None)):
            raise TypeError("control_transport MUST provide callable exchange")
        if not isinstance(page_hydrator, BoundedFederationPageHydrator):
            raise TypeError("page_hydrator MUST be BoundedFederationPageHydrator")
        if not isinstance(continuation_planner, FederationContinuationPlanner):
            raise TypeError("continuation_planner MUST be FederationContinuationPlanner")
        if not callable(record_target_provider):
            raise TypeError("record_target_provider MUST be callable")
        if not callable(monotonic_clock):
            raise TypeError("monotonic_clock MUST be callable")
        self._federation = federation_service
        self._control = control_transport
        self._hydrator = page_hydrator
        self._planner = continuation_planner
        self._targets_for_page = record_target_provider
        self._limits = limits or FederationSynchronizationLimits()
        self._monotonic = monotonic_clock

    @property
    def limits(self) -> FederationSynchronizationLimits:
        return self._limits

    def _clock(self) -> float:
        try:
            value = self._monotonic()
        except Exception as exc:
            _fail(
                "MONOTONIC_CLOCK_FAILED",
                f"synchronization monotonic clock failed: {type(exc).__name__}",
            )
        return _finite_number(value, code="INVALID_MONOTONIC_CLOCK")

    def _budget_state(self, start: float, previous: float) -> tuple[float, bool]:
        now = self._clock()
        if now < previous:
            _fail("MONOTONIC_CLOCK_ROLLBACK", "synchronization monotonic clock moved backwards")
        return now, now - start >= self._limits.total_timeout_seconds

    def _require_budget(self, start: float, previous: float) -> float:
        now, exhausted = self._budget_state(start, previous)
        if exhausted:
            _fail(
                "SYNCHRONIZATION_TIMEOUT",
                "aggregate synchronization time budget is exhausted before the next phase",
            )
        return now

    def _control_targets(
        self,
        values: Iterable[FederationControlTarget],
    ) -> tuple[FederationControlTarget, ...]:
        try:
            items = tuple(islice(values, self._limits.max_pages + 1))
        except TypeError:
            _fail("INVALID_CONTROL_TARGETS", "control targets MUST be iterable")
        except Exception as exc:
            _fail("INVALID_CONTROL_TARGETS", f"control target iteration failed: {type(exc).__name__}")
        if not items:
            _fail("EMPTY_CONTROL_TARGETS", "at least one explicit control target is required")
        if len(items) > self._limits.max_pages:
            _fail(
                "CONTROL_TARGET_LIMIT_EXCEEDED",
                "control target count exceeds configured synchronization page bound",
            )
        for item in items:
            if not isinstance(item, FederationControlTarget):
                _fail("INVALID_CONTROL_TARGET", "control targets MUST be FederationControlTarget values")
        return items

    @staticmethod
    def _initial_request_payload(
        request: Mapping[str, Any],
        prepared: PreparedFederationExchange,
    ) -> Mapping[str, Any]:
        if not isinstance(request, Mapping):
            _fail("INVALID_INITIAL_REQUEST", "initial federation request MUST be a mapping")
        if not isinstance(prepared, PreparedFederationExchange):
            _fail("INVALID_INITIAL_PREPARED_EXCHANGE", "initial prepared exchange has the wrong type")
        if prepared.transmitted is not False:
            _fail("INITIAL_PREPARED_EXCHANGE_STATE", "initial prepared exchange MUST be unsent")
        envelope = prepared.envelope
        if (
            not isinstance(envelope, tuple)
            or len(envelope) != 4
            or envelope[0] != "OLP-TRANSPORT"
            or not _exact_int(envelope[1], 1)
            or not isinstance(envelope[2], str)
            or not envelope[2]
            or not isinstance(envelope[3], Mapping)
        ):
            _fail("INVALID_INITIAL_PREPARED_EXCHANGE", "initial prepared envelope shape is invalid")
        try:
            request_snapshot = host_value_integrity_snapshot(request)
            prepared_snapshot = host_value_integrity_snapshot(envelope[3])
        except Exception as exc:
            _fail(
                "INITIAL_REQUEST_SNAPSHOT_FAILED",
                f"initial request integrity snapshot failed: {_nested_code(exc)}",
            )
        if request_snapshot != prepared_snapshot:
            _fail(
                "INITIAL_REQUEST_PREPARED_MISMATCH",
                "initial request differs from the immutable prepared request payload",
            )
        return envelope[3]

    @staticmethod
    def _validate_control_result(value: Any) -> HttpsFederationExchangeResult:
        if not isinstance(value, HttpsFederationExchangeResult):
            _fail("INVALID_CONTROL_RESULT", "control transport MUST return HttpsFederationExchangeResult")
        if not _exact_int(value.http_status, 200):
            _fail("INVALID_CONTROL_RESULT", "control result MUST report exact integer HTTP status 200")
        if (
            isinstance(value.response_body_bytes, bool)
            or not isinstance(value.response_body_bytes, int)
            or value.response_body_bytes < 1
        ):
            _fail("INVALID_CONTROL_RESULT", "control response byte count is invalid")
        if not isinstance(value.selected_address, str) or not value.selected_address:
            _fail("INVALID_CONTROL_RESULT", "control result selected address is invalid")
        if not isinstance(value.tls_server_hostname, str) or not value.tls_server_hostname:
            _fail("INVALID_CONTROL_RESULT", "control result TLS hostname is invalid")
        if not _exact_int(value.connection_attempts, 1):
            _fail("CONTROL_ATTEMPT_INVARIANT", "each control page MUST use exactly one connection attempt")
        if not _exact_int(value.redirects_followed, 0) or not _exact_int(value.retries_performed, 0):
            _fail("CONTROL_REPLAY_INVARIANT", "M31 forbids control redirects and retries")
        if value.proxy_used is not False or value.credentials_used is not False:
            _fail("CONTROL_AMBIENT_AUTHORITY_INVARIANT", "M31 forbids proxy or credential use")
        for name in (
            "establishes_peer_trust",
            "establishes_marketplace_truth",
            "establishes_agreement",
            "establishes_authorization",
        ):
            if getattr(value, name) is not False:
                _fail(
                    "CONTROL_AUTHORITY_INVARIANT",
                    f"M26 control result MUST keep {name}=false",
                )
        envelope = value.response_envelope
        if (
            not isinstance(envelope, tuple)
            or len(envelope) != 4
            or envelope[0] != "OLP-TRANSPORT"
            or not _exact_int(envelope[1], 1)
            or not isinstance(envelope[2], str)
            or not envelope[2]
        ):
            _fail("INVALID_CONTROL_RESULT", "control response envelope shape is invalid")
        return value

    @staticmethod
    def _detach_control_response(value: HttpsFederationExchangeResult) -> tuple[Any, ...]:
        try:
            detached = detach_host_value(value.response_envelope)
        except Exception as exc:
            _fail(
                "CONTROL_RESPONSE_DETACH_FAILED",
                f"control response immutable detachment failed: {_nested_code(exc)}",
            )
        if type(detached) is not tuple or len(detached) != 4:
            _fail("CONTROL_RESPONSE_DETACH_FAILED", "detached control response envelope is invalid")
        return detached

    @staticmethod
    def _bounded_page_targets(
        value: Iterable[RecordHydrationTarget],
        *,
        expected_count: int,
    ) -> tuple[RecordHydrationTarget, ...]:
        try:
            items = tuple(islice(value, expected_count + 1))
        except TypeError:
            _fail("INVALID_PAGE_RECORD_TARGETS", "page Record targets MUST be iterable")
        except Exception as exc:
            _fail(
                "INVALID_PAGE_RECORD_TARGETS",
                f"page Record target iteration failed: {type(exc).__name__}",
            )
        if len(items) != expected_count:
            _fail(
                "PAGE_RECORD_TARGET_COUNT_MISMATCH",
                "page Record target provider MUST return exactly one target per Record identity",
            )
        for item in items:
            if not isinstance(item, RecordHydrationTarget):
                _fail("INVALID_PAGE_RECORD_TARGET", "page Record targets MUST be RecordHydrationTarget values")
        return items

    @staticmethod
    def _validate_hydration_outcome(
        value: Any,
        *,
        validated: ValidatedFederationPage,
    ) -> FederationPageHydrationOutcome:
        if not isinstance(value, FederationPageHydrationOutcome):
            _fail("INVALID_HYDRATION_OUTCOME", "M28 hydrator returned the wrong outcome type")
        page = value.page_outcome
        if not isinstance(page, FederationPageOutcome):
            _fail("INVALID_HYDRATION_OUTCOME", "M28 page outcome has the wrong type")
        if value.hydrated_record_ids != validated.record_ids or page.record_ids != validated.record_ids:
            _fail("HYDRATION_PAGE_BINDING_MISMATCH", "M28 outcome Record identities differ from validated page")
        if page.source_completeness != validated.source_completeness:
            _fail("HYDRATION_PAGE_BINDING_MISMATCH", "M28 source completeness differs from validated page")
        if page.page_truncated is not validated.page_truncated or page.next_cursor != validated.next_cursor:
            _fail("HYDRATION_PAGE_BINDING_MISMATCH", "M28 page controls differ from validated page")
        if not _exact_int(value.retrieval_attempts, len(validated.record_ids)):
            _fail("HYDRATION_ATTEMPT_INVARIANT", "M28 retrieval attempts differ from validated Record count")
        expected_record_transport = bool(validated.record_ids)
        if value.record_transport_was_invoked is not expected_record_transport:
            _fail("HYDRATION_TRANSPORT_INVARIANT", "M28 Record transport fact is inconsistent")
        if not _exact_int(value.retries_performed, 0) or value.parallel_retrieval is not False:
            _fail("HYDRATION_REPLAY_INVARIANT", "M31 forbids M28 retries and parallel retrieval")
        if value.cursor_automatically_followed is not False:
            _fail("HYDRATION_CURSOR_AUTHORITY_INVARIANT", "M28 MUST NOT follow cursors")
        for name in (
            "proofs_verified",
            "establishes_truth",
            "establishes_authorization",
            "creates_agreement",
        ):
            if getattr(value, name) is not False:
                _fail("HYDRATION_AUTHORITY_INVARIANT", f"M28 outcome MUST keep {name}=false")
        if page.global_completeness != "UNKNOWN":
            _fail("HYDRATION_AUTHORITY_INVARIANT", "M24/M28 global completeness MUST remain UNKNOWN")
        if page.absence_is_deletion_evidence is not False:
            _fail("HYDRATION_AUTHORITY_INVARIANT", "M24/M28 absence MUST NOT become deletion evidence")
        if page.transport_exactly_once_claimed is not False or page.transport_was_invoked is not False:
            _fail("HYDRATION_AUTHORITY_INVARIANT", "M24 local page outcome MUST NOT claim transport guarantees")
        if page.creates_agreement is not False or page.authorizes_side_effects is not False:
            _fail("HYDRATION_AUTHORITY_INVARIANT", "M24/M28 MUST NOT create agreement or protected authority")
        stored = tuple(page.stored_record_ids)
        duplicates = tuple(page.duplicate_record_ids)
        if set(stored) & set(duplicates) or set(stored) | set(duplicates) != set(page.record_ids):
            _fail("HYDRATION_STORE_OUTCOME_INVARIANT", "M24 stored/duplicate identities do not partition the page")
        return value

    @staticmethod
    def _validate_continuation_outcome(
        value: Any,
        *,
        current_prepared: PreparedFederationExchange,
        current_request: Mapping[str, Any],
        expected_cursor: bytes,
    ) -> PreparedFederationExchange:
        if not isinstance(value, ContinuationPlanOutcome):
            _fail("INVALID_CONTINUATION_OUTCOME", "M29 planner returned the wrong outcome type")
        if value.disposition != CONTINUATION_PREPARED or value.prior_page_truncated is not True:
            _fail("CONTINUATION_INCONSISTENCY", "truncated accepted page requires one prepared continuation")
        if value.network_was_invoked is not False or value.cursor_automatically_followed is not False:
            _fail("CONTINUATION_AUTHORITY_INVARIANT", "M29 planning MUST remain transport-free")
        if value.authorization_established is not False or value.source_completeness_established is not False:
            _fail("CONTINUATION_AUTHORITY_INVARIANT", "M29 cursor binding MUST NOT grant authority/completeness")
        if value.global_completeness != "UNKNOWN" or value.absence_is_deletion_evidence is not False:
            _fail("CONTINUATION_AUTHORITY_INVARIANT", "M29 MUST preserve UNKNOWN global completeness")
        if value.creates_agreement is not False or value.authorizes_side_effects is not False:
            _fail("CONTINUATION_AUTHORITY_INVARIANT", "M29 MUST NOT create agreement or protected authority")
        prepared = value.prepared_exchange
        if not isinstance(prepared, PreparedFederationExchange) or prepared.transmitted is not False:
            _fail("INVALID_CONTINUATION_OUTCOME", "M29 MUST return one unsent PreparedFederationExchange")
        if prepared.binding != current_prepared.binding:
            _fail("CONTINUATION_BINDING_DRIFT", "M29 continuation changed immutable request binding")
        if prepared.envelope[:3] != current_prepared.envelope[:3]:
            _fail("CONTINUATION_MESSAGE_PROFILE_DRIFT", "M29 continuation changed message profile")
        payload = prepared.envelope[3]
        if not isinstance(payload, Mapping):
            _fail("INVALID_CONTINUATION_OUTCOME", "M29 continuation payload MUST be a mapping")
        if payload.get("cursor") != expected_cursor:
            _fail("CONTINUATION_CURSOR_DRIFT", "M29 continuation does not carry the exact opaque page cursor")
        current_without = {key: item for key, item in current_request.items() if key != "cursor"}
        next_without = {key: item for key, item in payload.items() if key != "cursor"}
        try:
            if host_value_integrity_snapshot(current_without) != host_value_integrity_snapshot(next_without):
                _fail("CONTINUATION_REQUEST_DRIFT", "M29 continuation changed a non-cursor request field")
        except FederationSynchronizationError:
            raise
        except Exception as exc:
            _fail(
                "CONTINUATION_SNAPSHOT_FAILED",
                f"continuation integrity snapshot failed: {_nested_code(exc)}",
            )
        return prepared

    def _outcome(
        self,
        *,
        disposition: str,
        pages_accepted: int,
        control_exchanges: int,
        continuations_planned: int,
        hydrated_record_count: int,
        record_retrieval_attempts: int,
        final_page_observed: bool,
        last_source_completeness: str | None,
        record_transport_was_invoked: bool,
    ) -> FederationSynchronizationOutcome:
        return FederationSynchronizationOutcome(
            disposition=disposition,
            pages_accepted=pages_accepted,
            control_exchanges=control_exchanges,
            continuations_planned=continuations_planned,
            continuations_transmitted=max(0, control_exchanges - 1),
            hydrated_record_count=hydrated_record_count,
            record_retrieval_attempts=record_retrieval_attempts,
            final_page_observed=final_page_observed,
            last_source_completeness=last_source_completeness,
            control_transport_was_invoked=control_exchanges > 0,
            record_transport_was_invoked=record_transport_was_invoked,
        )

    def synchronize(
        self,
        initial_request: Mapping[str, Any],
        initial_prepared: PreparedFederationExchange,
        control_targets: Iterable[FederationControlTarget],
    ) -> FederationSynchronizationOutcome:
        """Execute at most the explicitly bounded and pre-targeted page sequence."""
        targets = self._control_targets(control_targets)
        current_request = self._initial_request_payload(initial_request, initial_prepared)
        current_prepared = initial_prepared
        seen_cursors: set[bytes] = set()
        initial_cursor = current_request.get("cursor")
        if initial_cursor is not None:
            if not isinstance(initial_cursor, bytes):
                _fail("INVALID_INITIAL_CURSOR", "prepared initial cursor MUST be opaque bytes")
            seen_cursors.add(initial_cursor)

        start = self._clock()
        last = start
        page_index = 0
        pages_accepted = 0
        control_exchanges = 0
        continuations_planned = 0
        hydrated_records = 0
        record_attempts = 0
        record_transport_was_invoked = False
        last_source_completeness: str | None = None

        while True:
            last = self._require_budget(start, last)
            target = targets[page_index]
            try:
                raw_control_result = self._control.exchange(
                    current_prepared,
                    endpoint=target.endpoint,
                    authorization=target.authorization,
                )
            except Exception as exc:
                _fail("CONTROL_EXCHANGE_FAILED", f"M26 control exchange failed: {_nested_code(exc)}")
            control_exchanges += 1
            last = self._require_budget(start, last)
            control_result = self._validate_control_result(raw_control_result)
            response_envelope = self._detach_control_response(control_result)

            try:
                validated = self._federation.validate_page(
                    current_prepared,
                    response_envelope,
                )
            except Exception as exc:
                _fail("PAGE_VALIDATION_FAILED", f"M24 page validation failed: {_nested_code(exc)}")
            if not isinstance(validated, ValidatedFederationPage):
                _fail("INVALID_VALIDATED_PAGE", "M24 validate_page returned the wrong type")
            last = self._require_budget(start, last)

            next_total = hydrated_records + len(validated.record_ids)
            if next_total > self._limits.max_total_records:
                _fail(
                    "TOTAL_RECORD_LIMIT_EXCEEDED",
                    "validated page would exceed the aggregate synchronization Record bound",
                )

            try:
                raw_page_targets = self._targets_for_page(
                    validated.record_ids,
                    page_number=page_index + 1,
                )
            except Exception as exc:
                _fail(
                    "PAGE_RECORD_TARGET_PROVIDER_FAILED",
                    f"page Record target provider failed: {_nested_code(exc)}",
                )
            page_targets = self._bounded_page_targets(
                raw_page_targets,
                expected_count=len(validated.record_ids),
            )
            last = self._require_budget(start, last)

            try:
                raw_hydration = self._hydrator.hydrate_and_accept(
                    current_prepared,
                    response_envelope,
                    page_targets,
                )
            except Exception as exc:
                _fail("PAGE_HYDRATION_FAILED", f"M28 page hydration failed: {_nested_code(exc)}")
            hydration = self._validate_hydration_outcome(raw_hydration, validated=validated)

            pages_accepted += 1
            hydrated_records = next_total
            record_attempts += hydration.retrieval_attempts
            record_transport_was_invoked = (
                record_transport_was_invoked or hydration.record_transport_was_invoked
            )
            last_source_completeness = hydration.page_outcome.source_completeness
            last, budget_exhausted = self._budget_state(start, last)

            if not validated.page_truncated:
                return self._outcome(
                    disposition=SYNC_FINAL_PAGE_ACCEPTED,
                    pages_accepted=pages_accepted,
                    control_exchanges=control_exchanges,
                    continuations_planned=continuations_planned,
                    hydrated_record_count=hydrated_records,
                    record_retrieval_attempts=record_attempts,
                    final_page_observed=True,
                    last_source_completeness=last_source_completeness,
                    record_transport_was_invoked=record_transport_was_invoked,
                )

            if pages_accepted >= self._limits.max_pages:
                return self._outcome(
                    disposition=SYNC_STOPPED_PAGE_LIMIT,
                    pages_accepted=pages_accepted,
                    control_exchanges=control_exchanges,
                    continuations_planned=continuations_planned,
                    hydrated_record_count=hydrated_records,
                    record_retrieval_attempts=record_attempts,
                    final_page_observed=False,
                    last_source_completeness=last_source_completeness,
                    record_transport_was_invoked=record_transport_was_invoked,
                )
            if page_index + 1 >= len(targets):
                return self._outcome(
                    disposition=SYNC_STOPPED_CONTROL_TARGET_LIMIT,
                    pages_accepted=pages_accepted,
                    control_exchanges=control_exchanges,
                    continuations_planned=continuations_planned,
                    hydrated_record_count=hydrated_records,
                    record_retrieval_attempts=record_attempts,
                    final_page_observed=False,
                    last_source_completeness=last_source_completeness,
                    record_transport_was_invoked=record_transport_was_invoked,
                )
            if budget_exhausted:
                return self._outcome(
                    disposition=SYNC_STOPPED_TIME_LIMIT,
                    pages_accepted=pages_accepted,
                    control_exchanges=control_exchanges,
                    continuations_planned=continuations_planned,
                    hydrated_record_count=hydrated_records,
                    record_retrieval_attempts=record_attempts,
                    final_page_observed=False,
                    last_source_completeness=last_source_completeness,
                    record_transport_was_invoked=record_transport_was_invoked,
                )

            cursor = validated.next_cursor
            if not isinstance(cursor, bytes):
                _fail("INVALID_VALIDATED_CURSOR", "truncated validated page MUST carry opaque cursor bytes")
            if cursor in seen_cursors:
                _fail("CURSOR_REPLAY_DETECTED", "opaque continuation cursor repeated within one bounded synchronization call")
            seen_cursors.add(cursor)

            try:
                raw_plan = self._planner.plan(
                    current_request,
                    current_prepared,
                    validated,
                )
            except Exception as exc:
                _fail("CONTINUATION_PLANNING_FAILED", f"M29 continuation planning failed: {_nested_code(exc)}")
            continuations_planned += 1
            next_prepared = self._validate_continuation_outcome(
                raw_plan,
                current_prepared=current_prepared,
                current_request=current_request,
                expected_cursor=cursor,
            )
            last, budget_exhausted = self._budget_state(start, last)
            if budget_exhausted:
                return self._outcome(
                    disposition=SYNC_STOPPED_TIME_LIMIT,
                    pages_accepted=pages_accepted,
                    control_exchanges=control_exchanges,
                    continuations_planned=continuations_planned,
                    hydrated_record_count=hydrated_records,
                    record_retrieval_attempts=record_attempts,
                    final_page_observed=False,
                    last_source_completeness=last_source_completeness,
                    record_transport_was_invoked=record_transport_was_invoked,
                )

            current_prepared = next_prepared
            current_request = next_prepared.envelope[3]
            page_index += 1
