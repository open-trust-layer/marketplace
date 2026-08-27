"""Bounded transport-free preparation of one inbound immutable Record response.

M33 is the server-side counterpart to M27 retrieval, but stops before transport.
A canonical Record Identity is never treated as disclosure authority. One explicit
local authorization decision MUST succeed before one exact local Record lookup.
"""
from __future__ import annotations

import base64
import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any, Final

from .contracts import (
    ExactRecordSource,
    InboundRecordDisclosureAuthorizer,
    RecordEnvelopePayloadProvider,
    RecordIdentityProvider,
    RecordTransportEnvelopeMaker,
    RecordTransportEnvelopeVerifier,
    RecordValidator,
)
from .prepared_integrity import (
    PreparedExchangeIntegrityError,
    detach_host_value,
    host_value_integrity_snapshot,
)

INBOUND_RECORD_RETRIEVAL_OPERATION: Final = (
    "https://open-trust-layer.github.io/marketplace/runtime/v1/"
    "operation/olp-record-retrieval"
)
MAX_INBOUND_RECORD_SOURCE_BYTES: Final = 2_048
_RECORD_ID_SHAPE_RE = re.compile(r"^r1_[A-Za-z0-9_-]{43}$")


class InboundRecordError(RuntimeError):
    """Fail-closed M33 error with a stable local reason code."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def _fail(code: str, message: str) -> None:
    raise InboundRecordError(code, message)


def _canonical_record_identity(value: object) -> str:
    """Require the exact M27-compatible OLP Record Identity transport form."""
    if type(value) is not str or not _RECORD_ID_SHAPE_RE.fullmatch(value):
        _fail(
            "INVALID_RECORD_IDENTITY_SHAPE",
            "requested Record Identity MUST have bounded r1_ base64url transport shape",
        )
    body = value[3:]
    try:
        decoded = base64.b64decode(body + "=", altchars=b"-_", validate=True)
    except (ValueError, base64.binascii.Error):
        _fail(
            "INVALID_RECORD_IDENTITY",
            "requested Record Identity MUST use canonical base64url transport encoding",
        )
    if len(decoded) != 32:
        _fail("INVALID_RECORD_IDENTITY", "requested Record Identity MUST encode 32 octets")
    canonical = base64.urlsafe_b64encode(decoded).rstrip(b"=").decode("ascii")
    if canonical != body:
        _fail(
            "INVALID_RECORD_IDENTITY",
            "requested Record Identity contains non-canonical base64url pad bits",
        )
    return value


def _local_source(value: object) -> str:
    if type(value) is not str or not value:
        raise ValueError("local_source MUST be non-empty exact text")
    try:
        encoded = value.encode("utf-8")
    except UnicodeEncodeError as exc:
        raise ValueError("local_source MUST be valid UTF-8 text") from exc
    if len(encoded) > MAX_INBOUND_RECORD_SOURCE_BYTES:
        raise ValueError("local_source exceeds the M33 runtime bound")
    return value


def _detach(value: Any, *, code: str, label: str) -> Any:
    try:
        return detach_host_value(value)
    except PreparedExchangeIntegrityError as exc:
        _fail(code, f"{label} cannot be safely detached: {exc.code}")


@dataclass(frozen=True)
class InboundRecordRequestContext:
    """Immutable local context for one exact Record disclosure decision."""

    local_source: str
    requested_record_identity: str
    operation: str = field(default=INBOUND_RECORD_RETRIEVAL_OPERATION, init=False)
    request_authenticated: bool = field(default=False, init=False)
    peer_identity_proven: bool = field(default=False, init=False)
    prior_page_membership_is_authorization: bool = field(default=False, init=False)
    authorizes_protected_side_effects: bool = field(default=False, init=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "local_source", _local_source(self.local_source))
        object.__setattr__(
            self,
            "requested_record_identity",
            _canonical_record_identity(self.requested_record_identity),
        )


def _context_snapshot(context: InboundRecordRequestContext) -> tuple[Any, ...]:
    return (
        "inbound-record-request-context-v1",
        context.local_source,
        context.operation,
        context.requested_record_identity,
    )


@dataclass(frozen=True)
class PreparedInboundRecordResponse:
    """One exact deeply detached OLP ``record`` envelope, prepared but unsent."""

    request_context: InboundRecordRequestContext
    envelope: tuple[Any, ...]
    integrity_snapshot: tuple[Any, ...] | None = field(default=None, repr=False)
    transmitted: bool = field(default=False, init=False)
    local_record_found: bool = field(default=True, init=False)
    identity_verified: bool = field(default=True, init=False)
    marketplace_semantics_verified: bool = field(default=True, init=False)
    proofs_verified: bool = field(default=False, init=False)
    request_authenticated: bool = field(default=False, init=False)
    peer_identity_proven: bool = field(default=False, init=False)
    global_existence: str = field(default="UNKNOWN", init=False)
    absence_is_deletion_evidence: bool = field(default=False, init=False)
    creates_agreement: bool = field(default=False, init=False)
    establishes_truth: bool = field(default=False, init=False)
    establishes_ownership: bool = field(default=False, init=False)
    establishes_authority: bool = field(default=False, init=False)
    establishes_trust: bool = field(default=False, init=False)
    establishes_authorization: bool = field(default=False, init=False)
    authorizes_protected_side_effects: bool = field(default=False, init=False)

    def __post_init__(self) -> None:
        if type(self.request_context) is not InboundRecordRequestContext:
            raise ValueError("request_context has the wrong type")
        detached_envelope = detach_host_value(self.envelope)
        if type(detached_envelope) is not tuple or len(detached_envelope) != 4:
            raise ValueError("prepared inbound Record envelope MUST be one exact four-element tuple")
        marker, version, message_type, payload = detached_envelope
        if marker != "OLP-TRANSPORT":
            raise ValueError("prepared inbound Record envelope marker is invalid")
        if type(version) is not int or version != 1:
            raise ValueError("prepared inbound Record envelope version MUST equal integer 1")
        if message_type != "record":
            raise ValueError("prepared inbound Record envelope MUST use message type 'record'")
        if not isinstance(payload, Mapping) or any(type(key) is not str for key in payload):
            raise ValueError("prepared inbound Record payload MUST be a string-keyed map")
        current = (
            "prepared-inbound-record-response-v1",
            _context_snapshot(self.request_context),
            host_value_integrity_snapshot(detached_envelope),
        )
        if self.integrity_snapshot is not None and self.integrity_snapshot != current:
            raise ValueError("prepared inbound Record response integrity snapshot mismatch")
        object.__setattr__(self, "envelope", detached_envelope)
        if self.integrity_snapshot is None:
            object.__setattr__(self, "integrity_snapshot", current)


class BoundedInboundRecordResponder:
    """Prepare one locally authorized immutable Record response and stop."""

    def __init__(
        self,
        *,
        local_source: str,
        record_source: ExactRecordSource,
        authorize_disclosure: InboundRecordDisclosureAuthorizer,
        validate_record: RecordValidator,
        record_identity: RecordIdentityProvider,
        prepare_payload: RecordEnvelopePayloadProvider,
        make_record_envelope: RecordTransportEnvelopeMaker,
        verify_record_envelope: RecordTransportEnvelopeVerifier,
    ) -> None:
        self._local_source = _local_source(local_source)
        if not callable(getattr(record_source, "get", None)):
            raise TypeError("record_source MUST provide callable get(record_id)")
        for name, helper in (
            ("authorize_disclosure", authorize_disclosure),
            ("validate_record", validate_record),
            ("record_identity", record_identity),
            ("prepare_payload", prepare_payload),
            ("make_record_envelope", make_record_envelope),
            ("verify_record_envelope", verify_record_envelope),
        ):
            if not callable(helper):
                raise TypeError(f"{name} MUST be callable")
        self._record_source = record_source
        self._authorize_disclosure = authorize_disclosure
        self._validate_record = validate_record
        self._record_identity = record_identity
        self._prepare_payload = prepare_payload
        self._make_record_envelope = make_record_envelope
        self._verify_record_envelope = verify_record_envelope

    def _validate_local_record(self, record: Any, expected: str, *, phase: str) -> None:
        try:
            self._validate_record(record)
        except Exception as exc:
            code = getattr(exc, "code", None)
            suffix = f": {code}" if type(code) is str else ""
            _fail("INVALID_LOCAL_RECORD", f"local Record failed Marketplace validation during {phase}{suffix}")
        try:
            derived = self._record_identity(record)
        except Exception as exc:
            _fail(
                "RECORD_IDENTITY_DERIVATION_FAILED",
                f"local Record identity derivation failed during {phase}: {type(exc).__name__}",
            )
        if type(derived) is not str:
            _fail("INVALID_IDENTITY_PROVIDER_RESULT", "Record identity provider MUST return exact text")
        derived = _canonical_record_identity(derived)
        if derived != expected:
            _fail(
                "LOCAL_RECORD_IDENTITY_MISMATCH",
                "local Record authoritative identity does not match requested immutable identity",
            )

    def prepare(self, *, requested_record_identity: str) -> PreparedInboundRecordResponse:
        expected = _canonical_record_identity(requested_record_identity)
        context = InboundRecordRequestContext(
            local_source=self._local_source,
            requested_record_identity=expected,
        )

        try:
            decision = self._authorize_disclosure(context)
        except Exception as exc:
            _fail(
                "DISCLOSURE_AUTHORIZATION_FAILED",
                f"local Record disclosure authorizer failed: {type(exc).__name__}",
            )
        if type(decision) is not bool:
            _fail("INVALID_DISCLOSURE_DECISION", "Record disclosure decision MUST be exact boolean")
        if decision is not True:
            _fail("DISCLOSURE_DENIED", "local policy denied immutable Record disclosure")

        try:
            record = self._record_source.get(expected)
        except Exception as exc:
            _fail("RECORD_SOURCE_FAILED", f"exact local Record source failed: {type(exc).__name__}")
        if record is None:
            _fail(
                "LOCAL_RECORD_NOT_FOUND",
                "requested Record is not currently available in the local source; global existence is unknown",
            )

        self._validate_local_record(record, expected, phase="preparation-start")

        try:
            payload_value = self._prepare_payload(record, expected_record_identity=expected)
        except Exception as exc:
            code = getattr(exc, "code", None)
            suffix = f": {code}" if type(code) is str else ""
            _fail("RECORD_PAYLOAD_PREPARATION_FAILED", f"Record payload preparation failed{suffix}")

        self._validate_local_record(record, expected, phase="post-payload-preparation")

        detached_payload = _detach(
            payload_value,
            code="UNSAFE_RECORD_PAYLOAD",
            label="prepared Record payload",
        )
        if not isinstance(detached_payload, Mapping):
            _fail("INVALID_RECORD_PAYLOAD", "prepared Record payload MUST be a mapping")
        if any(type(key) is not str for key in detached_payload):
            _fail("INVALID_RECORD_PAYLOAD", "prepared Record payload keys MUST be exact text")
        payload_snapshot = host_value_integrity_snapshot(detached_payload)

        try:
            envelope_value = self._make_record_envelope(detached_payload)
        except Exception as exc:
            code = getattr(exc, "code", None)
            suffix = f": {code}" if type(code) is str else ""
            _fail("RECORD_ENVELOPE_PREPARATION_FAILED", f"Record envelope preparation failed{suffix}")
        if host_value_integrity_snapshot(detached_payload) != payload_snapshot:
            _fail("RECORD_PAYLOAD_MUTATED", "Record envelope maker mutated prepared payload")

        detached_envelope = _detach(
            envelope_value,
            code="UNSAFE_RECORD_ENVELOPE",
            label="prepared Record envelope",
        )
        if type(detached_envelope) is not tuple or len(detached_envelope) != 4:
            _fail("INVALID_RECORD_ENVELOPE", "prepared Record envelope MUST be an exact four-element tuple")
        marker, version, message_type, envelope_payload = detached_envelope
        if marker != "OLP-TRANSPORT":
            _fail("INVALID_RECORD_ENVELOPE", "prepared Record envelope marker is invalid")
        if type(version) is not int or version != 1:
            _fail("INVALID_RECORD_ENVELOPE", "prepared Record envelope version MUST equal integer 1")
        if message_type != "record":
            _fail("RECORD_MESSAGE_TYPE_REQUIRED", "prepared response MUST use OLP message type 'record'")
        if host_value_integrity_snapshot(envelope_payload) != payload_snapshot:
            _fail("RECORD_ENVELOPE_PAYLOAD_DRIFT", "prepared Record envelope changed the validated payload")

        envelope_snapshot = host_value_integrity_snapshot(detached_envelope)
        try:
            verification = self._verify_record_envelope(
                detached_envelope,
                expected_record_identity=expected,
            )
        except Exception as exc:
            code = getattr(exc, "code", None)
            suffix = f": {code}" if type(code) is str else ""
            _fail("RECORD_ENVELOPE_VERIFICATION_FAILED", f"prepared Record envelope verification failed{suffix}")
        if host_value_integrity_snapshot(detached_envelope) != envelope_snapshot:
            _fail("RECORD_ENVELOPE_MUTATED", "Record envelope verifier mutated prepared envelope")
        if not isinstance(verification, Mapping):
            _fail("INVALID_RECORD_VERIFICATION_RESULT", "Record envelope verifier MUST return a mapping")
        expected_keys = {
            "requested_record_identity",
            "recomputed_record_identity",
            "identity_verified",
            "marketplace_semantics_verified",
            "proofs_verified",
            "establishes_truth",
            "establishes_ownership",
            "establishes_authority",
            "establishes_trust",
            "establishes_authorization",
            "automatically_ingested",
        }
        if set(verification) != expected_keys:
            _fail("INVALID_RECORD_VERIFICATION_RESULT", "Record verification result shape is invalid")
        if verification["requested_record_identity"] != expected or verification["recomputed_record_identity"] != expected:
            _fail("RECORD_VERIFICATION_IDENTITY_DRIFT", "Record verifier identity binding drifted")
        if verification["identity_verified"] is not True or verification["marketplace_semantics_verified"] is not True:
            _fail("RECORD_VERIFICATION_NOT_ESTABLISHED", "Record identity/Marketplace verification MUST be explicit true")
        for key in (
            "proofs_verified",
            "establishes_truth",
            "establishes_ownership",
            "establishes_authority",
            "establishes_trust",
            "establishes_authorization",
            "automatically_ingested",
        ):
            if verification[key] is not False:
                _fail("RECORD_VERIFICATION_AUTHORITY_ESCALATION", f"Record verifier promoted forbidden fact {key}")

        return PreparedInboundRecordResponse(
            request_context=context,
            envelope=detached_envelope,
        )
