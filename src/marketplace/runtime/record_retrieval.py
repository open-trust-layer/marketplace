"""Authorized one-shot HTTPS retrieval of one immutable OLP Record envelope.

Milestone 27 reuses the accepted M25/M26 destination, DNS, TLS and HTTP response
boundaries.  This module deliberately does not import OLP, recompute Record
Identity, validate Marketplace semantics, or store the received Record.  Those
steps live behind a separate injected/reference verification boundary.
"""
from __future__ import annotations

import base64
import re
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Final

from .https_transport import (
    EnvelopeJsonDecoder,
    FederationHttpsTransportError,
    HttpsFederationTransportLimits,
    Resolver,
    SecureConnection,
    SecureConnector,
    _default_resolver,
    _default_secure_connector,
    _read_response,
    _remaining_timeout,
    _validated_response_envelope,
)
from .network_policy import (
    CanonicalFederationEndpoint,
    FederationEgressPolicy,
    FederationEndpointAuthorization,
    validate_endpoint_authorization,
    validate_resolved_addresses,
)

RECORD_RETRIEVAL_OPERATION: Final = (
    "https://open-trust-layer.github.io/marketplace/runtime/v1/"
    "operation/olp-record-retrieval"
)
_RECORD_ID_SHAPE_RE = re.compile(r"^r1_[A-Za-z0-9_-]{43}$")


