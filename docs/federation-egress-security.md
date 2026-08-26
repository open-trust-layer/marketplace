# Federation Egress Security Boundary

Status: Milestone 25 reference implementation

## Purpose

Milestone 25 establishes a deterministic, fail-closed outbound federation destination policy **before Marketplace gains concrete network capability**.

It validates configured HTTPS endpoints, creates short-lived local endpoint authorizations, and classifies caller-supplied resolver results. It does not resolve DNS, open sockets, perform TLS, make HTTP requests, read proxy configuration, read credentials, retry remote operations, or send any Marketplace data.

```text
configured endpoint          != authorized endpoint
authorized endpoint          != resolved endpoint
resolved address             != safe forever
safe address classification  != successful TLS connection
endpoint authorization       != Marketplace operation authorization
transport authorization      != agreement / trust / legitimacy
URL parsing                  != permission to connect
```

The existing Milestone 24 offline federation service remains the only federation runtime service. M25 adds a security prerequisite for a future concrete transport; it does not add transmission.

## Reference module

The package exposes the M25 boundary at:

```text
marketplace.runtime.network_policy
```

The module uses only a reviewed deterministic standard-library import surface for parsing and address classification. It contains no DNS/network/TLS/process/environment/credential access, file I/O, or dynamic code execution.

## Endpoint policy

`FederationEgressPolicy` defines explicit local policy inputs:

```text
policy_id
policy_version
allowed_hosts
allowed_ports
max_path_bytes
max_authorization_lifetime_seconds
```

The reference profile is deliberately restrictive.

A configured federation endpoint must:

- use `https`;
- use an explicitly allowlisted DNS name;
- use ASCII-only, canonical DNS labels;
- not use a trailing dot, repeated dots, percent-encoded authority, underscore labels, IDNA/punycode, or IP literal;
- contain no userinfo or embedded credentials;
- use an explicitly allowed TCP port;
- contain no query string or fragment;
- use an ASCII path from the reference safe subset;
- contain no percent-encoded path, backslash, repeated slash, `.` segment, or `..` segment;
- stay within the configured path and endpoint byte limits.

Host comparison is performed on a canonical lowercase DNS name, so case differences cannot bypass the allowlist. Allowlist entries themselves must already be lowercase, sorted, and unique.

The default/reference port policy is `443` only. Additional ports require explicit policy configuration.

## Short-lived endpoint authorization

`authorize_federation_endpoint(...)` creates an immutable `FederationEndpointAuthorization` bound to:

```text
authorization_id
policy_id
policy_version
canonical_endpoint
hostname
port
path_mode = EXACT
path
allowed_operations
issued_at_epoch
expires_at_epoch
```

The maximum reference authorization lifetime is 300 seconds, and a selected policy may make it shorter.

`validate_endpoint_authorization(...)` does not trust the dataclass instance merely because its type is correct. It revalidates the public/fabricatable authorization shape, exact negative authority flags, endpoint, policy and operation at use time and fails closed when:

- authorization identifier, policy identifier/version, time values, or operation collection are malformed;
- policy id/version changed;
- endpoint/host/port/path no longer match exactly;
- operation is not explicitly authorized;
- authorization is not yet valid;
- authorization is expired;
- the validity window exceeds current policy;
- any negative authority flag is not exactly `false`.

The result is local operator egress-policy evidence only.

```text
endpoint authorization != M11 protected-operation authorization
endpoint authorization != legal permission
endpoint authorization != peer trust
```

M26 must revalidate authorization immediately before any external connection attempt.

## Resolver-result classification

`validate_resolved_addresses(...)` accepts resolver results supplied by a caller. It performs no DNS itself.

The reference classifier rejects addresses that are:

- non-IP text;
- loopback;
- private;
- link-local;
- multicast;
- unspecified;
- reserved/non-global;
- IPv4-mapped IPv6;
- IPv6 transition/tunnel forms such as 6to4 and Teredo;
- IPv6 translation/NAT64 prefixes `64:ff9b::/96` and `64:ff9b:1::/48`.

