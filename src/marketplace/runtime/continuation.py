"""Transport-free one-step planning for an M8 federation continuation.

Milestone 29 turns one already validated truncated page into exactly one newly
prepared, unsent M8 exchange. Cursor bytes remain opaque and never become
network authority, completeness proof, discovery input, or loop permission.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from itertools import islice
from typing import Any, Final

from .contracts import (
    FederationCursorBinder,
    FederationCursorBindingValidator,
    FederationRequestValidator,
)
from .federation import (
    MAX_OFFLINE_FEDERATION_CURSOR_BYTES,
    MAX_OFFLINE_FEDERATION_PAGE_RECORDS,
    FederationRequestBinding,
    OfflineFederationService,
    PreparedFederationExchange,
    ValidatedFederationPage,
)

NO_CONTINUATION: Final = "NO_CONTINUATION"
CONTINUATION_PREPARED: Final = "PREPARED"
_MAX_HOST_SNAPSHOT_DEPTH: Final = 8
_MAX_HOST_SNAPSHOT_ITEMS: Final = 512


class FederationContinuationError(RuntimeError):
    """Fail-closed local M29 continuation-planning error."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def _fail(code: str, message: str) -> None:
    raise FederationContinuationError(code, message)


def _nested_code(exc: BaseException) -> str:
    code = getattr(exc, "code", None)
    return code if isinstance(code, str) and code else type(exc).__name__


def _exact_int(value: object, expected: int) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value == expected


def _snapshot_host_value(value: Any, *, code: str, depth: int = 0) -> Any:
    """Detach the small supported M8 host representation from mutable aliases.

    This is not a second M8 semantic validator. It only copies the concrete
    scalar/list/tuple/string-key-map shapes already accepted at this runtime
    boundary so injected helpers cannot silently mutate the planner's evidence.
    """
    if depth > _MAX_HOST_SNAPSHOT_DEPTH:
        _fail(code, "federation request host value exceeds the M29 snapshot depth bound")
    if value is None or isinstance(value, (bool, int, str, bytes)):
        return value
    if isinstance(value, tuple):
        if len(value) > _MAX_HOST_SNAPSHOT_ITEMS:
            _fail(code, "federation request tuple exceeds the M29 snapshot item bound")
        return tuple(
            _snapshot_host_value(item, code=code, depth=depth + 1)
            for item in value
        )
    if isinstance(value, list):
        if len(value) > _MAX_HOST_SNAPSHOT_ITEMS:
            _fail(code, "federation request list exceeds the M29 snapshot item bound")
        return [
            _snapshot_host_value(item, code=code, depth=depth + 1)
            for item in value
        ]
    if isinstance(value, Mapping):
        try:
            items = tuple(islice(value.items(), _MAX_HOST_SNAPSHOT_ITEMS + 1))
        except FederationContinuationError:
            raise
        except Exception as exc:
            _fail(code, f"federation request mapping snapshot failed: {type(exc).__name__}")
        if len(items) > _MAX_HOST_SNAPSHOT_ITEMS:
            _fail(code, "federation request mapping exceeds the M29 snapshot item bound")
        result: dict[str, Any] = {}
        for key, item in items:
            if not isinstance(key, str) or not key:
                _fail(code, "federation request mappings MUST use non-empty text keys")
            if key in result:
                _fail(code, "federation request mapping repeats a key during snapshot")
            result[key] = _snapshot_host_value(item, code=code, depth=depth + 1)
        return result
    _fail(code, f"unsupported federation request host value type {type(value).__name__}")


def _snapshot_mapping(value: Any, *, code: str) -> dict[str, Any]:
    snapshot = _snapshot_host_value(value, code=code)
    if not isinstance(snapshot, dict):
        _fail(code, "federation request host value MUST be a mapping")
    return snapshot


