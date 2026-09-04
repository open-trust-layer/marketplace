# M17.1D Android application

M17.1D introduces the first Android client source for the shared Marketplace Application Layer.

The Android client consumes the same application API reviewed for Web. It does not create a second Marketplace model, protocol, identity scheme, ranking system, or lifecycle authority.

## First checkpoint

This checkpoint contains:
- a Jetpack Compose application shell;
- an injected `MarketplaceTransport` port;
- a bounded application API client for `/api/intents`, `/responses`, and `/api/sync`;
- root browse state separated from exact hydrated intent/response detail;
- snapshot-watermark full-resync recovery and bounded incremental sync;
- structured root product-listing creation plus raw reviewed response JSON input;
- presentation-only WGS84 map text/surface;
- in-memory only application state.

The transport port is deliberately abstract. No concrete socket, HTTP stack, DNS, TLS, or remote-origin selection is introduced by this checkpoint.


## Exact M17.1B2 HTTP parity

The Android client follows the already-merged HTTP contract exactly:
- `POST /api/intents` returns a bounded write receipt with `change_seq` and `disposition`; it does not return a record;
- `POST /api/intents/{id}/responses` returns the same write-receipt shape;
- write dispositions are limited to `STORED` and `DUPLICATE`;
- `GET /api/intents/{id}/responses` currently returns one bounded `record_ids` list and exposes no continuation cursor.

Android therefore does not invent response pagination. The response panel is explicitly a bounded view and completeness is not claimed. Exact response records are hydrated only from the identities returned by that reviewed route.

## Sync model

Full resynchronization follows the same client-safe sequence as M17.1C:
1. capture a local snapshot watermark from `/api/sync` without a cursor;
2. hydrate the current root-intent projection through bounded opaque list pages;
3. promote the captured watermark only after hydration succeeds;
4. continue bounded incremental sync from that watermark.

`SYNC_CURSOR_EXPIRED` triggers full resynchronization. A sync page budget that ends with `has_more=true` must report that more changes remain; it must not claim global or local completion.

Sync history is coordination evidence only. It does not classify a record as a root intent or response and does not establish global completeness, truth, ownership, ranking, legitimacy, or settlement state.

## Authoring boundary

Root product-listing creation serializes only the 12 reviewed primitive M17.1R transport fields to `/api/product-listings`; M17.1Q/M72 remains authoritative for semantic validation and record construction. Response authoring still forwards raw reviewed record JSON. Android source does not build, sign, validate, or derive canonical Record Identity for Marketplace/OLP records.

## Authority boundary

This repository checkpoint performs source-level development only:
- no Android runtime or emulator launch;
- no live network or concrete Android HTTP transport;
- no Android SDK/JDK/Gradle installation or dependency resolution;
- no persistent local cache, database, preferences, credentials, or session storage;
- no app signing, keystore use, Play Console, or distribution;
- no self-update, package installation, download/install, or background updater capability;
- no production server/database/deployment mutation.

The current workstation does not expose a validated Android build toolchain, so this checkpoint does not claim Android compilation or APK validation. Those claims require a separately reviewed toolchain and an observed green build.

Offline cache and application update/distribution remain later explicitly reviewed sub-slices with their own retention, integrity, rollback, signing, and provenance requirements.
