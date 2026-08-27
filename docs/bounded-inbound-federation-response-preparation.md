# Bounded Inbound Federation Response Preparation

**Milestone:** M32

**Status:** non-normative reference runtime architecture

**Risk:** HIGH

**Network posture:** transport-free; no listener, socket, HTTP/TLS server, retry loop, background worker, or live peer execution

## Purpose

M32 adds the local preparation boundary for one inbound Marketplace M8 snapshot or sync request. It validates one supplied transport envelope, requires one explicit local disclosure decision, materializes one bounded local page, validates that page through existing M8 helpers, and prepares one immutable response envelope.

M32 stops before transmission.

It does not implement an inbound network server. A future transport adapter may invoke M32 only after separately establishing whatever transport/authentication facts and local authorization inputs that adapter requires.

## Authority boundary

```text
valid M8 request                 != permission to disclose Record IDs
request source                   != authenticated peer identity
request capability declaration  != local capability enablement
operation profile               != disclosure authorization
cursor possession               != authorization
cursor binding                  != requester identity proof
page source result              != protocol-valid response
prepared response               != transmitted response
response record_ids             != authorization to fetch unrelated Records
source completeness             != global completeness
final page                      != global marketplace completeness
absence                         != deletion evidence
prepared disclosure             != truth / trust / agreement / protected-action authority
```

M32 treats the disclosure decision as an injected local policy fact. Request validity, source URI, operation, capabilities, page size, cursor presence, and transport-envelope validity cannot substitute for that decision.

The disclosure authorizer is called exactly once after request validation and binding checks and before the page source. Only exact boolean `True` permits page materialization. `False`, non-boolean values, or authorizer failure stop the request before local Record enumeration.

## Record-body minimization

The M8 control response contains canonical Record IDs rather than Record bodies. M32 therefore does **not** return selected Record bodies in `PreparedInboundFederationResponse`.

Selected Records are used transiently only to:

1. validate Marketplace Record conformance through the injected existing validator;
2. derive canonical OLP Record Identities;
3. evaluate the selected page through the existing M8 page evaluator;
4. verify that the evaluator did not mutate the selected Record set.

After that, only canonical IDs and page-control facts enter the prepared control response.

This intentionally leaves actual Record-body serving as a separate future authorization/transport boundary rather than turning one control-page authorization into blanket Record disclosure authority.

## Request handling

The caller selects one configured operation profile locally, for example snapshot or sync. M32 then:

1. deeply detaches the supplied request envelope using the bounded M30 immutable host representation;
2. validates it against the configured request message type;
3. requires the transport validator to preserve the negative facts that transport does not define Record Identity and transport authentication is not object proof;
4. validates/normalizes the M8 request payload;
5. cross-binds the normalized operation to the configured operation profile;
6. requires the normalized request `source` to equal the responder's configured local federation source;
7. enforces canonical required capabilities, page-size bounds, and exact cursor-presence consistency;
8. creates one immutable `InboundFederationRequestContext`.

The request context explicitly keeps `request_authenticated = False`, `peer_identity_proven = False`, and `authorizes_protected_side_effects = False`.

## Cursor boundary

Incoming and outgoing cursors remain opaque bytes.

M32 does not decode, generate, interpret, rank, log, persist, or authenticate cursors.

An incoming cursor is exposed only inside the already-authorized immutable request context passed to the page source. The page source/policy component decides how, if at all, to interpret that cursor for local pagination.

A truncated page must return one bounded nonempty opaque `next_cursor` no larger than the existing M8 4096-byte maximum. A final page must not return a cursor.

Cursor possession does not grant disclosure authorization and does not prove remote identity.

## Local page limits

`BoundedInboundFederationResponder` defaults to a local maximum of **256 Records per prepared page**.

The hard runtime maximum remains the existing M8 page maximum of **10,000 Records**. The local cap is explicit and fail-closed: M32 rejects a request whose requested `page_size` exceeds the configured local maximum rather than silently rewriting the request.

