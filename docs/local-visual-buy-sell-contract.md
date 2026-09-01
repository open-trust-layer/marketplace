# M76 — Transport-Free Local Visual Buy/Sell Contract

## Baseline

M76 starts from merged-green M75 commit
`f8d060e82d7afe5b27909e0cfbfc1064372343af`.

M75 already owns the bounded human-input parser and delegates all Marketplace/OLP semantics to M72/M74.
M76 adds only a deterministic visual contract above that reviewed path. It does not introduce a second
human-input parser, Marketplace validation path, matching method, runtime owner, or transport.

## Architecture/risk audit

The repository already contains a hardened one-shot loopback HTTP authority path from M59 through M70.
That graph is intentionally bound to the M32/M33 federation and record-serving application adapters. Reusing
it directly for Marketplace UI form traffic would conflate two distinct semantic/authority domains and would
make a visual feature appear to be federation traffic.

M76 therefore stops before network authority. The visual contract is transport-free and lives in the explicit
OLP-dependent `marketplace.reference` layer next to M74/M75. A future loopback UI milestone may host this
contract, but must add a separately reviewed UI integration boundary rather than disguising UI requests as
federation requests.

Risk: **MODERATE transport-free local visual adapter**.

## Product surface

`render_local_buy_sell_form()` returns one deterministic, self-contained HTML form. The form contains the same
twelve human fields consumed by M75:

- seller principal URI;
- subject URI;
- listing title;
- listing description;
- exact consideration decimal;
- currency code;
- exact quantity decimal;
- quantity unit URI;
- latitude;
- longitude;
- buyer principal URI; and
- caller-selected buyer action URI.

The form declares `POST /local-buy-sell` only as the future local integration contract. M76 itself does not
start an HTTP server, parse HTTP bytes, bind a socket, or launch a browser.

`LocalVisualSubmission` is a frozen/slotted exact dataclass containing those twelve fields. The submission
function requires that exact type; mapping subclasses, arbitrary iterables, and transport objects are not
accepted.

`submit_local_buy_sell_form()` maps the exact form object onto M75's reviewed prompt interface and calls
`run_local_buy_sell_console()` exactly once with deterministic injected reader/writer callables. The M75 writer
is deliberately discarded rather than retained as a transcript. M76 does not reimplement M75 decimal,
coordinate, UTF-8, size, listing, or buyer validation.

## Result contract

A successful submission returns deterministic inert HTML containing only:

- seller Record Identity;
- buyer Record Identity;
- method-relative match conclusion;
- `protocol_truth=false`; and
- `creates_agreement=false`.

The submitted title, description, buyer principal, buyer action URI, raw field values, M73 map projection, and
M75 line output are not reflected into the result page.

Generated record identities and match conclusion are escaped before insertion into HTML. A successful result is
also checked to retain exact false authority flags before rendering.

## HTML safety

Both form and result pages are static strings with inline CSS only. They contain no:

- script;
- iframe;
- external stylesheet;
- external image or map resource;
- remote URL;
- browser-launch instruction;
- JavaScript URL;
- cookie/session mechanism; or
- executable payload surface.

The only navigation values are local relative paths (`/local-buy-sell` and `/`).

## Failure behavior

M76 wraps M75 failures in stable `LocalVisualInteractionError` codes without reflecting hostile raw input.

- invalid M75 human input -> `SUBMISSION_INVALID`;
- unexpected M75 prompt/interface drift -> `VISUAL_BINDING_DRIFT`;
- unexpected reviewed result type -> `VISUAL_RESULT_INVALID`;
- any attempted truth/agreement promotion -> `VISUAL_AUTHORITY_VIOLATION`;
- other reviewed M75 execution failure -> `SUBMISSION_FAILED`.

M76 performs no retry, fallback parser, alternate matching path, or alternate Marketplace materialization.

## Retention

M76 adds no persistent storage and no new runtime owner. The immutable submission and transient local closures
exist only for the synchronous call. No transcript or raw-input archive is stored. M74 still owns the underlying
Marketplace runtime and synchronously clears it before return under the existing EPHEMERAL / 10-second maximum
retention policy.

## Capability boundary

Exercised capabilities:

- repository source read/write during development;
- deterministic local string/object execution in tests and CI.

Not requested or exercised:

- `NETWORK_EXTERNAL`;
- loopback socket bind/listen/accept/connect;
- DNS or TLS;
- HTTP client/server execution;
- browser launch or browser automation;
- external map-provider access;
- credentials, login/session secrets, cookies, or identity-secret handling;
- durable filesystem/database persistence;
- subprocess, shell, thread, timer, queue, watcher, or background worker;
- agreement creation, payment, settlement, asset transfer, inventory mutation, deployment, or production runtime.

## Tests-first provenance

- `442e7f9eb684c93af2cb19524ea52c96b4c7b684` — visual behavioral contract committed before
  `local_visual_v1.py` existed.
- `1589a82e3a3c4c9d55f6c68da8e1abe0a98f2ddd` — transport-free visual implementation.
- `d73bf5219579dc7926b21c5a484ecc4d791b35c8` — explicit reference-package export.
- `b9731d5e7cbda5f64378d183571e7a9921f69e36` — artifact/authority contract committed while this document
  was absent.
- `0662bc4da4ae0c03fe8e36351680cdb9744abf86` — corrected one artifact-test source assertion; the remaining
  RED state was exactly this missing document.

## Optimization evidence

Rendering the form is constant-size deterministic string construction. One submission creates one twelve-entry
fixed tuple, one twelve-entry prompt/value dictionary, one bounded prompt-name set, one M75 call, and one result
page. There is no retry, polling, cache, queue, filesystem scan, network round trip, process, thread, background
task, browser operation, or unbounded iterable consumption.

## Next boundary

After M76 is merged-green, separately audit the smallest loopback-only HTTP integration capable of hosting
exactly this reviewed form/result contract. That milestone must preserve a strict local-only endpoint, explicit
opt-in, bounded request/response sizes, one reviewed semantic path, deterministic cleanup, and no external
network/deployment/credential/payment/settlement authority unless separately authorized.
