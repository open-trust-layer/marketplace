# Bounded Inbound Federation Retained-Binding Hardening

## Status

Milestone 60 hardens the existing M32 `BoundedInboundFederationResponder`
without adding a new disclosure, transport, listener, or execution layer.
It is based on exact merged-green M59 commit
`ccf7f8d04944dd26d5f2c19123ae478ae120aa16`.

M60 is **HIGH source/security risk** because M32 is the local inbound federation
disclosure boundary. M59 witnesses the exact M32 responder object and its
`prepare_response` method, but that alone cannot detect post-construction
substitution of policy/source/semantic capabilities retained inside M32.

The tests-first RED specification is preserved at exact commit
`a6d2152fdc014e649046e4650f6b89e32b34df60`.
On the unchanged M59 source it demonstrates retained-helper replacement,
configuration/profile drift, and mid-call authority substitution before the
production hardening exists.

## Threat model

A same-process attacker with mutation access to one constructed M32 responder
must not be able to replace a retained disclosure authorizer, page source,
semantic validator/evaluator, Record helper, envelope helper, or private M32
execution helper and have the replacement silently become authority.
M60 therefore retains an independent construction-time witness for the exact
M32 helper/configuration graph and validates it before each guarded helper
selection and after attacker-influenced callbacks where later authority remains.

The retained helper witness covers:

- transport-envelope validation;
- exchange-request validation and scope fingerprinting;
- capability negotiation;
- page evaluation and result validation;
- response-envelope creation;
- Record validation and Record Identity derivation;
- the explicit disclosure authorizer;
- the bounded local page source.

M60 also witnesses local source, detached capability advertisement,
advertised page/cursor limits, configured page limit, operation-profile mapping
and immutable profile-field snapshots, plus the reviewed private M32 helper
method graph used to select and validate those capabilities.

## Fail-closed behavior

Retained capability or private helper replacement fails with stable
`INBOUND_FEDERATION_BINDING_DRIFT`. Retained configuration, profile, limit, or
advertisement drift fails with stable `INBOUND_FEDERATION_CONFIGURATION_DRIFT`.
Arbitrary replacement exception text is not promoted into these failures.
Comparison of retained capabilities is identity/type based. Numeric witness
slots are exact-type checked before value comparison, and configuration
snapshots contain only reviewed exact-safe primitive structures. A poisoned
witness must therefore fail without invoking caller-controlled equality.

M60 preserves M32 as a reusable multi-request responder. It does not make M32
one-shot and does not change M8 request/result semantics, disclosure policy,
page contents, Record Identity authority, resource ceilings, or route behavior.

The hardened path revalidates retained bindings after callbacks that can mutate
the responder before selecting a later helper. In particular, an authorized
callback cannot replace the page source for the same request, and a result
validator cannot replace the envelope maker for the same response.

## Authority boundary

M60 establishes no requester authentication, peer identity, truth, ownership,
trust, agreement, completeness, authorization, or new disclosure permission.
The existing explicit M32 disclosure decision remains authoritative.

M60 is deterministic source-only hardening. It performs no socket construction,
bind, listen, accept, connect, DNS, TLS, peer traffic, deployment, service
activation, credential access, filesystem persistence, logging, retry loop,
concurrency, or background work.

Calling the existing M55/M59 execution chain with a real operating-system
socket constructor remains `NETWORK_EXTERNAL` and requires fresh explicit
authorization immediately before execution. Production activation remains
separately `DEPLOY`.
## Retention and recovery

M60 introduces no new durable content-bearing storage. Existing responder
configuration references retain the same lifetime as M32 and remain subject to
the project EPHEMERAL post-use retention ceiling where content-bearing data is
involved.

The blast radius is source, tests, documentation, and packaged source bytes
only. No listener, port, peer connection, schema, credential, certificate,
service, deployment, durable user/content record, or protected external effect
is created by M60 acceptance. Recovery is an ordinary source-control revert of
the M60 merge commit.

## Acceptance

M60 acceptance requires the preserved tests-first RED history to turn green on
the implementation, including all retained-helper substitutions, configuration
and profile drift, mid-call TOCTOU mutation, private helper poisoning, and
hostile-equality regression coverage.

Existing M32 behavior plus M34/M59 and the broader inbound stack must remain
green. Repository compile/audit/whitespace gates, unchanged 816/816 semantic
vectors, deterministic generator replays, reproducible package artifact,
isolated package/reference smokes, and exact-head self-hosted Windows
conformance are required.

Because M60 is HIGH source/security risk, merge additionally requires explicit
maintainer/security self-review, zero unresolved review threads, and an eligible
independent review or a fresh PR-specific Section 7.2(A) owner authorization
naming the exact final PR head SHA. Merge must be SHA-guarded, and exact
merged-main self-hosted acceptance must pass before M60 is COMPLETE.
