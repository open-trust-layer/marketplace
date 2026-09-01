# M72 — Human Product Listing Profile and Builder

## Baseline

M72 starts from merged-green M71 commit
`907811c2a2a62711448ff9d05a482c674599b770` and issue #158.

M71 already provides the transport-neutral local publish/get/search application facade.
M72 adds the first human-facing construction profile without changing Marketplace core
record semantics or introducing a second identity, validation, persistence, or transport path.

## Human listing projection

The M72 profile is identified by:

`https://open-trust-layer.github.io/marketplace/semantics/v1/profile/product-listing-v1`

A human listing is still one ordinary `MarketIntentV1`. Familiar product fields are mapped
into the existing reviewed structures instead of becoming new direct MarketIntent fields.

| Human field | MarketIntent representation |
| --- | --- |
| seller | `issuer.principal` |
| product | one `subjects[].uri` |
| sell intent | profile-defined `action.id` |
| title | semantic term value |
| description | semantic term value |
| consideration | `ValueExpressionV1` monetary form |
| quantity | `QuantityV1` |
| map position | `LocationConditionV1` |

The direct MarketIntent content shape therefore remains exactly the Specification 0003
shape. M72 does not add direct `title`, `price`, `quantity`, `location`, mutable status,
view-count, or ranking fields.

## Exact decimal handling

`ExactDecimal` accepts an integer coefficient plus scale `0..18` and normalizes redundant
trailing decimal zeroes before producing `DecimalV1`. Boolean values are rejected as
integers. The application projection also bounds coefficients to the signed 64-bit range
before the OLP reference validator performs its authoritative record-value validation.

A monetary listing consideration must be non-negative and uses exactly one three-letter
uppercase currency code. M72 does not perform currency conversion, valuation, settlement,
escrow, tax calculation, or payment execution.

Quantity must be positive. The first profile defaults naturally to the profile's `item`
unit URI, while the builder accepts any bounded absolute unit URI so later product classes
can use profile-defined units without changing core Marketplace semantics.

## Location profile

M72 defines one deterministic map-ready location scheme:

`https://open-trust-layer.github.io/marketplace/semantics/v1/profile/product-listing-v1/location/wgs84-e6`

Latitude and longitude are signed integer microdegrees (`e6`) rather than floating-point
values. Latitude is bounded to `[-90_000_000, 90_000_000]`; longitude is bounded to
`[-180_000_000, 180_000_000]`.

This is an issuer-attributed listing location only. It is not geocoded, reverse-geocoded,
verified, trusted, proof of custody, proof of ownership, or a claim that a product remains
at that location. M73 may render these coordinates against deterministic/offline fixtures
without granting a browser or map provider authority to M72.

## Layering

`marketplace.application.listing` is pure projection code. It imports no OLP, network,
filesystem persistence, database, process, concurrency, or browser stack and keeps the
Marketplace package's declared runtime dependency list empty.

`marketplace.reference.product_listing_v1` is the explicit OLP-dependent reference adapter.
It creates one `RecordV1`, runs the existing Marketplace validator, and applies the stricter
product-listing profile shape before returning or rendering a listing.

## Security and authority boundary

M72 is a MODERATE product/application change. It authorizes only project read/write and
deterministic local execution during development. It does not authorize or invoke live
socket/bind/listen/accept/connect behavior, DNS, TLS, HTTP serving, browser automation,
map-provider access, credentials, deployment, durable storage, settlement, or production
runtime actions.

A valid listing remains attributable data, not truth, ownership, availability, legality,
fair value, authority, agreement, settlement, or permission for a protected side effect.

The application builder revalidates the complete `ProductListingDraft` immediately before
projection, including exact nested `ExactDecimal` scalar types, and builds from a fresh
reviewed draft. The reference extractor requires the exact reviewed OLP `RecordV1` type and
exact frozen envelope container classes before any general Marketplace validation. It then
detaches a bounded trusted snapshot of the OLP-frozen value graph and reconstructs a fresh
`RecordV1`; only that detached record is passed to the general Marketplace validator and
profile parser.

## Privacy and retention

M72 adds no durable repository. When published through the existing in-memory runtime,
listing content remains governed by the existing default `EPHEMERAL` retention class and
10-second retention window. Precise coordinates can be privacy-sensitive and should be
coarsened or omitted by future UI policy when exact location is unnecessary.

## Tests-first provenance

