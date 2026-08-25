# Specification 0013 — Marketplace Deployment Profiles & Runtime Boundaries

**Status:** Draft v0.1
**Milestone:** 14 — Deployment Profiles & Runtime Boundaries
**Depends on:** Marketplace Specifications 0001–0012 and applicable Open Layer Protocol transport, resolution, privacy, proof, identity/authority, and conformance semantics.

## 1. Purpose

This specification defines a portable, bounded deployment-description and readiness-evaluation profile for Marketplace implementations.

It answers a narrow operational question:

> Given an explicit deployment profile, exact configured component/adaptor bindings, exact service declarations, and exact local component observations, what local readiness conclusion may this implementation report?

It does not define one Marketplace server, cloud, database, broker, container platform, process supervisor, transport, operator, or hosting model.

## 2. Requirements language

The key words **MUST**, **MUST NOT**, **REQUIRED**, **SHOULD**, **SHOULD NOT**, and **MAY** are normative for this profile.

## 3. Constitutional boundaries

A conforming deployment profile preserves these distinctions:

```text
deployment descriptor          != Marketplace Record
component readiness            != external reachability
adapter binding                != operator authority
configured endpoint            != reachable endpoint
transport security             != OLP proof validity
service capability             != universal permission
deployment readiness           != protected-side-effect authorization
operator identifier            != globally trusted operator
configuration fingerprint      != signature
result fingerprint             != authentication
missing observation            != component failure proven
local READY                     != global service availability
```

Operational metadata MUST NOT silently become Marketplace evidence or universal trust state.

## 4. OLP and Marketplace boundaries

M14 does not create a fourth universal Marketplace record type. Deployment profiles, component observations, health state, process identifiers, credentials, and local adapter configuration are runtime metadata.

OLP remains authoritative for immutable evidence identity, proofs, relationships, resolution, privacy, and transport primitives. M8 remains authoritative for Marketplace federation message meaning.

A deployment MAY publish attributable OLP evidence about its service or status, but that publication is separate from the local M14 descriptor and has independent issuer/proof semantics.

## 5. Core profile identifier

The reference profile is:

```text
https://open-trust-layer.github.io/marketplace/semantics/v1/deployment/profile/core-node-v1
```

The reference helper MUST reject another profile identifier rather than silently applying core semantics under a different label.

## 6. DeploymentProfileV1

The exact v1 descriptor shape is:

```text
{
  version: 1,
  profile: AbsoluteURI,
  deployment_id: AbsoluteURI,
  operator: AbsoluteURI,
  components: [ComponentV1, ...],
  services: [ServiceV1, ...],
  critical: [AbsoluteURI, ...],
  context: { AbsoluteURI => OLPValue, ... }
}
```

No additional fields are permitted in v1. Components and services MUST be non-empty, bounded, duplicate-free by id, and sorted by UTF-8 id order.

`deployment_id` is a deployment-local identifier. It is not OLP Record Identity and does not create a global node registry.

## 7. ComponentV1

Each component is declared as:

```text
{
  id: AbsoluteURI,
  role: AbsoluteURI,
  adapter: AbsoluteURI,
  required: Boolean,
  critical: [AbsoluteURI, ...]
}
```

`role` describes the runtime responsibility. `adapter` identifies the configured implementation binding for that responsibility. Neither field proves that the implementation is healthy, secure, reachable, trusted, or authoritative.

The core profile defines reusable role URIs for transport ingress/egress, evidence storage, resolution, policy/authorization, evaluators, protected side-effect executors, and diagnostics. Profiles MAY define additional absolute-URI roles.

Required and optional components remain explicit. Hidden singleton/global dependencies are outside the portable model.

## 8. ServiceV1

Each service is declared as:

```text
{
  id: AbsoluteURI,
  capability: AbsoluteURI,
  mode: READ_ONLY | SIDE_EFFECT,
  required: Boolean,
  required_roles: [AbsoluteURI, ...],
  endpoints: [AbsoluteURI, ...],
  critical: [AbsoluteURI, ...]
}
```

