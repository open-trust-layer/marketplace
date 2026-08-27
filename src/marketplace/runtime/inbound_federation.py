"""Bounded transport-free inbound federation response preparation.

M32 validates one configured M8 snapshot/sync request, requires one explicit
local disclosure decision, materializes one bounded local page, and prepares one
immutable response envelope. It contains no listener, socket, HTTP/TLS server,
retry loop, scheduler, persistence, or transmission primitive.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any, Final

from .contracts import (
    FederationCapabilityNegotiator,
    FederationEnvelopeMaker,
    FederationEnvelopeValidator,
    FederationPageEvaluator,
    FederationRequestValidator,
    FederationResultValidator,
    FederationScopeFingerprintProvider,
    InboundFederationDisclosureAuthorizer,
    InboundFederationPageSource,
    RecordIdentityProvider,
    RecordValidator,
)
from .federation import FederationOperationProfile
from .prepared_integrity import (
    PreparedExchangeIntegrityError,
    detach_host_value,
    host_value_integrity_snapshot,
)

DEFAULT_MAX_INBOUND_PAGE_RECORDS: Final = 256
MAX_INBOUND_PAGE_RECORDS: Final = 10_000
MAX_INBOUND_CURSOR_BYTES: Final = 4_096


class InboundFederationError(RuntimeError):
    """Stable local failure for one M32 inbound preparation attempt."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def _fail(code: str, message: str) -> None:
    raise InboundFederationError(code, message)


def _detach(value: Any, *, code: str, label: str) -> Any:
    try:
        return detach_host_value(value)
    except PreparedExchangeIntegrityError as exc:
        _fail(code, f"{label} cannot be safely detached: {exc.code}")


@dataclass(frozen=True)
class InboundFederationRequestContext:
    """Immutable local interpretation of one validated inbound request."""

    source: str
    operation: str
    scope: Mapping[str, Any]
    scope_fingerprint: str
    required_capabilities: tuple[str, ...]
    page_size: int
    cursor: bytes | None
    request_message_type: str
    result_message_type: str
    request_authenticated: bool = field(default=False, init=False)
    peer_identity_proven: bool = field(default=False, init=False)
    authorizes_protected_side_effects: bool = field(default=False, init=False)

    def __post_init__(self) -> None:
        text_values = (
            self.source,
            self.operation,
            self.scope_fingerprint,
            self.request_message_type,
            self.result_message_type,
        )
        if any(type(value) is not str or not value for value in text_values):
            raise ValueError("inbound request context text fields MUST be non-empty exact strings")
        if (
            type(self.required_capabilities) is not tuple
            or not self.required_capabilities
            or not all(type(item) is str and item for item in self.required_capabilities)
            or self.required_capabilities
            != tuple(sorted(self.required_capabilities, key=lambda item: item.encode("utf-8")))
            or len(self.required_capabilities) != len(set(self.required_capabilities))
        ):
            raise ValueError("required_capabilities MUST be a sorted unique exact tuple of text")
        if type(self.page_size) is not int or not 1 <= self.page_size <= MAX_INBOUND_PAGE_RECORDS:
            raise ValueError("page_size is outside the inbound runtime bound")
        if self.cursor is not None and (
            type(self.cursor) is not bytes or not 1 <= len(self.cursor) <= MAX_INBOUND_CURSOR_BYTES
        ):
            raise ValueError("cursor MUST be bounded opaque exact bytes")
        detached_scope = detach_host_value(self.scope)
        if not isinstance(detached_scope, Mapping):
            raise ValueError("scope MUST be a mapping")
        object.__setattr__(self, "scope", detached_scope)


@dataclass(frozen=True)
class InboundFederationPageMaterial:
    """One authorized local page candidate before M8 semantic evaluation."""

    records: tuple[Any, ...]
    source_completeness: str
    page_truncated: bool
    next_cursor: bytes | None = None

    def __post_init__(self) -> None:
        if type(self.records) is not tuple:
            raise ValueError("records MUST be an exact tuple")
        if type(self.source_completeness) is not str or not self.source_completeness:
            raise ValueError("source_completeness MUST be non-empty exact text")
        if type(self.page_truncated) is not bool:
            raise ValueError("page_truncated MUST be exact boolean")
        if self.page_truncated:
            if (
                type(self.next_cursor) is not bytes
                or not 1 <= len(self.next_cursor) <= MAX_INBOUND_CURSOR_BYTES
            ):
                raise ValueError("a truncated page requires one bounded opaque next cursor")
        elif self.next_cursor is not None:
            raise ValueError("a final page MUST NOT contain a next cursor")


