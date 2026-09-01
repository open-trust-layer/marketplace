# M74 — First End-to-End Local Buy/Sell Demo

## Baseline

M74 starts from merged-green M73 commit
`c1e4366e088a33074401bd68651f9300615411c7`.

M71 already provides the local publish/search/get application facade and shared ephemeral runtime.
M72 provides the reviewed human seller-listing profile and genuine OLP record bridge. M73 provides
an inert deterministic HTML/SVG projection. M74 composes those surfaces; it does not replace them.

## Product purpose

`run_local_buy_sell_demo()` demonstrates one complete local Marketplace path:

1. validate and build one genuine M72 seller product-listing record;
2. build one genuine core Marketplace buyer/request intent over the same subject;
3. publish both into one owned local runtime;
4. discover the exact seller listing through the existing M5 discovery evaluator;
5. resolve both exact Record Identities through the local matching service;
6. evaluate compatibility through the existing M5 match evaluator;
7. render the seller through the existing M73 offline projection;
8. close and clear the owned runtime before the result reaches the caller.

The returned `LocalBuySellDemoResult` contains only immutable bounded result data: the two Record
Identities, the exact discovered seller identity tuple, the match method/conclusion and non-authority
flags, discovery completeness/absence metadata, and the already-inert seller HTML projection. It does
not retain either OLP `RecordV1` object or a live runtime/repository reference.

## Buyer/request intent semantics

The seller side is the exact M72 `product-listing-v1` sell profile. The buyer side intentionally uses
only the already-reviewed core Marketplace `MarketIntentV1` shape. `buyer_action_uri` is caller-supplied
and must survive normal core Marketplace validation as an absolute action URI. M74 does not create a
new normative global meaning for a "buy" action identifier.

The buyer request uses the same exact subject URI as the reviewed seller listing. The demo then supplies
`SATISFIED` as the explicit base-status input to the existing example exact matching method. That input is
a bounded demonstration choice, not protocol truth. The existing evaluator remains authoritative for the
result and must return `protocol_truth = false` and `creates_agreement = false`.

No agreement, proposal, acceptance, order, payment, settlement, ownership transfer, inventory mutation,
or execution authorization is created by M74.

## Discovery semantics

Seller discovery reuses the M71 application facade and M5 evaluator with exact filters for:

- the M72 product-listing profile;
- the M72 sell action URI;
- the seller listing's exact subject URI.

The result must resolve exactly the locally published seller Record Identity. The normal discovery
metadata remains unchanged: global completeness is `UNKNOWN` and absence is not negative evidence.
There is no fuzzy/latest/global lookup and no network fallback.

## Retention and cleanup

The M74 demo owns its runtime and enters it as a context manager immediately after construction. Any
published records therefore remain inside that one bounded call and are unconditionally cleared on
normal return or exception before the result reaches the caller.

The runtime repository keeps the existing default `EPHEMERAL` / 10-second configuration. M74 does not
override `retention_seconds`. Because this demo never exposes the runtime and closes it synchronously,
it uses a close-only scheduler rather than creating a background timer whose only purpose would be to
expire state that is already destroyed before return. This shortens actual retention relative to the
10-second maximum; it does not extend or persist state.

## Security and authority

M74 is a MODERATE application/reference composition change. Development authority is limited to project
read/write and deterministic local execution. M74 neither requests nor exercises `NETWORK_EXTERNAL` or
`DEPLOY`.

The M74 source adds no socket, bind, listen, accept, connect, DNS, TLS, HTTP client/server, browser or
map-provider access, credentials, durable filesystem/database persistence, subprocess, thread, background
worker, payment, settlement, or production deployment capability.

The reference layer remains the explicit OLP-dependent boundary. The transport-neutral application layer
continues to import no OLP implementation and receives no M74-specific dependency or authority.

## Tests-first provenance

- `bee8fdada64e02e63b43be83b66f93fb3aea705a` — behavioral M74 tests committed while
  `src/marketplace/reference/local_demo_v1.py` was absent.
- `0fc6d11739a41b03b700911edfb29d87ec3f3b80` — local buy/sell demo composition implementation.
- `f7c62bf4a911366342437eab7a6fa900a5e5f4d8` — artifact/security contract committed RED while this
  document was absent; the local source-only artifact run had four passing checks and one expected
  failure for the missing document.

The developer Python environment is intentionally not modified to install the pinned OLP dependency
graph. Source syntax, artifact membership, and static authority checks are exercised locally. Genuine
OLP behavior and the complete repository/package/vector acceptance remain authoritative in the existing
isolated self-hosted CI with exact OLP pin `41b768e50b6cb9cc8e516ad7b6c40969f9ed7b6c`.

## Optimization evidence

M74 adds constant-cardinality composition around exactly two records. Seller discovery is bounded to
eight local records and the owned repository contains only the seller and buyer demo records. Matching
performs exact local identity reads and delegates once to the existing evaluator. Rendering delegates once
to the existing bounded M73 projection.

There is no retry, cache, queue, polling loop, network round trip, filesystem scan, process, thread,
background task, or unbounded iterable consumption introduced by M74.

## Next boundary

After M74 is merged-green, the roadmap should reassess the smallest genuinely interactive local-user
boundary. HTTP serving, browser execution, external maps, durable storage, identity/credential use,
settlement, and deployment remain separately governed capabilities and are not implied by this demo.