`required_roles` MUST be non-empty and every role MUST have at least one configured component. Endpoints MAY be empty for offline, local, file-based, or otherwise non-network services.

A configured endpoint is only routing/deployment metadata. M14 does not test DNS, TLS, HTTP, queue, P2P, filesystem, or remote-service availability.

## 9. Side-effect services

A `SIDE_EFFECT` service MUST depend on both:

- the core policy/authorization role; and
- the core side-effect-executor role.

A descriptor that omits either dependency is invalid with `SIDE_EFFECT_AUTHORIZATION_GATE_REQUIRED`.

This is a composition invariant, not an authorization decision. Even when every backing component is `READY`, the M14 result MUST report `protected_side_effect_authorized = false`.

A consuming application MUST still submit each protected operation through the applicable Milestone 11 authorization boundary before invoking the executor.

## 10. Transport neutrality

M14 does not mandate HTTP, REST, gRPC, message queues, P2P, ActivityPub, local IPC, files, removable media, or any other transport. Such mechanisms are replaceable adapter choices behind declared component roles.

## 11. ComponentObservationV1

Readiness evaluation consumes ephemeral observations:

```text
{
  component_id: AbsoluteURI,
  adapter: AbsoluteURI,
  status: READY | DEGRADED | FAILED | UNKNOWN,
  critical: [AbsoluteURI, ...]
}
```

An observation MUST name a configured component and MUST bind to the exact configured adapter. An adapter mismatch is treated as component failure for this evaluation.

Exact duplicate observations are deduplicated and counted. Conflicting observations for the same component are rejected rather than resolved by arrival order or latest-wins semantics.

Missing observations remain `UNKNOWN`; they are not silently converted into proven failure.

## 12. Critical deployment semantics

Critical URIs may appear at descriptor, component, service, or observation scope.

The evaluator accepts an explicit, sorted, duplicate-free `understood_critical` URI set. An unknown critical dependency MUST fail closed:

- component/observation critical uncertainty makes that component `UNKNOWN`;
- service critical uncertainty makes that service `UNRESOLVED`; and
- descriptor-level critical uncertainty makes overall readiness `NOT_READY` and suppresses all advertised/degraded capability lists.

Understanding a critical URI means only that the implementation claims to process that semantic dependency. It does not prove the dependency is safe or correct.

## 13. Role readiness

When several components implement the same role, role readiness is selected conservatively by available local evidence: `READY` if any exact binding is ready, otherwise `DEGRADED`, then `UNKNOWN`, then `FAILED`.

This permits explicit redundancy without defining a universal load-balancing, failover, or quorum policy.

## 14. Service readiness

A service is evaluated from its declared required roles:

```text
all roles READY            -> READY
any role DEGRADED          -> DEGRADED
any role UNKNOWN           -> UNRESOLVED
any role FAILED            -> UNAVAILABLE
```

Unknown service-level critical semantics also produce `UNRESOLVED`.

A service capability enters `advertised_capabilities` only when that service is `READY`. A degraded service capability enters `degraded_capabilities` only when that service is `DEGRADED`.

These lists are local process outputs. They do not establish external reachability, transport security, authorization, trust, legality, or uptime.

## 15. Overall readiness

The overall result is `READY`, `DEGRADED`, or `NOT_READY`.

`NOT_READY` is returned when any required component is `FAILED` or `UNKNOWN`, any required service is `UNAVAILABLE` or `UNRESOLVED`, or descriptor-level critical semantics are not understood.

`DEGRADED` is returned when no required path is blocking but at least one component or service is not fully `READY`, including optional paths.

`READY` requires all declared component and service paths to be locally ready under understood critical semantics.

A deployment MAY expose service-level traces even when the overall deployment is `NOT_READY`; consumers MUST use the overall readiness result when making a deployment-level claim.

## 16. Configuration context

