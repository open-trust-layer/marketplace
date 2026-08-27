# Send-Time Prepared Payload Binding Hardening

Milestone 30 resolves the prepared-payload alias/TOCTOU finding discovered during the M29 security review.

The finding was specific: M24 previously placed the caller-supplied request mapping into the OLP transport envelope by reference. Although `PreparedFederationExchange` and its outer tuple are frozen/immutable shells, nested request mappings and lists could still be changed after preparation and before M26 serialization.

M30 closes that boundary **without adding any new network capability**.

## Safety boundary

```text
frozen dataclass shell              != deeply immutable request
original caller request             != prepared send payload
prepared binding                    != permission for later payload drift
successful M24 validation           != mutable alias safe forever
M30 immutable prepared payload      != network authorization
M30 immutable prepared payload      != peer identity / truth / trust
```

## Chosen resolution

Issue #65 allowed either send-time semantic revalidation or an immutable/deeply detached prepared representation. M30 chooses the latter.

Every `PreparedFederationExchange` now:

1. receives the abstract OLP request envelope produced by the existing M24 path;
2. recursively detaches the supported bounded M8 host representation from caller-owned mappings/lists;
3. replaces mappings with `FrozenDict` and lists with `FrozenList` values that preserve normal `dict`/`list` comparison and OLP encoder compatibility while rejecting ordinary mutation APIs;
4. stores each frozen container's authoritative state in private immutable tuples rather than in inherited mutable `dict`/`list` storage;
5. retains tuples, exact scalar types, and bytes as immutable values;
6. records an immutable type-tagged integrity snapshot covering both the `FederationRequestBinding` and the complete prepared envelope.

The detached payload is what the existing M26 transport later serializes. Mutating the original request after `prepare(...)` cannot change the prepared envelope.

The inherited `dict`/`list` storage of `FrozenDict`/`FrozenList` is intentionally left empty and ignored. Even explicit calls such as `dict.__setitem__(frozen, ...)` or `list.append(frozen, ...)` can only change ignored base storage; iteration, indexing, length, equality, copying, integrity snapshots, and OLP encoding all read the private immutable tuple state.

## Prepare-time envelope cross-binding

M30 also hardens the boundary immediately before the immutable prepared object is constructed. The injected M8 envelope maker is not treated as authority to reinterpret the already validated request.

`OfflineFederationService.prepare(...)` now snapshots the validated request before invoking the envelope maker and requires all of the following before construction succeeds:

- the envelope maker must not mutate the validated request;
- the result must contain exactly four transport-envelope elements;
- the transport marker must remain `OLP-TRANSPORT`;
- the transport version must remain exact integer `1`;
- the request message type must exactly match the configured M8 operation profile;
- the envelope payload's type-tagged snapshot must exactly equal the validated request snapshot.

A miswired or hostile envelope maker therefore cannot silently change the message profile or payload and then rely on the immutable wrapper to preserve the wrong value.

## Integrity snapshot

The snapshot is local integrity metadata, not protocol evidence and not cryptographic proof. It is type-tagged so Python scalar equality does not collapse semantically distinct host values such as `True` and `1`.

The snapshot binds:

- binding source;
- binding operation;
- binding scope fingerprint;
- binding required capabilities;
- binding page size;
- expected result message type;
- OLP transport marker/version;
- request message type;
- the complete detached request payload, including any opaque cursor bytes.

`dataclasses.replace(...)` cannot silently change the binding or envelope while retaining an old snapshot: construction fails closed on mismatch.

## Bounded host representation

The M30 detacher accepts only the host-value forms needed by the M8 request boundary:

- `None`;
- exact booleans;
- exact integers;
- exact text;
- exact bytes;
- tuples;
- ordinary/frozen lists;
- ordinary/frozen string-key mappings.

It rejects unsupported/custom container types, duplicate/invalid mapping keys, more than 512 items in one collection, or nesting deeper than 8 levels.

