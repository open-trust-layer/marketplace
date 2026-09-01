# M79 — Bounded One-Shot Local UI Loopback Acceptance Client

## Baseline

M79 starts from merged-green M78 commit
`2a58f6c1cb9736a3e5a333152efbc06c8732e718`.

M78 provides the reviewed one-shot local UI host. M79 adds the smallest matching
client-side acceptance primitive so the exact M78 wire boundary can later be exercised
without adding a browser, external networking, a multi-request service loop, or a
second Marketplace semantic path.

## Architecture decision

The client lives in `marketplace.reference` because it is specifically an acceptance
edge for the OLP-dependent local Marketplace UI path. It does not reuse or relabel the
M59–M70 federation/record-serving graph.

Packaged `local_ui_loopback_client_v1` never selects a real socket provider. A caller
must supply:

1. exact runtime opt-in `EXECUTE_ONE_LOCAL_UI_LOOPBACK_CLIENT`;
2. an exact M77 `LocalUiHttpRequest`; and
3. an injected socket-constructor capability.

Source and CI tests use deterministic doubles only. A real `connect()` is not exercised
by implementation or CI and remains a separately authorized runtime action.

Risk classification: **MODERATE source-level local client transport authority**.

## Endpoint boundary

The destination is fixed in source:

- IPv4 TCP stream;
- exact host `127.0.0.1`;
- exact integer port `1024..65535` selected by the caller;
- one socket, one connect, one request, one response, then close;
- 5-second socket timeout;
- no DNS, TLS, proxy, redirect target, hostname normalization, wildcard interface, or external destination.

The M79 client opt-in is distinct from the M78 host opt-in. Neither token is merge,
deployment, credential, payment, settlement, or external-network authorization.

## Request boundary

M79 accepts only the exact M77 request type and the two reviewed local UI profiles:

- `GET /` with no body and no content type;
- `POST /local-buy-sell` with exact
  `application/x-www-form-urlencoded` and a non-empty body bounded by the existing
  M77 49,152-byte request maximum.

The client serializes strict HTTP/1.1 with exact `Host: 127.0.0.1:<port>` and
`Connection: close`. POST adds exact `Content-Type` and canonical `Content-Length`.
No Authorization, Cookie, proxy, forwarding, upgrade, transfer-encoding, or browser
headers are added.

M79 does not parse or reinterpret seller/buyer form fields. M77/M76/M75/M74 remain the
only Marketplace semantic path.

## Response boundary

The client reads one response under fixed bounds:

- response head: max 8,192 bytes;
- response body: max 65,536 bytes;
- headers: max 32;
- per header value: max 4,096 printable ASCII bytes;
- read calls: max 64;
- write calls: max 64;
- I/O chunk: max 4,096 bytes.

The response must use exact HTTP/1.1 framing and a canonical decimal `Content-Length`.
Duplicate, unknown, malformed, transfer-encoding, credential/session, redirect, or
ambiguous headers fail closed. Bytes received beyond the declared response are rejected.
The body must be valid UTF-8 but is not returned or retained.

The following M77/M78 security headers are independently required with exact values:

- `Content-Type: text/html; charset=utf-8`;
- `Cache-Control: no-store`;
- `X-Content-Type-Options: nosniff`;
- `Referrer-Policy: no-referrer`;
- the reviewed restrictive Content Security Policy;
- `Connection: close` from M78 framing.

`Allow` is the only optional response header because M77 may emit it for a 405 response.

## Result, errors, and cleanup

`LocalUiLoopbackClientResult` is frozen and metadata-only. It contains host, port,
request method/target, status, byte counts, and explicit negative authority flags. It
contains no request bytes, response bytes, body, form values, transcript, socket, or
human content.

Connection, write, read, framing, and provider failures map to stable bounded error codes
without reflecting exception or payload text. Socket close is attempted once before
return; inability to confirm cleanup becomes `CLEANUP_UNCERTAIN`.

## Manual acceptance tool

Repository-only `tools/local_ui_loopback_client_acceptance.py` provides deterministic
GET and POST fixtures.

Network-inert planning examples:

```text
python tools/local_ui_loopback_client_acceptance.py --port 8780 --request get --dry-run
python tools/local_ui_loopback_client_acceptance.py --port 8780 --request post --dry-run
```

A real one-shot client requires the exact M79 token:

```text
python tools/local_ui_loopback_client_acceptance.py --port 8780 --request get --execute-one-local-ui-loopback-client EXECUTE_ONE_LOCAL_UI_LOOPBACK_CLIENT
```

The tool does not launch M78, a browser, or a subprocess. It assumes an independently
started and separately authorized M78 one-shot host is already listening.

## Retention and privacy

M79 adds no file/database persistence, request/response archive, transcript, log sink,
telemetry payload store, cookie/session store, cache, queue, thread, subprocess, worker,
or daemon lifecycle.

Wire bytes exist only during one synchronous client call and are released before return.
The existing project EPHEMERAL content maximum of 10 seconds remains controlling.

## Tests-first provenance

Branch history preserves the required ordering:

- `43b44efb9b4b51d86d42e5c2cfb35d8900939a93` — behavior/security tests before implementation;
- `1244cd27ffbdcc3df14f4604ce0ce7ba1abaa0a1` — packaged client implementation;
- `5e29f4ead01a1f6a8044142cbc523e31c7a30c46` — artifact/authority tests before tool/export/document completion;
- `bbe07c67d50175b5e40178c46cde532df28bea23` — inert-by-default repository-only manual client tool;
- `0ca2b0c6157ed7b661ecc2dc9255aa6e9083fd38` — public reference export.

## Optimization evidence

The client owns one bounded transaction only. There is no retry, polling, connection
pool, keep-alive reuse, background task, thread, subprocess, filesystem scan, DNS lookup,
TLS handshake, browser action, or external route.

Request serialization performs one fixed-header construction and one body append. Writes
advance monotonically under a 64-call ceiling. Response accumulation uses one bounded
byte buffer, parses the head once after the terminator is found, and stops at the exact
declared body length. Cleanup is one close attempt.

The optimization target is a minimal authority surface and deterministic reviewability;
no existing quality, security, conformance, artifact, or cleanup gate is weakened.

## Capability boundary

Development/CI authority exercised:

- `READ_PROJECT`;
- `WRITE_PROJECT`;
- deterministic local execution using injected socket doubles.

Latent/manual authority added by reviewed source:

- one explicit IPv4 loopback `connect/send/recv/close` transaction after exact M79 opt-in.

Not authorized by M79 implementation/CI:

- live socket execution;
- external networking, DNS, or TLS;
- browser launch/automation;
- service deployment or multi-request runtime;
- subprocess orchestration of host and client;
- credentials, cookies, authentication/session secrets;
- durable persistence;
- payment, settlement, ownership/inventory mutation, agreement creation, or protocol-truth promotion;
- provider administration.

## Next boundary

After M79 is merged-green, a separately authorized live acceptance may run the reviewed
M78 host and M79 client on one workstation, first GET then POST, using an operator-selected
loopback port and explicit runtime tokens. That live action must remain separate from merge
authorization and does not imply browser, deployment, external-network, credential, payment,
or settlement authority.