`context` is a bounded map from absolute URI keys to valid OLP values. It carries non-secret deployment semantics such as region, replica count, or local mode identifiers.

Context is part of the configuration fingerprint and therefore part of exact reuse binding.

Context MUST NOT be used as an unstructured credential bag.

## 17. Secret-safe descriptors and diagnostics

Portable M14 descriptors MUST NOT contain credential material.

The reference helper rejects secret-like field names such as token, password, credential, API key, private key, or client secret, including nested mappings. This is a structural guardrail, not a complete secret scanner.

Opaque values can still contain sensitive material that the helper cannot reliably identify. Therefore every result explicitly reports `secret_material_absence_established = false`.

Implementations SHOULD keep credentials in environment-specific secret stores or injected runtime dependencies and SHOULD redact diagnostics at the boundary.

## 18. Fingerprints

M14 defines deterministic SHA-256-based configuration, input, and result fingerprints over canonical OLP encoding of normalized processing metadata.

Fingerprints are integrity/replay metadata. They are not OLP Record Identity, signatures, authenticated timestamps, or trust claims.

## 19. Exact reuse

A prior deployment result is reusable by the reference helper only when both the configuration fingerprint and the complete normalized observation/input fingerprint are unchanged.

A changed component status, adapter binding, understood-critical set, service declaration, endpoint set, context value, or component composition therefore prevents exact reuse.

Reuse does not establish current external availability. Runtime conditions may change after an observation was produced.

## 20. Boundary flags

Every reference result explicitly reports `false` for:

```text
endpoint_reachability_established
operator_authority_established
transport_security_established
external_service_availability_established
protected_side_effect_authorized
marketplace_record_identity_affected
secret_material_absence_established
global_marketplace_role_established
result_authentication_established
```

## 21. Resource ceilings

The core reference profile bounds processing as follows:

```text
components                 256
services                   256
set-like URI members       256
context entries            128
component observations    1024
URI UTF-8 length          2048 bytes
```

Implementations MAY choose lower local limits. They MUST NOT silently raise portable v1 processing beyond the core ceilings while claiming the same conformance profile.

All network probes, resolver activity, storage calls, subprocesses, health checks, or side-effect execution remain outside the pure reference evaluator and require their own explicit bounds/timeouts.

## 22. Determinism and ordering

Set-like URI fields are duplicate-free and sorted by UTF-8 bytes. Components and services are sorted by id. Observation order is semantically neutral after normalization.

## 23. Relationship to M8 federation

M8 defines abstract federation request/result semantics and OLP transport reuse. M14 describes which local components back an implementation's declared services.

A deployment profile MUST NOT reinterpret an M8 message, cursor, idempotency binding, receiver outcome, or Record Identity.

A transport adapter MAY be replaced without changing Marketplace evidence semantics when the replacement preserves the required abstract behavior.

## 24. Relationship to M11 authorization

M14 can say that a policy/authorization adapter and a side-effect executor are locally ready. It cannot say that a particular operation is authorized.

Authorization remains request-specific and must happen before the protected side effect.

## 25. Health, readiness, and liveness

M14 standardizes a deterministic readiness projection over supplied observations. It does not standardize process liveness, restart policy, SLA/SLO objectives, remote health probes, or orchestrator-specific health endpoints.

An implementation MAY expose `/health`, Kubernetes probes, systemd status, queue metrics, or equivalent diagnostics, but those are deployment adapters around the M14 semantics rather than protocol requirements.

## 26. Composition and dependency injection

A deployment SHOULD assemble role implementations explicitly at a composition boundary. Core semantic evaluators SHOULD receive dependencies rather than locating hidden global clients, credential stores, databases, queues, or transports.

This keeps infrastructure replaceable and makes startup validation, testing, and failure ownership explicit.

## 27. Failure outcomes

Invalid descriptors and conflicting observations are explicit errors. Ordinary absence or degradation is represented in traces and readiness outcomes rather than raised as an exceptional crash.

## 28. Privacy and diagnostics

