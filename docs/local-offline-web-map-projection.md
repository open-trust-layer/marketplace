# M73 — Local Offline Web/Map Projection

## Baseline

M73 starts from merged-green M72 commit
`a64edadf6fe962e1ea48542a1714c50f4c0a97aa`.

M72 already provides the validated, immutable `ProductListingDraft` application shape and
an OLP-dependent reference extractor for genuine product-listing records. M73 adds only a
bounded presentation projection over those reviewed inputs.

## Product purpose

M73 provides the first human-visible local Marketplace surface:

- one deterministic HTML document;
- one inline SVG coordinate map;
- numbered listing markers;
- title, description, price, quantity, location, seller, and subject text;
- an explicit empty-local-view state.

This is a presentation artifact, not a server, browser session, map client, discovery engine,
record validator, persistence layer, or source of Marketplace authority.

## Offline map fixture

`OfflineMapFixture` is an immutable bounded equirectangular canvas. The default fixture is
720 by 360 logical units. WGS84 integer microdegrees are projected with integer arithmetic
only; no floating-point geospatial library, tile set, geocoder, reverse geocoder, or remote
map provider is consulted.

The map is intentionally a coordinate fixture rather than geographic truth. It contains a
static grid, axes, and listing markers. It does not claim road, border, address, ownership,
product custody, availability, or location verification.

Latitude remains bounded to `[-90_000_000, 90_000_000]`; longitude remains bounded to
`[-180_000_000, 180_000_000]`. The UI formats microdegrees deterministically to six decimal
places for display.

## Rendering boundary

`render_product_listing_page()` accepts only an exact tuple and rejects more than 64
listings before enumeration. Every entry must be the exact M72 `ProductListingDraft` type
and is reconstructed before rendering so privately rebound invalid fields fail closed.

All human-controlled text is HTML-escaped before inclusion. The generated page contains no
script, iframe, stylesheet link, image source, hyperlink target, form submission, or other
external-resource reference. CSS and SVG are inline and deterministic.

## Genuine-record bridge

`marketplace.reference.web_map_v1` is the explicit OLP-dependent bridge. It accepts only an
exact bounded tuple of genuine OLP `RecordV1` values, reuses the M72 product-listing
extractor for profile validation, and passes only the resulting reviewed drafts to the pure
application renderer.

The bridge does not introduce a second validation path. Non-listing records, malformed
profiles, hostile container substitutions, and semantic drift continue to fail through the
existing M72 reference adapter.

## Security and authority

M73 is a MODERATE product/presentation source change. Development authority is limited to
project read/write and deterministic local execution. M73 neither requests nor exercises
`NETWORK_EXTERNAL` or `DEPLOY`.

It adds no socket, bind, listen, accept, connect, DNS, TLS, HTTP client/server, browser
automation, map-provider access, credentials, database, durable filesystem persistence,
background worker, payment, settlement, or production runtime capability.

The visible location remains issuer-attributed data, not verified truth. An empty local view
is explicitly not evidence of global nonexistence or deletion.

## Privacy and retention

M73 does not retain listings independently. When inputs come from the existing local runtime,
the existing EPHEMERAL policy and 10-second maximum retention remain authoritative. Exact
coordinates can be privacy-sensitive; future interactive UI policy may coarsen or omit them,
but M73 does not silently alter issuer-supplied coordinates.

## Tests-first provenance

- `4fa6d11451468a0122c6854daca646de598ddaeb` — behavioral projection tests committed RED
  before `marketplace.application.web_map` existed.
- `10ef86eebffd4feeefce8c75cb40128378a03598` — pure offline HTML/SVG implementation.
- `cb5d1c75b01c5e154aef3fbdbe33a862841e06d6` — artifact and genuine-record integration
  contracts committed before the reference bridge, exports, and this document.

The developer Python intentionally does not carry the pinned OLP dependency graph. Pure M73
behavior and artifact checks run locally; genuine-record integration is authoritative in the
repository's isolated self-hosted CI with the exact reviewed OLP pin.

## Optimization evidence

Projection is O(n) over at most 64 validated listings. Each coordinate projection is
constant-time integer arithmetic. Rendering performs one bounded tuple review and bounded
string construction with no retry, cache, queue, thread, process, background task, network
round trip, filesystem scan, or unbounded iterable consumption.

M74 may compose this static view into the first local buy/sell demonstration, but any actual
HTTP serving, browser execution, or external map access remains a separately governed
capability boundary and is not implied by M73.
