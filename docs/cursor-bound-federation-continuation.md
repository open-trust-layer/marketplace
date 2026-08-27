# Cursor-Bound Federation Continuation Planning

Milestone 29 adds a **transport-free, one-step continuation planner** above the accepted M8/M24/M28 federation runtime.

Its purpose is deliberately narrow: given one prior M8 request, the exact `PreparedFederationExchange` produced for that request, and one already validated M28 page, determine whether there is no continuation or prepare exactly one next **unsent** M8 request carrying the page's opaque cursor.

M29 does not transmit that request and does not introduce a synchronization loop.

## Authority boundary

```text
next_cursor                  != network permission
cursor binding               != authorization
cursor binding               != peer identity proof
cursor binding               != source completeness proof
truncated page               != permission to loop
prepared continuation        != transmitted continuation
prepared continuation        != automatic cursor follow
same source/scope/operation  != same authorization validity
page sequence                != global marketplace history
missing later page           != deletion evidence
```

A successful M29 result therefore keeps all of these facts negative:

- network invoked = false;
- cursor automatically followed = false;
- authorization established = false;
- source completeness established = false;
- global completeness = `UNKNOWN`;
- deletion evidence = false;
- agreement created = false;
- protected side effect authorized = false.

## Inputs and independent binding

The planner requires all three values:

1. the original prior request mapping;
2. the prior `PreparedFederationExchange`;
3. the `ValidatedFederationPage` produced for that exchange.

The original request is required because M8 cursor binding operates on the **scope object**, not only the page's stored scope fingerprint. M29 re-runs the existing injected M8 request validator so the normalized scope and its fingerprint are recovered through the same semantic authority used by M24.

M29 then requires exact agreement across the normalized request, prepared binding, prepared envelope, and validated page for:

- source;
- operation;
- scope fingerprint;
- required capabilities;
- page size;
- request envelope marker/version/message type;
- prior request payload.

A final page is not allowed to bypass these checks. Context is validated first; only then may `page_truncated == false` and `next_cursor is None` produce `NO_CONTINUATION`.

## Cursor semantics remain M8 semantics

M29 does not implement a second cursor algorithm.

The packaged runtime receives injected cursor helpers and the reference composition uses the existing M8 functions:

- `bind_cursor(source, operation, scope, cursor)`;
- `validate_cursor_binding(binding, source, operation, scope)`.

The planner independently requires the validator result to preserve:

- `status == CURSOR_BOUND_TO_SOURCE_OPERATION_SCOPE`;
- exact cursor byte count;
- `authorization_proof == false`;
- `source_completeness_proof == false`.

Any hostile or miswired helper that promotes cursor binding into authorization or completeness fails closed.

## Exactly one request change

For a truncated page, the planner copies the prior request and changes **only** the `cursor` field.

If the prior request had no cursor, the field is added. If it already had a cursor, page N -> N+1 replaces that value with the exact new opaque bytes. Every other host-representation key/value must remain equal.

The next request is passed through the existing `OfflineFederationService.prepare(...)`; M29 never constructs a `PreparedFederationExchange` directly.

The returned continuation must:

- remain `transmitted == false`;
- preserve the exact prior `FederationRequestBinding`;
- preserve the prior envelope marker/version/request message type;
- carry exactly the constructed next request as payload;
- preserve the exact cursor bytes.

Any drift fails closed.

## One-step only

One invocation yields either:

```text
NO_CONTINUATION
```

or:

```text
PREPARED -> one PreparedFederationExchange
```

There is no loop, recursion, retry, backoff, concurrency, scheduler, cursor auto-follow, endpoint discovery, DNS, TLS, HTTP, socket, process, filesystem, or background worker in the M29 module.

A later multi-page network orchestrator is a separate HIGH-risk milestone.

## Privacy and retention

Cursor bytes are opaque transport control data. M29:

- does not interpret them;
- does not derive URLs or endpoints from them;
- does not log them;
- does not write them to a file, cache, database, journal, or checkpoint;
- does not duplicate them into the public outcome object.

Cursor-bearing values exist only in the caller-supplied page/request and the newly prepared request/envelope. If a future component retains such values after use, they remain subject to the project's `EPHEMERAL` maximum of 10 seconds post-use.

## Failure model

Planning is local and side-effect-free. Failures may include:

- malformed or mismatched prior request;
- prior prepared-envelope mismatch;
- validated-page binding mismatch;
- invalid page authority flags;
- missing/empty/oversized truncated-page cursor;
- request-validator failure or hostile result;
- cursor bind/validation failure;
- cursor authority/completeness promotion;
- continuation prepare failure;
- binding/message-profile/request/cursor drift;
- a prepared continuation falsely reporting prior transmission.

Failure creates no network operation, storage mutation, retry, or background continuation.

## Packaging and conformance

M29 adds no Marketplace runtime dependency and introduces no new semantic vector suite. Existing semantic authority remains M8 and the pinned Open Layer Protocol source.

Acceptance requires:

- all Marketplace unit/adversarial tests green;
- existing 816 semantic vectors unchanged and passing;
- all 13 deterministic generators replaying byte-for-byte;
- repository audit green;
- reproducible wheel/artifact gate green;
- isolated runtime and reference-adapter package smokes green;
- Git whitespace checks green;
- `marketplace/runtime/continuation.py` present in the shipped runtime package;
- this document present in the repository;
- exact-head PR acceptance evidence and merged-main CI before M29 is declared complete.

## Out of scope

M29 intentionally excludes:

- performing the continuation POST/GET;
- automatic cursor following;
- multi-page loops;
- retries/backoff;
- parallel page execution;
- cumulative synchronization budgets;
- durable checkpoints/resume;
- cursor replay cache;
- endpoint discovery;
- authentication/API keys/mTLS/signatures;
- proof verification;
- transactional repository semantics;
- inbound federation service.
