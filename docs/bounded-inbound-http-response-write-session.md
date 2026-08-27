# Milestone 46 — Bounded Inbound HTTP Response Write Session

## Status

M46 owns response-write accounting above M44/M45 without invoking a writer or transport.

```text
M44 plan -> future already-returned write count -> M45 transition -> M46-owned next state
```

M46 is deliberately transport-free. It does not grant `NETWORK_EXTERNAL` authority and does not prove that any byte reached a peer.

## Construction boundary

`BoundedInboundHttpResponseWriteSession` accepts exactly one construction-bound M45 transitioner and one exact M43 `PreparedInboundHttpReadResponse`. The retained M45 transitioner must retain one exact M44 planner.

The constructor accepts no initial byte offset and no initial write-call count. Canonical state is always:

```text
bytes_written = 0
write_calls_completed = 0
```

The M43 prepared-response object is integrity-replayed and retained only while the session is open.

## Owned transition

`accept_write_count(accepted_write_bytes)` accepts one already-returned positive exact integer. It performs no writer call.

For each accepted count M46:

1. validates the owned state and construction-bound helper/configuration identities;
2. replays the exact current M44 plan;
3. invokes the captured exact M45 transition once;
4. preserves nested M45/M44 reason metadata on rejection;
5. rejects authority promotion on the original M45 transition before `dataclasses.replace()` can normalize `init=False` fields;
6. replays M45 transition integrity;
7. requires the M45 prior-plan witness to equal M46's exact current-plan witness;
8. requires exact one-call and exact byte-count advancement;
9. independently invokes M44 on the returned counters;
10. requires the independently derived M44 witness to equal M45's next-plan witness; and
11. mutates owned counters/plan only after every check succeeds.

A self-consistent hostile M45 next plan therefore cannot widen or alter the next M44 budget silently.

## State integrity

The open-state witness binds:

- exact retained M43 object identity;
- exact M43 integrity witness;
- owned cumulative byte count;
- owned write-call count;
- exact current M44 plan witness;
- captured M45 transition function identity; and
- captured M44 plan function identity.

Direct private counter resets, prepared-response rebinding, plan rebinding, captured-helper drift, and M45-retained-M44 binding drift fail closed.

## Public progress and completion

`InboundHttpResponseWriteSessionProgress` exposes only accounting and an M44 plan. It contains no raw response bytes.

`take_completed()` is available only after the current M44 plan is `COMPLETE`. It returns one frozen `CompletedInboundHttpResponseWriteSession` and closes the source session first. Completion is local accounting only.

`close()` is idempotent and releases M46's retained prepared-response reference. Closed state cannot be reopened through the public API.

## Authority boundary

The following facts remain false on M46 progress/completion objects:

```text
writer_invoked = False
socket_accessed = False
tls_terminated = False
transmitted = False
request_authenticated = False
peer_identity_proven = False
establishes_marketplace_truth = False
establishes_trust = False
establishes_authorization = False
authorizes_protected_side_effects = False
```

In particular:

```text
owned bytes_written       != proof bytes were sent
owned write-call count    != proof a writer was invoked
M44 COMPLETE              != transmission evidence
M45 accepted transition   != delivery evidence
M46 completed handoff     != authenticated peer response
```

## Explicitly out of scope

M46 contains no writer callback invocation, response-slice write, socket/send, listener, TLS, process, filesystem, persistence, logging, concurrency, deployment, credential handling, or live external-network execution.

A later writer-invocation layer may consume a writer only through deterministic/non-live fixtures during source review unless separately authorized immediately before real external execution.

## Retention

The retained M43 prepared response and all write-session state are `EPHEMERAL` and must be released within the project maximum of 10 seconds post-use. M46 provides explicit `close()` and one-shot completion ownership transfer but does not claim automatic wall-clock deletion without caller lifecycle cooperation.

## Recovery

M46 is source-only. Recovery is ordinary source revert. No external state, network peer, deployment, credential, database, settlement, or protected side effect is mutated by this milestone.
