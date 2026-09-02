# M17.1B2 — Deterministic HTTP Transport Binding

Status: source-level, framework-neutral application transport adapter. This slice does not start or authorize a live HTTP runtime.

## Purpose

M17.1B2 completes the transport binding needed between the merged `MarketplaceApplicationApiService` and later shared clients. The target remains:

`OLP -> Marketplace Application Core -> Marketplace Application API -> HTTP binding -> M17.1C Web / M17.1D Android`

Web, Android, and future agents consume the same application facade. The HTTP layer does not define a second Marketplace model or protocol truth.

## Exact routes

- `GET /api/intents` -> bounded `list_intents`
- `POST /api/intents` -> root `create_intent`
- `GET /api/intents/{id}` -> exact `get_intent`
- `POST /api/intents/{id}/responses` -> `respond_to_intent`
- `GET /api/intents/{id}/responses` -> bounded `list_responses`
- `GET /api/sync` -> snapshot watermark when `cursor` is omitted, or bounded incremental local application `sync` when `cursor=N` is supplied

## Boundary

`ApplicationHttpRequest` represents already-framed method, path, exact query pairs, content type, and body bytes. `ApplicationHttpResponse` contains bounded status, headers, and JSON bytes. A later host or framework may translate real HTTP traffic into these values, but this module performs no wire parsing and owns no listener or service lifecycle.

Record JSON encode/decode functions are injected. This keeps OLP/Marketplace record materialization at the reviewed record boundary rather than teaching the HTTP adapter new semantic rules.

The adapter is deliberately framework-neutral: no FastAPI, Starlette, ASGI, WSGI, Ktor, socket provider, PostgreSQL driver, browser, or Android dependency is introduced.

## Bounds and failure behavior

Request and response bodies are finite and checked before materialization or emission. JSON request bodies must be strict UTF-8 objects with no BOM, duplicate member names, or non-finite numbers. Query members are exact, duplicate-free, route-specific, and bounded.

Errors use stable JSON codes/messages and never include submitted payload content or downstream exception text. Responses use `Cache-Control: no-store`, `X-Content-Type-Options: nosniff`, `Referrer-Policy: no-referrer`, and a restrictive CSP. No CORS widening, cookies, sessions, redirects, or credential surfaces are added.

The sync cursor remains local application coordination metadata and is not protocol truth, ownership, ranking, agreement, or global completeness. `GET /api/sync` without a cursor captures a current bounded snapshot watermark; a client can capture that watermark, perform bounded list/detail hydration, and then resume incremental sync from that watermark. An expired retained-history cursor is normalized to stable `SYNC_CURSOR_EXPIRED` and HTTP `409 Conflict`, so clients can restart this snapshot/full-resynchronization sequence without storage-detail reflection.

## Explicit exclusions

This slice provides **no live HTTP server** and **no socket** bind/listen/accept/connect capability. It adds no DNS/TLS/external networking, live database connection or migration, credentials, cookies, session state, background workers, browser execution, Android runtime, production deployment, payment, settlement, or fulfillment authority.

## Next product slices

After exact-head FULL validation, review, and separately authorized merge of this work unit, the next planned product step is **M17.1C Web**: an interactive map/list/create/detail/respond client against this shared API. **M17.1D Android** remains a Kotlin/Jetpack Compose client consuming the same API/model with separately governed local/offline cache semantics.