def _validate_raw_request_shape(value: Any) -> dict[str, Any]:
    request = _snapshot_mapping(value, code="INVALID_PRIOR_REQUEST")
    required = {"version", "source", "operation", "scope", "required_capabilities", "page_size"}
    allowed = required | {"cursor"}
    if set(request) - allowed or not required.issubset(request):
        _fail("INVALID_PRIOR_REQUEST", "prior federation request shape is invalid")
    if not _exact_int(request.get("version"), 1):
        _fail("INVALID_PRIOR_REQUEST", "prior federation request version MUST be exact integer 1")
    if not isinstance(request.get("source"), str) or not request["source"]:
        _fail("INVALID_PRIOR_REQUEST", "prior federation request source MUST be non-empty text")
    if not isinstance(request.get("operation"), str) or not request["operation"]:
        _fail("INVALID_PRIOR_REQUEST", "prior federation request operation MUST be non-empty text")
    if not isinstance(request.get("scope"), Mapping):
        _fail("INVALID_PRIOR_REQUEST", "prior federation request scope MUST be a mapping")
    required_caps = request.get("required_capabilities")
    if not isinstance(required_caps, (tuple, list)) or not required_caps or not all(
        isinstance(item, str) and item for item in required_caps
    ):
        _fail("INVALID_PRIOR_REQUEST", "prior federation request capabilities MUST be non-empty text values")
    page_size = request.get("page_size")
    if (
        isinstance(page_size, bool)
        or not isinstance(page_size, int)
        or not 1 <= page_size <= MAX_OFFLINE_FEDERATION_PAGE_RECORDS
    ):
        _fail("INVALID_PRIOR_REQUEST", "prior federation request page_size is outside the M8 runtime bound")
    if "cursor" in request:
        cursor = request["cursor"]
        if not isinstance(cursor, bytes) or not 1 <= len(cursor) <= MAX_OFFLINE_FEDERATION_CURSOR_BYTES:
            _fail("INVALID_PRIOR_REQUEST", "prior request cursor MUST be bounded opaque bytes")
    return request


def _normalized_request(value: Any) -> dict[str, Any]:
    normalized = _snapshot_mapping(value, code="INVALID_REQUEST_VALIDATOR_RESULT")
    required = {
        "version",
        "source",
        "operation",
        "scope",
        "scope_fingerprint",
        "required_capabilities",
        "page_size",
        "cursor_present",
    }
    if set(normalized) != required or not _exact_int(normalized.get("version"), 1):
        _fail("INVALID_REQUEST_VALIDATOR_RESULT", "normalized M8 request shape/version is invalid")
    if not isinstance(normalized.get("source"), str) or not normalized["source"]:
        _fail("INVALID_REQUEST_VALIDATOR_RESULT", "normalized request source MUST be non-empty text")
    if not isinstance(normalized.get("operation"), str) or not normalized["operation"]:
        _fail("INVALID_REQUEST_VALIDATOR_RESULT", "normalized request operation MUST be non-empty text")
    if not isinstance(normalized.get("scope"), Mapping):
        _fail("INVALID_REQUEST_VALIDATOR_RESULT", "normalized request scope MUST be a mapping")
    fingerprint = normalized.get("scope_fingerprint")
    if not isinstance(fingerprint, str) or not fingerprint:
        _fail("INVALID_REQUEST_VALIDATOR_RESULT", "normalized scope fingerprint MUST be non-empty text")
    capabilities = normalized.get("required_capabilities")
    if not isinstance(capabilities, tuple) or not capabilities or not all(
        isinstance(item, str) and item for item in capabilities
    ):
        _fail("INVALID_REQUEST_VALIDATOR_RESULT", "normalized capabilities MUST be a non-empty tuple of text")
    if len(capabilities) != len(set(capabilities)) or capabilities != tuple(
        sorted(capabilities, key=lambda item: item.encode("utf-8"))
    ):
        _fail("INVALID_REQUEST_VALIDATOR_RESULT", "normalized capabilities MUST be UTF-8 sorted and unique")
    page_size = normalized.get("page_size")
    if (
        isinstance(page_size, bool)
        or not isinstance(page_size, int)
        or not 1 <= page_size <= MAX_OFFLINE_FEDERATION_PAGE_RECORDS
    ):
        _fail("INVALID_REQUEST_VALIDATOR_RESULT", "normalized page_size is outside the M8 runtime bound")
    if not isinstance(normalized.get("cursor_present"), bool):
        _fail("INVALID_REQUEST_VALIDATOR_RESULT", "normalized cursor_present MUST be boolean")
    return normalized


