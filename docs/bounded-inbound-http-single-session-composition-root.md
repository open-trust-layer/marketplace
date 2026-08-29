# Bounded Inbound HTTP Single-Session Composition Root

Milestone 57 closes the source-level wiring gap between M56 and M55 without
executing transport authority.

The boundary constructs one exact
`BoundedInboundHttpResponsePreparerCompositionFactory` and one exact
`BoundedInboundHttpSingleSessionOrchestrator`, sharing the same explicit clock.
It returns the exact M55 orchestrator and does not call `run_once()`.

## Authority boundary

M57 composition is not network authorization. Successful composition does not
prove a listener exists, a socket was created, a peer connected, TLS terminated,
or any request was received.

A later M55 `run_once()` using a real operating-system socket constructor remains
`NETWORK_EXTERNAL` and requires fresh explicit authorization immediately before
execution. Production activation remains separately `DEPLOY`.

## Public surface

`BoundedInboundHttpSingleSessionCompositionRoot` is initialized with:

- one exact M35 `BoundedInboundHttpWireAdapter`;
- one explicit callable clock;
- one exact integer port within `1024..65535`.
Its one `__call__(constructor)` accepts the explicit Python TCP socket-constructor
capability and returns one exact M55 orchestrator.

Construction invokes neither the constructor nor the clock. It does not bind,
listen, accept, connect, read, write, resolve DNS, terminate TLS, spawn work,
persist state, or activate a service.

## Exact composition

One successful call constructs:

1. exact M56 around the retained M35 adapter and explicit clock;
2. exact M55 around the supplied constructor, that exact M56 instance, the same
   clock object, and the configured port;
3. no additional result wrapper or semantic authority.

M57 verifies that M55 retained the exact M56 instance, exact clock, exact port,
and exact constructor capability before returning the orchestrator.

## One-shot and retention behavior

The first call becomes terminal before validation or lower construction. A
second call always fails with `SESSION_COMPOSITION_EXHAUSTED`.

M57 releases every reference it owns to M34/M35, the clock, port, lower classes,
class snapshots, helper bindings, and its binding witness in an unconditional
terminal path on success or failure. The returned exact M55/M56 graph owns only
the references required for later execution.
## Binding hardening

Before M56 construction, M57 witnesses the exact M34, M35, M56, and M55 class
identity surfaces plus the retained M35-to-M34 object binding. This prevents a
post-construction M34 class substitution from being selected while M56 is being
built.

The first executable helper invocation is preceded by an inline identity check
of M57's own class snapshot and captured validation helpers. A poisoned private
validator therefore fails closed before it can execute.

These checks cover concrete class/helper substitution paths under the reviewed
HIGH threat model. They are not a claim of universal immunity from arbitrary
coherent mutation of all Python process state.

## Failure handling

M57 exposes only stable local error codes. M56 and M55 rejections may contribute
one bounded lower-layer code; arbitrary exception text is never reflected.

Invalid M35 type, clock, port, or constructor fails before any transport
operation. Construction failures do not create a live listener because M55
construction itself does not invoke the injected socket constructor.

## Security invariants

M57 adds no socket, TLS, DNS, process, filesystem, logging, persistence,
concurrency, retry, sleep, loop, comprehension, or background-work surface.
It does not duplicate M34 routing/disclosure, M35 framing, M36-M43 read
semantics, M50 transaction semantics, or M52-M54 transport boundaries.

Composition success does not establish requester authentication, peer identity,
Marketplace truth, trust, authorization, or permission for protected side
effects.

The project EPHEMERAL retention ceiling remains unchanged at no more than ten
seconds where transient project data is retained by applicable lower runtime
components.

## Acceptance

Source acceptance uses deterministic in-memory fixtures and capability doubles
only. Required evidence includes tests-first regressions, adversarial class and
private-helper substitution tests, exact export/package membership, repository
audit, whitespace and compile checks, reproducible wheel verification, all
816 conformance vectors and deterministic generator replays, exact-head
self-hosted CI, HIGH security self-review, zero unresolved review threads, and
exact merged-main verification after any authorized merge.

No source-acceptance test for M57 may instantiate or exercise a real operating-
system socket.
