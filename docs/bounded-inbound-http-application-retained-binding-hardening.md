# Inbound HTTP Application Retained-Binding Hardening

## Status

Milestone 58 hardens the existing M34 `BoundedInboundHttpApplicationAdapter`.
It is based on exact merged M57 commit `cf51edebec534597ef9e5d5deb4d5e1ba2feacd1`.

M58 is **HIGH source/security risk** because M34 sits immediately above the
M32/M33 disclosure responders. The milestone remains deterministic and offline.
It adds no network, deployment, persistence, authentication, or protected-side-
effect authority.

## Problem

Before M58, M34 detached caller routes and limits at construction, but retained
several later-selected Python bindings without an independent witness:

- the exact M32 and M33 responder objects;
- their effective response-preparation callables;
- JSON decoder and encoder callables;
- the private route map and application limits;
- private M34 helper/validator authority.

A same-process post-construction substitution could therefore select changed
retained authority before the older result-integrity checks rejected semantics.
## Retained graph witness

Successful M34 construction now records exact identity witnesses for the
retained responders and codecs, plus immutable snapshots of route and limit
configuration.

It also records the reviewed M32 `prepare_response` and M33 `prepare` class
bindings, the effective responder callables selected at construction, and the
M34 helper graph used by `handle()`.

Before M34 selects a responder or codec, `_validate_bindings()` verifies:

- exact retained M32/M33 responder identity and type;
- exact decoder/encoder identity;
- unchanged M32/M33 reviewed class method bindings;
- unchanged effective responder callable binding;
- unchanged private route-map identity and content snapshot;
- unchanged private limit identity and numeric snapshot;
- unchanged critical M34 helper and integrity-function bindings.

Binding replacement fails `APPLICATION_BINDING_DRIFT`. In-place route or limit
content change fails `APPLICATION_CONFIGURATION_DRIFT`.
## Callback revalidation

Decoder, responder, and encoder calls are attacker-influenced callback windows.
M58 therefore validates the graph before those calls and again immediately
after a successful callback returns, before later authority is selected.

This specifically blocks a decoder from rebinding M32 before dispatch and an
encoder from rebinding the decoder used for strict local round-trip validation.
A callback that raises still maps to the existing bounded local M34 failure;
its arbitrary exception text is not reflected.

Construction-time configured responder callables remain supported. M58 binds
the exact effective callable that existed when construction succeeded, including
the existing deterministic test seam, and rejects later substitution.

## Helper poisoning

`handle()` verifies the captured M34 validator identity inline before invoking
it. The validator itself raises stable `InboundHttpError` values directly while
checking `_fail` and other reviewed helper identities. A poisoned private
validator or captured M34 helper therefore cannot execute first.

The protection is deliberately bounded. It does not claim universal immunity to
an attacker that can coherently rewrite all related Python process state and all
witnesses at once.
## Authority and side-effect boundary

M58 does not authorize or perform socket construction, bind/listen/accept,
connect, DNS, TLS, peer traffic, deployment, filesystem persistence, logging,
secrets access, background work, retries, or protected economic side effects.

It does not change M32/M33 disclosure semantics and does not establish requester
authentication, peer identity, truth, ownership, trust, agreement,
authorization, or global completeness/existence.

Any real M55/M57 `run_once()` using an operating-system socket constructor
remains `NETWORK_EXTERNAL` and requires fresh explicit authorization immediately
before execution. Production activation remains separately `DEPLOY`.

## Retention

No new content-bearing storage is introduced. Requests, envelopes, prepared
responses, and encoded bodies remain EPHEMERAL under the project ten-second
post-use ceiling. The new witnesses contain only in-process object/callable
references and bounded route/limit configuration required during adapter life.

## Acceptance

M58 preserves a test-only red commit proving all adversarial regressions fail on
the old M34 implementation. The same tests must pass on the hardened head.
Required acceptance also includes focused M34/M35/M43/M56/M57 compatibility,
repository/source guards, deterministic conformance replay, reproducible package
artifact verification, exact-head self-hosted Windows acceptance, HIGH security
self-review, zero unresolved review threads, and merged-main verification after
an authorized merge.

No M58 source-acceptance test may create or exercise a real operating-system
socket.

## Recovery

M58 changes source, tests, and documentation only. It creates no listener,
service, schema, credential, durable content, peer connection, or deployment.
Recovery is an ordinary source-control revert of the M58 merge commit.