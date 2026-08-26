"""Pure federation egress policy and endpoint-authorization helpers.

Milestone 25 intentionally performs no DNS lookup, socket creation, HTTP request,
TLS handshake, proxy discovery, credential lookup, process execution, or other
external I/O. It validates configuration and caller-supplied resolver results so
a later transport adapter can fail closed before gaining network capability.
"""
from __future__ import annotations

import ipaddress
import re
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Final
from urllib.parse import urlsplit

MAX_ENDPOINT_BYTES: Final = 4_096
MAX_PATH_BYTES: Final = 2_048
MAX_ALLOWED_HOSTS: Final = 128
MAX_ALLOWED_PORTS: Final = 16
MAX_ALLOWED_OPERATIONS: Final = 64
MAX_OPERATION_BYTES: Final = 512
MAX_AUTHORIZATION_ID_BYTES: Final = 128
MAX_POLICY_ID_BYTES: Final = 256
MAX_AUTHORIZATION_LIFETIME_SECONDS: Final = 300
MAX_RESOLVED_ADDRESSES: Final = 32

_DNS_LABEL_RE = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$")
_PATH_RE = re.compile(r"^/[A-Za-z0-9._~/-]*$")


class FederationNetworkPolicyError(RuntimeError):
    """Fail-closed M25 endpoint, authorization, or address-policy error."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def _fail(code: str, message: str) -> None:
    raise FederationNetworkPolicyError(code, message)


def _ascii_text(value: object, *, name: str, max_bytes: int) -> str:
    if not isinstance(value, str) or not value:
        _fail("INVALID_TEXT", f"{name} MUST be non-empty text")
    try:
        encoded = value.encode("ascii")
    except UnicodeEncodeError:
        _fail("NON_ASCII_TEXT", f"{name} MUST use unambiguous ASCII text")
    if len(encoded) > max_bytes:
        _fail("TEXT_LIMIT_EXCEEDED", f"{name} exceeds {max_bytes} bytes")
    if any(byte < 0x21 or byte == 0x7F for byte in encoded):
        _fail("UNSAFE_TEXT", f"{name} MUST NOT contain whitespace or control characters")
    return value


def _canonical_dns_name(value: object, *, policy_entry: bool = False) -> str:
    name = _ascii_text(value, name="hostname", max_bytes=253)
    lowered = name.lower()
    if policy_entry and lowered != name:
        _fail("NONCANONICAL_ALLOWLIST_HOST", "allowlisted hostnames MUST already be lowercase")
    if lowered.endswith(".") or lowered.startswith(".") or ".." in lowered:
        _fail("AMBIGUOUS_HOSTNAME", "hostname MUST NOT use leading/trailing/repeated dots")
    if "%" in lowered or "_" in lowered:
        _fail("AMBIGUOUS_HOSTNAME", "hostname contains an unsafe or ambiguous character")
    try:
        ipaddress.ip_address(lowered)
    except ValueError:
        pass
    else:
        _fail("IP_LITERAL_FORBIDDEN", "reference federation endpoints MUST use allowlisted DNS names")
    labels = lowered.split(".")
    if len(labels) < 2:
        _fail("INVALID_HOSTNAME", "reference federation hostname MUST contain at least two DNS labels")
    for label in labels:
        if label.startswith("xn--"):
            _fail("IDNA_HOST_FORBIDDEN", "punycode/IDNA hostnames are not accepted by the reference policy")
        if not _DNS_LABEL_RE.fullmatch(label):
            _fail("INVALID_HOSTNAME", f"invalid DNS label {label!r}")
    return lowered


def _canonical_path(path: str, max_path_bytes: int) -> str:
    candidate = path or "/"
    try:
        encoded = candidate.encode("ascii")
    except UnicodeEncodeError:
        _fail("NON_ASCII_PATH", "endpoint path MUST use unambiguous ASCII text")
    if len(encoded) > max_path_bytes:
        _fail("PATH_LIMIT_EXCEEDED", f"endpoint path exceeds {max_path_bytes} bytes")
    if "\\" in candidate or "%" in candidate:
        _fail("AMBIGUOUS_PATH", "endpoint path MUST NOT contain backslashes or percent-encoding")
    if not _PATH_RE.fullmatch(candidate):
        _fail("INVALID_PATH", "endpoint path contains characters outside the reference safe subset")
    if candidate != "/" and "//" in candidate:
        _fail("AMBIGUOUS_PATH", "endpoint path MUST NOT contain repeated slashes")
    segments = candidate.split("/")
    if any(segment in {".", ".."} for segment in segments):
        _fail("PATH_TRAVERSAL", "endpoint path MUST NOT contain dot-segments")
    return candidate


def _canonical_operations(values: Iterable[object]) -> tuple[str, ...]:
    items: list[str] = []
    for index, value in enumerate(values):
        if index >= MAX_ALLOWED_OPERATIONS:
            _fail("OPERATION_LIMIT_EXCEEDED", f"more than {MAX_ALLOWED_OPERATIONS} operations are not permitted")
        items.append(_ascii_text(value, name="operation", max_bytes=MAX_OPERATION_BYTES))
    if not items:
        _fail("EMPTY_OPERATIONS", "at least one federation operation MUST be authorized")
    normalized = tuple(sorted(items, key=lambda item: item.encode("utf-8")))
    if len(normalized) != len(set(normalized)):
        _fail("DUPLICATE_OPERATION", "authorized federation operations MUST be unique")
    return normalized


@dataclass(frozen=True)
class FederationEgressPolicy:
    """Local reference policy for outbound federation endpoint authorization."""

    policy_id: str
    policy_version: int
    allowed_hosts: tuple[str, ...]
    allowed_ports: tuple[int, ...] = (443,)
    max_path_bytes: int = MAX_PATH_BYTES
    max_authorization_lifetime_seconds: int = MAX_AUTHORIZATION_LIFETIME_SECONDS

    def __post_init__(self) -> None:
        _ascii_text(self.policy_id, name="policy_id", max_bytes=MAX_POLICY_ID_BYTES)
        if isinstance(self.policy_version, bool) or not isinstance(self.policy_version, int) or self.policy_version < 1:
            raise ValueError("policy_version MUST be a positive integer")
        if not isinstance(self.allowed_hosts, tuple) or not 1 <= len(self.allowed_hosts) <= MAX_ALLOWED_HOSTS:
            raise ValueError(f"allowed_hosts MUST contain 1..{MAX_ALLOWED_HOSTS} entries")
        canonical_hosts = tuple(_canonical_dns_name(host, policy_entry=True) for host in self.allowed_hosts)
        if canonical_hosts != tuple(sorted(canonical_hosts, key=lambda host: host.encode("ascii"))):
            raise ValueError("allowed_hosts MUST be sorted in canonical ASCII order")
        if len(canonical_hosts) != len(set(canonical_hosts)):
            raise ValueError("allowed_hosts MUST be unique")
        if not isinstance(self.allowed_ports, tuple) or not 1 <= len(self.allowed_ports) <= MAX_ALLOWED_PORTS:
            raise ValueError(f"allowed_ports MUST contain 1..{MAX_ALLOWED_PORTS} entries")
        for port in self.allowed_ports:
            if isinstance(port, bool) or not isinstance(port, int) or not 1 <= port <= 65_535:
                raise ValueError("allowed_ports MUST contain valid integer TCP ports")
        if self.allowed_ports != tuple(sorted(self.allowed_ports)) or len(self.allowed_ports) != len(set(self.allowed_ports)):
            raise ValueError("allowed_ports MUST be sorted and unique")
        if isinstance(self.max_path_bytes, bool) or not isinstance(self.max_path_bytes, int) or not 1 <= self.max_path_bytes <= MAX_PATH_BYTES:
            raise ValueError(f"max_path_bytes MUST be within 1..{MAX_PATH_BYTES}")
        lifetime = self.max_authorization_lifetime_seconds
        if isinstance(lifetime, bool) or not isinstance(lifetime, int) or not 1 <= lifetime <= MAX_AUTHORIZATION_LIFETIME_SECONDS:
            raise ValueError(
                "max_authorization_lifetime_seconds MUST be within "
                f"1..{MAX_AUTHORIZATION_LIFETIME_SECONDS}"
            )


@dataclass(frozen=True)
class CanonicalFederationEndpoint:
    """Canonical endpoint value produced by the M25 reference policy."""

    url: str
    hostname: str
    port: int
    path: str


@dataclass(frozen=True)
class FederationEndpointAuthorization:
    """Short-lived local authorization for one exact endpoint and operation set."""

    authorization_id: str
    policy_id: str
    policy_version: int
    canonical_endpoint: str
    hostname: str
    port: int
    path_mode: str
    path: str
    allowed_operations: tuple[str, ...]
    issued_at_epoch: int
    expires_at_epoch: int
    establishes_marketplace_authorization: bool = False
    establishes_agreement: bool = False
    establishes_trust: bool = False


@dataclass(frozen=True)
class ResolvedEndpointAddresses:
    """Caller-supplied resolver results after pure address classification."""

    hostname: str
    addresses: tuple[str, ...]
    dns_was_performed: bool = False
    safe_forever: bool = False


def canonicalize_federation_endpoint(
    endpoint: object,
    policy: FederationEgressPolicy,
) -> CanonicalFederationEndpoint:
    """Canonicalize an exact HTTPS endpoint without resolving or contacting it."""
    if not isinstance(policy, FederationEgressPolicy):
        raise TypeError("policy MUST be FederationEgressPolicy")
    raw = _ascii_text(endpoint, name="endpoint", max_bytes=MAX_ENDPOINT_BYTES)
    if "\\" in raw:
        _fail("AMBIGUOUS_ENDPOINT", "endpoint MUST NOT contain backslashes")
    try:
        parsed = urlsplit(raw, allow_fragments=True)
        port = parsed.port
    except ValueError as exc:
        _fail("INVALID_ENDPOINT", f"endpoint could not be parsed safely: {exc}")
    if parsed.scheme.lower() != "https":
        _fail("HTTPS_REQUIRED", "federation endpoint scheme MUST be https")
    if not parsed.netloc:
        _fail("MISSING_HOST", "federation endpoint MUST include a hostname")
    if "@" in parsed.netloc or parsed.username is not None or parsed.password is not None:
        _fail("USERINFO_FORBIDDEN", "endpoint userinfo/credentials are forbidden")
    if "%" in parsed.netloc:
        _fail("AMBIGUOUS_HOSTNAME", "percent-encoded endpoint authority is forbidden")
    if parsed.query:
        _fail("QUERY_FORBIDDEN", "endpoint base MUST NOT contain a query string")
    if parsed.fragment:
        _fail("FRAGMENT_FORBIDDEN", "endpoint MUST NOT contain a fragment")
    hostname_value = parsed.hostname
    if hostname_value is None:
        _fail("MISSING_HOST", "federation endpoint MUST include a hostname")
    hostname = _canonical_dns_name(hostname_value)
    if hostname not in policy.allowed_hosts:
        _fail("HOST_NOT_ALLOWLISTED", f"hostname {hostname!r} is not explicitly allowlisted")
    resolved_port = 443 if port is None else port
    if resolved_port not in policy.allowed_ports:
        _fail("PORT_NOT_ALLOWLISTED", f"port {resolved_port} is not explicitly allowlisted")
    path = _canonical_path(parsed.path, policy.max_path_bytes)
    port_suffix = "" if resolved_port == 443 else f":{resolved_port}"
    return CanonicalFederationEndpoint(
        url=f"https://{hostname}{port_suffix}{path}",
        hostname=hostname,
        port=resolved_port,
        path=path,
    )


def authorize_federation_endpoint(
    *,
    endpoint: object,
    allowed_operations: Iterable[object],
    authorization_id: object,
    issued_at_epoch: int,
    expires_at_epoch: int,
    policy: FederationEgressPolicy,
) -> FederationEndpointAuthorization:
    """Create short-lived local endpoint authorization; performs no network I/O."""
    canonical = canonicalize_federation_endpoint(endpoint, policy)
    operations = _canonical_operations(allowed_operations)
    authorization_text = _ascii_text(
        authorization_id,
        name="authorization_id",
        max_bytes=MAX_AUTHORIZATION_ID_BYTES,
    )
    for name, value in (("issued_at_epoch", issued_at_epoch), ("expires_at_epoch", expires_at_epoch)):
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            _fail("INVALID_AUTHORIZATION_TIME", f"{name} MUST be a non-negative integer epoch second")
    if expires_at_epoch <= issued_at_epoch:
        _fail("INVALID_AUTHORIZATION_WINDOW", "authorization expiry MUST be later than issuance")
    if expires_at_epoch - issued_at_epoch > policy.max_authorization_lifetime_seconds:
        _fail(
            "AUTHORIZATION_WINDOW_TOO_LONG",
            "authorization lifetime exceeds the selected egress policy maximum",
        )
    return FederationEndpointAuthorization(
        authorization_id=authorization_text,
        policy_id=policy.policy_id,
        policy_version=policy.policy_version,
        canonical_endpoint=canonical.url,
        hostname=canonical.hostname,
        port=canonical.port,
        path_mode="EXACT",
        path=canonical.path,
        allowed_operations=operations,
        issued_at_epoch=issued_at_epoch,
        expires_at_epoch=expires_at_epoch,
    )


def validate_endpoint_authorization(
    authorization: FederationEndpointAuthorization,
    *,
    endpoint: object,
    operation: object,
    now_epoch: int,
    policy: FederationEgressPolicy,
) -> CanonicalFederationEndpoint:
    """Re-validate an authorization against exact current caller intent."""
    if not isinstance(authorization, FederationEndpointAuthorization):
        _fail("INVALID_AUTHORIZATION", "authorization has the wrong type")
    if isinstance(now_epoch, bool) or not isinstance(now_epoch, int) or now_epoch < 0:
        _fail("INVALID_CURRENT_TIME", "now_epoch MUST be a non-negative integer epoch second")
    operation_text = _ascii_text(operation, name="operation", max_bytes=MAX_OPERATION_BYTES)
    canonical = canonicalize_federation_endpoint(endpoint, policy)
    if authorization.policy_id != policy.policy_id or authorization.policy_version != policy.policy_version:
        _fail("AUTHORIZATION_POLICY_MISMATCH", "authorization was issued under a different egress policy")
    if authorization.establishes_marketplace_authorization or authorization.establishes_agreement or authorization.establishes_trust:
        _fail("AUTHORIZATION_AUTHORITY_ESCALATION", "endpoint authorization MUST NOT claim Marketplace authority")
    expected_binding = (
        canonical.url,
        canonical.hostname,
        canonical.port,
        "EXACT",
        canonical.path,
    )
    actual_binding = (
        authorization.canonical_endpoint,
        authorization.hostname,
        authorization.port,
        authorization.path_mode,
        authorization.path,
    )
    if actual_binding != expected_binding:
        _fail("AUTHORIZATION_ENDPOINT_MISMATCH", "authorization does not bind the exact endpoint")
    normalized_operations = _canonical_operations(authorization.allowed_operations)
    if normalized_operations != authorization.allowed_operations:
        _fail("INVALID_AUTHORIZATION", "authorization operation set is not canonical")
    if operation_text not in normalized_operations:
        _fail("OPERATION_NOT_AUTHORIZED", "federation operation is not authorized for this endpoint")
    if authorization.expires_at_epoch <= authorization.issued_at_epoch:
        _fail("INVALID_AUTHORIZATION_WINDOW", "authorization carries an invalid validity window")
    if authorization.expires_at_epoch - authorization.issued_at_epoch > policy.max_authorization_lifetime_seconds:
        _fail("AUTHORIZATION_WINDOW_TOO_LONG", "authorization exceeds current egress policy lifetime")
    if now_epoch < authorization.issued_at_epoch:
        _fail("AUTHORIZATION_NOT_YET_VALID", "endpoint authorization is not yet valid")
    if now_epoch >= authorization.expires_at_epoch:
        _fail("AUTHORIZATION_EXPIRED", "endpoint authorization has expired")
    return canonical


def _validate_global_unicast_address(value: object) -> ipaddress.IPv4Address | ipaddress.IPv6Address:
    text = _ascii_text(value, name="resolved_address", max_bytes=64)
    try:
        address = ipaddress.ip_address(text)
    except ValueError:
        _fail("INVALID_RESOLVED_ADDRESS", f"resolver result {text!r} is not an IP address")
    if isinstance(address, ipaddress.IPv6Address) and address.ipv4_mapped is not None:
        _fail("IPV4_MAPPED_IPV6_FORBIDDEN", "IPv4-mapped IPv6 results are rejected by the reference policy")
    if (
        not address.is_global
        or address.is_private
        or address.is_loopback
        or address.is_link_local
        or address.is_multicast
        or address.is_unspecified
        or address.is_reserved
    ):
        _fail("UNSAFE_RESOLVED_ADDRESS", f"resolved address {address.compressed!r} is not global unicast")
    return address


def validate_resolved_addresses(
    hostname: object,
    addresses: Iterable[object],
    *,
    max_addresses: int = MAX_RESOLVED_ADDRESSES,
) -> ResolvedEndpointAddresses:
    """Validate caller-supplied DNS results without performing DNS itself."""
    canonical_hostname = _canonical_dns_name(hostname)
    if isinstance(max_addresses, bool) or not isinstance(max_addresses, int) or not 1 <= max_addresses <= MAX_RESOLVED_ADDRESSES:
        _fail("INVALID_ADDRESS_LIMIT", f"max_addresses MUST be within 1..{MAX_RESOLVED_ADDRESSES}")
    parsed: list[ipaddress.IPv4Address | ipaddress.IPv6Address] = []
    for index, value in enumerate(addresses):
        if index >= max_addresses:
            _fail("RESOLVED_ADDRESS_LIMIT_EXCEEDED", "resolver returned too many addresses")
        parsed.append(_validate_global_unicast_address(value))
    if not parsed:
        _fail("EMPTY_RESOLUTION", "resolver result MUST contain at least one address")
    canonical = tuple(
        str(address)
        for address in sorted(
            set(parsed),
            key=lambda address: (address.version, address.packed),
        )
    )
    return ResolvedEndpointAddresses(
        hostname=canonical_hostname,
        addresses=canonical,
    )
