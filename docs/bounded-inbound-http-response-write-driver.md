# Milestone 49 — Bounded Inbound HTTP Response Write Driver

## Status

M49 adds finite local orchestration above the one-step M48 write invoker.

```text
M46 write state <- M47 outcome <- M48 one writer step <- M49 bounded driver
```

M49 owns no writer, socket, TLS stack, listener, deployment, process, or concrete transport. Acceptance uses deterministic in-memory writer and clock doubles only.

## Construction binding

`BoundedInboundHttpResponseWriteDriver` requires one exact M48 invoker and one callable clock. It captures the exact M48 `invoke_once`, `close`, and `closed` functions and the exact M48→M47→M46 graph present at construction.

The retained M44 `max_write_calls` inside M46 remains authoritative. M49 never increases that lower-layer write-call ceiling.

## Finite orchestration

`run_to_completion()` contains exactly one bounded loop. Each iteration calls the construction-bound M48 invoker at most once.

M49 limits are:

- `max_steps`: explicit finite driver-step ceiling;
- `max_elapsed_seconds`: explicit finite elapsed-time ceiling measured by the injected monotonic clock.
The driver may use at most `M44 max_write_calls + 1` steps. The one additional step is only the zero-writer M48 completion transfer after the final accepted write. It does not permit an additional writer call.

The default step ceiling is clamped to that same lower-layer bound plus the completion-transfer step. The absolute M49 hard maximum is 1025 steps, corresponding to M44's maximum 1024 write calls plus one transfer.

## Clock semantics

The injected clock is treated as a local accounting capability, not network authority. Values must be finite non-boolean numbers and must never move backwards.

M49 checks elapsed time before and after every M48 step. Clock exception, non-finite value, regression, or time-budget exhaustion is terminal and triggers construction-bound cleanup. Arbitrary clock exception text is not reflected.

## Failure and cleanup

M48 errors are never retried. Their nested M47/M46/M45/M44 reason metadata is preserved through the M49 error boundary.

After any consumed step, configuration drift, result drift, clock failure, time exhaustion, or step exhaustion closes the M48/M47/M46 source through the construction-captured cleanup boundary. If that cleanup authority itself cannot be verified, M49 reports `WRITE_DRIVER_CLEANUP_UNCERTAIN` instead of claiming erasure.

Public method replacement after construction cannot substitute M48 authority. Retained M44 limit drift is detected fail-closed.

## Completion

An M48 `PROGRESS` result increments local driver accounting only when its integrity replay succeeds. A later M48 `COMPLETED` result performs the one-shot M46 completion handoff with no writer call.
The completion result records driver steps, writer invocations, cumulative M46 write-call accounting, and elapsed local time. It carries no raw response bytes.

## Authority boundary

Successful local write accounting does **not** establish:

```text
socket_access_proven = False
tls_terminated = False
transmitted = False
request_authenticated = False
peer_identity_proven = False
establishes_marketplace_truth = False
establishes_trust = False
establishes_authorization = False
authorizes_protected_side_effects = False
```

M49 therefore does not claim peer receipt, network origin, authentication, authorization, or transmission merely because an injected writer returned accepted counts.

## Explicitly out of scope

No concrete socket/send stack, connect/bind/listen/accept, TLS termination, HTTP server, process, filesystem, persistence, logging, concurrency, deployment, credential handling, provider administration, external service activation, or live network execution is introduced.

A real network-backed writer remains a separate live-I/O boundary requiring separate authorization immediately before execution.

## Retention and recovery

All progress, completion, local timing/accounting, and retained response state remain EPHEMERAL and must be released within 10 seconds post-use. Recovery is ordinary source revert; M49 acceptance mutates no external state.
