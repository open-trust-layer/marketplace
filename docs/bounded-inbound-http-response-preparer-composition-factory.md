# Bounded Inbound HTTP Response-Preparer Composition Factory

Milestone 56 closes the last abstract response-preparer construction gap in the
one-shot inbound path without adding live network execution.

M56 composes the already-reviewed M35 through M43 boundaries around one
explicit reader capability. Construction returns the exact existing M43
`BoundedInboundHttpResponsePreparer`; it does not create a new result schema or
semantic authority.

## Scope

The factory constructor accepts only:

- one exact M35 `BoundedInboundHttpWireAdapter`; and
- one explicit callable monotonic clock for M42.

Its one-shot `__call__(reader)` accepts one explicit reader capability.
Construction itself does not invoke the reader or the clock.

No new configurable limits are introduced. M36, M37, and M42 are constructed
through their existing reviewed default-limit paths, so M56 cannot widen their
hard ceilings.

## Exact construction graph

One successful factory call constructs exactly one instance of each boundary in
this order:

1. M36 `BoundedInboundHttpStreamAssembler`
2. M37 `BoundedInboundHttpReadPlanner`
3. M38 `BoundedInboundHttpReadTransitioner`
4. M39 `BoundedInboundHttpReadSession`
5. M40 `BoundedInboundHttpReadOutcomeHandler`
6. M41 `BoundedInboundHttpReadInvoker`
7. M42 `BoundedInboundHttpReadDriver`
8. M43 `BoundedInboundHttpResponsePreparer`

The supplied reader is bound only at M41. The supplied clock is bound only at
M42. M43 then independently discovers and validates the exact retained
M39/M37/M36/M35/M34 graph through its existing construction checks.

M56 returns exact M43. It does not wrap the preparer or duplicate M34 routing,
M35 framing, M37 planning, M42 driving, or M43 response-preparation semantics.

## Binding integrity and one-shot ownership

M56 snapshots the reviewed M34-M43 class identity graph at construction and
revalidates it before and between lower-layer construction steps. A post-
construction replacement of a retained class constructor/helper therefore
fails closed before the substituted constructor is selected.

The factory also binds the exact M35-to-M34 object relation that existed when
the factory was created. It snapshots the M35 Host authority, exact M35 and M34
limit objects plus their scalar values, and the exact M34 application-handle
binding. Those values are revalidated before and between construction stages,
so a pre-call adapter swap, Host/limit drift, or application-handle substitution
cannot silently redefine the M43 graph being built. Validation reads retained
private state only after the corresponding exact class graph has been checked;
it does not invoke the application handler.

The factory keeps a private binding witness for these retained values, its clock,
construction graph, cleanup authority, release authority, and call path. The
witness is checked by identity before trusted private helpers are invoked.
Caller-defined equality is not used for capability or binding decisions.

A factory instance is one-shot. The first call consumes its construction
authority even when input or lower construction fails. A successful call
releases M56's references after handing ownership to exact M43; a second call
cannot create another graph.

This is concrete hardening against the reviewed substitution paths. It is not a
claim that arbitrary hostile code sharing the same Python process can be fully
sandboxed by object-identity checks.

## Failure and cleanup

Construction errors are mapped to stable M56-local failure metadata; arbitrary
lower exception text is not exposed. The bounded stage name identifies only the
reviewed construction boundary being attempted.

If a failure occurs after exact M39 exists, M56 uses captured reviewed close
authority to clear and terminally close the partial read session before
releasing its own references. Failure to verify cleanup is itself fail-closed
and reported as cleanup uncertainty.

M56 creates no request bytes, response bytes, peer metadata, credentials,
certificate material, durable cursor, log, cache, or persisted session state.
Any lower-layer content that later exists during actual M43 execution remains
subject to the project's EPHEMERAL maximum retention of 10 seconds post-use.

## Live-network boundary

M56 imports no `socket` or TLS implementation and calls no `recv`, `send`,
`bind`, `listen`, `accept`, `connect`, DNS, process, filesystem, deployment, or
background primitive. Source acceptance and CI use deterministic doubles only.

M56 can be supplied to M55's existing abstract response-preparer factory slot,
but doing so still does not authorize a real operating-system listener. Running
M55 with the real OS socket constructor would create/operate live network
resources and remains a separate `NETWORK_EXTERNAL` action requiring fresh
explicit authorization immediately before execution.

Production service activation remains a separate `DEPLOY` action. M56 adds no
credential, secret, certificate, provider-administration, or protected economic
side-effect authority.

## Acceptance and rollback

Acceptance requires tests-first functional and adversarial coverage, source
guards, exact runtime exports, wheel membership, repository audit, the unchanged
full conformance gate, HIGH maintainer/security review, exact-head self-hosted
CI, zero unresolved review threads, a governance-qualified SHA-guarded merge,
and exact merged-main self-hosted acceptance.

Source acceptance changes only repository source, tests, documentation, and
package-membership rules. It leaves no real listener, port, peer connection,
service, credential, certificate, schema, user data, or production state.
Rollback is an ordinary source-control revert.
