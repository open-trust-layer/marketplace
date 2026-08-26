# Marketplace Reference Runtime Composition

**Status:** Milestone 20 — in development
**Scope:** local composition and lifecycle ownership for M17–M19 runtime services

Milestone 20 assembles the existing local runtime components into one coherent reference composition. It does not introduce a new Marketplace semantic method, transport, persistence layer, global operator, or protected-side-effect executor.

## Boundary

```text
reference composition       != mandatory implementation
shared local repository     != global marketplace state
runtime convenience API     != semantic authority
configured evaluator        != protocol truth
runtime close               != protocol record retirement/deletion
local capability            != network service
```

The composition layer owns wiring and process-local cleanup only. OLP remains Record Identity authority. Marketplace record validation, discovery semantics, and matching semantics remain explicit dependencies.

## Composition

`MarketplaceRuntime` exposes four components sharing one repository:

```text
                    +---------------------+
                    |   shared repository |
                    |  EPHEMERAL / bounded|
                    +----------+----------+
                               |
              +----------------+----------------+
              |                |                |
              v                v                v
       MarketplaceNode   LocalDiscovery   LocalMatch
                         Service          Service
```

The same record inserted through `MarketplaceNode` is therefore immediately available to local discovery and exact local match evaluation, subject to the repository's existing retention and capacity rules.

## Explicit semantic capabilities

`compose_runtime(...)` requires callers to provide:

- `validate_record`;
- `record_identity_text`;
- `evaluate_discovery`;
- `evaluate_match`;
- `repository`.

The composition root does not choose a hidden trust, ranking, matching, discovery, identity, or authorization method.

The M20 integration tests demonstrate a reference composition using:

- the existing M3 `validate_market_record` helper;
- pinned OLP `record_identity_text`;
- existing M5 `evaluate_discovery`;
- existing M5 `evaluate_match`.

Those functions remain injected rather than copied into the runtime composition layer.

## In-memory reference factory

`create_in_memory_runtime(...)` is a convenience factory for the already-defined `InMemoryEphemeralRecordRepository`.

It still requires all semantic/identity capabilities explicitly. Its convenience is limited to selecting local memory storage and wiring the three runtime services around it.

The factory preserves:

- `EPHEMERAL` retention class;
- default maximum post-use retention of **10 seconds**;
- rejection of retention configured above 10 seconds;
- bounded `max_entries`;
- injectable expiry scheduler for deterministic testing;
- no new dependency;
- no network/filesystem/database behavior.

## Lifecycle ownership

The runtime aggregate owns the supplied repository lifecycle. Calling `MarketplaceRuntime.close()` delegates to `repository.close()`.

For the in-memory reference repository this:

- clears retained process-local records immediately;
- cancels current scheduled expiry work;
- is idempotent;
- leaves no hidden result cache or secondary retained copy.

`MarketplaceRuntime` also supports context-manager use so transient state is closed on both normal and exceptional exit.

This cleanup has a deliberately narrow meaning:

```text
runtime close
    != OLP retire
    != Marketplace withdrawal
    != global deletion
    != evidence invalidation
```

It states only that this runtime instance no longer retains its process-local EPHEMERAL copy.

## Safety and capability surface

M20 introduces no:

- network access;
- HTTP/gRPC/P2P/federation adapter;
- filesystem/database persistence;
- dependency installation;
- secret or credential management;
- ranking or recommendation;
- automatic candidate pairing;
- agreement formation;
- settlement/fulfillment/remedy execution;
- authorization bypass;
- deployment capability.

The runtime remains a local application composition around already-tested semantic ports.

## Acceptance

M20 tests must demonstrate:

- one repository instance is shared by node, discovery, and match services;
- actual M3/OLP/M5 functions can be injected together;
- ingested records are immediately visible to discovery and matching;
- compatible M5 results remain non-truth and non-agreement;
- the in-memory factory preserves the 10-second retention maximum and bounded capacity;
- `close()` is idempotent and clears transient state;
- context-manager normal and exceptional exit both clear transient state;
- all existing semantic vectors and deterministic generator replay remain unchanged and green.

After M20, the local composition boundary is stable enough to evaluate the next larger engineering step separately: packageable semantic adapters versus the first external federation transport. Network capability must not be introduced as an incidental convenience of local composition.
