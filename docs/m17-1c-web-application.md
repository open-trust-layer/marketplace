# M17.1C Web — Shared Marketplace Application Client

Status: source-level Web client staging. No browser launch or live HTTP server is authorized by this slice.

## Purpose

M17.1C Web provides the first interactive Web surface above the shared Marketplace application API introduced by M17.1B/M17.1B2. It consumes only same-origin `/api/...` routes and does not define a second Marketplace model.

The initial surface combines bounded intent list, presentation-only WGS84 map projection, exact record detail, raw reviewed-record JSON create/respond forms, and client-side sync recovery.

## Sync recovery

The client captures a snapshot watermark before bounded full list/detail hydration. It then resumes incremental `/api/sync?cursor=N` polling semantics from that local application watermark. `SYNC_CURSOR_EXPIRED` restarts the same bounded snapshot/full-resync sequence.

Full-resync hydration follows the opaque `/api/intents` cursor across at most four bounded pages. Invalid or repeated cursors, duplicate identities across pages, or exhaustion of that page budget fail closed before the captured snapshot watermark is promoted to the active incremental sync cursor.

The watermark is application coordination metadata only. It does not claim protocol truth, global completeness, ownership, agreement, ranking, or legitimacy.

The sync stream is not treated as the root browse projection. Incremental sync consumes at most four pages per explicit sync action; if the final page still reports `has_more=true`, the client refreshes the bounded root view but reports that more changes remain instead of claiming synchronization is complete. Any validated sync change marks the bounded browse view dirty; the client then refreshes root intent identities through `/api/intents`. Exact response identities are hydrated separately through `/api/intents/{id}` for detail display and are never inserted into the root list by browser-side semantic inference.

## Authority boundary

The Web client uses no local persistent storage, credentials, cookies, service workers, background workers, CDN dependencies, external map providers, or cross-origin API targets. Human/record text is rendered with safe DOM text primitives rather than HTML injection.

## Explicit exclusions

This staging slice performs no browser launch and starts no live HTTP server. It adds no socket listener, DNS/TLS provider, live PostgreSQL connection or migration, credential/session authority, Android runtime, production deployment, payment, settlement, fulfillment, or provider-administration capability.

The create/respond forms remain at the raw reviewed record JSON boundary. JavaScript does not build, sign, validate, or derive canonical record identity; the shared application/API boundary remains authoritative for admission.

## Next slice

After M17.1B2 is separately authorized and merged, this staging work can be rebased onto merged-green `main`, validated as its own exact-head work unit, and prepared for M17.1C Web review. **M17.1D Android** remains a separate client consuming the same shared contract.
