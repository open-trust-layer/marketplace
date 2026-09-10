# M17.5V - Authenticated foreground loopback runtime execution seam

Profile: `MARKETPLACE_APPLICATION_AUTH_FOREGROUND_RUNTIME_V1`.

Baseline: exact merged-green `df31103fdd86a0a34bb99db8c45191b35b657f63`.

M17.5V adds one source-level foreground execution seam for an already-built exact
M17.5U authenticated loopback launch plan. It does not select a concrete server
provider, build an authentication graph, initialize application state, or start a
server during implementation or CI.

## Contract

The function accepts exactly:

- an exact existing `MarketplaceAuthenticatedLoopbackLaunchPlan`;
- a caller-injected existing `MarketplaceAsgiServerProvider` shape;
- exact source token `EXECUTE_ONE_AUTHENTICATED_MARKETPLACE_LOOPBACK_SERVER`.

The seam validates the token before provider inspection. It then independently
revalidates the launch metadata and authenticated graph before obtaining
`provider.run`. Only after those checks may the provider be delegated exactly once
as:

```text
run(application=plan.asgi, host=plan.host, port=plan.port)
```

Normal provider return maps to `None`. Provider lookup or execution failure becomes
one stable non-reflective `MarketplaceAuthenticatedLocalRuntimeError`; there is no
retry or fallback into the existing unauthenticated runtime function.

## Authenticated graph boundary

Execution accepts only exact IPv4 loopback `127.0.0.1` and the existing
`MIN_LAUNCH_PORT..MAX_LAUNCH_PORT` bounds. The execution boundary independently
checks exact M17.5U/T/R/P/O object types and the critical identity chain, including:

- `plan.asgi is plan.startup.asgi.asgi`;
- `plan.startup.asgi.http is plan.startup.http`;
- `plan.startup.http.authentication is plan.startup.authentication`;
- exact authenticated session ASGI adapter type;
- authenticated ASGI site/application-HTTP/session-HTTP bindings.

A forged, cross-bound, widened-host, malformed-port, or substituted-ASGI plan fails
before provider attribute access. Invalid token similarly fails with token before
provider inspection or execution.

## Capability boundary

M17.5V source implementation and CI use fake providers only. The seam itself does
not read a clock, consume challenge/session credential material, load provisioning
files or trust/evidence, generate a challenge or session token, invoke an
authentication request handler, perform no application initialization, access a
store/database, read environment/config/registry/filesystem values, discover a
provider, or perform any socket/network operation.

There is no concrete provider selection. Production source does not import, select,
instantiate, or execute `UvicornLoopbackServerProvider` or real Uvicorn. There is no
socket bind/listen/accept/connect, localhost HTTP request, PostgreSQL initialization,
retry, persistence, cache, subprocess, thread/process/task creation, service
mutation, background work, private-key operation, or signing activity.

The inherited provider protocol is imported only as the already-reviewed injection
boundary from `runtime_server.py`. M17.5V does not call
`run_marketplace_application_foreground(...)` and does not widen that unauthenticated
runtime path.

## Failure disclosure

All M17.5V-owned failures use one stable message. Failures do not reflect trust or
evidence bytes, principals, verification methods, challenge/session credentials,
provider or OS exception text, PostgreSQL/configuration values, alternate hosts,
request data, or application data.

Provider failure is attempted exactly once and is never retried.

## Exact scope

The exact six-file scope is:

1. `src/marketplace/application/auth_runtime_server.py`;
2. `tests/test_m17_5v_auth_runtime_server.py`;
3. `tests/test_m17_5v_auth_runtime_server_artifacts.py`;
4. `docs/m17-5v-auth-runtime-server.md`;
5. `tools/package_artifact_gate.py`;
6. `tests/test_package_artifact_gate.py`.

Existing `runtime_server.py`, `uvicorn_provider.py`, `auth_launch.py`, authentication
predecessors, bootstrap/executable entry points, provider/runtime source, dependency
metadata, workflows, repository audit, Web, Android, PostgreSQL, configuration and
services remain unchanged.

## Activation boundary

The existence of this execution seam is not live execution authority. Implementation,
review, CI, packaging and any later source merge do not authorize real provider
selection, Uvicorn execution, socket/network activity, application/PostgreSQL
initialization, provisioning/configuration loading, deployment, publication, or
production/public-network access.

A future authenticated bootstrap/activation milestone must separately define and
receive authority for provisioning selection, application initialization, concrete
provider selection, real localhost execution, and rollback/replacement behavior.

## Rollback

Rollback is source-only rollback of any separately authorized merge. Because no
existing bootstrap, executable entry point, provider selector, service, or runtime
path selects M17.5V, implementation and CI create no runtime state. Source-only
rollback requires no socket/session cleanup, trust-store mutation, database action,
provider administration, service restart, configuration rollback, or external-data
deletion.