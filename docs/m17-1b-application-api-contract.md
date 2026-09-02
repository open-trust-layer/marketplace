# M17.1B — Transport-Independent Marketplace Application API Contract

Status: source-level implementation candidate on the merged M17.1A base; no HTTP runtime is authorized or implemented here.

## Purpose

M17.1B defines one transport-independent application facade for future Web, Android,
AI-agent, and HTTP adapters. It sits above `MarketplaceApplicationStateService` and
keeps persistence, transport, and Marketplace protocol semantics separate.

```text
Web / Android / agents / future HTTP adapter
                    |
                    v
MarketplaceApplicationApiService
          |                    |
          v                    v
application state        IntentQueryPort
          |
          v
canonical Marketplace / OLP records
```

The application API coordinates local product behavior. It is not protocol truth,
not an ownership registry, not a legitimacy oracle, and not a universal ranking.

## Future endpoint mapping

The future transport adapter will map the minimum MVP routes onto these application
operations without moving business logic into HTTP handlers:

- `GET /api/intents` -> `list_intents(...)`
- `POST /api/intents` -> `create_intent(record)`
- `GET /api/intents/{id}` -> `get_intent(record_id)`
- `POST /api/intents/{id}/responses` -> `respond_to_intent(parent_id, record)`
- `GET /api/intents/{id}/responses` -> `list_responses(parent_id, ...)`
- `GET /api/sync` -> `sync(cursor, ...)`

This milestone does not choose FastAPI, Ktor, ASGI, WSGI, a socket implementation,
or an HTTP server. It performs no bind/listen/accept/connect operation.

## Intent creation and response binding

`create_intent` is for root intents. A record that already carries `response_to`
parents is rejected from that operation so a response cannot be mislabeled as a root
creation by the transport path.

`respond_to_intent` first verifies that the supplied response is an intent record and
that its existing Marketplace `response_to` relation includes the exact path parent. Only
then it performs a no-refresh `peek` of the parent, requires local existence, and verifies
that the parent is also an intent record. Only a successfully classified intent is read
again through the normal retention-refreshing `get`. Invalid response binding or a
wrong-type parent therefore cannot extend parent retention. Multiple reviewed proposal
parents remain possible; the application endpoint does not replace or reinterpret protocol
negotiation semantics.

## Browse/query separation

`GET /api/intents` is intentionally backed by `IntentQueryPort`, not by the sync
change log. Sync history can contain repeated UPSERT entries and DELETE tombstones;
it is therefore not a discovery projection.

The query port returns bounded record identities only. A later PostgreSQL discovery
projection may implement this port, but that is a separate schema/query decision and
must not add hidden ranking, ownership, legitimacy, or global-completeness semantics.

## Sync

`GET /api/sync` delegates to the M17.1A monotonic local application cursor. The cursor
is source-local application coordination metadata. It does not claim global history,
source completeness, canonical ordering, or protocol truth.

## Bounds and failure behavior

Intent, response, and sync page sizes are bounded to at most 256 entries. The facade
independently rejects downstream response/sync result overruns and malformed sync cursor
progression. Invalid IDs, cursors, limits, query result shapes, and parent bindings fail
closed before protected state mutation. Error messages are stable and do not reflect
submitted payload bodies.

Initialization is explicit. The API facade calls the shared state-service startup path,
which in M17.1A performs schema validation/migration and required retention cleanup
before product operations become available.

Exact intent lookup uses the same two-phase retention rule: a no-refresh `peek` is used
for type validation, then `get` refreshes retention only for a valid intent. This adds one
bounded local persistence read on successful get/respond paths in exchange for preventing
invalid endpoint use from becoming a retention-extension mechanism.

## Explicit exclusions

M17.1B source staging adds no HTTP server, no live database connection, no PostgreSQL
schema migration, no browser or Android runtime, no credentials, no external networking,
no payment or settlement action, and no production deployment.

The PostgreSQL persistence profile and 30-day retention authority remain exactly those
of M17.1A; this API facade does not extend retention or create a new data class.

## Next integration step

Policy v1.5 and M17.1A are merged and merged-main validated, and this contract has been
replayed onto that accepted base. The next step is exact-head FULL validation and review
of this work-unit PR. A later transport PR may bind these operations to HTTP routes, but
only after framework/dependency admission and separate capability review. Web and Android
clients should consume the same application contract rather than duplicating Marketplace
business logic.
