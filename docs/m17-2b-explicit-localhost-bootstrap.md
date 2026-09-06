# Product M17.2B — explicit localhost MVP bootstrap

Work item: #238.

Baseline: exact merged-green `main` `43a4ed852284ceb21e7004f0659e58bf38b695e6`.

## Purpose

M17.2B adds one repository-only bootstrap command that joins the already-reviewed M17 application pieces into a direct localhost path for a **later separately authorized run**.

It deliberately does not add another application, HTTP, ASGI, database-state, or server abstraction. The tool reuses:

- M17.2A `build_reference_postgres_marketplace_application_launch_plan(...)` for the exact PostgreSQL-backed reference graph;
- the existing top-level `web/index.html`, `web/app.js`, and `web/styles.css` client artifacts;
- the existing application `composition.initialize()` path for reviewed PostgreSQL migration/startup retention maintenance;
- M17.1O `UvicornLoopbackServerProvider` as the reviewed local server provider adapter; and
- M17.1N `run_marketplace_application_foreground(...)` plus `EXECUTE_ONE_MARKETPLACE_LOOPBACK_SERVER` for final foreground loopback delegation.

The result is a concrete source path toward the visible Web MVP rather than a parallel semantic stack.

## Risk classification

**HIGH source change.**

The source is capable, when separately and explicitly executed, of:

1. reading one fixed environment variable containing a PostgreSQL DSN;
2. reading the three fixed repository Web assets;
3. selecting the reviewed pinned PostgreSQL provider;
4. opening PostgreSQL connections during initialization;
5. applying the already-reviewed M17.1A schema migration and startup retention maintenance; and
6. selecting the reviewed Uvicorn adapter and activating one foreground IPv4-loopback server.

The PR, tests, and CI do not perform those live effects. Classifying the source as HIGH is intentional and is not reduced merely because validation uses deterministic doubles.

## Command surface

The tool is repository-only:

```text
tools/marketplace_localhost.py
```

It is not a package entry point, daemon, service definition, deployment unit, browser launcher, or production command.

The port must be an exact integer in the unprivileged range `1024..65535`. The host is fixed to:

```text
127.0.0.1
```

There is no caller option for public bind, IPv6 wildcard, TLS, proxy trust, workers, reload, WebSockets, or arbitrary Uvicorn configuration.

### Inert dry-run

The dry-run validates only bounded localhost metadata:

```text
python tools/marketplace_localhost.py --port 18080 --dry-run
```

Dry-run does not select or read:

- environment state;
- PostgreSQL DSNs or credentials;
- filesystem Web assets;
- `psycopg`;
- Uvicorn;
- sockets or network providers.

It does not build the application graph, initialize PostgreSQL, or run a server.

### Live execution boundary

The live path requires the exact M17.2B source token:

```text
EXECUTE_MARKETPLACE_LOCALHOST_MVP_V1
```

The token is an implementation safety gate only. It is **not** repository-governance approval, runtime authorization, deployment permission, database-administration permission, or production authority.

A future live run additionally requires separate explicit authority for its exact runtime scope.

The only DSN source is the fixed environment-variable name:

```text
MARKETPLACE_POSTGRES_DSN
```

The DSN value is bounded to 8192 characters, must be non-empty exact text, rejects NUL/CR/LF, and is never printed or included in a tool error. The source offers no CLI DSN parameter so credentials are not deliberately moved into process command-line arguments.

The reviewed dependency declarations remain unchanged:

```text
postgres = ["psycopg[binary]==3.3.5"]
local-server = ["uvicorn==0.52.4", "click==8.5.0", "h11==0.16.0"]
```

M17.2B does not install either optional extra. Dependency installation remains a separate capability and authorization boundary.

## Exact Web asset boundary

Only these three paths are accepted:

```text
web/index.html
web/app.js
web/styles.css
```

The live filesystem reader is not selected until after the exact M17.2B execution token is validated. It derives the repository root from the tool file, requires the `web` directory and each selected asset to resolve inside that exact directory, rejects symlinked `web`/asset paths, requires regular files, checks the existing application response-size bound before reading, and rejects size drift observed across the read.

The asset bytes are then passed directly into M17.2A. No alternate Web root, template rendering, dynamic asset discovery, recursive traversal, upload surface, or browser automation is added.

## PostgreSQL and initialization boundary

`psycopg` selection is lazy and occurs only on the live post-opt-in path. M17.2B does not change the pinned optional dependency declaration and does not create a second persistence implementation.

The selected `psycopg.connect(dsn)` callable is wrapped only as the `ConnectionFactory` already expected by M17.2A. Constructing the launch plan remains inert: no connection is opened by M17.2A construction.

