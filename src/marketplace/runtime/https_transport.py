"""Authorized synchronous HTTPS transport for one Marketplace federation envelope.

Milestone 26 is the first reference runtime component with concrete external
network capability.  It deliberately implements a small HTTP/1.1 subset rather
than using an environment-aware URL opener: one POST, no redirects, no proxy,
no credentials, no retries, no pooling, and no background work.

Tests inject resolver/connector doubles; invoking the default resolver/connector
is an explicit NETWORK_EXTERNAL operation and requires operator authorization.
"""
from __future__ import annotations

import ipaddress
import socket
import ssl
import threading
import time
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from typing import Any, Final, Protocol

from .federation import PreparedFederationExchange
from .network_policy import (
    FederationEgressPolicy,
    FederationEndpointAuthorization,
    validate_endpoint_authorization,
    validate_resolved_addresses,
)

DEFAULT_CONNECT_TIMEOUT_SECONDS: Final = 5.0
DEFAULT_READ_TIMEOUT_SECONDS: Final = 10.0
DEFAULT_TOTAL_TIMEOUT_SECONDS: Final = 15.0
DEFAULT_MAX_REQUEST_BYTES: Final = 1 * 1024 * 1024
DEFAULT_MAX_RESPONSE_BYTES: Final = 1 * 1024 * 1024
DEFAULT_MAX_HEADER_BYTES: Final = 32 * 1024
DEFAULT_MAX_RESOLVED_ADDRESSES: Final = 16
DEFAULT_MAX_CONCURRENT_EXCHANGES: Final = 4
MAX_TIMEOUT_SECONDS: Final = 60.0
MAX_BODY_BYTES: Final = 16 * 1024 * 1024
MAX_HEADER_BYTES: Final = 128 * 1024
MAX_CONCURRENT_EXCHANGES: Final = 32


