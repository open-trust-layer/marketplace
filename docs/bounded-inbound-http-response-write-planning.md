# M44 — Bounded Inbound HTTP Response Write Planning

M44 adds a pure, transport-free next-write budget above one exact M43 prepared inbound HTTP response.

It accepts only an integrity-replayed M43 prepared response plus caller-local `write_calls_completed` and `bytes_written` accounting. It returns either `WRITE` with a finite `next_write_bytes` budget or `COMPLETE` when local accounting covers the whole prepared response.

`COMPLETE` is **not proof of transmission**. M44 never invokes a writer, touches a socket, terminates TLS, authenticates a requester, establishes peer identity, or creates Marketplace truth/trust/authorization/protected-side-effect authority. All such facts remain explicitly false.

The plan never contains response payload bytes or a raw write slice. It binds only the M43 integrity witness and bounded byte/call metadata. A future layer that owns actual response progress must bind the original M43 response independently rather than infer transport facts from M44 accounting.

## Limits

Defaults:

- `max_write_calls = 64`
- `max_write_bytes = 16 KiB`

Hard maxima:

- `max_write_calls = 1024`
- `max_write_bytes = 1 MiB`

If response bytes remain when the write-call budget is exhausted, M44 fails closed. A response already fully accounted may be `COMPLETE` at the exact call limit because no additional write is planned.

## Retention

M43 response material and M44 plans are **EPHEMERAL**, maximum 10 seconds post-use. M44 adds no cache, journal, file, log, checkpoint, process, thread, timer, background worker, or durable store.

## Out of scope

Writer invocation, socket `send`, partial-write outcome semantics, connection lifecycle, listener, TLS, deployment, retries/backoff, and live peer execution are separate later boundaries.
