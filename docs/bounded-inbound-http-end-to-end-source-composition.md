# Bounded Inbound HTTP End-to-End Source Composition

## Status

Milestone 59 adds the final transport-free source-composition boundary from the
existing inbound disclosure responders to the existing one-session HTTP stack.
It is based on exact merged-green M58 commit
`01567675d2f77e95e0f02da4a5b180ce79b627da`.

M59 is **HIGH source/security risk** because it is the first composition root
that retains exact M32/M33 disclosure responders and joins them to M34, M35,
and the M57 infrastructure-adjacent source composition chain.

M59 remains deterministic and offline. Construction does not invoke a socket
constructor, clock, reader, listener, or M55 `run_once()`.

## Composition boundary

`BoundedInboundHttpEndToEndSourceCompositionRoot` receives exactly:

- one exact M32 `BoundedInboundFederationResponder`;
- one exact M33 `BoundedInboundRecordResponder`;
- one bounded exact tuple of M34 control routes;
- one transport-envelope JSON decoder and encoder;
- one explicit M35 HTTP authority;
- one callable clock;
- one explicit M57/M55 loopback port.

Its one public call accepts one TCP socket-constructor capability. A successful
call constructs exactly one M34 application adapter, one M35 wire adapter, one
M57 source-composition root, and returns the exact M55 orchestrator produced by
that M57 root.

M59 adds no second disclosure, HTTP framing, transport, listener, or execution
stack. Existing lower layers remain authoritative for their own semantics and
resource limits.

## Retained graph witness

At successful M59 construction, the root records exact object/callable/config
bindings plus reviewed class-identity snapshots for M32, M33, M34, M35, M56,
M55, and M57.

The witness includes:

- exact M32/M33 responder objects and effective response call bindings;
- exact control-route tuple identity and immutable path/operation snapshot;
- exact decoder/encoder identities;
- exact authority, clock, and port references;
- exact M34, M35, and M57 construction class identities;
- the reviewed M59 class-snapshot and validation helper graph.

This is important before lower construction. Without the M59 witness, a class
or route mutation occurring after M59 configuration but before M34/M57 creation
could otherwise be captured by a lower layer as its new construction-time
baseline.

Binding replacement fails with stable
`END_TO_END_COMPOSITION_BINDING_DRIFT`. In-place retained route mutation fails
`END_TO_END_COMPOSITION_CONFIGURATION_DRIFT`.

## Verified handoffs

M59 validates its retained graph before lower construction and across each
construction boundary. After M34 construction it verifies the exact M32/M33,
codec, and route bindings. After M35 construction it verifies the exact M34 and
authority binding. Before invoking M57 it verifies the exact M35/M34, clock, and
port bindings.

The returned object must be the exact existing M55 orchestrator. M59 also
verifies its retained M56 preparer factory, M35/M34 path, clock, listener port,
and supplied socket-constructor capability.

No constructor or clock call occurs during this handoff.
## Error and authority semantics

M59 maps lower construction failure to stable M59-local codes and does not
reflect arbitrary lower exception text. Where a reviewed lower boundary already
provides a stable code, M59 may retain that code only as bounded `lower_code`
metadata.

Source composition success establishes no requester authentication, peer
identity, truth, ownership, trust, agreement, authorization, disclosure
permission, global existence/completeness, or protected-side-effect authority.
Those facts remain exactly as defined by M32/M33 and the existing lower stack.

## External-effect boundary

M59 does not authorize or perform real socket construction, bind, listen,
accept, connect, DNS, TLS, peer traffic, deployment, service activation,
filesystem persistence, content logging, credential access, retries,
concurrency, or background work.

Calling M55 `run_once()` with a real operating-system socket constructor remains
`NETWORK_EXTERNAL` and requires fresh explicit authorization immediately before
execution. Production activation remains separately `DEPLOY`.

## Retention

M59 introduces no new durable content-bearing storage. Retained responder,
route, codec, and configuration references exist only for the one-shot source
composition lifetime and are released on terminal success or failure.
Existing EPHEMERAL content remains subject to the project ten-second post-use
ceiling.

## Acceptance

M59 preserves a test-first commit made before the production module existed.
Acceptance requires the same tests to pass on the implementation, focused
M32/M33/M34/M35/M43/M56/M57 compatibility, source and repository guards,
unchanged 816/816 vectors with deterministic replay, reproducible package and
isolated smoke gates, and exact-head self-hosted Windows acceptance.

Because M59 is HIGH source/security risk, merge additionally requires zero
unresolved review threads plus an eligible independent review or a fresh
PR-specific Section 7.2(A) exact-head owner authorization. A SHA-guarded merge
and exact merged-main self-hosted acceptance are required before M59 is marked
COMPLETE.

No M59 source-acceptance test may create or exercise a real operating-system
socket.

## Recovery

M59 changes source, tests, documentation, exports, and local package membership
only. It creates no listener, service, schema, credential, certificate, peer
connection, durable user/content data, or deployment. Recovery is an ordinary
source-control revert of the M59 merge commit.
