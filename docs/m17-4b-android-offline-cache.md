# M17.4B Android offline cache

M17.4B implements the owner-approved `MARKETPLACE_ANDROID_OFFLINE_CACHE_MVP` as a source-only Android capability.

Exact starting baseline: `1155c9c1452d40785bf8c219a1a467e8372d28c6`.

## Approved retention profile

The cache may retain at most:

- 320 records total;
- 256 root records;
- 64 responses for the most recently selected cached parent;
- 32 MiB of canonical Marketplace record JSON;
- 24 hours since the last successful authoritative online synchronization that leaves local state non-truncated.

Cached content is always presented as `OFFLINE / CACHED` and is never represented as current, complete, globally authoritative, owned, endorsed, or protocol truth.

## Storage boundary

The Android adapter uses one fixed app-private file under `Context.filesDir`; callers cannot supply a path.

The on-disk envelope contains a format version, a JSON payload string and a SHA-256 digest of that exact payload. Loads fail closed on malformed UTF-8/JSON, checksum mismatch, unknown shape, invalid record identity, invalid canonical record JSON, count/byte overflow, clock rollback, or unsupported format.

Writes use a fixed temporary file plus same-directory atomic replace. Expired cache is removed before adoption. Deletion/write failure is surfaced as a stable non-reflective cache error rather than silently extending retention.

No Room, DataStore, SharedPreferences, database schema, external storage, device identifier, credential, secret, or new dependency is introduced.

## Online/offline state

A successful full synchronization writes a fresh root snapshot and starts a new 24-hour cache epoch.

A successful incremental synchronization refreshes that epoch only when the bounded sync finishes with `has_more == false`. A truncated/backlogged sync does not refresh cache retention.

When startup cannot reach the exact reviewed loopback API because the transport is unavailable, a non-expired valid snapshot may be adopted as the explicit offline fallback. Offline selection uses only cached root/detail data and, when available, the cached responses for the last selected parent.

Create and Proposal operations remain online-only. The UI disables submit controls while cached/offline, and the state layer independently fails closed with `OFFLINE_WRITE_UNAVAILABLE`.

There is no background sync, retry worker, alarm, WorkManager, service, push path, or hidden network activation. Manual foreground sync is the only path back to online authoritative application state.

## Authority boundary

This implementation is source-only. This change performs:

- no Android build;
- no adb, emulator, device action, APK install or app-data mutation;
- no dependency installation or widening;
- no signing, publishing or update distribution;
- no server or PostgreSQL mutation;
- no configuration/service mutation;
- no production access or deployment.

A later real Android build/device acceptance remains a separate exact-head authorization boundary. Merge likewise remains separately governed.

### Foreground expiry limitation

Because this approved slice explicitly forbids background services, alarms and WorkManager, the app cannot wake itself at the 24-hour boundary solely to delete a file. After 24 hours the cache is never eligible for adoption; the next foreground cache load removes it before use. A detected wall-clock rollback also deletes the cache fail-closed. Therefore the implementation does not claim wall-clock-timed physical erasure while the application is not running.
