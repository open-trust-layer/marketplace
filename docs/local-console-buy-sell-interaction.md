# M75 — Bounded Local Console Buy/Sell Interaction

## Baseline

M75 starts from merged-green M74 commit
`e9b8f7aebf3927e7cbd1ed3fd0092a9725fc4f46`.

M72 already defines the bounded human product-listing draft. M74 already owns the genuine OLP
materialization, ephemeral runtime, local publish/search/resolve/match composition, and authority-preserving
result. M75 adds only a local line-oriented interaction adapter over those reviewed surfaces.

## Product purpose

`run_local_buy_sell_console()` is the first direct local-user input boundary in the reference layer. A host
supplies two ordinary callables:

- `read_line(prompt) -> str` for one bounded line of local input; and
- `write_line(line)` for bounded local output.

The adapter prompts for one seller principal, subject, listing title/description, exact consideration,
currency, quantity/unit, WGS84 coordinates, buyer principal, and caller-selected buyer action URI. It then
constructs the existing M72 `ProductListingDraft` and delegates once to M74
`run_local_buy_sell_demo()`.

The adapter itself does not open a terminal, start a process, bind a socket, launch a browser, read or write
a file, or choose an external transport. A host may bind the injected callables to a console or another
strictly local line-oriented surface without changing Marketplace semantics.

## Exact numeric input

Human consideration and quantity values are parsed as decimal text directly into the existing
`ExactDecimal` representation. Binary floating-point conversion is never used.

Latitude and longitude are accepted as decimal-degree text with at most six fractional digits and are
converted by integer arithmetic into the existing WGS84 E6 representation. The M72 `ProductListingDraft`
remains authoritative for the final coordinate ranges and all other listing validation.

## Input safety

Every line is required to be non-empty UTF-8 text and is bounded before downstream materialization.
Field bounds are deliberately small and aligned with the existing listing surface where applicable:

- principal / subject / action / unit URI: 2048 UTF-8 bytes;
- title: 120 UTF-8 bytes;
- description: 4096 UTF-8 bytes;
- decimal text: 64 UTF-8 bytes;
- currency code: 3 UTF-8 bytes;
- coordinate text: 32 UTF-8 bytes.

Malformed, non-text, oversized, numerically unsupported, or otherwise invalid user input fails with stable
`LocalConsoleInteractionError` codes. Error text does not reflect the hostile raw value.

No credential, password, secret, payment instrument, settlement instruction, filesystem path, command,
script, or executable payload is requested by M75.

## Output and retention

Successful output is intentionally narrower than the M74 return value. The local writer receives only:

- seller Record Identity;
- buyer Record Identity;
- method-relative match conclusion;
- `protocol_truth=false`; and
- `creates_agreement=false`.

The listing description, buyer principal, raw input lines, and inert M73 HTML are not written by the M75
adapter. No transcript or input archive is retained.

The returned value is the already-reviewed immutable `LocalBuySellDemoResult`. M75 introduces no new
runtime ownership. M74 still creates the local runtime, clears it synchronously before return, and preserves
the repository's EPHEMERAL / 10-second maximum retention policy.

## Semantic and authority boundaries

M75 does not create a new validation path, matching method, buyer action taxonomy, agreement mechanism,
settlement path, or protocol truth. The existing M72 and M74 components remain authoritative.

A successful interaction still means only that the exact locally supplied buyer/seller pair was reported as
`COMPATIBLE_UNDER_METHOD` by the existing demonstration method. It does not create an agreement, order,
payment, settlement, ownership transfer, inventory mutation, execution authorization, legal conclusion,
or universal truth.

## Security / capability classification

Risk: **MODERATE local interaction adapter**.

Exercised capabilities:

- project source read/write during development;
- deterministic local execution in acceptance;
- caller-injected local line input/output.

Not requested or exercised:

- `NETWORK_EXTERNAL`;
- `DEPLOY`;
- socket bind/listen/accept/connect;
- DNS, TLS, HTTP client/server;
- browser automation or external map-provider access;
- credentials or identity-secret handling;
- durable filesystem or database persistence;
- subprocess, shell, thread, timer, queue, or background worker;
- payment, settlement, asset-transfer execution, or production runtime.

The adapter remains in `marketplace.reference`, the explicit OLP-dependent composition boundary. The
transport-neutral application and runtime packages do not import M75.

## Tests-first provenance

- `de1ea83c65d15e8cc2b20019b5c49a4513a0cd44` — behavioral contract committed while
  `local_console_v1.py` was absent.
- `c4308dbebce28e965681b4a5cd2f05dd387141c1` — bounded console adapter implementation.
- `9f4f7ad31d277274e1f4178f66be3a1f7ed9a814` — explicit reference-package export.
- `28d2f7e22d4e8647017d504377b2b43b1229f5fd` — artifact/authority contract committed while this
  document was absent.

The complete behavior, package, repository, semantic-vector, artifact, and cleanup acceptance remains the
existing self-hosted CI gate with the repository's exact pinned OLP source.

## Optimization evidence

M75 performs exactly twelve bounded line reads, a constant amount of integer/string parsing, one M72 draft
construction, one M74 call, and seven bounded output writes. It adds no retry, polling loop, cache, queue,
filesystem scan, network round trip, process, thread, background task, or unbounded iterable consumption.

## Next boundary

After M75 is merged-green, reassess whether the next useful user experience should be a separately governed
**loopback-only visual interaction**. Any HTTP listener, browser execution, local web server, persisted state,
credential use, external map access, settlement, payment, or deployment remains a separate capability and
must not be inferred from M75.
