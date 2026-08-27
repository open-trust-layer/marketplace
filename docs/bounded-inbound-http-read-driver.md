# Bounded Inbound HTTP Read-to-Completion Driver

**Milestone:** 42
**Risk:** HIGH
**Runtime external-I/O capability:** only transitively through the already construction-bound M41 injected reader; development/CI uses deterministic in-memory doubles only.

## Purpose

M42 composes the one-step M41 boundary into a strictly finite read-to-completion driver. It does not own, accept, discover, or invoke a reader directly.

```text
M37 finite read-call ceiling
        |
        v
M39-owned read state
        |
        v
M40 outcome semantics
        |
        v
M41 exactly zero-or-one reader call per invocation
        |
        v
M42 finite step/time orchestration
```

M42 is deliberately narrower than a connection loop. It drives one existing request session only, has one bounded loop, stops on first terminal error, and adds no concrete transport primitive.

## Construction-bound authority

The constructor accepts exactly:

- one exact `BoundedInboundHttpReadInvoker`;
- one injected callable monotonic clock;
- optional exact immutable `InboundHttpReadDriverLimits`.

M42 captures the original exact M41 `invoke_once`, `close`, and `closed` getter functions and binds them to the supplied exact M41 instance. It also validates the reviewed M41 -> M40 -> M39 object chain and snapshots the M39-retained M37 `max_read_calls` ceiling.

M42 never stores or calls M41's injected reader directly.

The supplied M41/M40/M39 chain may already own a valid partial or complete request state when M42 is constructed. M42 does not reset or reinterpret that prior state. Its step/time accounting starts only when `run_to_completion()` begins, while M39 `reads_completed` remains cumulative local accounting for the whole owning session.

The configured M42 step ceiling must not exceed the actual M37 read-call ceiling retained by the construction-bound M39 session. With no explicit M42 limits, the effective default is `min(64, retained_m37_max_read_calls)`.

This is intentionally conservative: an M41 completion-transfer call consumes an M42 orchestration step even though it performs no reader call. M42 therefore may stop before exercising every theoretical M37 read slot rather than widening lower-layer authority.

## Finite limits

```text
default max M42 steps:          64
hard max M42 steps:           1024
default aggregate time budget: 30 seconds
hard aggregate time budget:   120 seconds
```

`max_steps` is an exact positive integer. Boolean impersonation is rejected.

`max_elapsed_seconds` is a finite positive non-boolean integer/float and is normalized to float. NaN, infinities, zero/negative values, and values above the hard maximum are rejected.

The injected clock is checked before and after every M41 step. Clock exceptions, non-finite values, or backward movement fail closed with stable M42 reason codes. There is no sleep, alarm, thread, scheduler, cancellation token, signal, or background timeout worker.

The elapsed-time budget covers only the M42 `run_to_completion()` call. It does not claim to measure or constrain time spent before M42 was constructed around an existing M39 session.

## Driver behavior

`run_to_completion()` contains one finite `for` loop bounded by the construction-frozen M42 step ceiling.

For every iteration M42:

1. validates construction bindings and the reviewed M41 -> M40 -> M39 chain;
2. samples the clock and proves it has not regressed;
3. checks the aggregate time budget before starting the next M41 step;
4. invokes the construction-captured exact M41 `invoke_once()` exactly once;
5. treats every M41 error as terminal and never retries it;
6. validates M42/M41 bindings again;
7. samples and validates the clock again;
8. replays the exact immutable M41 result;
9. increments M42 `reader_invocations` only when that exact M41 result truthfully records `reader_invoked=True`;
10. continues only for exact M41 `PROGRESS` carrying a canonical M37 READ/COMPLETE plan;
11. returns immediately for exact M41 `COMPLETED` after proving the M41 source session is closed.

Step exhaustion closes/clears through captured M41 cleanup authority before failing `READ_DRIVER_STEP_LIMIT_EXHAUSTED`.

Time exhaustion closes/clears before returning `READ_DRIVER_TIME_LIMIT_EXHAUSTED`.

