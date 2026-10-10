# M17.6N — Enrollment-aware foreground runtime seam

Profile: `MARKETPLACE_APPLICATION_AUTH_ENROLLMENT_FOREGROUND_RUNTIME_V1`

Exact implementation baseline: `356766ad3dc1539e9f052be922cf33974fa63562`

Risk classification: **HIGH security/privacy / explicit authenticated enrollment runtime-execution source capability**.

M17.6N introduces one explicit, source-level foreground runtime seam for the already-reviewed M17.6M enrollment-aware loopback launch plan. The seam is **unselected**: no startup, launch, reference, Web, Android, configuration, service, Uvicorn, or Moon Company path invokes it.

## Exact six-file scope

Added:

1. `src/marketplace/application/auth_enrollment_runtime_server.py`
2. `tests/test_m17_6n_auth_enrollment_runtime_server.py`
3. `tests/test_m17_6n_auth_enrollment_runtime_server_artifacts.py`
4. `docs/m17-6n-auth-enrollment-runtime-server.md`

Modified only for wheel membership:

5. `tools/package_artifact_gate.py`
6. `tests/test_package_artifact_gate.py`

No existing startup, launch, runtime, ASGI, HTTP, reference, Web, Android, provider, dependency, workflow, PostgreSQL, configuration, service, audit, or governance source is modified.

## Explicit execution token

A caller must provide the exact string:

`EXECUTE_ONE_AUTHENTICATION_ENROLLMENT_MARKETPLACE_LOOPBACK_SERVER`

The token must be an exact `str`; subclasses and alternate strings fail before provider inspection.

The token is source-level authority only. It is not loaded from environment, configuration, CLI, files, network, or a provider.

## Exact plan and graph boundary

Before inspecting the provider, the seam revalidates:

- exact M17.6M launch-plan type;
- host exactly `127.0.0.1`;
- exact integer port inside the reviewed Marketplace loopback bounds;
- exact M17.6L startup-overlay type;
- enrollment HTTP bound to the exact authenticated HTTP composition;
- enrollment ASGI bound to the exact enrollment HTTP composition;
- exact runtime-input identity across enrollment and authenticated ASGI graphs;
- plan ASGI is exactly the M17.6K enrollment-aware ASGI object;
- exact application site;
- exact ordinary Marketplace HTTP adapter;
- exact authenticated session HTTP adapter;
- exact enrollment HTTP adapter;
- exact runtime-clock ownership.

Forged, cross-bound, or corrupted plans fail before provider inspection.

## Provider boundary

Only after the exact execution token and exact plan graph pass validation may the seam inspect one injected `MarketplaceAsgiServerProvider.run`.

The callable is inspected at most once and delegated to at most once:

`run(application=plan.asgi, host=plan.host, port=plan.port)`

There is no provider discovery, fallback, retry, background execution, process/thread creation, service wrapper, or concrete provider selection.

Provider shape failures and provider exceptions collapse to the stable non-reflective error:

`authentication enrollment loopback runtime failed`

Provider exception details are not reflected.

## Qualification execution boundary

M17.6N tests use a **deterministic provider probe** only. They do not invoke Uvicorn, create sockets, bind/listen/accept, or start a real server.

Before the deterministic provider call, validation performs zero:

- wall-clock reads;
- credential/challenge/session material generation;
- enrollment nonce generation, issuance, or consumption;
- approval-policy calls;
- attestor calls;
- provisioning loads;
- application initialization;
- HTTP/ASGI request handling;
- socket creation;
- filesystem/network/database access.

The only side effect modeled by a successful test invocation is one in-memory probe call.

## Explicit non-authority

M17.6N authorizes no:

- real runtime execution;
- Uvicorn or concrete server-provider activation;
- socket creation/bind/listen/accept;
- localhost smoke-run;
- public-network execution;
- provider discovery/configuration;
- service/background task/thread/process;
- concrete nonce provider;
- persistent/shared nonce authority;
- concrete approval policy;
- signer/private-key custody/provider;
- trust-anchor/evidence mutation;
- browser enrollment activation;
- WebCrypto client selection;
- Android action;
- PostgreSQL/configuration/service mutation;
- dependency/workflow/audit widening;
- production/public-network activity;
- deployment, publishing, or distribution.

## Moon Company boundary

M17.6N exposes a precise source-level Moon Commerce runtime capability boundary while preserving Marketplace independence and trust separation.

It adds no Moon Company runtime/control-plane, registry, event-bus, or agent dependency. Moon Company does not gain execution authority, provider ownership, enrollment authority, session authority, signing authority, or production-control authority from this seam.

## Rollback

Rollback is **source-only rollback**: revert the exact M17.6N merge.

Because the seam remains unselected and qualification uses deterministic probes only, rollback requires no listener shutdown, session cleanup, nonce cleanup, key revocation, trust-store change, database rollback, service restart, provider administration, browser/device cleanup, or deployment rollback.