Before any stateful initialization, M17.2B independently revalidates that the returned object is the exact `MarketplaceApplicationLaunchPlan`, contains the exact `MarketplaceApplicationComposition` and exact `MarketplaceAsgiHttpAdapter`, retains the fixed loopback/port boundary, and keeps the ASGI adapter identity-bound to that composition's site. A forged or cross-bound plan fails as `M17_2B_LAUNCH_PLAN_INVALID` before database initialization.

Only after that exact graph check does the bootstrap invoke exactly one:

```text
plan.composition.initialize()
```

That call is the existing reviewed application initialization boundary. It may open PostgreSQL connections, apply the existing transactional migration, and perform startup retention cleanup in a future authorized live run. M17.2B adds no migration SQL, alternate schema, retention override, retry loop, or database administration surface.

Initialization failure is normalized to `M17_2B_DATABASE_INITIALIZATION_FAILED` and prevents server delegation.

## Server boundary

M17.2B selects the existing `UvicornLoopbackServerProvider` only on the live post-opt-in path. Selection requires the imported adapter symbol to be an exact class, construction to return that exact type, and its `run` attribute to be callable. The adapter itself continues to lazy-import real Uvicorn only when its reviewed `run(...)` method executes.

After successful initialization, the bootstrap delegates exactly once through:

```text
run_marketplace_application_foreground(
    plan=plan,
    provider=provider,
    execute_token=EXECUTE_ONE_MARKETPLACE_LOOPBACK_SERVER,
)
```

No retry, background thread/task/process, service installation, browser launch, public listener, or alternate server path is introduced. Provider/server failure is normalized to `M17_2B_LOOPBACK_SERVER_FAILED`.

## Threat-boundary review

The HIGH-risk path is intentionally ordered fail-closed:

1. validate exact unprivileged port;
2. validate the exact M17.2B live execution token;
3. select the environment getter and read only `MARKETPLACE_POSTGRES_DSN`;
4. select the fixed repository asset reader and adopt exactly three bounded asset byte strings;
5. select the pinned PostgreSQL provider and create an inert connection factory;
6. build the exact M17.2A launch plan;
7. revalidate exact launch-plan/composition/ASGI types, loopback metadata, and ASGI-to-site identity binding;
8. select and exact-type-check the existing reviewed Uvicorn adapter;
9. initialize the existing application composition exactly once;
10. only after successful initialization, delegate exactly once to M17.1N foreground execution.

Negative/security properties covered by deterministic tests include:

- help and dry-run never select live providers;
- wrong execution token fails before environment/filesystem/provider selection;
- privileged/out-of-range ports fail before live provider selection;
- DSN source name is fixed and secret values are not reflected;
- Web asset names are exact and bytes are bounded;
- PostgreSQL provider import is lazy and connection establishment remains later than factory construction;
- Uvicorn adapter selection requires the exact callable provider shape without importing real Uvicorn;
- M17.2A is reused rather than bypassed;
- a forged launch plan is rejected before database initialization;
- database initialization precedes server delegation;
- initialization failure prevents server delegation;
- provider failures are non-reflective and not retried;
- source has no browser, subprocess, threading, multiprocessing, asyncio, direct socket, retry loop, wildcard bind, or alternate public host surface.

CI uses only patches, fake importers, fake environment getters, fake asset readers, and fake server/database boundaries. It does not read a live DSN, load the actual runtime Web assets through the bootstrap, import real `psycopg`/Uvicorn through the bootstrap execution path, connect to PostgreSQL, bind a socket, or launch a browser.

## Rollback and recovery

Source rollback is removal/revert of:

- `tools/marketplace_localhost.py`;
- `tests/test_m17_2b_explicit_localhost_bootstrap.py`; and
- this document.

The source/CI work itself creates no runtime state.

For any future separately authorized live run:

- failure before `composition.initialize()` creates no database mutation through M17.2B;
- initialization uses the existing M17.1A transactional migration semantics and startup cleanup behavior;
- initialization failure prevents server start;
- once initialization has succeeded, a subsequent server/provider failure may leave the reviewed application schema/startup-maintenance result in PostgreSQL; M17.2B does not claim to reverse committed existing schema/retention work;
- the server path is foreground and has no automatic retry/restart;
- any database restore, schema reversal, service mutation, or deployment rollback beyond existing transactional semantics requires separate explicit authority.

## Explicit non-authority

Creating, reviewing, testing, or merging M17.2B does **not** authorize or perform:

- dependency installation;
- reading a real DSN/secret;
- filesystem asset loading by the live bootstrap;
- PostgreSQL connection, migration, provisioning, administration, retention mutation, or data change;
- Uvicorn execution;
- socket bind/listen/accept/connect or network traffic;
- browser launch;
- service/process/background-worker creation or restart;
- configuration mutation;
- Android build/runtime/sign/install/distribution;
- production deployment, public exposure, TLS termination, or proxy trust;
- payment, settlement, fulfillment, inventory, or protected-side-effect execution.

A real localhost activation remains a separate HIGH runtime action and requires its own explicit authorization after the source has passed governance and merged-main verification.
