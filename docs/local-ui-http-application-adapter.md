# M77 — Bounded Local UI HTTP Application Adapter

## Baseline

M77 starts from merged-green M76 commit
`cfa9a180d19d3ed5d039e96de3c7dd7c8fbbb3ce`.

M76 already owns the deterministic HTML form/result contract and delegates all human Marketplace semantics through M75 into M72/M74. M77 adds only a strict HTTP application boundary above M76. It deliberately does not add a socket, listener, browser launcher, deployment process, or second Marketplace path.

## Architecture/risk audit

The repository already contains a hardened M59–M70 loopback execution graph, but that graph is semantically bound to federation and record-serving routes. Reusing it for local Marketplace UI traffic would conflate distinct authority domains and make UI requests appear to be federation traffic.

M77 therefore introduces a new UI-only adapter in `marketplace.reference`. It consumes an already-framed request object and returns an already-framed response object. Transport ownership remains absent. A following milestone may place exactly this adapter behind one explicitly authorized one-shot loopback transport.

Risk: **MODERATE transport-free local HTTP application adapter**.

## Public surface

`LocalUiHttpRequest` is an exact frozen/slotted request object containing:

- method;
- target;
- optional content type; and
- body bytes.

`LocalUiHttpResponse` is an exact frozen/slotted response object containing:

- status code;
- reason phrase;
- ordered immutable headers; and
- response body bytes.

`handle_local_ui_http_request()` accepts only the exact request type and exact primitive field types. Request metadata is bounded before route handling.

## Exact routes

Only two local UI routes exist:

- `GET /` — returns the exact M76 `render_local_buy_sell_form()` output;
- `POST /local-buy-sell` — accepts one bounded form submission and delegates to the exact M76 `submit_local_buy_sell_form()` path.

Any other target returns a stable `404`. A known route with the wrong method returns stable `405` plus an exact `Allow` header. Lowercase or alternate method spellings are not normalized.

`GET /` accepts neither a body nor a content type.

## Form decoding

POST accepts only exact `application/x-www-form-urlencoded`.

The encoded body is capped at **49,152 bytes before decoding or field materialization**. This bound covers the reviewed M75 field maxima even under percent-encoding expansion while remaining finite and explicit.

The parser requires exactly twelve ampersand-separated pairs and exactly the twelve M76 field names, once each:

- `seller_principal`;
- `subject_uri`;
- `title`;
- `description`;
- `consideration`;
- `currency_code`;
- `quantity`;
- `unit_uri`;
- `latitude`;
- `longitude`;
- `buyer_principal`; and
- `buyer_action_uri`.

Field names are required in their literal reviewed ASCII spelling. Unknown, missing, duplicate, malformed, or noncanonical pairs fail closed. Percent escapes are decoded by a bounded local decoder; malformed escapes and invalid UTF-8 fail closed. `+` is interpreted as SP according to the form encoding.

M77 does **not** duplicate M75/M76 human-field validation. Once transport decoding succeeds, values are placed into the exact `LocalVisualSubmission` type and M76 remains authoritative for human input, Marketplace construction, local publish/search/resolve/match, and false authority flags.

## Response safety

Every response is bounded to 65,536 UTF-8 bytes and carries deterministic headers including:

- `Content-Type: text/html; charset=utf-8`;
- exact `Content-Length`;
- `Cache-Control: no-store`;
- `X-Content-Type-Options: nosniff`;
- `Referrer-Policy: no-referrer`; and
- a restrictive Content Security Policy with `default-src 'none'`, local self form submission, inline style allowance for the reviewed M76 page, no base URI, and no framing.

M77 emits no cookies, session identifiers, redirects, CORS widening, authentication claims, external resource references, or raw hostile-input reflection.

Stable application failures use bounded fixed HTML. Invalid M76 submission data maps to `400`; unexpected reviewed M76 execution failure maps to a fixed `500` without reflecting lower-layer exception text.

## Retention

M77 adds no persistence, transcript, request archive, log sink, cookie, session, cache, or runtime owner. `Cache-Control: no-store` explicitly tells a future HTTP host not to retain page responses. Request and form-decoding objects exist only for the synchronous call. M74 remains the owner of the underlying Marketplace runtime and its existing EPHEMERAL / maximum 10-second retention policy.

## Capability boundary

Exercised capabilities:

- repository source read/write during development;
- deterministic local byte/string/object execution in tests and CI.

Not requested or exercised:

- `NETWORK_EXTERNAL`;
- loopback socket bind/listen/accept/connect;
- DNS or TLS;
- live HTTP client/server execution;
- browser launch or browser automation;
- external map-provider access;
- credentials, login/session secrets, cookies, or identity-secret handling;
- durable filesystem/database persistence;
- subprocess, shell, thread, timer, queue, watcher, or background worker;
- agreement creation, payment, settlement, asset transfer, inventory mutation, deployment, or production runtime.

The source imports no `socket`, `http`, `urllib`, requests client, subprocess, concurrency, filesystem, or browser module and performs no transport calls.

## Tests-first provenance

Remote branch commits preserve the reviewed order:

- `dc4c7375c9f177399c55baee0b9dd009ef4ceda7` — M77 behavioral contract committed before `local_ui_http_v1.py` existed;
- `078870ef3c2b3a8d56a9e33bc889aba6da42916a` — bounded HTTP application implementation;
- `8455d6aac851ee9ab252b30ce0049d98ca71b5f8` — artifact/authority contract committed while this document and public export were still absent;
- `c96d5483fbd91ea2bdf7ab80302d2401f9b66817` — explicit `marketplace.reference` export.

## Optimization evidence

The adapter performs no retries, polling, background work, filesystem scan, socket operation, network round trip, or unbounded iterable consumption.

GET is constant-size M76 rendering plus one UTF-8 encoding. POST first checks the encoded byte bound and exact delimiter count, then splits into at most twelve pairs. Each value is decoded once in a single forward pass, the exact twelve-field object is constructed once, and M76 is invoked once. Response construction performs one UTF-8 encoding and one bounded header tuple construction.

This keeps work linear in a hard-capped request body with constant field cardinality and preserves every existing quality/security/conformance gate.

## Next boundary

After M77 is merged-green, separately audit the smallest one-shot loopback transport that can host exactly `handle_local_ui_http_request()` under:

- explicit opt-in distinct from repository/merge authorization;
- fixed exact IPv4 loopback `127.0.0.1`;
- caller-selected bounded non-privileged port;
- one listener, one accepted connection, one request, one response, then terminal close;
- bounded read/write accounting and deterministic cleanup;
- no external network, DNS/TLS, browser automation, credentials, persistence, payment, settlement, deployment, or background service authority unless separately authorized.
