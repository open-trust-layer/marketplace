# Bounded Inbound Federation Response Preparation

**Milestone:** M32

**Status:** non-normative reference runtime architecture

**Risk:** HIGH

**Network posture:** transport-free; no listener, socket, HTTP/TLS server, retry loop, background worker, or live peer execution

## Purpose

M32 adds the local preparation boundary for one inbound Marketplace M8 snapshot or sync request. It validates one supplied transport envelope, rebinds its scope and capability requirements to local M8 facts, requires one explicit local disclosure decision, materializes one bounded local page, validates that page through existing M8 helpers, and prepares one immutable response envelope.

M32 stops before transmission.

It does not implement an inbound network server. A future transport adapter may invoke M32 only after separately establishing whatever transport/authentication facts and local authorization inputs that adapter requires.

## Authority boundary

```text
valid M8 request                 != permission to disclose Record IDs
request source                   != authenticated peer identity
request capability declaration  != local capability enablement
capability negotiation          != disclosure authorization
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

M32 treats the disclosure decision as an injected local policy fact. Request validity, source URI, operation, capabilities, page size, cursor presence, transport-envelope validity, and successful capability negotiation cannot substitute for that decision.

The disclosure authorizer is called exactly once after request validation, scope binding, local capability negotiation, and other request binding checks, and before the page source. Only exact boolean `True` permits page materialization. `False`, non-boolean values, or authorizer failure stop the request before local Record enumeration.

## Scope binding

M32 does not trust a request normalizer to rewrite scope invisibly.

Before disclosure authorization, the responder uses the existing injected M8 `scope_fingerprint(...)` semantic helper to derive fingerprints independently from:

1. the detached raw request scope; and
2. the normalized request scope returned by the existing M8 request validator.

Both derived fingerprints must be non-empty exact text and must equal the request validator's reported `scope_fingerprint`. Any mismatch fails closed before capability negotiation, disclosure authorization, or page-source invocation.

This preserves semantic normalization where raw list/tuple host representations may differ while preventing a miswired/hostile normalizer from silently changing the requested scope.

The final prepared-response integrity witness binds both the canonical scope fingerprint **and the immutable scope host representation**. Replacing the request context with a different scope while reusing the old fingerprint therefore invalidates the witness.

## Local capability binding

A request's `required_capabilities` field is a requirement, not proof that the local responder implements or enables those capabilities.

The responder is configured with one detached local M8 capability advertisement whose `source` must equal the responder's configured local source. After request normalization/scope binding and before disclosure authorization, M32 invokes the existing injected M8 `negotiate_capabilities(...)` helper exactly for the request's canonical required-capability tuple.

M32 requires:

- exact negotiation result shape;
- `required_capabilities` preserved exactly;
- `status = SUPPORTED`;
- empty unsupported and unavailable sets;
- `no_silent_downgrade = True`.

Any unsupported/unavailable requirement, silent-downgrade attempt, result-shape drift, or required-set drift fails before disclosure authorization or Record enumeration.

The local capability advertisement is deeply detached at responder construction, so later caller mutation cannot silently change the responder's capability state for an in-progress value.

The responder also honors the advertisement's local resource limits rather than treating only M8 hard maxima as operative. Its configured `max_page_records` cannot exceed the advertised `max_page_records`, and both supplied inbound cursors and prepared outbound `next_cursor` values must stay within the advertised `max_cursor_bytes` value. These checks are fail-closed and occur before any later phase that does not need to run.

Successful capability negotiation remains only a local compatibility fact. It does not authenticate a peer and does not authorize disclosure.

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
4. independently fingerprints the detached raw request scope;
5. validates/normalizes the M8 request payload;
6. cross-binds the normalized operation to the configured operation profile;
7. requires the normalized request `source` to equal the responder's configured local federation source;
8. independently fingerprints the normalized scope and requires raw, normalized, and reported scope fingerprints to agree;
9. enforces canonical required capabilities, configured/advertised page-size bounds, and exact cursor-presence/local cursor-limit consistency;
10. creates one immutable `InboundFederationRequestContext`;
11. requires the exact requested capabilities to be fully supported by the detached local capability advertisement;
12. only then invokes the local disclosure authorizer.

The request context explicitly keeps `request_authenticated = False`, `peer_identity_proven = False`, and `authorizes_protected_side_effects = False`.

## Cursor boundary

Incoming and outgoing cursors remain opaque bytes.

M32 does not decode, generate, interpret, rank, log, persist, or authenticate cursors.

An incoming cursor is exposed only inside the authorized immutable request context passed to the page source. The page source/policy component decides how, if at all, to interpret that cursor for local pagination.

A truncated page must return one bounded nonempty opaque `next_cursor` no larger than both the existing M8 4096-byte maximum and the responder's local advertised cursor limit. A final page must not return a cursor. An incoming cursor must satisfy the same local advertised limit before disclosure authorization.

Cursor possession does not grant disclosure authorization and does not prove remote identity.

## Local page limits

`BoundedInboundFederationResponder` defaults to a local maximum of **256 Records per prepared page**.

The hard runtime maximum remains the existing M8 page maximum of **10,000 Records**. The local cap is explicit and fail-closed: M32 rejects a request whose requested `page_size` exceeds the configured local maximum rather than silently rewriting the request. The configured local maximum itself cannot exceed the local capability advertisement's `max_page_records` value.

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

Its integrity snapshot binds the immutable request context including the actual frozen scope, canonical Record IDs, page controls, and response-envelope host representation. Dataclass replacement or other local rebinding cannot silently reuse an old snapshot for a changed prepared response.

## Alias and helper hardening

M32 reuses M30's tuple-backed immutable `FrozenDict`/`FrozenList` host values.

Consequences:

- mutation of the caller's original request after entry cannot alter the detached request M32 validates;
- mutation of the caller's capability-advertisement object after construction cannot alter the responder's detached advertisement;
- a disclosure authorizer cannot change the authoritative request scope by mutating a mapping alias;
- a result validator or envelope maker cannot mutate the authoritative frozen response payload;
- mutation of an envelope-maker list/dict alias after `prepare_response(...)` cannot change the returned prepared response;
- if a page evaluator mutates selected Record content such that canonical Record Identity changes, M32 fails closed before constructing a response.

These protections do not make transport authentication, source URIs, capability advertisements, or page contents true or trusted.

## No network/server surface

`inbound_federation.py` contains no concrete socket, SSL/TLS, HTTP, URL client/server, async loop, thread, subprocess, filesystem, or logging imports.

It has no listener, `accept()` loop, server lifecycle, retry/backoff, endpoint discovery, rate limiter, scheduler, background worker, credential store, or persistence primitive.

A source-level adversarial test enforces this boundary.

## Retention and privacy

M32 introduces no durable state.

Request envelope/payload, cursor, local capability advertisement/context, local authorization context, selected Record bodies used transiently during preparation, response payload, and response envelope remain EPHEMERAL under the project retention policy, with a maximum of **10 seconds post-use**.

M32 does not log request, response, Record, capability, or cursor contents.

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