def _validate_prepared(
    value: Any,
    *,
    expected_payload: Mapping[str, Any],
    code: str,
) -> PreparedFederationExchange:
    if not isinstance(value, PreparedFederationExchange):
        _fail(code, "prepared exchange has the wrong type")
    if not isinstance(value.binding, FederationRequestBinding):
        _fail(code, "prepared exchange binding has the wrong type")
    if value.transmitted is not False:
        _fail(code, "continuation planning requires an unsent prepared exchange")
    envelope = value.envelope
    if (
        not isinstance(envelope, tuple)
        or len(envelope) != 4
        or envelope[0] != "OLP-TRANSPORT"
        or not _exact_int(envelope[1], 1)
        or not isinstance(envelope[2], str)
        or not envelope[2]
    ):
        _fail(code, "prepared exchange envelope shape is invalid")
    payload_snapshot = _snapshot_mapping(envelope[3], code=code)
    if payload_snapshot != expected_payload:
        _fail(code, "prepared exchange envelope does not exactly bind the supplied request payload")
    return value


def _bind_normalized_to_prepared(
    normalized: Mapping[str, Any],
    prior_request: Mapping[str, Any],
    prepared: PreparedFederationExchange,
) -> None:
    binding = prepared.binding
    if normalized["source"] != binding.source:
        _fail("PRIOR_REQUEST_BINDING_MISMATCH", "normalized source differs from prepared binding")
    if normalized["operation"] != binding.operation:
        _fail("PRIOR_REQUEST_BINDING_MISMATCH", "normalized operation differs from prepared binding")
    if normalized["scope_fingerprint"] != binding.scope_fingerprint:
        _fail("PRIOR_REQUEST_BINDING_MISMATCH", "normalized scope fingerprint differs from prepared binding")
    if normalized["required_capabilities"] != binding.required_capabilities:
        _fail("PRIOR_REQUEST_BINDING_MISMATCH", "normalized capabilities differ from prepared binding")
    if normalized["page_size"] != binding.page_size:
        _fail("PRIOR_REQUEST_BINDING_MISMATCH", "normalized page_size differs from prepared binding")
    if normalized["cursor_present"] is not ("cursor" in prior_request):
        _fail("PRIOR_REQUEST_BINDING_MISMATCH", "normalized cursor presence differs from prior request")


def _bind_page_to_prepared(page: Any, prepared: PreparedFederationExchange) -> ValidatedFederationPage:
    if not isinstance(page, ValidatedFederationPage):
        _fail("INVALID_VALIDATED_PAGE", "validated page has the wrong type")
    binding = prepared.binding
    if page.source != binding.source:
        _fail("VALIDATED_PAGE_BINDING_MISMATCH", "validated page source differs from prepared binding")
    if page.operation != binding.operation:
        _fail("VALIDATED_PAGE_BINDING_MISMATCH", "validated page operation differs from prepared binding")
    if page.scope_fingerprint != binding.scope_fingerprint:
        _fail("VALIDATED_PAGE_BINDING_MISMATCH", "validated page scope differs from prepared binding")
    if page.page_size != binding.page_size:
        _fail("VALIDATED_PAGE_BINDING_MISMATCH", "validated page size differs from prepared binding")
    if not isinstance(page.page_truncated, bool):
        _fail("INVALID_VALIDATED_PAGE", "validated page truncation state MUST be boolean")
    if not isinstance(page.source_completeness, str) or not page.source_completeness:
        _fail("INVALID_VALIDATED_PAGE", "validated page source completeness MUST be non-empty text")
    if page.global_completeness != "UNKNOWN":
        _fail("VALIDATED_PAGE_AUTHORITY_ESCALATION", "validated page MUST preserve global completeness UNKNOWN")
    if page.absence_is_deletion_evidence is not False:
        _fail("VALIDATED_PAGE_AUTHORITY_ESCALATION", "validated page absence MUST NOT become deletion evidence")
    if page.creates_agreement is not False or page.authorizes_side_effects is not False:
        _fail("VALIDATED_PAGE_AUTHORITY_ESCALATION", "validated page MUST NOT create agreement or side-effect authority")
    cursor = page.next_cursor
    if page.page_truncated:
        if not isinstance(cursor, bytes) or not 1 <= len(cursor) <= MAX_OFFLINE_FEDERATION_CURSOR_BYTES:
            _fail("INVALID_VALIDATED_PAGE", "truncated validated page requires one bounded opaque cursor")
    elif cursor is not None:
        _fail("INVALID_VALIDATED_PAGE", "final validated page MUST NOT carry a continuation cursor")
    return page


