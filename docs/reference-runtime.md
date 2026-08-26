# Marketplace Reference Runtime

**Status:** Milestone 17 — in development
**Scope:** transport-neutral, in-process reference runtime composition

Milestone 17 introduces the first reusable runtime/application package under `src/marketplace/` without turning the reference implementation into a mandatory Marketplace architecture.

## Boundary

The runtime preserves these distinctions:

```text
runtime composition          != mandatory Marketplace implementation
in-process node              != global Marketplace operator
record storage               != ownership / truth / endorsement
validated Marketplace record != authorized protected action
M14 readiness                != authorization
M16 proposed step            != execution authority
runtime result               != protocol truth
local memory retention       != durable Marketplace history
```

OLP remains authoritative for `RecordV1` validation and Record Identity. Marketplace semantic validation remains defined by the Marketplace specifications and conformance helpers. The runtime receives validation and identity capabilities explicitly rather than inventing parallel semantics.

## Package structure

```text
src/marketplace/
└── runtime/
    ├── contracts.py
    ├── node.py
    ├── repository.py
    └── retention.py
```

`contracts.py` defines the narrow runtime capabilities. `MarketplaceNode` orchestrates validation, identity derivation, repository storage, retrieval, and close. The runtime does not construct network, database, framework, credential, deployment, settlement, fulfillment, or protected-action infrastructure internally.

## Ingestion order

The reference node uses:

```text
candidate record
-> Marketplace semantic validation
-> OLP Record Identity text derivation
-> bounded repository put
-> explicit ingest outcome
```

Validation occurs before identity derivation and storage. Invalid input therefore cannot create repository state.

## EPHEMERAL retention

The reference in-memory repository is deliberately content-bearing and therefore uses the project `EPHEMERAL` retention class.

The default and maximum supported post-use retention is:

```text
10 seconds
```

A successful put, duplicate delivery, or read refreshes the post-use deadline. Automatic expiry is scheduled; cleanup does not depend on an operator remembering to call a purge command.

Each entry carries an expiry generation. When an older timer races with a later refresh, the stale callback cannot delete the refreshed entry because its generation no longer matches.

The repository is bounded to a configured entry count and rejects an insertion when capacity is exhausted. Configuration above the project maximum entry ceiling is rejected.

Exact duplicate delivery refreshes retention and returns `DUPLICATE`. Reuse of one Record Identity for different content fails closed as `RECORD_IDENTITY_COLLISION` rather than silently overwriting data.

`close()` marks the repository closed, clears retained content, and cancels scheduled expiry work. Further reads or writes fail explicitly.

This in-memory repository is not durable Marketplace history and is not a persistence adapter.

## Composition with existing semantics

The runtime package itself remains dependency-injected. Current tests demonstrate composition with:

- `tools/marketplace_record_v1.py::validate_market_record`; and
- pinned OLP `record_identity_text`.

This proves the runtime can use the existing semantic and identity authorities without copying their logic into a second implementation.

## Acceptance integration

The existing M12 gate remains the single acceptance authority. It now places both `src/` and `tools/` on the controlled Python path for tests and validators, and the repository audit compiles `src/**/*.py` in addition to existing tool/test source.

M17 does not add or modify Marketplace semantic vectors. The existing 816 vectors and all 13 deterministic generators must remain byte-for-byte green.

## Explicitly out of scope

M17 does not add:

- HTTP, REST, gRPC, P2P, ActivityPub, or other transport adapters;
- PostgreSQL, SQLite, filesystem, or object-store persistence;
- external discovery or federation calls;
- authentication providers or credential handling;
- deployment/cloud/container integration;
- settlement or fulfillment execution;
- protected workflow execution; or
- a new Marketplace/OLP identity mechanism.

Those capabilities, if added later, must remain replaceable adapters and must preserve M11 authorization, retention, project-isolation, and least-privilege requirements.