The page source must return an exact `InboundFederationPageMaterial` whose `records` field is an exact tuple. Arbitrary iterables/generators are rejected without enumeration.

M32 checks the tuple length against both the validated request page size and configured local cap before invoking the Record validator or M8 page evaluator.

## Page evaluation and response construction

After local authorization and page materialization, M32:

1. validates every selected Record with the existing injected Marketplace validator;
2. derives one canonical OLP Record Identity per selected Record;
3. rejects duplicate Record Identities;
4. sorts the selected page deterministically by Record Identity;
5. invokes the existing M8 `evaluate_exchange_page(...)` semantics;
6. requires source, operation, scope fingerprint, Record IDs, page controls, and ordering meaning to match exactly;
7. requires `global_completeness = UNKNOWN` and `absence_is_deletion_evidence = False`;
8. revalidates/re-identifies the selected Records after evaluation to detect helper-side mutation;
9. constructs one response payload from only validated/evaluated values;
10. validates the result payload again using the existing M8 result validator;
11. creates one response envelope using the configured result message type;
12. validates that created envelope again and requires exact payload/profile preservation;
13. deeply detaches the final prepared response.

The prepared response is one local value only. No send operation exists in M32.

## Prepared response facts

`PreparedInboundFederationResponse` fixes these facts:

```text
transmitted = False
request_authenticated = False
peer_identity_proven = False
global_completeness = UNKNOWN
absence_is_deletion_evidence = False
creates_agreement = False
establishes_truth = False
establishes_trust = False
authorizes_protected_side_effects = False
```

Its integrity snapshot binds the immutable request context, canonical Record IDs, page controls, and response-envelope host representation. Dataclass replacement or other local rebinding cannot silently reuse an old snapshot for a changed prepared response.

## Alias and helper hardening

M32 reuses M30's tuple-backed immutable `FrozenDict`/`FrozenList` host values.

Consequences:

- mutation of the caller's original request after entry cannot alter the detached request M32 validates;
- a disclosure authorizer cannot change the authoritative request scope by mutating a mapping alias;
- a result validator or envelope maker cannot mutate the authoritative frozen response payload;
- mutation of an envelope-maker list/dict alias after `prepare_response(...)` cannot change the returned prepared response;
- if a page evaluator mutates selected Record content such that canonical Record Identity changes, M32 fails closed before constructing a response.

These protections do not make transport authentication, source URIs, or page contents true or trusted.

## No network/server surface

`inbound_federation.py` contains no concrete socket, SSL/TLS, HTTP, URL client/server, async loop, thread, subprocess, filesystem, or logging imports.

It has no listener, `accept()` loop, server lifecycle, retry/backoff, endpoint discovery, rate limiter, scheduler, background worker, credential store, or persistence primitive.

A source-level adversarial test enforces this boundary.

## Retention and privacy

M32 introduces no durable state.

Request envelope/payload, cursor, local authorization context, selected Record bodies used transiently during preparation, response payload, and response envelope remain EPHEMERAL under the project retention policy, with a maximum of **10 seconds post-use**.

M32 does not log request, response, Record, or cursor contents.

## Out of scope

- network listener / HTTP server / socket accept loop;
- TLS termination;
- remote peer authentication;
- authorization-token issuance;
- endpoint/routing discovery;
- rate limiting by IP/identity;
- retries/backoff;
- multi-request server lifecycle;
- background workers/schedulers;
- submission-v1 receiving/ingest side effects;
- durable cursor/checkpoint state;
- cursor encoding/cryptography policy;
- automatic cursor issuance;
- Record-body network serving;
- live federation peer execution;
- global completeness claims;
- truth/trust/agreement/protected-action authority.

## Recovery

M32 adds no migration, deployment, listener, credential, durable database state, or live network side effect. Code recovery is by reverting its future merge commit.
