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
- raw reviewed record JSON create/respond inputs;
- presentation-only WGS84 map text/surface;
- in-memory only application state.

The transport port is deliberately abstract. No concrete socket, HTTP stack, DNS, TLS, or remote-origin selection is introduced by this checkpoint.

## Sync model

Full resynchronization follows the same client-safe sequence as M17.1C:
1. capture a local snapshot watermark from `/api/sync` without a cursor;
2. hydrate the current root-intent projection through bounded opaque list pages;
3. promote the captured watermark only after hydration succeeds;
4. continue bounded incremental sync from that watermark.

`SYNC_CURSOR_EXPIRED` triggers full resynchronization. A sync page budget that ends with `has_more=true` must report that more changes remain; it must not claim global or local completion.

Sync history is coordination evidence only. It does not classify a record as a root intent or response and does not establish global completeness, truth, ownership, ranking, legitimacy, or settlement state.

## Authoring boundary

Create/respond accepts raw reviewed record JSON and forwards that raw body through the shared application API boundary. Android source does not build, sign, validate, or derive canonical Record Identity for Marketplace/OLP records.

Human-friendly structured authoring remains a shared backend/application concern so Web and Android do not drift into competing semantic implementations.

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