- `64ffa88ac2e6f6c51e252229ef38687cbf0fb9a5` — human listing projection tests committed RED before `listing.py` existed.
- `7622a28e59678e2f49047d7a37715ec5898493c2` — pure application projection implementation.
- `8701c13c540fc66575e2b2470ef9a249c720628b` — OLP/reference integration tests committed before the reference adapter.
- `708a45596542b12f03d514cd3c0cb9ebc71ede87` — exact `RecordV1` builder/extractor adapter.
- `af1fe3aa51069db85766daf3912373e5638c73fb` — artifact/security contract committed RED before this document existed.

The bare developer Python intentionally does not contain the pinned OLP dependency. Pure
application and artifact tests run locally; OLP-backed behavioral integration is verified
by the repository's isolated self-hosted CI using the exact reviewed OLP pin.

## Post-implementation extraction review

The first focused review found two issues before M72 acceptance was finalized:

- OLP `profiles` are identity-equivalent regardless of tuple ordering, so the product-listing
  extractor must validate the exact profile set rather than one incidental order.
- a frozen `RecordV1` can be privately rebound after construction, so changed envelope
  containers must be rejected before a general validator touches them.

Tests-only commit `1a54893fa3b460a956adfb52c49c9f108d4aeb4e` captures those regressions.
Fix commit `c7885fdfea82c2ef5fd4b0b8fa7cfb3d0781def1` added exact-container/profile-set
preflight, and commit `11eb411c66a94ef87936b584726ad6a5e6dfaa55` preserved the established
`PRODUCT_LISTING_PROFILE_REQUIRED` failure contract.

A second deterministic standard-library probe then established that exact
`MappingProxyType` alone is not an inert trust marker: when it wraps a hostile `dict`
subclass, boolean/length/iteration/items operations can dispatch overridden methods.
`gc.get_referents()` exposed the proxy's backing object without executing those methods,
allowing the adapter to distinguish an exact built-in `dict` backing from a hostile subclass.

Tests-only commit `8d4104a44ff16c15da33bbea7688405372caea00` captures both the hostile
mappingproxy-backing case and a hostile nested mapping inside an otherwise exact backing
`dict`. Fix commit `5c9ae037ce9e8827d817137118a20f5df6b57d48` replaces trust-by-proxy-type
with a bounded detached snapshot. The walker accepts only exact immutable/scalar built-ins,
exact tuples, and mappingproxies whose direct backing is an exact built-in `dict`; it caps
nesting depth at 16 and each collection at 64 members, then validates only a freshly
reconstructed trusted `RecordV1`.

Artifact commit `8bb677972039412f21c5430d5d1e099f6d87ab0e` binds those bounds, inert
backing-object inspection, detached reconstruction, and reviewed-record validation into the
repository acceptance contract.

## Post-implementation draft review

The same private-rebinding threat was then checked on the application input side. A frozen
`ProductListingDraft` can still be deliberately modified with `object.__setattr__`; the old
builder would call `.as_mapping()` on a rebound `consideration` field, and the old draft
validator could compare a tampered `ExactDecimal.coefficient` subclass before proving that
the nested scalar was an exact integer.

Tests-only commit `c232531a90a64399b703daa04d8c4cb8193eac79` reproduces both cases without
OLP or external I/O. Fix commit `f3384a1f360147ef17f67432436a05388b82e690` revalidates exact decimal
scalars, rebuilds a fresh reviewed `ProductListingDraft`, and projects only from that fresh
snapshot. Artifact commit `c77732ed6cb3ef275b3e6494aba2e41dbe2b6fe1` binds both the reviewed-draft
and detached-record guards into acceptance.

No new external capability, dependency, network surface, persistence path, settlement
authority, or protocol semantic was introduced by any of these hardening steps.

## Optimization evidence

Construction is constant-size work over one bounded draft: no scan, retry, pagination,
network call, persistence write, scheduler, background task, or unbounded iterable is
introduced. Decimal canonicalization performs at most 18 trailing-zero reductions.

The map-ready location representation uses two integers and avoids floating-point parsing,
geocoding, or normalization. Extraction traverses only the bounded M72 frozen record graph,
creates one detached trusted snapshot, and validates that snapshot before rendering fields.
The builder performs one bounded draft revalidation and one fresh deterministic projection.

No existing quality, security, integration, governance, artifact, or semantic-conformance
gate is weakened, bypassed, skipped, removed, or renamed.