@dataclass(frozen=True)
class ContinuationPlanOutcome:
    """One local planning outcome; cursor bytes are not duplicated here."""

    disposition: str
    prepared_exchange: PreparedFederationExchange | None
    prior_page_truncated: bool
    network_was_invoked: bool = False
    cursor_automatically_followed: bool = False
    authorization_established: bool = False
    source_completeness_established: bool = False
    global_completeness: str = "UNKNOWN"
    absence_is_deletion_evidence: bool = False
    creates_agreement: bool = False
    authorizes_side_effects: bool = False


class FederationContinuationPlanner:
    """Plan at most one unsent continuation from one validated M8 page."""

    def __init__(
        self,
        *,
        federation_service: OfflineFederationService,
        validate_exchange_request: FederationRequestValidator,
        bind_cursor: FederationCursorBinder,
        validate_cursor_binding: FederationCursorBindingValidator,
    ) -> None:
        if not isinstance(federation_service, OfflineFederationService):
            raise TypeError("federation_service MUST be OfflineFederationService")
        if not callable(validate_exchange_request):
            raise TypeError("validate_exchange_request MUST be callable")
        if not callable(bind_cursor):
            raise TypeError("bind_cursor MUST be callable")
        if not callable(validate_cursor_binding):
            raise TypeError("validate_cursor_binding MUST be callable")
        self._federation = federation_service
        self._validate_request = validate_exchange_request
        self._bind_cursor = bind_cursor
        self._validate_cursor_binding = validate_cursor_binding

    def plan(
        self,
        prior_request: Mapping[str, Any],
        prior_prepared: PreparedFederationExchange,
        validated_page: ValidatedFederationPage,
    ) -> ContinuationPlanOutcome:
        """Return NO_CONTINUATION or one exact newly prepared unsent exchange."""
        request = _validate_raw_request_shape(prior_request)
        prepared = _validate_prepared(
            prior_prepared,
            expected_payload=request,
            code="INVALID_PRIOR_PREPARED_EXCHANGE",
        )

        request_guard = _snapshot_mapping(request, code="INVALID_PRIOR_REQUEST")
        try:
            normalized_value = self._validate_request(request)
        except Exception as exc:
            _fail("PRIOR_REQUEST_VALIDATION_FAILED", f"M8 request validation failed: {_nested_code(exc)}")
        if request != request_guard:
            _fail("REQUEST_VALIDATOR_MUTATED_INPUT", "M8 request validator mutated the detached prior request")
        normalized = _normalized_request(normalized_value)
        _bind_normalized_to_prepared(normalized, request_guard, prepared)
        page = _bind_page_to_prepared(validated_page, prepared)

        if not page.page_truncated:
            return ContinuationPlanOutcome(
                disposition=NO_CONTINUATION,
                prepared_exchange=None,
                prior_page_truncated=False,
            )

        cursor = page.next_cursor
        if not isinstance(cursor, bytes):
            _fail("INVALID_VALIDATED_PAGE", "truncated validated page cursor type changed unexpectedly")
        scope = _snapshot_mapping(normalized["scope"], code="INVALID_REQUEST_VALIDATOR_RESULT")
        scope_guard = _snapshot_mapping(scope, code="INVALID_REQUEST_VALIDATOR_RESULT")
        try:
            cursor_binding = self._bind_cursor(
                normalized["source"],
                normalized["operation"],
                scope,
                cursor,
            )
        except Exception as exc:
            _fail("CURSOR_BINDING_FAILED", f"M8 cursor binding failed: {_nested_code(exc)}")
        if scope != scope_guard:
            _fail("CURSOR_HELPER_MUTATED_SCOPE", "M8 cursor binder mutated the detached normalized scope")
        try:
            cursor_validation_value = self._validate_cursor_binding(
                cursor_binding,
                normalized["source"],
                normalized["operation"],
                scope,
            )
        except Exception as exc:
            _fail("CURSOR_BINDING_VALIDATION_FAILED", f"M8 cursor validation failed: {_nested_code(exc)}")
        if scope != scope_guard:
            _fail("CURSOR_HELPER_MUTATED_SCOPE", "M8 cursor validator mutated the detached normalized scope")
        cursor_validation = _snapshot_mapping(
            cursor_validation_value,
            code="INVALID_CURSOR_VALIDATOR_RESULT",
        )
        expected_cursor_result_keys = {
            "status",
            "cursor_bytes",
            "authorization_proof",
            "source_completeness_proof",
        }
        if set(cursor_validation) != expected_cursor_result_keys:
            _fail("INVALID_CURSOR_VALIDATOR_RESULT", "cursor validator result shape is invalid")
        if cursor_validation.get("status") != "CURSOR_BOUND_TO_SOURCE_OPERATION_SCOPE":
            _fail("INVALID_CURSOR_VALIDATOR_RESULT", "cursor validator status is invalid")
        if not _exact_int(cursor_validation.get("cursor_bytes"), len(cursor)):
            _fail("INVALID_CURSOR_VALIDATOR_RESULT", "cursor validator byte count is invalid")
        if cursor_validation.get("authorization_proof") is not False:
            _fail("CURSOR_AUTHORITY_ESCALATION", "cursor binding MUST NOT establish authorization")
        if cursor_validation.get("source_completeness_proof") is not False:
            _fail("CURSOR_AUTHORITY_ESCALATION", "cursor binding MUST NOT establish source completeness")

        next_request = _snapshot_mapping(request_guard, code="INVALID_PRIOR_REQUEST")
        next_request["cursor"] = cursor
        next_request_guard = _snapshot_mapping(next_request, code="INVALID_PRIOR_REQUEST")
        try:
            next_prepared_value = self._federation.prepare(next_request)
        except Exception as exc:
            _fail("CONTINUATION_PREPARE_FAILED", f"continuation preparation failed: {_nested_code(exc)}")
        if next_request != next_request_guard:
            _fail("CONTINUATION_PREPARE_MUTATED_REQUEST", "continuation preparation mutated the detached next request")
        next_prepared = _validate_prepared(
            next_prepared_value,
            expected_payload=next_request_guard,
            code="INVALID_CONTINUATION_PREPARED_EXCHANGE",
        )
        if next_prepared.binding != prepared.binding:
            _fail("CONTINUATION_BINDING_DRIFT", "continuation preparation changed the prior request binding")
        if next_prepared.envelope[:3] != prepared.envelope[:3]:
            _fail("CONTINUATION_MESSAGE_PROFILE_DRIFT", "continuation preparation changed envelope marker/version/message type")

        prior_without_cursor = _snapshot_mapping(request_guard, code="INVALID_PRIOR_REQUEST")
        prior_without_cursor.pop("cursor", None)
        next_payload = _snapshot_mapping(
            next_prepared.envelope[3],
            code="INVALID_CONTINUATION_PREPARED_EXCHANGE",
        )
        next_without_cursor = dict(next_payload)
        next_without_cursor.pop("cursor", None)
        if next_without_cursor != prior_without_cursor:
            _fail("CONTINUATION_REQUEST_DRIFT", "continuation request changed fields other than cursor")
        if next_payload.get("cursor") != cursor:
            _fail("CONTINUATION_CURSOR_DRIFT", "continuation request did not preserve exact opaque cursor bytes")

        return ContinuationPlanOutcome(
            disposition=CONTINUATION_PREPARED,
            prepared_exchange=next_prepared,
            prior_page_truncated=True,
        )
