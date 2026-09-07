# M17.5F — Synthetic application-auth composition qualification

Profile: `MARKETPLACE_APPLICATION_AUTH_COMPOSITION_SYNTHETIC_V1`

Recovery baseline: `fad069fd973a7fc875dafecfba51e6e4a0bdc3f0`

Risk classification: **HIGH security/privacy source qualification**. This milestone proves deterministic composition only; it grants no live authentication, credential, provider, runtime, device, database, network, publishing, or deployment authority.

## Scope

M17.5F is deliberately additive and test-only. The implementation consists only of:

- `tests/test_m17_5f_auth_composition_synthetic.py`
- `tests/test_m17_5f_auth_composition_artifacts.py`
- `docs/m17-5f-auth-composition-synthetic.md`

No existing application-auth source, application/runtime source, Web source, Android source, dependency manifest, workflow, or configuration file is modified by this milestone.

The qualification reuses the already-reviewed M17.5B/C/D/E contracts. It does not introduce a second authentication/session model.

## Deterministic composition proved

The synthetic acceptance harness composes the existing M17.5D server-side session-establishment seam with the existing M17.5C authenticated application HTTP adapter using an **in-process** ASGI driver. It uses only fixed synthetic fixtures and injected doubles:

- exact synthetic principal `did:example:alice`;
- exact synthetic verification method `did:example:alice#key-1`;
- canonical deterministic 32-byte challenge fixture `bytes(range(32))`;
- canonical deterministic 32-byte session-token fixture `bytes(range(32, 64))`;
- injected deterministic `CredentialMaterialSource` behavior;
- injected deterministic `AuthenticationProofVerifier` behavior returning the reviewed `VerifiedAuthenticationProof` facts;
- injected exact principal-binding verifier;
- no socket, localhost listener, remote origin, provider, resolver, database, subprocess, or external network transport.

The test-only `SyntheticMemorySessionClient` mirrors the reviewed M17.5E carrier and route-selection semantics so server composition can be qualified without selecting active client entry points. The **actual Web and Android client code is not executed** in M17.5F; instead, artifact tests verify that the committed Web and Android M17.5E source retains the same exact bearer-routing, principal-derivation, invalidation, logout, and credential-negative offline boundaries.

This distinction is intentional: M17.5F demonstrates coherent source composition without claiming a browser, Android runtime, Gradle, emulator, device, or live-login acceptance result.

## Qualified invariants

The deterministic tests prove the following bounded properties:

1. A synthetic client requests exactly one challenge for the exact synthetic principal and verification method.
2. The existing M17.5D HTTP contract accepts one deterministic fake proof document through an injected verifier; no real signature/proof verification occurs.
3. The exact canonical `mkt1_...` bearer returned by the existing session-establishment service is adopted only into test-local memory.
4. `GET /api/auth/session` returns non-secret session facts; challenge, proof, and session token are absent from the inspection document.
5. Session inspection is non-touching: advancing the injected clock does not refresh the recorded last-used time.
6. Anonymous browse requests remain Authorization-negative while the synthetic memory session is active.
7. Missing local session blocks protected writes before transport dispatch.
8. Structured product-listing and proposal requests derive seller/buyer principal from the active session rather than an editable caller principal.
9. A caller attempt to override a structured principal fails before dispatch.
10. Raw publication issuer mismatch fails before transport/server write dispatch.
11. A server-side `AUTH_SESSION_INVALID` response clears the test-local memory session.
12. Logout clears local state before its single transport attempt and never restores the session after transport failure.
13. A newly constructed client instance has no credential recovery or persistence.
14. Existing Web and Android entry points remain unselected.
15. Android offline-cache source remains bearer/Authorization-negative.

## Threat and failure boundary

The qualification preserves existing stable M17.5D/M17.5C failure semantics rather than inventing new protocol truth. Existing predecessor regression suites remain responsible for malformed challenge/proof handling, one-use and expiry semantics, verifier/binding/material-source failure handling, collision handling, malformed bearer rejection, duplicate sensitive-header rejection, body bounds, capacity bounds, and non-reflective error behavior.

M17.5F adds the composition-level assertions that matter at the seam: no bearer on anonymous reads, fail-before-dispatch without a local session, fail-before-dispatch for structured principal override or raw issuer mismatch, local invalidation on `AUTH_SESSION_INVALID`, and local-first one-attempt logout.

No challenge, proof, bearer token, private material, or credential is intentionally emitted through repr/toString, logs, caches, persistent state, errors, timers, retry queues, callbacks, redirects, service workers, WorkManager, AlarmManager, background services, or cross-origin propagation by this test slice.

## Explicit non-authority

M17.5F authorizes none of the following:

- concrete challenge/session generation or CSPRNG/provider selection;
- private-key creation, import, custody, browser wallet/extension access, Android Keystore access, or other private-key handling;
- real OLP signing, cryptographic proof creation, or real proof verification;
- DID/resolver/provider lookup, administration, or network activity;
- OAuth, OIDC, password, JWT, cookie, callback, redirect, or cross-origin credential capability;
- credential or session persistence;
- Web `index.html` or active `app.js` authentication selection;
- Android `MainActivity` authentication selection;
- live localhost auth-capable server selection or service restart;
- PostgreSQL access or mutation;
- configuration or secret mutation;
- Android Gradle/build/install/emulator/adb/device execution — **no Android build** is part of this qualification;
- production/public-network access;
- publishing or deployment.

**No runtime activation** is performed or implied. There is **no credential persistence** and no credential recovery across a new client instance.

## Validation

Focused qualification:

```text
python -m unittest \
  tests.test_m17_5f_auth_composition_synthetic \
  tests.test_m17_5f_auth_composition_artifacts
```

Relevant predecessor security regression:

```text
python -m unittest \
  tests.test_m17_5b_application_auth_contracts \
  tests.test_m17_5b_application_auth_contracts_artifacts \
  tests.test_m17_5c_bearer_session_transport \
  tests.test_m17_5d_session_establishment \
  tests.test_m17_5d_session_establishment_hardening \
  tests.test_m17_5d_session_establishment_artifacts \
  tests.test_m17_5e_client_session_artifacts
```

Repository conformance remains the authoritative exact-head acceptance gate.

## Rollback and blast radius

Rollback is a **source-only rollback**: if this slice is later merged, revert the exact M17.5F merge. Because the change adds only tests and documentation and selects no live generator, proof verifier, provider, runtime composition, Web entry point, Android entry point, database path, service, or credential store, rollback requires no credential revocation, database migration, provider action, service restart, Android cleanup, or deployment action.

The blast radius is limited to deterministic test fixtures, test-only composition code, source/artifact assertions, and this documentation.

## Later milestone boundary

A later milestone must separately review and explicitly authorize any concrete authentication authority, including CSPRNG challenge/session generation, exact proof/signature format, private-key custody, real proof verifier/resolver/provider policy, runtime auth composition selection, active Web/Android login UX, localhost/device execution, configuration, database, service, provider/network, publishing, or deployment actions.

M17.5F proves only that the existing source contracts can compose coherently under deterministic synthetic conditions.
