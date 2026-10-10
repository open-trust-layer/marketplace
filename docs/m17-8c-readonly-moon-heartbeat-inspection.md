# M17.8C — Read-only Marketplace Moon heartbeat source inspection

## Purpose

Source metadata can be stale while an unrelated process serves a loopback
port. Neither a file's existence nor a process ID, on its own, proves that
Marketplace is healthy, supervised, current, or connected to Moon Core.

The standalone `tools/marketplace_moon_heartbeat_inspect.py` inspects only
the explicitly named local state root and its
`heartbeats/hello-world-marketplace/<instance_uuid>.json` files. It does
not inspect or alter another component's state.

## Operator invocation (PowerShell)

From an exact Marketplace checkout (with Python 3.11+):

```powershell
python tools/marketplace_moon_heartbeat_inspect.py `
  --state-root "C:\Users\ilyav\.moon\state" `
  --expected-release-sha "<reviewed-40-hex-main-sha>" `
  --max-age-seconds 45
```

The operator supplies the **release being evaluated**. A repository HEAD,
a stale file's claimed version, and a running server are independent facts.

The tool reads at most 32 source JSON records of 4096 bytes each, requires
regular files, strict exact JSON fields, duplicate-free standard JSON, a
canonical UUID filename matching `instance_id`, well-formed UTC timestamps,
Marketplace service ID, positive integer process ID and bounded version and
environment strings. Files named `relay.json` are **not** local producer
evidence and are ignored. The report contains only stable codes, a bounded
file count and age; it never prints filenames, process identities, record
contents or raw exception text.

## Fail-closed outcomes

| Result | CLI exit | Meaning |
| --- | --- | --- |
| `SOURCE_MISSING` | 1 | No local producer source JSON found |
| `SOURCE_STALE` | 1 | Latest embedded `observed_at` exceeds the chosen age |
| `SOURCE_FUTURE` | 1 | Latest timestamp is more than five seconds ahead |
| `RELEASE_MISMATCH` | 1 | Freshest claimed release differs from the expected exact SHA |
| `SOURCE_INVALID`, `SOURCE_UNAVAILABLE`, `TOO_MANY_FILES` | 1 | File/schema/availability or scan bound failure |
| `FRESH_METADATA_UNVERIFIED` | **2** | Fresh matching metadata only; **not** process health |

There is deliberately **no `PASS`, `HEALTHY`, or exit-0 result**. Even
fresh metadata does not prove the process is alive, that its PID wasn't
reused, that its port serves that release, or that the relay accepted it.
A current-runtime health declaration must come from a separate
owner-authorized process/supervisor/relay evidence chain. This inspector
must not be used to bypass any of those checks or refresh stale timestamps.

## Relationship to Moon Company #519

The Marketplace manifest continues to declare a **development workspace**
(`health.kind=workspace`); no new heartbeat requirement is imposed.
This diagnostic does not launch Marketplace, enable the opt-in producer,
restart tasks, connect to X230i, read secrets, touch PostgreSQL, or alter
payment/customer-order state. The workspace versus supervised-runtime
decision and three genuine end-to-end heartbeat cycles remain in
[Issue #519](https://github.com/open-trust-layer/marketplace/issues/519).

Source-only rollback: revert the inspector, its tests and this document.
