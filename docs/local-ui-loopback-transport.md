# M78 — Explicit One-Shot Local UI Loopback Transport

## Baseline

M78 starts from merged-green M77 commit
`718b95a52789e4297adf0fa22eeb730188ddf31f`.

M77 already owns the bounded transport-free HTTP application contract for the local visual buy/sell flow. M78 adds the smallest separately governed transport edge able to host exactly one M77 request/response transaction on IPv4 loopback.

## Architecture decision

The existing M59–M70 loopback execution graph remains semantically bound to federation and immutable-record serving. Reusing that graph for the local Marketplace UI would conflate two distinct authority domains. M78 therefore adds a UI-specific reference transport rather than relabeling federation transport as UI transport.

The packaged `marketplace.reference.local_ui_loopback_v1` module does **not** choose a real socket provider. A caller must supply both:

1. the exact execution opt-in token `EXECUTE_ONE_LOCAL_UI_LOOPBACK_SESSION`; and
2. an explicit socket-constructor capability.

The repository-only `tools/local_ui_loopback_acceptance.py` tool is the only M78 artifact that can select Python's real `socket.socket`, and that import occurs only inside the real-provider function after the command-line execution token has been validated. Import, help, invalid input, and dry-run paths remain network-inert.

Risk classification: **MODERATE source-level local transport authority**. Source/CI development uses deterministic injected doubles and does not exercise live bind/listen/accept.

## Endpoint and authority boundary

The endpoint is fixed by source code:

- address family: IPv4;
- transport: TCP stream;
- bind host: exact `127.0.0.1`;
- port: exact integer `1024..65535`, selected by the caller;
- backlog: exactly `1`;
- accepted peer: must report exact IPv4 loopback host `127.0.0.1`;
- one listener, one accepted connection, one request, one response, then close.

There is no caller-controlled host/interface, wildcard bind, DNS, TLS, proxy, redirect target, remote destination, or outbound `connect()` surface.

M78 execution opt-in is a runtime capability gate only. It is **not** repository merge authorization, deployment authorization, provider administration authority, credential authority, payment authority, settlement authority, or permission for external networking.

## HTTP/1.1 request boundary

M78 reads at most one request under fixed byte/call ceilings and then constructs the exact M77 `LocalUiHttpRequest` object.

Reviewed bounds:

- request head: max 8,192 bytes;
- M77 request body: max 49,152 bytes;
- request headers: max 32;
- per header value: max 4,096 ASCII bytes;
- read calls: max 64;
- read chunk: max 4,096 bytes;
- listener/connection socket timeout: 5 seconds.

The wire parser requires exact HTTP/1.1 framing, exact CRLF line endings, a single `Host` header equal to `127.0.0.1:<port>`, canonical bounded decimal `Content-Length` when present, unique bounded ASCII header names, and bounded printable ASCII header values.

Credential/session or ambiguous transport headers are rejected, including `Authorization`, `Proxy-Authorization`, `Cookie`, `Set-Cookie`, `Transfer-Encoding`, `Expect`, `Upgrade`, `TE`, `Trailer`, and proxy-connection headers.

Already-received bytes beyond the declared request are rejected as trailing/pipelined input. The one-shot close prevents any later bytes from becoming a second request on the same accepted connection.

M78 does not reinterpret Marketplace fields. Once wire framing succeeds, M77 remains the exact HTTP application path; M76/M75/M74 remain authoritative for visual submission, human-field validation, Marketplace construction, local publish/search/resolve/match behavior, and semantic non-authority.

## HTTP response boundary

M78 accepts only the exact M77 `LocalUiHttpResponse` type, independently rechecks status/header/body framing invariants, appends `Connection: close`, and transmits the response under a fixed 128-call write ceiling.

The M77 `Content-Length` must exactly match the response body. Duplicate response headers, a pre-existing `Connection` header, malformed ASCII metadata, or an oversized response fail closed before transmission completes.

M78 does not add cookies, CORS widening, authentication claims, redirects, external assets, sessions, or browser authority.

