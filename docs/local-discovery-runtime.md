# Marketplace Local Discovery Runtime

**Status:** Milestone 18 — in development
**Scope:** bounded, read-only discovery over process-local Marketplace evidence

Milestone 18 composes the Milestone 17 in-process runtime with the existing Milestone 5 matching/discovery semantics. It does not define a second discovery method and does not add network federation, ranking authority, recommendation, agreement formation, or protected side effects.

## Boundary

```text
local discovery result      != global marketplace view
source completeness         != global completeness
query match                 != endorsement
query match                 != agreement
result order                != canonical ranking
missing local record        != negative evidence
runtime-held evidence       != durable global history
```

Milestone 5 remains authoritative for `DiscoveryQueryV1` validation and discovery-result semantics. The runtime service receives an evaluator capability explicitly and returns the evaluator mapping without adding a second interpretation layer.

## Runtime composition

```text
DiscoveryQueryV1
      |
      v
LocalDiscoveryService
      |
      +--> bounded local RecordSource
      |        |
      |        v
      |    EPHEMERAL snapshot
      |
      +--> existing M5 evaluate_discovery(...)
               |
               v
        source-scoped result
```

The default reference composition uses `InMemoryEphemeralRecordRepository` as the bounded local source and `tools/marketplace_matching_v1.py::evaluate_discovery` as the semantic evaluator.

## Bounded local snapshots

`InMemoryEphemeralRecordRepository.snapshot(limit)` has intentionally strict behavior:

- `limit` must be a positive integer within the repository's configured capacity;
- the method returns the complete current local record set only when it fits inside `limit`;
- if more records are present than the caller permits, the operation fails with `REPOSITORY_READ_LIMIT_EXCEEDED` instead of truncating;
- accepted snapshots are ordered by exact Record Identity text for deterministic runtime behavior;
- only accepted/returned records have their post-use retention refreshed;
- overflow does not refresh any record;
- stale expiry callbacks remain harmless because M17 generation checks still apply.

Failing instead of truncating prevents a partial local snapshot from being silently presented to an evaluator as if it represented the full declared local source.

## Retention behavior

The local repository remains content-bearing `EPHEMERAL` storage with the project maximum post-use retention of **10 seconds**.

Snapshot acquisition is lazy at the discovery-service boundary. The existing M5 evaluator validates query and source metadata before it consumes the supplied record iterable. Therefore a request rejected before evidence consumption does not refresh local record retention merely because a discovery call was constructed.

When the evaluator consumes the local source, the accepted snapshot counts as use and refreshes the returned records' retention deadline. No second cache or durable discovery result store is introduced.

## Resource and safety properties

M18 introduces no:

- network access or remote fallback;
- HTTP/gRPC/P2P transport;
- filesystem or database persistence;
- package dependency;
- credential or secret handling;
- ranking/recommendation engine;
- agreement creation;
- settlement, fulfillment, remedy, or other protected side effect.

The runtime remains bounded by repository capacity, caller snapshot limit, M5 query cardinality rules, and the existing M5 evaluation limits.

## Malformed candidates

The runtime repository is an evidence-storage boundary, not a semantic authority. Normal ingestion through `MarketplaceNode` validates Marketplace semantics before storage. Discovery nevertheless delegates candidate validation to M5 as well, preserving M5 behavior for a supplied OLP Record that is nonconforming as Marketplace evidence.

This defense-in-depth behavior does not make malformed evidence valid and does not convert ignored evidence into negative evidence.

## Acceptance

M18 tests must demonstrate:

- deterministic bounded snapshots;
- overflow without partial return or retention refresh;
- snapshot retention refresh and stale-callback safety;
- invalid runtime limits fail before source/evaluator use;
- invalid M5 queries do not refresh local evidence;
- empty local discovery preserves source scope and non-adverse absence;
- exact positive discovery uses the existing M5 evaluator;
- malformed Marketplace candidates are handled by M5 semantics;
- discovery fails closed when the local source exceeds the requested bound;
- the runtime does not reinterpret the evaluator result;
- all existing semantic vectors and generator replay remain unchanged and green.

M18 remains a local read-only runtime capability. Remote federation and durable persistence stay separate future milestones because they introduce distinct network, authentication, TLS, SSRF/egress, retry, availability, and retention risks.
