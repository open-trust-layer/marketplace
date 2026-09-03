# M17.1I same-origin Web/API site host adapter

M17.1I adds a **source-only** host boundary that joins the reviewed M17.1C Web shell and the existing Marketplace Application HTTP adapter without activating a network runtime.

The adapter accepts an already-framed `ApplicationHttpRequest`. Exact `/api/*` paths are delegated unchanged to the reviewed application HTTP adapter. The static surface is limited to `/`, `/index.html`, `/app.js`, and `/styles.css`.

Static content is provided only as **injected static asset bytes**. The adapter does not discover paths, read files, normalize aliases, or traverse directories. `/` is an explicit alias for the injected index bytes; no other aliasing is accepted.

The static response profile is bounded by the existing Marketplace application HTTP response limit and uses deterministic content types, `no-store`, `nosniff`, a same-origin content-security profile, and `Cross-Origin-Resource-Policy: same-origin`. There is **no CORS expansion**.

Request metadata, body size, and query shape are reviewed before API delegation. Duplicate query names, malformed query tuples, oversized bodies, control characters, unknown static paths, path-normalization variants, traversal-like paths, and unsupported static methods fail closed with stable non-reflective errors.

## Authority boundary

This slice adds **no socket/server activation**, TLS listener, host/port ownership, public traffic, process/service lifecycle, or deployment behavior.

It adds **no runtime filesystem traversal** or arbitrary file-read capability. A future executable host composition may inject the three reviewed Web artifacts, but selecting and loading those bytes is outside this adapter and requires its own reviewed runtime boundary.

It adds **no live PostgreSQL connection**, provider selection, credentials, migrations, database provisioning, or secret/environment discovery. The application HTTP dependency is injected and remains inert until its separately reviewed composition is initialized by an authorized runtime.

No Android dependency resolution/build/runtime, signing, installation, distribution, configuration change, service restart, production deployment, or other runtime mutation is part of M17.1I.
