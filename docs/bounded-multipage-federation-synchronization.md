# Bounded Multi-Page Federation Synchronization

**Milestone:** M31

**Status:** non-normative reference runtime architecture

**Risk:** HIGH

**Network posture:** concrete external I/O remains exclusively in existing M26/M27 adapters; development and CI use injected deterministic doubles

## Purpose

M31 composes four already reviewed boundaries into one strictly bounded sequential operation:

1. M26 performs one authorized federation control exchange;
2. M24 validates the returned M8 page without side effects;
3. M28 retrieves, verifies, and accepts exactly that page's Records;
4. M29 may prepare exactly one unsent continuation for a truncated page.

M30's deeply detached `PreparedFederationExchange` representation is the request-integrity foundation for every control send.

M31 does **not** add another socket, TLS, HTTP, DNS, resolver, proxy, credential, retry, scheduler, or persistence implementation.

## Authority boundary

```text
next_cursor                     != permission to send another request
prepared continuation           != transmitted continuation
one endpoint authorization      != unbounded loop authority
one successful exchange         != retry permission
one accepted page               != global completeness
finite control target sequence  != endpoint discovery
record target provider          != record authorization
page finality                    != global marketplace completeness
partial local progress          != transactional synchronization
synchronization outcome         != truth / trust / agreement / protected-action authority
```

The orchestrator never mints authorization. Every possible control request requires one explicit `FederationControlTarget` supplied before execution. Each target contains an exact endpoint and an already existing `FederationEndpointAuthorization`. A target slot is consumed by at most one control exchange.

Repeated use of the same authorization value in separate finite target slots is still a caller decision; M31 never expands one slot into an unbounded loop. M26 independently revalidates the selected authorization before DNS and again immediately before connection.

## Limits

`FederationSynchronizationLimits` defaults to:

- `max_pages = 4`;
- `max_total_records = 64`;
- `total_timeout_seconds = 120`.

Hard maxima are:

- 16 pages;
- 256 hydrated Records across the whole call;
- 300 seconds aggregate orchestration budget.

The aggregate time budget is a **phase-start budget**, not asynchronous cancellation. M31 checks a monotonic clock before and after blocking phases and never starts another external/control/hydration phase once exhausted. M26 and M28 retain their own phase-specific timeout enforcement for work already in progress.

## Execution order

For each page M31 performs this order:

```text
explicit control slot
    -> M26-compatible one-shot control exchange
    -> strict transport-result/negative-authority validation
    -> M24 side-effect-free page validation
    -> aggregate Record budget check
    -> bounded page Record-target resolution
    -> M28 hydrate_and_accept
    -> strict M28/M24 outcome cross-binding
    -> final page? stop
    -> local page/control/time bound exhausted? bounded stop
    -> repeated cursor? fail closed
    -> M29 one-step continuation planning
    -> strict continuation cross-binding
    -> next explicit control slot
```

M31 validates hostile/miswired helper results even when the helper has an existing runtime-compatible surface. In particular, a control result cannot claim retries, redirects, proxy/credential use, multiple connection attempts, trust, truth, agreement, or authorization; M28 and M29 outcomes are likewise checked for forbidden authority promotion.

## Cursor handling

Cursors remain opaque bytes. M31 does not decode, log, persist, index, rank, or reinterpret them.

Within one synchronization call, M31 keeps only a small in-memory set of cursor byte values already used/observed. Repetition fails closed with `CURSOR_REPLAY_DETECTED` before another continuation is planned or sent. This is a per-call loop-safety guard, not a durable replay cache and not a completeness proof.

The cursor set is EPHEMERAL content. It exists only for the active call and is not retained by the orchestrator afterward.

## Bounded stop versus failure

A fully accepted truncated page can end the call normally with one of these bounded local stop dispositions:

- `STOPPED_PAGE_LIMIT`;
- `STOPPED_CONTROL_TARGET_LIMIT`;
- `STOPPED_TIME_LIMIT`.

These dispositions do not claim an error at the already accepted page. They state only that M31 refused to begin another continuation step.

A malformed result, hostile authority claim, Record-budget overflow, cursor replay, M24/M28/M29 failure, or other invariant violation raises `FederationSynchronizationError` with a stable local code.

## Partial progress

M31 is not cross-page transactional. A later page can fail after earlier pages were already accepted into the existing EPHEMERAL repository.

Therefore:

```text
later-page failure != rollback of earlier accepted pages
bounded stop       != global completeness
final M8 page      != global marketplace completeness
```

The outcome reports counts and operational facts only:

- pages accepted;
- control exchanges performed;
- continuations planned/transmitted;
- hydrated Record count;
- Record retrieval attempts;
- final-page observation;
- last declared source completeness;
- whether control/Record transport was invoked.

It always preserves `global_completeness = UNKNOWN` and negative truth/trust/agreement/authorization/protected-side-effect facts.

## Record-target provider

The injected `PageRecordTargetProvider` receives only the validated page number and exact `record_ids`. It does not receive cursor bytes.

Its output is bounded to exactly one `RecordHydrationTarget` per page Record identity before M28 is invoked. The provider itself is not a network authorization mechanism: every returned target still contains an explicit M27/M25 authorization that M28/M27 validates before use.

M31 performs the aggregate Record-limit check **before** invoking the provider, so an oversized page cannot trigger target resolution or Record transport.

## No retry, parallelism, or background execution

M31 contains no retry/backoff path, parallel page execution, parallel Record retrieval, recursion, background task, scheduler, thread, process, or async loop. M28 remains sequential and M26 remains one-shot.

A failed control exchange, hydration, or continuation plan terminates the call. M31 never silently retries.

## Retention and privacy

M31 introduces no durable storage. Request, page, cursor, authorization, endpoint, and target values are operational/transient inputs already governed by existing runtime policy.

Cursor/request/response content remains EPHEMERAL with the project maximum retention of **10 seconds post-use**. M31 does not log or persist those values.

No credentials or secrets are introduced.

## CI and live-network boundary

M31 development and CI MUST use deterministic injected control-transport and Record-retrieval doubles. No live federation peer is authorized by this milestone or its tests.

Actually invoking M31 with concrete default M26/M27 network adapters is a `NETWORK_EXTERNAL` operation and requires explicit operator authorization immediately before that live execution.

## Recovery

M31 adds no schema migration, deployment, durable checkpoint, or server state. Code recovery is by reverting the M31 merge commit.

Already accepted EPHEMERAL Records are governed by the existing repository retention lifecycle; M31 does not promise rollback of prior page ingest.
