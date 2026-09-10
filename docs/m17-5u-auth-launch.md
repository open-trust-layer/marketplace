# M17.5U - Inert authenticated loopback launch plan

Profile: `MARKETPLACE_APPLICATION_AUTH_LOOPBACK_LAUNCH_PLAN_V1`.

Baseline: exact merged-green `d8789b893a654c8565724fe1b8887a54391b1e61`.

M17.5U adds one source-only authenticated launch-selection object. It attaches
only inert host/port metadata to an already-built exact M17.5T startup graph.
It never executes or reconstructs that graph.

## Contract

The builder accepts exactly:

- exact string host `127.0.0.1`;
- exact integer port within the existing `MIN_LAUNCH_PORT..MAX_LAUNCH_PORT`;
- exact `MarketplaceAuthenticatedStartupComposition` from M17.5T.

The frozen/slotted plan retains the validated host and port, the exact startup
object, and the exact authenticated ASGI adapter already held at
`startup.asgi.asgi`. No second application, authentication, HTTP, ASGI,
runtime-input, provisioning, launch or provider graph is constructed.

The plan validates identity coherence before return:

- `startup.http.authentication is startup.authentication`;
- `startup.asgi.http is startup.http`;
- the retained adapter is exactly `startup.asgi.asgi`.

Exact concrete predecessor and ASGI adapter types are required. Direct plan
construction is subject to the same checks as the public builder.

## Capability boundary

Successful plan creation performs zero clock reads and performs
zero credential-material calls. It performs no provisioning read, trust/evidence
composition or injected
callable invocation, request handling, application initialization, store or
database access, socket/network action, provider lookup/execution, subprocess,
environment/config/registry access, retry, persistence, caching or background
work.

There is no fallback host, wildcard or IPv6 bind, hostname resolution, default
or dynamic port, free-port probing, socket inspection, runtime-server call or
provider selection. Host and port remain inert metadata only. There is no socket bind
and no runtime activation.

All M17.5U-owned failures use one stable non-reflective error. No trust/evidence
bytes, principals, challenge/session material, paths, provider/OS details or
application data are reflected.

## Exact scope

The exact six-file scope is:

1. `src/marketplace/application/auth_launch.py`;
2. `tests/test_m17_5u_auth_launch.py`;
3. `tests/test_m17_5u_auth_launch_artifacts.py`;
4. `docs/m17-5u-auth-launch.md`;
5. `tools/package_artifact_gate.py`;
6. `tests/test_package_artifact_gate.py`.

Existing authentication predecessors, `launch.py`, `runtime_server.py`,
providers, dependencies, workflows, repository audit, Web, Android,
PostgreSQL, configuration, services and executable entry points remain
unchanged.

## Rollback

Rollback is source-only rollback of the eventual separately authorized merge.
Because M17.5U performs no socket bind and no runtime selection or execution,
rollback requires no session cleanup, trust-store mutation, provider action,
service restart, database action, configuration rollback or external-data
deletion.

Implementation, review and CI do not authorize merge, runtime execution,
provisioning operations, credential generation, private-key/signing activity,
deployment, publishing, production/public-network activity or distribution.