Deployment diagnostics can expose topology, provider choices, internal component names, endpoint locations, and operational state. Implementations SHOULD disclose only what is needed for the declared diagnostic purpose.

M10 privacy/data-minimization principles remain applicable. M14 does not create an entitlement to receive internal health state or topology.

Logs SHOULD use stable non-secret identifiers and SHOULD avoid dumping complete configuration or exception objects that may contain credentials injected outside the portable descriptor.

## 29. Security boundary

The reference evaluator is pure processing over supplied metadata. Untrusted M14 input MUST NOT trigger network calls, subprocess execution, filesystem mutation, credential access, remote health probes, payment submission, moderation, or another protected side effect.

Adapters that perform such operations belong outside the evaluator and remain subject to their own validation, authorization, timeouts, and resource bounds.

## 30. Example: read-only node

A small deployment may configure only transport ingress and evidence storage, exposing a read-only discovery/evidence service. If both exact adapters are observed `READY`, the service capability is locally advertised and the deployment may be `READY` without any side-effect executor.

## 31. Example: write-capable node

A write-capable deployment additionally configures a policy/authorization component and a side-effect executor. The write service declares both roles as dependencies.

If every component is `READY`, M14 may report the write capability as locally ready. The result still reports `protected_side_effect_authorized = false`; each actual write requiring a protected effect must pass M11 authorization.

## 32. Example: optional resolver

A deployment may configure an optional resolver component/service. If that optional component lacks an observation, required read paths can remain usable while overall readiness is `DEGRADED` and the resolver capability is not advertised.

## 33. Conformance processing profile

The non-normative reference implementation is:

```text
tools/marketplace_deployment_v1.py
```

Vectors are generated and independently replayed with:

```text
python tools/generate_deployment_vectors.py
python tools/validate_deployment_vectors.py
```

The committed artifact is `conformance/vectors/deployment-profiles-v1.json`.

## 34. Conformance coverage

M14 vectors cover valid read/write deployment composition, ready/degraded/not-ready outcomes, redundancy, missing observations, capability deduplication, offline services, endpoint sets, critical semantics, observation ordering/replay, exact reuse, malformed descriptors, side-effect gate omissions, secret-like fields, conflicting observations, and resource ceilings.

## 35. Deferred and out of scope

M14 does not standardize:

- a mandatory hosted Marketplace application;
- Kubernetes, Docker, systemd, serverless, VM, or bare-metal packaging;
- a database, cache, object store, search engine, or queue product;
- one HTTP path layout or one federation transport;
- global service discovery or operator registry;
- credential distribution or secret rotation;
- TLS certificate issuance;
- uptime/SLA policy;
- autoscaling, leader election, or consensus;
- backup/restore policy;
- billing, payment, tax, or legal compliance;
- universal trust in a deployment operator; or
- authorization of individual protected operations.

Later profiles MAY standardize selected deployment adapters while preserving these boundaries.

## 36. Acceptance boundary

Milestone 14 is satisfied when independent processors reproduce the committed M14 vectors while preserving these properties:

1. deployment metadata does not become Marketplace Record Identity;
2. no mandatory server, cloud, storage engine, queue, container platform, or transport is introduced;
3. runtime roles and adapter bindings are explicit and replaceable;
4. required/optional components and services produce deterministic `READY`, `DEGRADED`, or `NOT_READY` outcomes;
5. capabilities are advertised only from locally ready backing roles under understood critical semantics;
6. unknown critical deployment semantics fail closed;
7. side-effect services require an explicit policy/authorization gate and side-effect executor dependency;
8. readiness never authorizes a protected side effect;
9. secret-like fields are rejected without claiming perfect secret detection;
10. configuration/input/result fingerprints remain integrity metadata rather than authentication;
11. the evaluator performs no hidden network, filesystem, process, credential, or side-effect activity;
12. processing is deterministic and resource-bounded; and
13. every earlier Marketplace conformance suite remains green.