Only ordinary global-unicast IPv4/IPv6 results outside those transition/translation forms are accepted. Results are bounded, deduplicated, and canonicalized.

The returned `ResolvedEndpointAddresses` explicitly records:

```text
dns_was_performed = false
safe_forever       = false
```

This is intentional. A previous classification does not authorize a future connection.

## DNS-rebinding boundary

M25 does not attempt to solve DNS rebinding by caching a prior lookup. Instead it establishes the rule a concrete transport must follow:

1. revalidate the short-lived endpoint authorization immediately before network use;
2. freshly resolve the approved hostname;
3. reject the exchange if resolution is empty, excessive, malformed, or contains an unsafe address;
4. select/connect only to an address from that freshly validated set;
5. preserve the approved DNS hostname for TLS SNI and certificate hostname verification;
6. do not silently re-resolve to a different address inside a generic HTTP client after policy validation.

The actual resolver and connection implementation belong to M26 and require their own negative tests.

## Ambient environment isolation

M25 reads no ambient process/network configuration.

A future reference transport MUST NOT silently inherit:

- `HTTP_PROXY`, `HTTPS_PROXY`, `ALL_PROXY`, or equivalent proxy environment variables;
- `.netrc` credentials;
- user/global credential stores;
- process-global URL opener handlers;
- system configuration that silently introduces redirects or proxy routing outside the reviewed connection path.

If proxy support is ever added, it requires an explicit separately reviewed policy and must preserve the same destination authorization semantics.

## Executable no-network invariant

M25 tests inspect `src/marketplace/runtime/network_policy.py` and constrain it to the reviewed import surface:

```text
__future__
ipaddress
re
collections.abc
dataclasses
typing
urllib.parse
```

They also reject dynamic import/eval/exec, file opening/compilation, and concrete DNS/network/TLS/process/environment/credential capabilities. The module may parse URLs through `urllib.parse`; it cannot use `urllib.request`.

The base package dependency list remains empty.

The reproducible artifact gate explicitly requires:

```text
marketplace/runtime/network_policy.py
```

so a built Marketplace wheel cannot pass acceptance after silently dropping the security boundary.

The repository audit also requires this document and the runtime module.

## Retention and logging

M25 introduces no persisted records, messages, DNS cache, request log, credential material, or remote telemetry.

Endpoint-policy objects are ordinary process-local Python values. M25 adds no persistence mechanism for them.

A future network adapter must keep operational logs metadata-only by default and must not log request/response bodies, credentials, authorization tokens, raw evidence, or other content-bearing payloads into long-lived logs.

## What M25 does not do

Milestone 25 intentionally does not implement:

- DNS lookup;
- sockets;
- HTTP clients or servers;
- TLS contexts or handshakes;
- redirects;
- proxies;
- authentication headers or credentials;
- retries/backoff;
- rate limiting;
- connection pooling;
- background synchronization;
- endpoint discovery;
- live federation peers;
- network logging/telemetry;
- agreement formation;
- settlement/fulfillment execution;
- protected side effects.

## M26 entry criteria

The first concrete HTTPS federation transport may begin only after M25 is merged and merged-main CI is green.

M26 must consume the M25 policy rather than implementing a parallel destination validator. At minimum it must add and test:

- fresh DNS resolution immediately before connection;
- DNS-rebinding-resistant connection to a validated selected address;
- TLS certificate and hostname verification with the authorized DNS hostname;
- no plaintext HTTP fallback;
- redirects disabled by default;
- ambient proxies disabled by default;
- explicit connect/read/total timeout budgets;
- strict request and response byte limits;
- bounded concurrency;
- deterministic response-envelope handling;
- privacy-safe metadata-only diagnostics;
- explicit behavior for authentication and credentials, if introduced;
- bounded retry behavior tied to operation/idempotency semantics, if introduced.

M26 is a higher-risk capability milestone because it will request `NETWORK_EXTERNAL`. M25 deliberately stops before that boundary.