## Cleanup and terminal behavior

Connection and listener close are each attempted exactly once before the function returns or raises. Close failure is reported only as stable `CLEANUP_UNCERTAIN`; caller-controlled exception text is never reflected.

All other lower transport/application failures are mapped to stable bounded M78 error codes without raw request/form/exception reflection. The returned `LocalUiLoopbackResult` contains metadata only: host, port, method, target, status, byte counts, and explicit negative authority flags. It retains no request bytes, response bytes, body, form values, transcript, or live socket object.

## Retention

M78 adds no file/database persistence, request archive, response archive, transcript, log sink, cookie store, session store, cache, telemetry payload store, background worker, or daemon lifecycle.

Request/response bytes exist only during the synchronous one-shot call. M74 remains the owner of the underlying Marketplace runtime and its existing EPHEMERAL / maximum 10-second retention boundary. M77 responses still carry `Cache-Control: no-store`.

## Manual acceptance tool

Dry-run is network-inert:

```text
python tools/local_ui_loopback_acceptance.py --port 8767 --dry-run
```

A live one-shot bind/listen/accept requires the exact runtime opt-in token:

```text
python tools/local_ui_loopback_acceptance.py --port 8767 --execute-one-local-ui-loopback-session EXECUTE_ONE_LOCAL_UI_LOOPBACK_SESSION
```

The tool does not launch a browser. A live manual acceptance run is a separate deliberate execution action and is not performed merely because the source or PR is approved.

## Capability boundary

Development/CI capabilities exercised:

- `READ_PROJECT`;
- `WRITE_PROJECT`;
- deterministic `EXECUTE_LOCAL` with injected socket doubles.

Latent/manual authority added by reviewed source:

- one explicit local IPv4 loopback bind/listen/accept/send/receive transaction after exact runtime opt-in.

Not requested or authorized by M78:

- `NETWORK_EXTERNAL`;
- DNS or TLS;
- outbound connection authority;
- browser launch or browser automation;
- multi-request server loops or background service lifecycle;
- deployment or production operation;
- credentials, cookies, authentication/session secrets, or secret management;
- durable filesystem/database persistence;
- payment, settlement, ownership/inventory mutation, agreement creation, or protocol-truth promotion;
- subprocess, thread, queue, watcher, scheduler, or daemon authority;
- provider administration.

## Tests-first provenance

Branch history preserves the required order:

- `f2e9da2e55a817034e23fe918b914665d4bb191f` — M78 behavior/security contract committed before `local_ui_loopback_v1.py` existed;
- `7a40038796893c9b1281a08a7a4b90efb187bae7` — packaged one-shot transport implementation;
- `62fff6d39be824d20d06baf1710672291b453206` — artifact/authority contract committed while the manual tool, export, and this document were still absent;
- `e4dfedad996d36e4cf80017f92660e078c44ba92` — repository-only explicit manual socket-provider tool;
- `4e53216245e8cd92196da00593fdd7a84d45c56a` — reviewed public reference export.

## Optimization evidence

The transport owns only one bounded request/response transaction. It contains no accept loop, retry loop, polling loop, background task, queue, thread, subprocess, filesystem scan, DNS lookup, TLS handshake, outbound connection, or browser action.

Request accumulation is linear in a hard-capped request size and uses a single byte buffer. Header parsing occurs once after the terminator is found. M77 is invoked exactly once. Response framing occurs once, followed by bounded forward-only partial-write accounting. Socket cleanup is one attempt per owned object with no retry.

This intentionally optimizes for small authority surface, deterministic cleanup, and reviewability rather than throughput; no existing quality/security/conformance gate is reduced.

## Next boundary

After M78 is merged-green, reassess whether a separately governed **live local visual acceptance milestone** is justified. Such a milestone may exercise the repository-only one-shot loopback tool on a workstation and validate the GET/POST wire path with an explicit local client, but browser launch/automation, multi-request service lifetime, deployment, external networking, credentials, persistence, payments, and settlement remain separate authority decisions.