These limits are local implementation bounds below the broader OLP OJVE limits. They prevent an integrity operation from becoming an unbounded traversal surface.

## M26 behavior remains unchanged

M30 does not modify `src/marketplace/runtime/https_transport.py` and does not add or alter:

- endpoint discovery;
- DNS behavior;
- TLS policy;
- HTTP method/profile;
- redirects;
- retries;
- proxies;
- credentials;
- background work;
- concurrency limits;
- authorization lifetime;
- response parsing.

M26 still performs one explicitly authorized HTTPS exchange only. The difference is that the request object reaching M26 is no longer aliased to mutable caller state.

No live federation peer is contacted by M30 development or CI.

## End-to-end former-exploit regression proof

The M30 test suite reproduces the original vulnerability shape across the actual M24 -> M26 composition while replacing the network with a deterministic fake connection:

1. create a valid M8 sync request;
2. call M24 `prepare(...)`;
3. mutate the caller-owned request's source, operation, page size, cursor, nested scope, and capability list;
4. pass the already prepared exchange to the unchanged M26 transport;
5. allow M26 to serialize and write one HTTP request to the fake connection;
6. compare the transmitted HTTP body against independently encoded original and attacker-mutated envelopes.

Acceptance requires that the transmitted body equal the original request exactly and differ from the mutated request. This proves the former caller-alias path is closed at the real M26 serialization boundary without making a live network request.

A separate adversarial regression explicitly invokes base `dict`/`list` mutation primitives against the frozen payload and requires both the encoded bytes and integrity snapshot to remain unchanged.

## Privacy and retention

The immutable prepared representation does not create durable storage. Cursor bytes remain opaque and are not logged, interpreted, persisted, or copied into a new durable checkpoint. Prepared request content remains `EPHEMERAL` and subject to the project's maximum 10-second post-use retention rule when retained by a runtime component.

The integrity snapshot may contain opaque bytes already present in the prepared request, so it is part of the same EPHEMERAL prepared-exchange object and must not be logged or persisted independently.

## Adversarial acceptance

M30 tests require at least:

- mutation of the original request after `prepare(...)` cannot change the prepared payload;
- the exact former M24 -> M26 alias exploit shape cannot change transmitted bytes;
- top-level prepared payload mutation is rejected;
- nested scope/capability list mutation is rejected;
- explicit base `dict`/`list` mutation cannot change authoritative prepared values, encoded bytes, or the integrity snapshot;
- an envelope maker cannot mutate the validated request;
- an envelope maker cannot change the M8 request message profile;
- an envelope maker cannot return a payload different from the validated request;
- changed binding/envelope through dataclass replacement is rejected against the old snapshot;
- manual construction also detaches mutable aliases;
- boolean/integer snapshot values remain distinct;
- collection/depth bounds fail closed;
- the frozen prepared envelope remains encodable by the pinned OLP reference transport JSON adapter;
- the M30 integrity module contains no network, filesystem, process, concurrency, or logging imports;
- all pre-existing M25/M26/M27/M28/M29 tests remain green;
- 816/816 semantic vectors and 13/13 deterministic replays remain unchanged and passing;
- reproducible artifact/package/whitespace gates remain green;
- exact-head PR CI and merged-main CI are required before M30 is complete.

## Residual boundary

M30 protects the supported runtime host representation from caller-owned alias mutation, ordinary container mutation APIs, and direct base `dict`/`list` mutation calls while preserving OLP encoder compatibility.

It is not a sandbox against arbitrary code that already has power to subvert Python object internals, replace trusted runtime functions, mutate supposedly private slots through low-level reflection, or alter process memory. Such capabilities are process-compromise boundaries rather than federation transport-object behavior.

Most importantly:

```text
prepared payload immutability != authorization to send
prepared payload immutability != permission to auto-follow cursors
prepared payload immutability != unbounded synchronization permission
```

A future multi-page federation orchestrator remains a separate HIGH-risk milestone with explicit page/record/time budgets and independent authorization rules.
