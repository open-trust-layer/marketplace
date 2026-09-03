# M17.1G cross-client API contract parity

M17.1G adds a **declarative test fixture** for the already reviewed Marketplace Application HTTP contract. It exists only to make drift between the Python binding, Web client, and Android source visible in deterministic repository tests.

The fixture is not a protocol definition, server, schema authority, runtime registry, or client-specific business model. The Python Marketplace Application API remains the application semantic boundary, and canonical Marketplace records remain the semantic source objects.

## Shared contract

The parity fixture records the existing reviewed bounds and route shapes:

- page limit: 64 records/changes;
- request JSON bound: 256 KiB;
- response JSON bound: 300 KiB;
- `GET /api/intents` list semantics with optional bounded cursor;
- `POST /api/intents` write receipt only;
- exact intent detail hydration;
- response listing remains non-cursor and makes no completeness claim;
- response creation returns the same write-receipt shape;
- sync watermark and incremental sync retain `changes`, `next_cursor`, and `has_more`;
- `SYNC_CURSOR_EXPIRED` remains the stable HTTP 409 recovery signal.

## Authority boundary

The sync cursor is **local application coordination only**. It is not global truth, federation completeness, ownership, legitimacy, ranking, lifecycle authority, or protocol state.

The Web client now mirrors the reviewed 300 KiB application response bound before JSON parsing. This is client-side hardening only; it does not add a server, network endpoint, background process, persistent state, or credential surface.

M17.1G grants **no Android build or dependency resolution authority**. It does not install JDK/Gradle/Android SDK, bootstrap a wrapper, resolve repositories, compile Kotlin, package APK/AAB, execute an emulator/device, sign, install, distribute, or activate an updater.

No live PostgreSQL/database action, product backend activation, production deployment, service/configuration change, or runtime mutation is part of this checkpoint.

A future separately authorized compiled Android lane must prove that its executable client behavior preserves the same reviewed route, bound, write-receipt, response-list, and sync semantics. Until then, Android evidence remains source-level only.