def _context_snapshot(context: InboundFederationRequestContext) -> tuple[Any, ...]:
    return (
        "inbound-federation-request-context-v1",
        context.source,
        context.operation,
        host_value_integrity_snapshot(context.scope),
        context.scope_fingerprint,
        context.required_capabilities,
        context.page_size,
        context.cursor,
        context.request_message_type,
        context.result_message_type,
    )


@dataclass(frozen=True)
class PreparedInboundFederationResponse:
    """One deeply detached, authorized-but-unsent M8 control response."""

    request_context: InboundFederationRequestContext
    envelope: tuple[Any, ...]
    record_ids: tuple[str, ...]
    source_completeness: str
    page_truncated: bool
    next_cursor: bytes | None
    integrity_snapshot: tuple[Any, ...] | None = field(default=None, repr=False)
    transmitted: bool = field(default=False, init=False)
    request_authenticated: bool = field(default=False, init=False)
    peer_identity_proven: bool = field(default=False, init=False)
    global_completeness: str = field(default="UNKNOWN", init=False)
    absence_is_deletion_evidence: bool = field(default=False, init=False)
    creates_agreement: bool = field(default=False, init=False)
    establishes_truth: bool = field(default=False, init=False)
    establishes_trust: bool = field(default=False, init=False)
    authorizes_protected_side_effects: bool = field(default=False, init=False)

    def __post_init__(self) -> None:
        if type(self.request_context) is not InboundFederationRequestContext:
            raise ValueError("request_context has the wrong type")
        if (
            type(self.record_ids) is not tuple
            or not all(type(item) is str and item for item in self.record_ids)
            or self.record_ids != tuple(sorted(self.record_ids))
            or len(self.record_ids) != len(set(self.record_ids))
        ):
            raise ValueError("record_ids MUST be a sorted unique exact tuple of text")
        if type(self.source_completeness) is not str or not self.source_completeness:
            raise ValueError("source_completeness MUST be non-empty exact text")
        if type(self.page_truncated) is not bool:
            raise ValueError("page_truncated MUST be exact boolean")
        if self.page_truncated:
            if (
                type(self.next_cursor) is not bytes
                or not 1 <= len(self.next_cursor) <= MAX_INBOUND_CURSOR_BYTES
            ):
                raise ValueError("a truncated response requires one bounded opaque next cursor")
        elif self.next_cursor is not None:
            raise ValueError("a final response MUST NOT contain a next cursor")
        detached_envelope = detach_host_value(self.envelope)
        if type(detached_envelope) is not tuple or len(detached_envelope) != 4:
            raise ValueError("prepared inbound response envelope MUST be one exact four-element tuple")
        current = (
            "prepared-inbound-federation-response-v1",
            _context_snapshot(self.request_context),
            self.record_ids,
            self.source_completeness,
            self.page_truncated,
            self.next_cursor,
            host_value_integrity_snapshot(detached_envelope),
        )
        if self.integrity_snapshot is not None and self.integrity_snapshot != current:
            raise ValueError("prepared inbound response integrity snapshot mismatch")
        object.__setattr__(self, "envelope", detached_envelope)
        if self.integrity_snapshot is None:
            object.__setattr__(self, "integrity_snapshot", current)