class FederationHttpsTransportError(RuntimeError):
    """Fail-closed network transport error with stable local reason code."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def _fail(code: str, message: str) -> None:
    raise FederationHttpsTransportError(code, message)


class EnvelopeJsonEncoder(Protocol):
    def __call__(self, envelope: Any) -> bytes: ...


class EnvelopeJsonDecoder(Protocol):
    def __call__(self, body: bytes) -> Any: ...


class Resolver(Protocol):
    def __call__(self, hostname: str, port: int) -> Iterable[str]: ...


class SecureConnection(Protocol):
    def sendall(self, data: bytes) -> None: ...
    def recv(self, size: int) -> bytes: ...
    def settimeout(self, value: float) -> None: ...
    def close(self) -> None: ...


class SecureConnector(Protocol):
    def __call__(
        self,
        *,
        address: str,
        port: int,
        server_hostname: str,
        connect_timeout_seconds: float,
    ) -> SecureConnection: ...


@dataclass(frozen=True)
class HttpsFederationTransportLimits:
    connect_timeout_seconds: float = DEFAULT_CONNECT_TIMEOUT_SECONDS
    read_timeout_seconds: float = DEFAULT_READ_TIMEOUT_SECONDS
    total_timeout_seconds: float = DEFAULT_TOTAL_TIMEOUT_SECONDS
    max_request_bytes: int = DEFAULT_MAX_REQUEST_BYTES
    max_response_bytes: int = DEFAULT_MAX_RESPONSE_BYTES
    max_header_bytes: int = DEFAULT_MAX_HEADER_BYTES
    max_resolved_addresses: int = DEFAULT_MAX_RESOLVED_ADDRESSES
    max_concurrent_exchanges: int = DEFAULT_MAX_CONCURRENT_EXCHANGES

    def __post_init__(self) -> None:
        for name, value in (
            ("connect_timeout_seconds", self.connect_timeout_seconds),
            ("read_timeout_seconds", self.read_timeout_seconds),
            ("total_timeout_seconds", self.total_timeout_seconds),
        ):
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not 0 < float(value) <= MAX_TIMEOUT_SECONDS:
                raise ValueError(f"{name} MUST be within (0, {MAX_TIMEOUT_SECONDS}]")
        if self.total_timeout_seconds < self.connect_timeout_seconds:
            raise ValueError("total_timeout_seconds MUST be >= connect_timeout_seconds")
        for name, value, maximum in (
            ("max_request_bytes", self.max_request_bytes, MAX_BODY_BYTES),
            ("max_response_bytes", self.max_response_bytes, MAX_BODY_BYTES),
            ("max_header_bytes", self.max_header_bytes, MAX_HEADER_BYTES),
            ("max_resolved_addresses", self.max_resolved_addresses, 32),
            ("max_concurrent_exchanges", self.max_concurrent_exchanges, MAX_CONCURRENT_EXCHANGES),
        ):
            if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= maximum:
                raise ValueError(f"{name} MUST be within 1..{maximum}")


@dataclass(frozen=True)
class HttpsFederationExchangeResult:
    response_envelope: Any
    http_status: int
    response_body_bytes: int
    selected_address: str
    tls_server_hostname: str
    connection_attempts: int = 1
    redirects_followed: int = 0
    retries_performed: int = 0
    proxy_used: bool = False
    credentials_used: bool = False
    establishes_peer_trust: bool = False
    establishes_marketplace_truth: bool = False
    establishes_agreement: bool = False
    establishes_authorization: bool = False


def _default_resolver(hostname: str, port: int) -> Iterable[str]:
    """Fresh system DNS lookup used only when the concrete adapter is invoked."""
    try:
        results = socket.getaddrinfo(
            hostname,
            port,
            family=socket.AF_UNSPEC,
            type=socket.SOCK_STREAM,
            proto=socket.IPPROTO_TCP,
        )
        addresses = tuple(result[4][0] for result in results)
    except (OSError, IndexError, TypeError) as exc:
        _fail("DNS_RESOLUTION_FAILED", f"fresh federation DNS resolution failed: {type(exc).__name__}")
    return addresses


def _default_secure_connector(
    *,
    address: str,
    port: int,
    server_hostname: str,
    connect_timeout_seconds: float,
) -> SecureConnection:
    """Connect directly to an already-classified numeric address, then verify TLS hostname."""
    raw: Any | None = None
    try:
        parsed = ipaddress.ip_address(address)
        family = socket.AF_INET if parsed.version == 4 else socket.AF_INET6
        raw = socket.socket(family, socket.SOCK_STREAM, socket.IPPROTO_TCP)
        raw.settimeout(connect_timeout_seconds)
        destination: tuple[Any, ...]
        if parsed.version == 4:
            destination = (str(parsed), port)
        else:
            destination = (str(parsed), port, 0, 0)
        raw.connect(destination)

        context = ssl.create_default_context()
        context.minimum_version = ssl.TLSVersion.TLSv1_2
        context.check_hostname = True
        context.verify_mode = ssl.CERT_REQUIRED
        context.set_alpn_protocols(["http/1.1"])
        tls = context.wrap_socket(raw, server_hostname=server_hostname)
        selected = tls.selected_alpn_protocol()
        if selected not in (None, "http/1.1"):
            tls.close()
            _fail("TLS_ALPN_MISMATCH", "server selected an unsupported application protocol")
        return tls
    except FederationHttpsTransportError:
        if raw is not None:
            raw.close()
        raise
    except (OSError, ssl.SSLError, ValueError) as exc:
        if raw is not None:
            raw.close()
        _fail("TLS_CONNECTION_FAILED", f"HTTPS connection failed: {type(exc).__name__}")


def _request_bytes(endpoint_url_path: str, hostname: str, port: int, body: bytes) -> bytes:
    host_header = hostname if port == 443 else f"{hostname}:{port}"
    request_head = (
        f"POST {endpoint_url_path} HTTP/1.1\r\n"
        f"Host: {host_header}\r\n"
        "Content-Type: application/json\r\n"
        "Accept: application/json\r\n"
        "Connection: close\r\n"
        f"Content-Length: {len(body)}\r\n"
        "\r\n"
    ).encode("ascii")
    return request_head + body


def _remaining_timeout(start: float, total: float, phase: float, monotonic: Callable[[], float]) -> float:
    remaining = total - (monotonic() - start)
    if remaining <= 0:
        _fail("TOTAL_TIMEOUT", "federation HTTPS exchange exceeded total timeout budget")
    return min(phase, remaining)


def _recv_into_buffer(
    connection: SecureConnection,
    buffer: bytearray,
    *,
    target_bytes: int,
    hard_limit: int,
    start: float,
    limits: HttpsFederationTransportLimits,
    monotonic: Callable[[], float],
) -> None:
    while len(buffer) < target_bytes:
        if len(buffer) >= hard_limit:
            _fail("RESPONSE_LIMIT_EXCEEDED", "HTTPS response exceeded configured byte limit")
        connection.settimeout(
            _remaining_timeout(
                start,
                limits.total_timeout_seconds,
                limits.read_timeout_seconds,
                monotonic,
            )
        )
        try:
            chunk = connection.recv(min(16_384, hard_limit - len(buffer)))
        except (OSError, TimeoutError) as exc:
            _fail("HTTPS_READ_FAILED", f"HTTPS response read failed: {type(exc).__name__}")
        if not chunk:
            _fail("TRUNCATED_HTTP_RESPONSE", "HTTPS peer closed before declared response completed")
        buffer.extend(chunk)


def _read_response(
    connection: SecureConnection,
    *,
    start: float,
    limits: HttpsFederationTransportLimits,
    monotonic: Callable[[], float],
) -> tuple[int, bytes]:
    buffer = bytearray()
    marker = b"\r\n\r\n"
    while marker not in buffer:
        if len(buffer) >= limits.max_header_bytes:
            _fail("HTTP_HEADER_LIMIT_EXCEEDED", "HTTPS response headers exceed configured limit")
        connection.settimeout(
            _remaining_timeout(
                start,
                limits.total_timeout_seconds,
                limits.read_timeout_seconds,
                monotonic,
            )
        )
        try:
            chunk = connection.recv(min(4_096, limits.max_header_bytes - len(buffer)))
        except (OSError, TimeoutError) as exc:
            _fail("HTTPS_READ_FAILED", f"HTTPS response header read failed: {type(exc).__name__}")
        if not chunk:
            _fail("TRUNCATED_HTTP_RESPONSE", "HTTPS peer closed before response headers completed")
        buffer.extend(chunk)

    header_bytes, initial_body = bytes(buffer).split(marker, 1)
    try:
        header_text = header_bytes.decode("ascii")
    except UnicodeDecodeError:
        _fail("INVALID_HTTP_HEADERS", "HTTPS response headers MUST be ASCII in the M26 reference profile")
    lines = header_text.split("\r\n")
    if not lines or not lines[0].startswith("HTTP/1.1 "):
        _fail("UNSUPPORTED_HTTP_VERSION", "M26 accepts HTTP/1.1 responses only")
    if any(ord(ch) < 0x20 or ord(ch) == 0x7F for ch in lines[0]):
        _fail("INVALID_HTTP_STATUS", "HTTPS response status line contains a control character")
    status_parts = lines[0].split(" ", 2)
    if len(status_parts) < 2 or len(status_parts[1]) != 3 or not status_parts[1].isdigit():
        _fail("INVALID_HTTP_STATUS", "HTTPS response status line is malformed")
    status = int(status_parts[1])

    headers: dict[str, list[str]] = {}
    for line in lines[1:]:
        if not line or line[0] in " \t" or ":" not in line:
            _fail("INVALID_HTTP_HEADERS", "HTTPS response contains malformed or folded header line")
        name, value = line.split(":", 1)
        if not name or any(ch not in "!#$%&'*+-.^_`|~0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz" for ch in name):
            _fail("INVALID_HTTP_HEADERS", "HTTPS response contains invalid header name")
        clean = value.strip(" \t")
        if any(ord(ch) < 0x20 or ord(ch) == 0x7F for ch in clean):
            _fail("INVALID_HTTP_HEADERS", "HTTPS response contains an unsafe header control character")
        headers.setdefault(name.lower(), []).append(clean)

    if status != 200:
        _fail("HTTP_STATUS_REJECTED", f"federation endpoint returned HTTP status {status}")
    if headers.get("content-type") != ["application/json"]:
        _fail("HTTP_CONTENT_TYPE_REJECTED", "M26 requires exactly Content-Type: application/json")
    if "transfer-encoding" in headers:
        _fail("HTTP_TRANSFER_ENCODING_REJECTED", "M26 does not accept Transfer-Encoding")
    if "content-encoding" in headers:
        _fail("HTTP_CONTENT_ENCODING_REJECTED", "M26 does not accept compressed response bodies")
    lengths = headers.get("content-length")
    if lengths is None or len(lengths) != 1 or not lengths[0].isdigit():
        _fail("HTTP_CONTENT_LENGTH_REQUIRED", "M26 requires one canonical Content-Length")
    if lengths[0] != "0" and lengths[0].startswith("0"):
        _fail("HTTP_CONTENT_LENGTH_REQUIRED", "Content-Length MUST use canonical decimal form")
    body_length = int(lengths[0])
    if body_length < 1 or body_length > limits.max_response_bytes:
        _fail("HTTP_BODY_LIMIT", "response Content-Length is outside configured M26 bounds")
    if len(initial_body) > body_length:
        _fail("HTTP_BODY_OVERFLOW", "response contains bytes beyond declared Content-Length")

    body = bytearray(initial_body)
    _recv_into_buffer(
        connection,
        body,
        target_bytes=body_length,
        hard_limit=limits.max_response_bytes,
        start=start,
        limits=limits,
        monotonic=monotonic,
    )
    if len(body) != body_length:
        _fail("TRUNCATED_HTTP_RESPONSE", "response body length does not match Content-Length")
    return status, bytes(body)


def _validated_response_envelope(value: Any) -> tuple[Any, ...]:
    if not isinstance(value, (tuple, list)) or len(value) != 4:
        _fail("INVALID_RESPONSE_ENVELOPE", "decoded response MUST be one OLP transport envelope")
    marker, version, message_type, payload = value
    if marker != "OLP-TRANSPORT":
        _fail("INVALID_RESPONSE_ENVELOPE", "decoded response has the wrong transport marker")
    if isinstance(version, bool) or not isinstance(version, int) or version != 1:
        _fail("INVALID_RESPONSE_ENVELOPE", "decoded response has an unsupported transport version")
    if not isinstance(message_type, str) or not message_type:
        _fail("INVALID_RESPONSE_ENVELOPE", "decoded response message type MUST be non-empty text")
    return (marker, version, message_type, payload)


class AuthorizedHttpsFederationTransport:
    """One-shot authorized HTTPS federation control transport."""

    def __init__(
        self,
        *,
        policy: FederationEgressPolicy,
        encode_envelope_json: EnvelopeJsonEncoder,
        decode_envelope_json: EnvelopeJsonDecoder,
        limits: HttpsFederationTransportLimits | None = None,
        resolver: Resolver = _default_resolver,
        connector: SecureConnector = _default_secure_connector,
        wall_clock: Callable[[], float] = time.time,
        monotonic_clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if not isinstance(policy, FederationEgressPolicy):
            raise TypeError("policy MUST be FederationEgressPolicy")
        if not callable(encode_envelope_json) or not callable(decode_envelope_json):
            raise TypeError("envelope JSON codec functions MUST be callable")
        if not callable(resolver) or not callable(connector):
            raise TypeError("resolver and connector MUST be callable")
        if not callable(wall_clock) or not callable(monotonic_clock):
            raise TypeError("clock functions MUST be callable")
        self._policy = policy
        self._encode = encode_envelope_json
        self._decode = decode_envelope_json
        self._limits = limits or HttpsFederationTransportLimits()
        self._resolver = resolver
        self._connector = connector
        self._wall_clock = wall_clock
        self._monotonic = monotonic_clock
        self._concurrency = threading.BoundedSemaphore(self._limits.max_concurrent_exchanges)

    def exchange(
        self,
        prepared: PreparedFederationExchange,
        *,
        endpoint: str,
        authorization: FederationEndpointAuthorization,
    ) -> HttpsFederationExchangeResult:
        if not isinstance(prepared, PreparedFederationExchange):
            _fail("INVALID_PREPARED_EXCHANGE", "prepared exchange has the wrong type")
        if prepared.transmitted is not False:
            _fail("PREPARED_EXCHANGE_STATE", "M26 requires an M24 exchange that has not been transmitted")
        if not self._concurrency.acquire(blocking=False):
            _fail("CONCURRENCY_LIMIT", "maximum concurrent federation HTTPS exchanges reached")
        connection: SecureConnection | None = None
        try:
            start = self._monotonic()
            now = int(self._wall_clock())
            canonical = validate_endpoint_authorization(
                authorization,
                endpoint=endpoint,
                operation=prepared.binding.operation,
                now_epoch=now,
                policy=self._policy,
            )

            try:
                body = self._encode(prepared.envelope)
            except Exception as exc:
                _fail("REQUEST_ENVELOPE_ENCODING_FAILED", f"OLP JSON envelope encoding failed: {type(exc).__name__}")
            if not isinstance(body, bytes) or not 1 <= len(body) <= self._limits.max_request_bytes:
                _fail("REQUEST_BODY_LIMIT", "encoded federation request body is outside configured bounds")

            # Authorization is deliberately validated before the fresh resolver call.
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

            # DNS itself can consume time. Revalidate the same immutable authorization
            # again after fresh resolution and immediately before opening a socket.
            canonical = validate_endpoint_authorization(
                authorization,
                endpoint=endpoint,
                operation=prepared.binding.operation,
                now_epoch=int(self._wall_clock()),
                policy=self._policy,
            )
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

            request = _request_bytes(canonical.path, canonical.hostname, canonical.port, body)
            if len(request) > self._limits.max_request_bytes + self._limits.max_header_bytes:
                _fail("REQUEST_LIMIT_EXCEEDED", "HTTP request exceeds configured combined limit")
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
            response_envelope = _validated_response_envelope(decoded)
            return HttpsFederationExchangeResult(
                response_envelope=response_envelope,
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
