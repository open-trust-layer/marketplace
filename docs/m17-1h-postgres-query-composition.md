# M17.1H PostgreSQL root-intent query and source-only application composition

M17.1H closes a source-level wiring gap between the reviewed PostgreSQL application state, the transport-independent Marketplace Application API, and the deterministic HTTP binding.

The new `PostgresIntentQuery` is a bounded read-only adapter over the existing `MARKETPLACE_APPLICATION_STATE_MVP` schema. It lists only live root intents: records that are not indexed as responses in `marketplace_app_response_links`.

Pagination is deterministic by exact Record Identity. A continuation cursor is only a **local application coordination** cursor. It is not federation completeness, global truth, ranking, ownership, lifecycle authority, or protocol state.

Continuation cursors fail closed when they no longer identify a live root intent. Provider/database exceptions are normalized to stable application-query errors without reflecting DSNs, credentials, payloads, or provider diagnostics.

## Source-only application composition

`compose_marketplace_application()` wires injected dependencies into:

`MarketplaceApplicationStateService -> MarketplaceApplicationApiService -> MarketplaceApplicationHttpAdapter`

The composition object is inert until `initialize()` is called explicitly. It does not discover environment configuration, load secrets, install dependencies, create a database, bind a socket, or start a server.

## Authority boundary

This milestone authorizes and implements **no live PostgreSQL connection** and no live migration. Connection factories remain injected test/runtime dependencies; provider selection and credentials are outside this source slice.

There is **no HTTP socket/server execution** here. The HTTP adapter remains a deterministic request/response binding only; a future listener/server process requires a separate reviewed capability and explicit authorization.

No Android dependency resolution/build/runtime execution, signing, installation, distribution, production deployment, configuration change, service restart, or runtime mutation is part of M17.1H.

In normative terms, this cursor is for **local application coordination only** and carries no broader authority.
