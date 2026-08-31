# M71 — Local Marketplace Application Core

## Baseline

M71 starts from merged-green M69 commit
`b90a11ca0202ce0ea88f7892129b288e9ed57185`.

M70 remains a separate HIGH security hardening PR. M71 is intentionally branched from
merged `main` so product application work does not silently inherit unapproved M70 code.

## Product purpose

The repository already contains validated Marketplace evidence ingestion, exact local
lookup, bounded discovery, matching, federation, HTTP/runtime layers, and EPHEMERAL
storage. What it lacked was a small product-facing application boundary that a future
CLI, web UI, or map adapter can call without reaching directly into runtime internals.

M71 adds that boundary. It does not add a map or human listing schema yet.

## Tests-first provenance

Behavioral specification commit `c99759f5fafa06bca91c3c5fe4e456f37ce58a91`
was committed before the application source existed. The RED run failed specifically
because `marketplace.application` did not yet exist.

The tests require publish, exact lookup, local search metadata preservation, ordered
result materialization, and fail-closed handling for malformed or unresolvable results.

## Implementation

Implementation commit `0f0c04e166a6206e76d6ca4aaaba254e4fcebbd6` adds
`marketplace.application.LocalMarketplaceApplication` and immutable application result
types.

The facade delegates publication to the existing `MarketplaceNode`, delegates search to
the existing `LocalDiscoveryService`, and resolves only the exact Record Identities
returned by that local discovery result. It does not invent fallback lookup, global
market state, global absence, ranking, or additional semantic validation.

A CI integration test composes the real Marketplace validator, OLP Record Identity,
existing in-memory runtime, and M5 discovery evaluator to publish, retrieve, and search
one genuine `MarketIntent` end to end without transport I/O.

## Retention and safety

M71 creates no new repository or storage policy. The existing reference runtime remains
EPHEMERAL with the existing 10-second maximum; application reads continue to follow the
reviewed runtime retention behavior.

The dependency-free application core imports no OLP, socket, TLS, HTTP client/server,
async/background, subprocess, database, or external provider module. It creates no
credentials, durable state, settlement action, deployment, or protected external effect.

`NETWORK_EXTERNAL` and `DEPLOY` remain separately governed and are not exercised by M71.

## Optimization evidence

The application layer adds no loop beyond bounded exact result materialization, no retry,
queue, cache, background task, concurrency, I/O, or unbounded source enumeration.
Publication and exact lookup remain one direct delegation each. Search performs one
existing bounded discovery call followed by at most `max_records` exact local lookups.

No quality, security, integration, governance, artifact, or semantic conformance gate is
weakened, skipped, bypassed, removed, or renamed.

## Product roadmap

M71 is the first product-facing slice. The intended next steps are:

1. M72 — a human product-listing builder/profile that creates genuine `MarketIntent`
   records with title/description, consideration, quantity, and open-standard location;
2. M73 — a local web/map UI over the application facade, starting with deterministic
   offline map fixtures before any external map-provider access;
3. M74 — the first local end-to-end buy/sell demonstration using genuine Marketplace
   intents and the existing matching/runtime foundation.