class RecordRetrievalTransportError(RuntimeError):
    """Fail-closed M27 retrieval-specific error with stable local code."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def _fail(code: str, message: str) -> None:
    raise RecordRetrievalTransportError(code, message)


def _expected_record_identity(value: object) -> str:
    """Require canonical bounded OLP Record Identity transport text before DNS.

    This duplicates only the transport presentation rule needed to keep an
    untrusted/noncanonical path from reaching the network.  It does not compute
    or validate the Record Identity of any received Record; that remains the
    pinned-OLP reference verifier's responsibility.
    """
    if not isinstance(value, str) or not _RECORD_ID_SHAPE_RE.fullmatch(value):
        _fail(
            "INVALID_EXPECTED_RECORD_IDENTITY_SHAPE",
            "expected Record Identity MUST have bounded r1_ base64url transport shape",
        )
    body = value[3:]
    try:
        decoded = base64.b64decode(body + "=", altchars=b"-_", validate=True)
    except (ValueError, base64.binascii.Error):
        _fail(
            "INVALID_EXPECTED_RECORD_IDENTITY",
            "expected Record Identity MUST use canonical base64url transport encoding",
        )
    if len(decoded) != 32:
        _fail("INVALID_EXPECTED_RECORD_IDENTITY", "expected Record Identity MUST encode 32 octets")
    canonical = base64.urlsafe_b64encode(decoded).rstrip(b"=").decode("ascii")
    if canonical != body:
        _fail(
            "INVALID_EXPECTED_RECORD_IDENTITY",
            "expected Record Identity contains non-canonical base64url pad bits",
        )
    return value


def _require_exact_record_path(path: str, expected_record_identity: str) -> None:
    suffix = f"/v1/records/{expected_record_identity}"
    if not path.endswith(suffix):
        _fail(
            "ENDPOINT_RECORD_IDENTITY_MISMATCH",
            "authorized endpoint path MUST end with /v1/records/<expected Record Identity>",
        )


def _get_request_bytes(path: str, hostname: str, port: int) -> bytes:
    host_header = hostname if port == 443 else f"{hostname}:{port}"
    return (
        f"GET {path} HTTP/1.1\r\n"
        f"Host: {host_header}\r\n"
        "Accept: application/json\r\n"
        "Connection: close\r\n"
        "\r\n"
    ).encode("ascii")


@dataclass(frozen=True)
class RetrievedRecordTransportResult:
    """Transport-only result; identity and Marketplace semantics remain unverified."""

    expected_record_identity: str
    response_envelope: tuple[Any, ...]
    http_status: int
    response_body_bytes: int
    selected_address: str
    tls_server_hostname: str
    connection_attempts: int = 1
    redirects_followed: int = 0
    retries_performed: int = 0
    proxy_used: bool = False
    credentials_used: bool = False
    identity_verified: bool = False
    marketplace_semantics_verified: bool = False
    proofs_verified: bool = False
    establishes_truth: bool = False
    establishes_authorization: bool = False
    automatically_ingested: bool = False


class AuthorizedHttpsRecordRetriever:
    """Retrieve one exact OLP ``record`` envelope without interpreting the Record."""

    def __init__(
        self,
        *,
        policy: FederationEgressPolicy,
        decode_envelope_json: EnvelopeJsonDecoder,
        limits: HttpsFederationTransportLimits | None = None,
        resolver: Resolver = _default_resolver,
        connector: SecureConnector = _default_secure_connector,
        wall_clock: Callable[[], float] = time.time,
        monotonic_clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if not isinstance(policy, FederationEgressPolicy):
            raise TypeError("policy MUST be FederationEgressPolicy")
        if not callable(decode_envelope_json):
            raise TypeError("decode_envelope_json MUST be callable")
        if not callable(resolver) or not callable(connector):
            raise TypeError("resolver and connector MUST be callable")
        if not callable(wall_clock) or not callable(monotonic_clock):
            raise TypeError("clock functions MUST be callable")
        self._policy = policy
        self._decode = decode_envelope_json
        self._limits = limits or HttpsFederationTransportLimits()
        self._resolver = resolver
        self._connector = connector
        self._wall_clock = wall_clock
        self._monotonic = monotonic_clock
        self._concurrency = threading.BoundedSemaphore(self._limits.max_concurrent_exchanges)

    def _validate_pre_network_target(
        self,
        *,
        endpoint: str,
        authorization: FederationEndpointAuthorization,
        expected_record_identity: str,
        now_epoch: int,
    ) -> tuple[str, CanonicalFederationEndpoint, bytes]:
        """Validate every condition that can fail safely before DNS/network use."""
        expected = _expected_record_identity(expected_record_identity)
        canonical = validate_endpoint_authorization(
            authorization,
            endpoint=endpoint,
            operation=RECORD_RETRIEVAL_OPERATION,
            now_epoch=now_epoch,
            policy=self._policy,
        )
        _require_exact_record_path(canonical.path, expected)
        request = _get_request_bytes(canonical.path, canonical.hostname, canonical.port)
        if len(request) > self._limits.max_header_bytes:
            _fail("REQUEST_HEADER_LIMIT", "immutable-record GET request exceeds configured header bound")
        return expected, canonical, request

    def preflight(
        self,
        *,
        endpoint: str,
        authorization: FederationEndpointAuthorization,
        expected_record_identity: str,
    ) -> None:
        """Validate one retrieval target without DNS, socket creation, or storage.

        This is an early rejection aid for bounded batch orchestration only. It
        does not reserve authorization or make a later request safe: ``retrieve``
        independently repeats these checks and still revalidates after fresh DNS.
        """
        self._validate_pre_network_target(
            endpoint=endpoint,
            authorization=authorization,
            expected_record_identity=expected_record_identity,
            now_epoch=int(self._wall_clock()),
        )

    def retrieve(
        self,
        *,
        endpoint: str,
        authorization: FederationEndpointAuthorization,
        expected_record_identity: str,
    ) -> RetrievedRecordTransportResult:
        if not self._concurrency.acquire(blocking=False):
            _fail("CONCURRENCY_LIMIT", "maximum concurrent immutable-record retrievals reached")
        connection: SecureConnection | None = None
        try:
            start = self._monotonic()
            expected, canonical, request = self._validate_pre_network_target(
                endpoint=endpoint,
                authorization=authorization,
                expected_record_identity=expected_record_identity,
                now_epoch=int(self._wall_clock()),
            )

            try:
                resolver_values = self._resolver(canonical.hostname, canonical.port)
                resolved = validate_resolved_addresses(
                    canonical.hostname,
                    resolver_values,
                    max_addresses=self._limits.max_resolved_addresses,
                )
            except FederationHttpsTransportError:
                raise
            except Exception as exc:
                code = getattr(exc, "code", None)
                if isinstance(code, str):
                    _fail("UNSAFE_RESOLUTION", f"fresh resolver result rejected by M25 policy: {code}")
                _fail("DNS_RESOLUTION_FAILED", f"fresh resolver failed: {type(exc).__name__}")

            # DNS can consume authorization lifetime.  Revalidate immediately before connect.
            canonical = validate_endpoint_authorization(
                authorization,
                endpoint=endpoint,
                operation=RECORD_RETRIEVAL_OPERATION,
                now_epoch=int(self._wall_clock()),
                policy=self._policy,
            )
            _require_exact_record_path(canonical.path, expected)
            selected_address = resolved.addresses[0]

            connect_timeout = _remaining_timeout(
                start,
                self._limits.total_timeout_seconds,
                self._limits.connect_timeout_seconds,
                self._monotonic,
            )
            try:
                connection = self._connector(
                    address=selected_address,
                    port=canonical.port,
                    server_hostname=canonical.hostname,
                    connect_timeout_seconds=connect_timeout,
                )
            except FederationHttpsTransportError:
                raise
            except Exception as exc:
                _fail("TLS_CONNECTION_FAILED", f"secure connector failed: {type(exc).__name__}")

            connection.settimeout(
                _remaining_timeout(
                    start,
                    self._limits.total_timeout_seconds,
                    self._limits.read_timeout_seconds,
                    self._monotonic,
                )
            )
            try:
                connection.sendall(request)
            except (OSError, TimeoutError) as exc:
                _fail("HTTPS_WRITE_FAILED", f"HTTPS request write failed: {type(exc).__name__}")

            status, response_body = _read_response(
                connection,
                start=start,
                limits=self._limits,
                monotonic=self._monotonic,
            )
            try:
                decoded = self._decode(response_body)
            except Exception as exc:
                _fail("RESPONSE_ENVELOPE_DECODING_FAILED", f"OLP JSON envelope decoding failed: {type(exc).__name__}")
            envelope = _validated_response_envelope(decoded)
            if envelope[2] != "record":
                _fail("RECORD_MESSAGE_TYPE_REQUIRED", "immutable retrieval response MUST use OLP message type 'record'")

            return RetrievedRecordTransportResult(
                expected_record_identity=expected,
                response_envelope=envelope,
                http_status=status,
                response_body_bytes=len(response_body),
                selected_address=selected_address,
                tls_server_hostname=canonical.hostname,
            )
        finally:
            if connection is not None:
                try:
                    connection.close()
                except Exception:
                    pass
            self._concurrency.release()