A lower-layer error is wrapped as `READ_DRIVER_INVOCATION_REJECTED` while preserving M41/M40/M39/M38/M37/M36/M35 nested reason codes.

## Cleanup uncertainty

Because M42 may be constructed around an already-partial M39 session, a run-time binding or clock failure must not assume that zero completed M42 steps means zero retained request material. Run-time failures therefore use the construction-captured M41 cleanup boundary even before M42's first reader step when cleanup authority is intact.

M42's cleanup uses only the construction-captured exact M41 `close` and `closed` bindings.

If those bindings are no longer provably the construction-bound cleanup authority, or cleanup cannot be verified, M42 reports `READ_DRIVER_CLEANUP_UNCERTAIN` rather than claiming state was cleared.

This is fail-closed state-accounting, not process isolation. M42 does not claim to sandbox arbitrary same-process memory corruption.

## Completion result

`CompletedInboundHttpReadDriverResult` wraps the existing exact M39 `CompletedInboundHttpReadSession` one-shot handoff and records:

- M42 invocation steps performed during this driver run;
- M42-observed reader invocations, counted only from exact M41 results with `reader_invoked=True` during this driver run;
- cumulative M39 `reads_completed` local accounting, derived from the exact completion handoff;
- elapsed monotonic time for this M42 run;
- nested completion integrity witness;
- authority-negative facts.

`reads_completed` is local session accounting, not proof that an external reader or network was invoked. It may be greater than M42 `driver_steps` when the supplied session already contained valid prior transitions before M42 began. Conversely, `reader_invocations` describes only reader calls observed through M41 during this M42 run and does not prove that those calls accessed a socket or network.

Its M42 integrity witness includes only the existing M39 completion integrity snapshot plus bounded operational metadata, not a second copy of the raw request prefix.

The M39 completion object itself remains the explicit one-shot raw request handoff.

## Authority boundary

```text
finite M42 orchestration       != socket/listener authority
M41 reader invocation          != network origin proof
M39 reads_completed            != proof a reader was invoked
multiple M41 steps             != retry permission after error
elapsed clock budget           != transport timeout enforcement
completed request bytes        != authenticated requester
completed request bytes        != Marketplace truth or trust
M42 completion                 != response transmission
M42 source                     != deployment permission
```

M42 result facts remain:

```text
socket_access_proven = False
network_origin_proven = False
request_authenticated = False
peer_identity_proven = False
establishes_marketplace_truth = False
establishes_trust = False
establishes_authorization = False
authorizes_protected_side_effects = False
```

These mean M42 does not establish those facts. They do not claim that an eventual separately authorized concrete injected reader performed no network activity.

## Retention

M42 introduces no durable data store. Request bytes, M40/M41 outcomes, M42 intermediate results, and the final M39 completion handoff remain **EPHEMERAL, maximum 10 seconds post-use**.

No file, cache, journal, log, database, checkpoint, background erasure worker, or durable timer is added.

## Source exclusions

M42 itself contains no:

- direct reader callable field;
- socket, `recv`, network client, bind/listen/accept/connect;
- TLS/SSL;
- response send/write;
- retry/backoff;
- sleep/alarm/signal;
- asyncio/thread/process/subprocess;
- filesystem persistence;
- logging;
- deployment/service activation;
- credentials/secrets.

## Governance

M42 is a HIGH-risk source milestone eligible only while the adopted Section 7 standing owner mandate is valid. Maintainer/security self-review and CI are not independent human review.

Merge requires exact-head/current-main CI, HIGH adversarial/security review, expected-head SHA guarding, honest review provenance, and exact merged-main CI before completion.

The standing source-control mandate does not authorize actual live external reader execution, deployment, credentials/provider administration, CRITICAL work, destructive external state, or protected economic side effects.

## Out of scope

Concrete socket reader; accepted-socket adapter; listener/accept loop; TLS; response writer; full connection transaction; remote requester authentication/mTLS; rate limiting; retry/backoff; keep-alive/multiple requests; deployment/service activation; live Marketplace peer execution.

## Recovery

M42 adds only source/docs/tests. No migration, durable state, secret, deployment, listener, or live external side effect is introduced. Recovery is a normal source revert.
