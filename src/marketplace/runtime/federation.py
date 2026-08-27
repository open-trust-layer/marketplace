"""Offline federation preparation, response binding, and local ingest.

This module intentionally has no transmission primitive. It prepares abstract
M8/OLP transport values, validates caller-supplied responses, and only then
stores verified immutable records in the existing local EPHEMERAL runtime.
"""
from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from itertools import islice
from typing import Any

from .contracts import (
    FederationEnvelopeMaker,
    FederationEnvelopeValidator,
    FederationRequestValidator,
    FederationResultValidator,
    RecordIdentityProvider,
    RecordValidator,
    StoreDisposition,
)
from .node import MarketplaceNode

MAX_OFFLINE_FEDERATION_PAGE_RECORDS = 10_000
MAX_OFFLINE_FEDERATION_CURSOR_BYTES = 4_096


class OfflineFederationError(RuntimeError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def _fail(code: str, message: str) -> None:
    raise OfflineFederationError(code, message)


@dataclass(frozen=True)
class FederationOperationProfile:
    """Exact operation/message binding supplied by the selected M8 semantics."""

    operation: str
    request_message_type: str
    result_message_type: str

    def __post_init__(self) -> None:
        for name, value in (
            ("operation", self.operation),
            ("request_message_type", self.request_message_type),
            ("result_message_type", self.result_message_type),
        ):
            if not isinstance(value, str) or not value:
                raise ValueError(f"{name} MUST be non-empty text")


@dataclass(frozen=True)
class FederationRequestBinding:
    """Immutable local expectation for one prepared but unsent exchange."""

    source: str
    operation: str
    scope_fingerprint: str
    required_capabilities: tuple[str, ...]
    page_size: int
    expected_result_message_type: str


@dataclass(frozen=True)
class PreparedFederationExchange:
    """Abstract request value plus local binding; never a transmission."""

    binding: FederationRequestBinding
    envelope: tuple[Any, ...]
    transmitted: bool = False


@dataclass(frozen=True)
class ValidatedFederationPage:
    """Side-effect-free validation result for one M8 page response.

    This object describes only a page whose response envelope and M8 binding
    have been validated against one prepared exchange. It contains no supplied
    Record bodies and grants no storage, network, cursor-follow, agreement, or
    protected-action authority.
    """

    source: str
    operation: str
    scope_fingerprint: str
    page_size: int
    record_ids: tuple[str, ...]
    source_completeness: str
    page_truncated: bool
    next_cursor: bytes | None
    global_completeness: str = "UNKNOWN"
    absence_is_deletion_evidence: bool = False
    creates_agreement: bool = False
    authorizes_side_effects: bool = False


@dataclass(frozen=True)
class FederationPageOutcome:
    """Local result after complete response validation and EPHEMERAL ingest."""

    record_ids: tuple[str, ...]
    stored_record_ids: tuple[str, ...]
    duplicate_record_ids: tuple[str, ...]
    source_completeness: str
    page_truncated: bool
    next_cursor: bytes | None
    global_completeness: str = "UNKNOWN"
    absence_is_deletion_evidence: bool = False
    transport_exactly_once_claimed: bool = False
    transport_was_invoked: bool = False
    creates_agreement: bool = False
    authorizes_side_effects: bool = False


class OfflineFederationService:
    """Prepare and consume federation exchanges without performing network I/O."""

    def __init__(
        self,
        *,
        node: MarketplaceNode,
        validate_record: RecordValidator,
        record_identity_text: RecordIdentityProvider,
        validate_exchange_request: FederationRequestValidator,
        make_transport_envelope: FederationEnvelopeMaker,
        validate_transport_envelope: FederationEnvelopeValidator,
        validate_exchange_result: FederationResultValidator,
        operation_profiles: Sequence[FederationOperationProfile],
    ) -> None:
        profiles: dict[str, FederationOperationProfile] = {}
        for profile in operation_profiles:
            if not isinstance(profile, FederationOperationProfile):
                raise TypeError("operation_profiles MUST contain FederationOperationProfile values")
            if profile.operation in profiles:
                raise ValueError(f"duplicate federation operation profile {profile.operation!r}")
            profiles[profile.operation] = profile
        if not profiles:
            raise ValueError("at least one federation operation profile is required")
        self._node = node
        self._validate_record = validate_record
        self._record_identity_text = record_identity_text
        self._validate_exchange_request = validate_exchange_request
        self._make_transport_envelope = make_transport_envelope
        self._validate_transport_envelope = validate_transport_envelope
        self._validate_exchange_result = validate_exchange_result
        self._profiles = profiles

    def prepare(self, request: Mapping[str, Any]) -> PreparedFederationExchange:
        """Validate and envelope a request without resolving or contacting its source."""
        normalized = self._validate_exchange_request(request)
        if not isinstance(normalized, Mapping):
            _fail("INVALID_REQUEST_VALIDATOR_RESULT", "federation request validator MUST return a mapping")
        operation = normalized.get("operation")
        profile = self._profiles.get(operation)
        if profile is None:
            _fail("UNCONFIGURED_FEDERATION_OPERATION", f"no runtime message profile for {operation!r}")
        required = normalized.get("required_capabilities")
        if not isinstance(required, (tuple, list)) or not all(isinstance(item, str) and item for item in required):
            _fail("INVALID_REQUEST_VALIDATOR_RESULT", "normalized required_capabilities MUST be text values")
        required_tuple = tuple(required)
        if len(required_tuple) != len(set(required_tuple)) or required_tuple != tuple(sorted(required_tuple, key=lambda item: item.encode("utf-8"))):
            _fail("INVALID_REQUEST_VALIDATOR_RESULT", "normalized required_capabilities MUST be sorted and unique")
        page_size = normalized.get("page_size")
        if (
            isinstance(page_size, bool)
            or not isinstance(page_size, int)
            or not 1 <= page_size <= MAX_OFFLINE_FEDERATION_PAGE_RECORDS
        ):
            _fail("INVALID_REQUEST_VALIDATOR_RESULT", "normalized page_size is outside the offline runtime bound")
        source = normalized.get("source")
        fingerprint = normalized.get("scope_fingerprint")
        if not isinstance(source, str) or not source or not isinstance(fingerprint, str) or not fingerprint:
            _fail("INVALID_REQUEST_VALIDATOR_RESULT", "normalized source/scope_fingerprint MUST be non-empty text")

        envelope_value = self._make_transport_envelope(profile.request_message_type, request)
        if not isinstance(envelope_value, (tuple, list)):
            _fail("INVALID_ENVELOPE_MAKER_RESULT", "transport envelope maker MUST return a sequence")
        envelope = tuple(envelope_value)
        return PreparedFederationExchange(
            binding=FederationRequestBinding(
                source=source,
                operation=operation,
                scope_fingerprint=fingerprint,
                required_capabilities=required_tuple,
                page_size=page_size,
                expected_result_message_type=profile.result_message_type,
            ),
            envelope=envelope,
        )

    def validate_page(
        self,
        prepared: PreparedFederationExchange,
        response_envelope: Sequence[Any],
    ) -> ValidatedFederationPage:
        """Validate page control/binding semantics without Record bodies or storage.

        The result is intentionally insufficient for local ingest. ``accept_page``
        re-runs this same validation before validating supplied Records and before
        the first repository mutation. This makes M28 pre-network page inspection
        possible without creating a second M8 interpretation path.
        """
        if not isinstance(prepared, PreparedFederationExchange):
            _fail("INVALID_PREPARED_EXCHANGE", "prepared exchange has the wrong type")
        binding = prepared.binding

        envelope_result = self._validate_transport_envelope(
            response_envelope,
            binding.expected_result_message_type,
        )
        if not isinstance(envelope_result, Mapping) or "payload" not in envelope_result:
            _fail("INVALID_ENVELOPE_VALIDATOR_RESULT", "transport envelope validator MUST return payload")
        payload = envelope_result["payload"]
        if not isinstance(payload, Mapping):
            _fail("INVALID_FEDERATION_RESULT_PAYLOAD", "federation result payload MUST be a mapping")
        normalized_result = self._validate_exchange_result(payload)
        if not isinstance(normalized_result, Mapping):
            _fail("INVALID_RESULT_VALIDATOR_RESULT", "federation result validator MUST return a mapping")

        if normalized_result.get("source") != binding.source:
            _fail("FEDERATION_SOURCE_MISMATCH", "response source does not match prepared request")
        if normalized_result.get("operation") != binding.operation:
            _fail("FEDERATION_OPERATION_MISMATCH", "response operation does not match prepared request")
        if normalized_result.get("scope_fingerprint") != binding.scope_fingerprint:
            _fail("FEDERATION_SCOPE_MISMATCH", "response scope fingerprint does not match prepared request")
        if normalized_result.get("global_completeness") != "UNKNOWN":
            _fail("FEDERATION_GLOBAL_COMPLETENESS_FORBIDDEN", "response validator MUST preserve global completeness UNKNOWN")
        if normalized_result.get("absence_is_deletion_evidence") is not False:
            _fail("FEDERATION_DELETION_INFERENCE_FORBIDDEN", "response absence MUST NOT become deletion evidence")

        result_ids_value = normalized_result.get("record_ids")
        if not isinstance(result_ids_value, (tuple, list)) or not all(
            isinstance(item, str) and item for item in result_ids_value
        ):
            _fail("INVALID_RESULT_VALIDATOR_RESULT", "normalized result record_ids MUST contain text values")
        result_ids = tuple(result_ids_value)
        if len(result_ids) != len(set(result_ids)) or result_ids != tuple(sorted(result_ids)):
            _fail("INVALID_RESULT_VALIDATOR_RESULT", "normalized result record_ids MUST be sorted and unique")
        if len(result_ids) > binding.page_size:
            _fail(
                "FEDERATION_PAGE_SIZE_EXCEEDED",
                "response contains more records than the prepared request page_size",
            )

        page_truncated = normalized_result.get("page_truncated")
        source_completeness = normalized_result.get("source_completeness")
        if not isinstance(page_truncated, bool) or not isinstance(source_completeness, str) or not source_completeness:
            _fail("INVALID_RESULT_VALIDATOR_RESULT", "normalized page controls are invalid")

        next_cursor: bytes | None = None
        cursor = payload.get("next_cursor")
        if page_truncated:
            if (
                not isinstance(cursor, bytes)
                or not 1 <= len(cursor) <= MAX_OFFLINE_FEDERATION_CURSOR_BYTES
            ):
                _fail("INVALID_FEDERATION_CURSOR", "truncated page cursor is outside the offline runtime bound")
            next_cursor = cursor
        elif cursor is not None:
            _fail("INVALID_FEDERATION_CURSOR", "final page MUST NOT carry a next cursor")

        return ValidatedFederationPage(
            source=binding.source,
            operation=binding.operation,
            scope_fingerprint=binding.scope_fingerprint,
            page_size=binding.page_size,
            record_ids=tuple(sorted(result_ids)),
            source_completeness=source_completeness,
            page_truncated=page_truncated,
            next_cursor=next_cursor,
        )

    def accept_page(
        self,
        prepared: PreparedFederationExchange,
        response_envelope: Sequence[Any],
        records: Iterable[Any],
    ) -> FederationPageOutcome:
        """Validate one supplied page completely before any local repository mutation."""
        validated = self.validate_page(prepared, response_envelope)

        supplied: dict[str, Any] = {}
        supplied_values = tuple(islice(records, validated.page_size + 1))
        if len(supplied_values) > validated.page_size:
            _fail(
                "FEDERATION_SUPPLIED_RECORD_LIMIT_EXCEEDED",
                "supplied response records exceed the prepared request page_size",
            )
        for record in supplied_values:
            self._validate_record(record)
            record_id = self._record_identity_text(record)
            if not isinstance(record_id, str) or not record_id:
                _fail("INVALID_IDENTITY_PROVIDER_RESULT", "record identity provider MUST return non-empty text")
            if record_id in supplied:
                if supplied[record_id] != record:
                    _fail(
                        "FEDERATION_IDENTITY_CONFLICT",
                        "same supplied Record Identity maps to different content",
                    )
                _fail("FEDERATION_DUPLICATE_SUPPLIED_RECORD", "response records repeat a Record Identity")
            supplied[record_id] = record

        result_ids = validated.record_ids
        if set(supplied) != set(result_ids) or len(supplied) != len(result_ids):
            missing = tuple(sorted(set(result_ids) - set(supplied)))
            unexpected = tuple(sorted(set(supplied) - set(result_ids)))
            _fail(
                "FEDERATION_RECORD_SET_MISMATCH",
                f"response record IDs and supplied records differ; missing={missing}, unexpected={unexpected}",
            )

        # All semantic, binding, resource, page-control, cursor, and identity
        # checks complete before the first local mutation. Repository/storage
        # failures are local runtime failures, not federation validation failures.
        stored: list[str] = []
        duplicates: list[str] = []
        for record_id in sorted(supplied):
            outcome = self._node.ingest(supplied[record_id])
            if outcome.record_id != record_id:
                _fail("IDENTITY_PROVIDER_DRIFT", "node ingest identity differs from prevalidated identity")
            if outcome.disposition == StoreDisposition.STORED:
                stored.append(record_id)
            elif outcome.disposition == StoreDisposition.DUPLICATE:
                duplicates.append(record_id)
            else:
                _fail("UNSUPPORTED_STORE_DISPOSITION", f"unsupported local store disposition {outcome.disposition!r}")

        return FederationPageOutcome(
            record_ids=result_ids,
            stored_record_ids=tuple(stored),
            duplicate_record_ids=tuple(duplicates),
            source_completeness=validated.source_completeness,
            page_truncated=validated.page_truncated,
            next_cursor=validated.next_cursor,
        )
