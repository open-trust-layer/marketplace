# Milestone 47 — Bounded Inbound HTTP Response Write Outcome Semantics

## Status

M47 gives one **already-returned** response-write result a bounded local meaning without invoking a writer.

```text
M46 owned state <- M47 PROGRESS / ZERO / FAILURE outcome
```

M47 is transport-free and does not grant `NETWORK_EXTERNAL` authority.

## Canonical outcomes

`InboundHttpResponseWriteOutcome` has exactly three canonical kinds:

- `PROGRESS`: one positive exact integer `accepted_write_bytes`;
- `ZERO`: zero accepted bytes, terminal before completion;
- `FAILURE`: zero accepted bytes, generic terminal failure.

No exception/error text is carried by `FAILURE`. Outcomes contain no raw response bytes and no writer/socket/TLS/transmission authority.

An outcome models a caller-supplied fact for local state transition. It does **not** prove how that value was produced.

## Construction binding

`BoundedInboundHttpResponseWriteOutcomeHandler` retains one exact M46 session and captures the exact M46 `progress`, `accept_write_count`, `take_completed`, `close`, and `closed` function identities at construction.

Later replacement of public M46 methods cannot substitute authority. Coherent private function/bound-method rebinding is detected by the binding witness.

## Original-object validation order

M46 documents that `dataclasses.replace()` can reset `init=False` fields to defaults. M47 therefore checks every authority-negative field on the **original** supplied M46 progress/completion object before replay, then checks the replayed object again.

M47 applies the same rule to its own outcome objects. Raw `dataclasses.replace()` alone is never treated as proof that the source object carried no promoted authority.

## PROGRESS semantics

For one `PROGRESS(n)` outcome M47:

1. validates and replays the exact outcome;
2. obtains exact current M46 progress;
3. rejects/clears if M46 is already locally complete;
4. calls captured M46 `accept_write_count(n)` exactly once;
5. if M46 rejects the already-returned count, closes M46 and preserves M46/M45/M44 reason codes;
6. validates authority on the original returned M46 progress before replay;
7. requires exactly one additional write-call count;
8. requires cumulative byte count to increase by exactly `n`;
9. requires `last_accepted_write_bytes == n`;
10. re-reads current M46 progress and requires it to equal the returned state.

A rejected already-returned progress count is terminal because the external producer of that count may already have advanced independently of local state. M47 does not retry it.

## ZERO and FAILURE

`ZERO` before local completion closes M46 and raises `WRITE_ZERO_BEFORE_COMPLETE`.

`FAILURE` before local completion closes M46 and raises `WRITE_FAILURE_BEFORE_COMPLETE` using generic local text only.

Neither outcome is retryable within M47.

## Completion

M47 never requires a synthetic outcome after M46 reaches `WRITE_ACTION_COMPLETE`. Call `take_completed()` instead. It delegates to the captured one-shot M46 completion handoff, checks authority on the original completion before replay, and requires the source M46 session to be closed.

Supplying any new outcome after M46 is already complete is a protocol misuse: M47 closes the session and fails `WRITE_OUTCOME_AFTER_COMPLETE` rather than silently accepting an extra result.

## Authority boundary

All M47 outcome objects and returned M46 progress/completion witnesses remain authority-negative:

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
PROGRESS(n)                 != proof writer was invoked
PROGRESS(n)                 != proof n bytes reached peer
M46/M47 local completion    != response transmission
ZERO                         != authenticated peer close
FAILURE                      != network provenance
```

## Explicitly out of scope

No writer callback, response slice, socket/send, listener, TLS, process, filesystem, persistence, logging, concurrency, deployment, credential handling, or live external-network execution exists in M47.

A later writer-invocation layer may invoke a caller-supplied writer only through deterministic/non-live fixtures during source acceptance unless separately authorized immediately before real external execution.

## Retention and recovery

All M47 outcome/state information is `EPHEMERAL` and must be released within 10 seconds post-use. Terminal paths close M46, which releases its retained M43 response reference. M47 does not claim automatic wall-clock deletion without caller lifecycle cooperation.

M47 mutates no external state. Recovery is ordinary source revert.
