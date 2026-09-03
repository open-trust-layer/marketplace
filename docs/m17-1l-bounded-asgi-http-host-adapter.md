# M17.1L — bounded ASGI HTTP host adapter

Status: source-level host binding only. This milestone adds a **source-only ASGI 3 HTTP adapter** around the already reviewed inert Marketplace site host.

## Purpose

M17.1B2 intentionally stopped at `ApplicationHttpRequest` / `ApplicationHttpResponse` and left translation from a real host/framework as a later capability. M17.1I and M17.1J then joined the Web shell and shared product API behind `MarketplaceSiteHostAdapter`, still without transport ownership.

M17.1L fills only that missing standard host seam. The adapter accepts one ASGI HTTP scope plus bounded `http.request` events, translates them into the existing application request value, calls the existing site host exactly once, and emits one response start plus one final response body event.

It creates no new Marketplace route table, persistence model, protocol object, trust claim, authorization claim, or application semantics.

## ASGI profile

The reviewed profile is intentionally smaller than the whole ASGI ecosystem:

- ASGI callable version `3.0` only;
- HTTP scopes only;
- root-mounted same-origin application only (`root_path == ""`);
- HTTP/1.0, HTTP/1.1 and HTTP/2 scope metadata;
- decoded ASGI `path` is passed to the existing application boundary;
- bounded raw `query_string` is strictly percent-decoded as UTF-8 into duplicate-free query pairs;
- raw `+` in query components is rejected as ambiguous rather than silently assigning form semantics;
- request headers are bounded; duplicate `content-type` / `content-length` are rejected;
- `authorization`, `proxy-authorization`, and `cookie` request headers are rejected because authentication/session semantics do not exist in this milestone;
- request body accumulation is bounded by both byte count and ASGI event count;
- disconnect, malformed events, content-length mismatch, noncanonical metadata, and incomplete event streams fail closed;
- application responses must stay within the existing byte bound and use canonical duplicate-free ASCII headers with an exact matching `Content-Length`;
- `Set-Cookie` is rejected at the host boundary.

## Authority boundary

This milestone has **no server startup** and **no socket bind/listen/accept/connect** capability. It imports no ASGI server implementation and installs no dependency. In particular there is no Uvicorn, Hypercorn, Daphne, framework, listener, TLS terminator, DNS client, or network process started by this source.

There is **no live PostgreSQL connection**, schema migration, environment/secret loading, background worker, service lifecycle, production deployment, or configuration mutation. The adapter does not call application initialization.

The merged Web assets remain caller-injected bytes. There is **no runtime filesystem asset loading** in M17.1L.

There is **no WebSocket or lifespan authority**. Unsupported scopes are rejected rather than being treated as implicitly supported startup/shutdown or bidirectional channels.

## Relationship to earlier runtime work

The repository already contains reviewed bounded inbound HTTP work for federation/immutable-record disclosure and the historical local form UI. Those components remain valid for their original scopes, but they are not relabeled as the Product M17 application API or Web host.

M17.1L reuses the project's bounded/fail-closed design principles while keeping `MarketplaceSiteHostAdapter` as the sole Product M17 site/API route owner.

## Acceptance

- deterministic in-process tests exercise synthetic ASGI scopes and receive/send callables only;
- static Web routes and `/api/*` continue to be handled by the existing site/application adapters;
- query/header/body translation is bounded and fail-closed;
- sensitive request/session headers are not silently accepted;
- no server, network, database, filesystem, credential, deployment, Android, payment, settlement, or protected-side-effect authority is activated.

A later milestone may choose and pin a concrete ASGI server/runtime, load reviewed Web assets, select project-scoped configuration, and connect the PostgreSQL adapter. Each of those is a separate capability and requires its own risk review and authorization; none is implied by M17.1L.
