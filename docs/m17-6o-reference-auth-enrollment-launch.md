# M17.6O — Reference authentication-enrollment launch selection

Profile: `MARKETPLACE_REFERENCE_AUTHENTICATION_ENROLLMENT_LAUNCH_V1`

Exact implementation baseline: `97022443e9ed6d0d4e088e847b8c8df016ae145b`

Risk classification: **HIGH security/privacy / authenticated enrollment reference-selection source capability**.

M17.6O adds an inert reference-selection layer that attaches caller-supplied enrollment collaborators to one exact existing authenticated Marketplace launch graph. It composes the already-reviewed M17.6L startup overlay and M17.6M launch plan and **does not invoke M17.6N**.

## Exact six-file scope

Added:

1. `src/marketplace/reference/auth_enrollment_launch_v1.py`
2. `tests/test_m17_6o_reference_auth_enrollment_launch.py`
3. `tests/test_m17_6o_reference_auth_enrollment_launch_artifacts.py`
4. `docs/m17-6o-reference-auth-enrollment-launch.md`

Modified only for wheel membership:

5. `tools/package_artifact_gate.py`
6. `tests/test_package_artifact_gate.py`

No existing startup, launch, runtime, ASGI, HTTP, base reference-auth, Web, Android, provider, dependency, workflow, PostgreSQL, configuration, service, audit, or governance source is modified.

## Exact inputs

The selector accepts:

- one exact existing authenticated loopback launch plan;
- one exact existing M17.6H nonce authority;
- one caller-supplied purpose-specific approval policy;
- one caller-supplied purpose-specific attestor;
- one explicit authority value;
- one finite evidence lease.

It creates none of these authority-bearing collaborators.

The existing M17.6J layer validates the purpose-specific policy and attestor callables while retaining the exact caller objects. The selector does not call either collaborator.

## Exact composition

The selector derives:

- the authenticated startup directly from the authenticated launch plan;
- the runtime inputs directly from that startup.

It then composes exactly:

1. M17.6L enrollment startup using the caller-supplied nonce authority, policy, attestor, authority, and evidence lease;
2. M17.6M loopback launch metadata using the exact authenticated plan host and port.

The frozen result retains the authenticated plan, every caller-supplied collaborator/value, the exact enrollment startup, and the exact enrollment launch plan.

## Identity invariants

Selection fails closed unless:

- the authenticated launch plan and startup graph remain exact;
- host remains exact IPv4 loopback and port remains inside the reviewed range;
- the base authenticated ASGI still has no enrollment handler;
- the enrollment startup retains the exact authenticated startup and runtime-input object;
- enrollment HTTP retains the exact nonce authority, policy, attestor, authority, and evidence lease;
- the enrollment plan retains the exact enrollment startup;
- the enrollment plan host and port equal the authenticated plan exactly;
- the selected ASGI is exactly the M17.6K enrollment-aware ASGI object.

The base authenticated plan is not replaced or mutated.

## Inert and consumption boundary

Reference selection performs zero:

- wall-clock sampling;
- credential/challenge/session material generation;
- enrollment nonce material generation;
- nonce issuance or consumption;
- policy decisions;
- attestation/signing;
- HTTP/ASGI request handling;
- provider inspection;
- runtime invocation;
- socket creation/bind/listen/accept;
- application initialization;
- provisioning loads;
- filesystem/network/database access.

Qualification uses deterministic caller-supplied doubles only.

## Explicit authority boundary

M17.6O does not create or select:

- a nonce material source;
- persistent/shared nonce storage;
- an approval policy implementation;
- an attestor implementation;
- a signer or private key;
- trust anchors;
- a server provider;
- configuration/environment authority.

All such authority remains outside this reference selector.

## Runtime non-selection

The result is inert launch metadata. M17.6O **does not invoke M17.6N**, does not import/select Uvicorn, and does not call a provider.

No CLI, Web, Android, service, or Moon Company runtime path selects this reference module.

## Moon Company boundary

M17.6O gives Moon Commerce an inspectable reference composition for attaching enrollment capability while preserving Marketplace independence and authority separation.

It adds no Moon Company control-plane, registry, event-bus, agent, signer, policy, nonce-provider, session-authority, runtime-owner, or production-operator dependency.

## Rollback

Rollback is **source-only rollback**: revert the exact M17.6O merge.

Because selection is inert and caller collaborators are not invoked, rollback requires no listener shutdown, nonce cleanup, session cleanup, key revocation, trust-store change, database rollback, service restart, provider administration, browser/device cleanup, or deployment rollback.