class BoundedInboundFederationResponder:
    """Prepare exactly one locally authorized M8 response without transmitting it."""

    def __init__(
        self,
        *,
        local_source: str,
        validate_transport_envelope: FederationEnvelopeValidator,
        validate_exchange_request: FederationRequestValidator,
        scope_fingerprint: FederationScopeFingerprintProvider,
        negotiate_capabilities: FederationCapabilityNegotiator,
        capability_advertisement: Mapping[str, Any],
        evaluate_exchange_page: FederationPageEvaluator,
        validate_exchange_result: FederationResultValidator,
        make_transport_envelope: FederationEnvelopeMaker,
        validate_record: RecordValidator,
        record_identity_text: RecordIdentityProvider,
        authorize_disclosure: InboundFederationDisclosureAuthorizer,
        page_source: InboundFederationPageSource,
        operation_profiles: tuple[FederationOperationProfile, ...],
        max_page_records: int = DEFAULT_MAX_INBOUND_PAGE_RECORDS,
    ) -> None:
        if type(local_source) is not str or not local_source:
            raise ValueError("local_source MUST be non-empty exact text")
        if type(max_page_records) is not int or not 1 <= max_page_records <= MAX_INBOUND_PAGE_RECORDS:
            raise ValueError("max_page_records is outside the inbound runtime bound")
        if type(operation_profiles) is not tuple or not operation_profiles:
            raise ValueError("operation_profiles MUST be a non-empty exact tuple")
        profiles: dict[str, FederationOperationProfile] = {}
        for profile in operation_profiles:
            if type(profile) is not FederationOperationProfile:
                raise ValueError("operation_profiles MUST contain exact FederationOperationProfile values")
            if profile.operation in profiles:
                raise ValueError(f"duplicate inbound federation operation profile {profile.operation!r}")
            profiles[profile.operation] = profile

        try:
            detached_advertisement = detach_host_value(capability_advertisement)
        except PreparedExchangeIntegrityError as exc:
            raise ValueError(f"capability_advertisement cannot be safely detached: {exc.code}") from exc
        if not isinstance(detached_advertisement, Mapping):
            raise ValueError("capability_advertisement MUST be a mapping")
        if detached_advertisement.get("source") != local_source:
            raise ValueError("capability_advertisement source MUST equal local_source")
        limits = detached_advertisement.get("limits")
        if not isinstance(limits, Mapping):
            raise ValueError("capability_advertisement limits MUST be a mapping")
        advertised_page_limit = limits.get("max_page_records")
        advertised_cursor_limit = limits.get("max_cursor_bytes")
        if (
            type(advertised_page_limit) is not int
            or not 1 <= advertised_page_limit <= MAX_INBOUND_PAGE_RECORDS
        ):
            raise ValueError("capability_advertisement max_page_records is outside the M8 bound")
        if (
            type(advertised_cursor_limit) is not int
            or not 1 <= advertised_cursor_limit <= MAX_INBOUND_CURSOR_BYTES
        ):
            raise ValueError("capability_advertisement max_cursor_bytes is outside the M8 bound")
        if max_page_records > advertised_page_limit:
            raise ValueError("max_page_records MUST NOT exceed the local advertised page limit")

        self._local_source = local_source
        self._validate_transport_envelope = validate_transport_envelope
        self._validate_exchange_request = validate_exchange_request
        self._scope_fingerprint = scope_fingerprint
        self._negotiate_capabilities = negotiate_capabilities
        self._capability_advertisement = detached_advertisement
        self._advertised_cursor_limit = advertised_cursor_limit
        self._evaluate_exchange_page = evaluate_exchange_page
        self._validate_exchange_result = validate_exchange_result
        self._make_transport_envelope = make_transport_envelope
        self._validate_record = validate_record
        self._record_identity_text = record_identity_text
        self._authorize_disclosure = authorize_disclosure
        self._page_source = page_source
        self._profiles = profiles
        self._max_page_records = max_page_records

    @property
    def local_source(self) -> str:
        return self._local_source

    @property
    def max_page_records(self) -> int:
        return self._max_page_records

    def _validate_envelope_result(
        self,
        result: Any,
        *,
        expected_message_type: str,
        expected_payload: Any | None = None,
    ) -> Mapping[str, Any]:
        expected_keys = {
            "message_type",
            "payload",
            "transport_defines_record_identity",
            "transport_authentication_is_object_proof",
        }
        if type(result) is not dict or set(result) != expected_keys:
            _fail("INVALID_ENVELOPE_VALIDATOR_RESULT", "envelope validator returned an unexpected shape")
        if result["message_type"] != expected_message_type:
            _fail("ENVELOPE_MESSAGE_PROFILE_DRIFT", "envelope validator changed the configured message type")
        if result["transport_defines_record_identity"] is not False:
            _fail("TRANSPORT_IDENTITY_AUTHORITY_FORBIDDEN", "transport cannot define Record Identity")
        if result["transport_authentication_is_object_proof"] is not False:
            _fail("TRANSPORT_OBJECT_PROOF_FORBIDDEN", "transport authentication cannot become object proof")
        payload = result["payload"]
        if not isinstance(payload, Mapping):
            _fail("INVALID_FEDERATION_REQUEST_PAYLOAD", "validated transport payload MUST be a mapping")
        if expected_payload is not None:
            try:
                if host_value_integrity_snapshot(payload) != host_value_integrity_snapshot(expected_payload):
                    _fail("ENVELOPE_VALIDATOR_PAYLOAD_DRIFT", "envelope validator changed the transport payload")
            except PreparedExchangeIntegrityError as exc:
                _fail("ENVELOPE_VALIDATOR_PAYLOAD_UNSAFE", f"validated payload is unsafe: {exc.code}")
        return result

    def _scope_fingerprint_value(self, scope: Any, *, code: str, label: str) -> str:
        try:
            fingerprint = self._scope_fingerprint(scope)
        except Exception as exc:
            _fail(code, f"{label} fingerprint failed: {type(exc).__name__}")
        if type(fingerprint) is not str or not fingerprint:
            _fail(code, f"{label} fingerprint provider MUST return non-empty exact text")
        return fingerprint

    def _normalize_request(
        self,
        payload: Mapping[str, Any],
        *,
        profile: FederationOperationProfile,
    ) -> InboundFederationRequestContext:
        raw_scope = payload.get("scope")
        raw_scope_fingerprint = self._scope_fingerprint_value(
            raw_scope,
            code="RAW_SCOPE_FINGERPRINT_FAILED",
            label="raw request scope",
        )
        try:
            normalized = self._validate_exchange_request(payload)
        except Exception as exc:
            _fail("REQUEST_VALIDATION_FAILED", f"M8 request validation failed: {type(exc).__name__}")
        expected_keys = {
            "version",
            "source",
            "operation",
            "scope",
            "scope_fingerprint",
            "required_capabilities",
            "page_size",
            "cursor_present",
        }
        if type(normalized) is not dict or set(normalized) != expected_keys:
            _fail("INVALID_REQUEST_VALIDATOR_RESULT", "request validator returned an unexpected shape")
        if type(normalized["version"]) is not int or normalized["version"] != 1:
            _fail("INVALID_REQUEST_VALIDATOR_RESULT", "normalized request version MUST be exact integer 1")
        source = normalized["source"]
        operation = normalized["operation"]
        fingerprint = normalized["scope_fingerprint"]
        if any(type(item) is not str or not item for item in (source, operation, fingerprint)):
            _fail("INVALID_REQUEST_VALIDATOR_RESULT", "normalized request binding text is invalid")
        if operation != profile.operation:
            _fail("REQUEST_OPERATION_PROFILE_MISMATCH", "normalized request operation does not match configured profile")
        if source != self._local_source:
            _fail("REQUEST_SOURCE_MISMATCH", "inbound request source does not match the configured local source")

        normalized_scope_fingerprint = self._scope_fingerprint_value(
            normalized["scope"],
            code="NORMALIZED_SCOPE_FINGERPRINT_FAILED",
            label="normalized request scope",
        )
        if raw_scope_fingerprint != fingerprint or normalized_scope_fingerprint != fingerprint:
            _fail(
                "REQUEST_SCOPE_NORMALIZATION_DRIFT",
                "raw scope, normalized scope, and normalized scope fingerprint are not the same M8 scope",
            )

        capabilities_value = normalized["required_capabilities"]
        if not isinstance(capabilities_value, (tuple, list)):
            _fail("INVALID_REQUEST_VALIDATOR_RESULT", "normalized required_capabilities MUST be a sequence")
        capabilities = tuple(capabilities_value)
        if (
            not capabilities
            or not all(type(item) is str and item for item in capabilities)
            or capabilities != tuple(sorted(capabilities, key=lambda item: item.encode("utf-8")))
            or len(capabilities) != len(set(capabilities))
        ):
            _fail("INVALID_REQUEST_VALIDATOR_RESULT", "normalized required_capabilities are not canonical")

        page_size = normalized["page_size"]
        if type(page_size) is not int or not 1 <= page_size <= MAX_INBOUND_PAGE_RECORDS:
            _fail("INVALID_REQUEST_VALIDATOR_RESULT", "normalized page_size is outside the M8 runtime bound")
        if page_size > self._max_page_records:
            _fail("LOCAL_PAGE_LIMIT_EXCEEDED", "request page_size exceeds the configured local inbound limit")

        cursor_present = normalized["cursor_present"]
        if type(cursor_present) is not bool:
            _fail("INVALID_REQUEST_VALIDATOR_RESULT", "normalized cursor_present MUST be exact boolean")
        cursor = payload.get("cursor")
        if cursor is not None and (
            type(cursor) is not bytes or not 1 <= len(cursor) <= MAX_INBOUND_CURSOR_BYTES
        ):
            _fail("INVALID_REQUEST_CURSOR", "request cursor is outside the inbound runtime bound")
        if cursor is not None and len(cursor) > self._advertised_cursor_limit:
            _fail("LOCAL_CURSOR_LIMIT_EXCEEDED", "request cursor exceeds the local advertised cursor limit")
        if cursor_present is not (cursor is not None):
            _fail("REQUEST_CURSOR_NORMALIZATION_DRIFT", "normalized cursor presence differs from request payload")

        for key, expected in (
            ("source", source),
            ("operation", operation),
            ("page_size", page_size),
        ):
            if payload.get(key) != expected:
                _fail("REQUEST_BINDING_NORMALIZATION_DRIFT", f"normalized {key} differs from request payload")
        raw_capabilities = payload.get("required_capabilities")
        if not isinstance(raw_capabilities, (tuple, list)) or tuple(raw_capabilities) != capabilities:
            _fail("REQUEST_BINDING_NORMALIZATION_DRIFT", "normalized capabilities differ from request payload")

        scope = _detach(normalized["scope"], code="INVALID_NORMALIZED_SCOPE", label="normalized scope")
        if not isinstance(scope, Mapping):
            _fail("INVALID_NORMALIZED_SCOPE", "normalized scope MUST be a mapping")
        try:
            return InboundFederationRequestContext(
                source=source,
                operation=operation,
                scope=scope,
                scope_fingerprint=fingerprint,
                required_capabilities=capabilities,
                page_size=page_size,
                cursor=cursor,
                request_message_type=profile.request_message_type,
                result_message_type=profile.result_message_type,
            )
        except (ValueError, PreparedExchangeIntegrityError) as exc:
            _fail("INVALID_REQUEST_CONTEXT", f"cannot construct immutable request context: {type(exc).__name__}")

    def _require_local_capabilities(self, context: InboundFederationRequestContext) -> None:
        try:
            result = self._negotiate_capabilities(
                self._capability_advertisement,
                context.required_capabilities,
            )
        except Exception as exc:
            _fail("CAPABILITY_NEGOTIATION_FAILED", f"M8 capability negotiation failed: {type(exc).__name__}")
        expected_keys = {
            "status",
            "required_capabilities",
            "unsupported_capabilities",
            "unavailable_capabilities",
            "no_silent_downgrade",
        }
        if type(result) is not dict or set(result) != expected_keys:
            _fail("INVALID_CAPABILITY_NEGOTIATOR_RESULT", "capability negotiator returned an unexpected shape")
        required = result["required_capabilities"]
        unsupported = result["unsupported_capabilities"]
        unavailable = result["unavailable_capabilities"]
        if not isinstance(required, (tuple, list)) or tuple(required) != context.required_capabilities:
            _fail("CAPABILITY_NEGOTIATOR_BINDING_DRIFT", "capability negotiator changed required capabilities")
        if not isinstance(unsupported, (tuple, list)) or not isinstance(unavailable, (tuple, list)):
            _fail("INVALID_CAPABILITY_NEGOTIATOR_RESULT", "capability negotiation sets MUST be sequences")
        if result["no_silent_downgrade"] is not True:
            _fail("CAPABILITY_SILENT_DOWNGRADE_FORBIDDEN", "capability negotiation MUST preserve no-silent-downgrade")
        if result["status"] != "SUPPORTED" or tuple(unsupported) or tuple(unavailable):
            _fail("REQUIRED_CAPABILITY_UNAVAILABLE", "required inbound federation capabilities are not locally available")

    def _canonical_records(self, records: tuple[Any, ...]) -> tuple[tuple[Any, ...], tuple[str, ...]]:
        by_identity: dict[str, Any] = {}
        for record in records:
            try:
                self._validate_record(record)
            except Exception as exc:
                _fail("INVALID_PAGE_RECORD", f"selected Record failed validation: {type(exc).__name__}")
            try:
                record_id = self._record_identity_text(record)
            except Exception as exc:
                _fail("RECORD_IDENTITY_FAILED", f"selected Record identity failed: {type(exc).__name__}")
            if type(record_id) is not str or not record_id:
                _fail("INVALID_RECORD_IDENTITY_RESULT", "Record identity provider MUST return non-empty exact text")
            if record_id in by_identity:
                _fail("DUPLICATE_PAGE_RECORD_ID", "selected page repeats a Record Identity")
            by_identity[record_id] = record
        record_ids = tuple(sorted(by_identity))
        return tuple(by_identity[record_id] for record_id in record_ids), record_ids

    def _validate_page_evaluation(
        self,
        evaluation: Any,
        *,
        context: InboundFederationRequestContext,
        material: InboundFederationPageMaterial,
        record_ids: tuple[str, ...],
    ) -> None:
        expected_keys = {
            "source",
            "operation",
            "scope_fingerprint",
            "record_ids",
            "record_count",
            "duplicate_record_count",
            "source_completeness",
            "page_truncated",
            "next_cursor_present",
            "global_completeness",
            "absence_is_deletion_evidence",
            "ordering",
        }
        if type(evaluation) is not dict or set(evaluation) != expected_keys:
            _fail("INVALID_PAGE_EVALUATOR_RESULT", "page evaluator returned an unexpected shape")
        if evaluation["source"] != context.source:
            _fail("PAGE_SOURCE_BINDING_DRIFT", "page evaluator changed source")
        if evaluation["operation"] != context.operation:
            _fail("PAGE_OPERATION_BINDING_DRIFT", "page evaluator changed operation")
        if evaluation["scope_fingerprint"] != context.scope_fingerprint:
            _fail("PAGE_SCOPE_BINDING_DRIFT", "page evaluator changed scope fingerprint")
        evaluated_ids = evaluation["record_ids"]
        if not isinstance(evaluated_ids, (tuple, list)) or tuple(evaluated_ids) != record_ids:
            _fail("PAGE_RECORD_ID_DRIFT", "page evaluator Record IDs differ from selected Records")
        if type(evaluation["record_count"]) is not int or evaluation["record_count"] != len(record_ids):
            _fail("INVALID_PAGE_EVALUATOR_RESULT", "page evaluator record_count is invalid")
        if type(evaluation["duplicate_record_count"]) is not int or evaluation["duplicate_record_count"] != 0:
            _fail("INVALID_PAGE_EVALUATOR_RESULT", "page evaluator duplicate count is invalid")
        if evaluation["source_completeness"] != material.source_completeness:
            _fail("PAGE_COMPLETENESS_DRIFT", "page evaluator changed source completeness")
        if evaluation["page_truncated"] is not material.page_truncated:
            _fail("PAGE_TRUNCATION_DRIFT", "page evaluator changed truncation state")
        if evaluation["next_cursor_present"] is not (material.next_cursor is not None):
            _fail("PAGE_CURSOR_DRIFT", "page evaluator changed next-cursor presence")
        if evaluation["global_completeness"] != "UNKNOWN":
            _fail("GLOBAL_COMPLETENESS_FORBIDDEN", "page evaluator cannot establish global completeness")
        if evaluation["absence_is_deletion_evidence"] is not False:
            _fail("DELETION_INFERENCE_FORBIDDEN", "page absence cannot become deletion evidence")
        if evaluation["ordering"] != "REPRODUCIBLE_IDENTITY_ORDER_NOT_CHRONOLOGY":
            _fail("PAGE_ORDERING_DRIFT", "page evaluator changed the M8 ordering meaning")

    def _validate_result_normalization(
        self,
        normalized: Any,
        *,
        context: InboundFederationRequestContext,
        material: InboundFederationPageMaterial,
        record_ids: tuple[str, ...],
    ) -> None:
        expected_keys = {
            "version",
            "source",
            "operation",
            "scope_fingerprint",
            "record_ids",
            "source_completeness",
            "page_truncated",
            "next_cursor_present",
            "global_completeness",
            "absence_is_deletion_evidence",
        }
        if type(normalized) is not dict or set(normalized) != expected_keys:
            _fail("INVALID_RESULT_VALIDATOR_RESULT", "result validator returned an unexpected shape")
        if type(normalized["version"]) is not int or normalized["version"] != 1:
            _fail("INVALID_RESULT_VALIDATOR_RESULT", "normalized response version MUST be exact integer 1")
        if normalized["source"] != context.source:
            _fail("RESULT_SOURCE_BINDING_DRIFT", "result validator changed source")
        if normalized["operation"] != context.operation:
            _fail("RESULT_OPERATION_BINDING_DRIFT", "result validator changed operation")
        if normalized["scope_fingerprint"] != context.scope_fingerprint:
            _fail("RESULT_SCOPE_BINDING_DRIFT", "result validator changed scope fingerprint")
        normalized_ids = normalized["record_ids"]
        if not isinstance(normalized_ids, (tuple, list)) or tuple(normalized_ids) != record_ids:
            _fail("RESULT_RECORD_ID_DRIFT", "result validator changed Record IDs")
        if normalized["source_completeness"] != material.source_completeness:
            _fail("RESULT_COMPLETENESS_DRIFT", "result validator changed source completeness")
        if normalized["page_truncated"] is not material.page_truncated:
            _fail("RESULT_TRUNCATION_DRIFT", "result validator changed truncation state")
        if normalized["next_cursor_present"] is not (material.next_cursor is not None):
            _fail("RESULT_CURSOR_DRIFT", "result validator changed next-cursor presence")
        if normalized["global_completeness"] != "UNKNOWN":
            _fail("GLOBAL_COMPLETENESS_FORBIDDEN", "result validator cannot establish global completeness")
        if normalized["absence_is_deletion_evidence"] is not False:
            _fail("DELETION_INFERENCE_FORBIDDEN", "result validator cannot infer deletion from absence")

    def prepare_response(
        self,
        request_envelope: Sequence[Any],
        *,
        operation: str,
    ) -> PreparedInboundFederationResponse:
        """Prepare one authorized-but-unsent response page and stop."""
        if type(operation) is not str or not operation:
            _fail("INVALID_OPERATION_SELECTION", "operation selection MUST be non-empty exact text")
        profile = self._profiles.get(operation)
        if profile is None:
            _fail("UNCONFIGURED_FEDERATION_OPERATION", "no inbound profile is configured for the selected operation")
        if type(request_envelope) not in (tuple, list):
            _fail("INVALID_REQUEST_ENVELOPE", "request envelope MUST be one exact tuple/list host value")
        detached_envelope = _detach(request_envelope, code="INVALID_REQUEST_ENVELOPE", label="request envelope")
        if not isinstance(detached_envelope, (tuple, list)) or len(detached_envelope) != 4:
            _fail("INVALID_REQUEST_ENVELOPE", "request envelope MUST contain exactly four elements")

        try:
            envelope_result = self._validate_transport_envelope(
                detached_envelope,
                profile.request_message_type,
            )
        except Exception as exc:
            _fail("REQUEST_ENVELOPE_VALIDATION_FAILED", f"M8 envelope validation failed: {type(exc).__name__}")
        validated_envelope = self._validate_envelope_result(
            envelope_result,
            expected_message_type=profile.request_message_type,
            expected_payload=detached_envelope[3],
        )
        payload = _detach(
            validated_envelope["payload"],
            code="INVALID_FEDERATION_REQUEST_PAYLOAD",
            label="request payload",
        )
        if not isinstance(payload, Mapping):
            _fail("INVALID_FEDERATION_REQUEST_PAYLOAD", "request payload MUST be a mapping")
        context = self._normalize_request(payload, profile=profile)
        self._require_local_capabilities(context)

        try:
            disclosure_decision = self._authorize_disclosure(context)
        except Exception as exc:
            _fail("DISCLOSURE_AUTHORIZER_FAILED", f"local disclosure authorizer failed: {type(exc).__name__}")
        if type(disclosure_decision) is not bool:
            _fail("INVALID_DISCLOSURE_AUTHORIZER_RESULT", "local disclosure authorizer MUST return exact boolean")
        if disclosure_decision is not True:
            _fail("DISCLOSURE_DENIED", "local disclosure policy denied the inbound request")

        try:
            material = self._page_source(context)
        except Exception as exc:
            _fail("PAGE_SOURCE_FAILED", f"inbound page source failed: {type(exc).__name__}")
        if type(material) is not InboundFederationPageMaterial:
            _fail("INVALID_PAGE_SOURCE_RESULT", "page source MUST return exact InboundFederationPageMaterial")
        if type(material.records) is not tuple:
            _fail("INVALID_PAGE_SOURCE_RESULT", "page source Records MUST be an exact tuple")
        if len(material.records) > context.page_size or len(material.records) > self._max_page_records:
            _fail("PAGE_RECORD_LIMIT_EXCEEDED", "page source returned more Records than the authorized page bound")
        if type(material.page_truncated) is not bool:
            _fail("INVALID_PAGE_SOURCE_RESULT", "page_truncated MUST be exact boolean")
        if type(material.source_completeness) is not str or not material.source_completeness:
            _fail("INVALID_PAGE_SOURCE_RESULT", "source_completeness MUST be non-empty exact text")
        if material.page_truncated:
            if (
                type(material.next_cursor) is not bytes
                or not 1 <= len(material.next_cursor) <= MAX_INBOUND_CURSOR_BYTES
            ):
                _fail("INVALID_PAGE_CURSOR", "truncated response requires one bounded opaque next cursor")
            if len(material.next_cursor) > self._advertised_cursor_limit:
                _fail("LOCAL_CURSOR_LIMIT_EXCEEDED", "next cursor exceeds the local advertised cursor limit")
        elif material.next_cursor is not None:
            _fail("INVALID_PAGE_CURSOR", "final response MUST NOT contain a next cursor")

        canonical_records, record_ids = self._canonical_records(material.records)
        try:
            page_evaluation = self._evaluate_exchange_page(
                canonical_records,
                source=context.source,
                operation=context.operation,
                scope=context.scope,
                completeness=material.source_completeness,
                has_more=material.page_truncated,
                next_cursor=material.next_cursor,
                max_records=context.page_size,
            )
        except Exception as exc:
            _fail("PAGE_EVALUATION_FAILED", f"M8 page evaluation failed: {type(exc).__name__}")
        self._validate_page_evaluation(
            page_evaluation,
            context=context,
            material=material,
            record_ids=record_ids,
        )

        # The evaluator is an injected helper that sees Record objects. Re-run
        # validation/identity afterward so helper-side mutation cannot silently
        # change the selected Record set after the IDs were bound.
        _, post_evaluation_ids = self._canonical_records(canonical_records)
        if post_evaluation_ids != record_ids:
            _fail("PAGE_RECORD_MUTATION_DETECTED", "selected Records changed during page evaluation")

        response_payload: dict[str, Any] = {
            "version": 1,
            "source": context.source,
            "operation": context.operation,
            "scope_fingerprint": context.scope_fingerprint,
            "record_ids": record_ids,
            "source_completeness": material.source_completeness,
            "page_truncated": material.page_truncated,
        }
        if material.page_truncated:
            response_payload["next_cursor"] = material.next_cursor
        detached_payload = _detach(
            response_payload,
            code="INVALID_RESPONSE_PAYLOAD",
            label="response payload",
        )
        payload_snapshot = host_value_integrity_snapshot(detached_payload)

        try:
            normalized_result = self._validate_exchange_result(detached_payload)
        except Exception as exc:
            _fail("RESULT_VALIDATION_FAILED", f"M8 result validation failed: {type(exc).__name__}")
        self._validate_result_normalization(
            normalized_result,
            context=context,
            material=material,
            record_ids=record_ids,
        )
        if host_value_integrity_snapshot(detached_payload) != payload_snapshot:
            _fail("RESULT_VALIDATOR_MUTATED_PAYLOAD", "result validator mutated the detached response payload")

        try:
            envelope_value = self._make_transport_envelope(
                profile.result_message_type,
                detached_payload,
            )
        except Exception as exc:
            _fail("RESPONSE_ENVELOPE_CREATION_FAILED", f"M8 envelope creation failed: {type(exc).__name__}")
        if host_value_integrity_snapshot(detached_payload) != payload_snapshot:
            _fail("ENVELOPE_MAKER_MUTATED_PAYLOAD", "envelope maker mutated the detached response payload")
        if type(envelope_value) not in (tuple, list) or len(envelope_value) != 4:
            _fail("INVALID_ENVELOPE_MAKER_RESULT", "envelope maker returned an invalid host shape")
        detached_response_value = _detach(
            envelope_value,
            code="INVALID_RESPONSE_ENVELOPE",
            label="response envelope",
        )
        response_envelope = tuple(detached_response_value)
        if (
            response_envelope[0] != "OLP-TRANSPORT"
            or type(response_envelope[1]) is not int
            or response_envelope[1] != 1
            or response_envelope[2] != profile.result_message_type
        ):
            _fail("RESPONSE_ENVELOPE_PROFILE_DRIFT", "response envelope marker/version/message profile is invalid")
        if host_value_integrity_snapshot(response_envelope[3]) != payload_snapshot:
            _fail("RESPONSE_ENVELOPE_PAYLOAD_DRIFT", "response envelope payload differs from validated result")

        try:
            response_validation = self._validate_transport_envelope(
                response_envelope,
                profile.result_message_type,
            )
        except Exception as exc:
            _fail("RESPONSE_ENVELOPE_VALIDATION_FAILED", f"M8 response envelope validation failed: {type(exc).__name__}")
        self._validate_envelope_result(
            response_validation,
            expected_message_type=profile.result_message_type,
            expected_payload=detached_payload,
        )

        try:
            return PreparedInboundFederationResponse(
                request_context=context,
                envelope=response_envelope,
                record_ids=record_ids,
                source_completeness=material.source_completeness,
                page_truncated=material.page_truncated,
                next_cursor=material.next_cursor,
            )
        except (ValueError, PreparedExchangeIntegrityError) as exc:
            _fail("INVALID_PREPARED_RESPONSE", f"cannot construct immutable prepared response: {type(exc).__name__}")
