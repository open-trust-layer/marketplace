# M17.1N — Explicit foreground loopback server execution boundary

M17.1N adds an **explicit foreground loopback server execution boundary** above the reviewed M17.1M launch plan. It is the smallest source-level seam through which a later separately selected server implementation can consume the existing Marketplace ASGI application.

The boundary does not select or install a server. Development and CI use only an **injected server provider** supplied by the caller.

## Exact execution contract

The execution function accepts only:

- an exact `MarketplaceApplicationLaunchPlan` from M17.1M;
- the exact loopback host `127.0.0.1` already carried by that plan;
- an exact integer TCP port within `1..65535`;
- an injected server provider exposing one foreground `run(...)` call; and
- the exact repository-owned execute token `EXECUTE_ONE_MARKETPLACE_LOOPBACK_SERVER`.

The token is a source/runtime safety gate. It is not repository governance approval, deployment authorization, or permission to select or activate a real networking provider.

Before provider lookup, the execution seam revalidates the exact M17.1J `MarketplaceApplicationComposition`, exact M17.1L `MarketplaceAsgiHttpAdapter`, and identity binding of the adapter to `composition.site`. Manually forged or cross-bound launch plans fail closed before provider invocation.

After all validation succeeds, the boundary delegates exactly once to the injected provider with the existing M17.1L ASGI object plus the reviewed host and port metadata. There is no retry, polling, worker, thread, task, process, or background lifecycle in this slice.

Provider exceptions are normalized to one stable non-reflective local runtime error. Provider exception text is not promoted through the Marketplace boundary.

## Authority boundary

M17.1N deliberately retains these exclusions:

- **no concrete ASGI server dependency** is added or selected;
- **no real socket activation** occurs in development or CI;
- no bind, listen, accept, connect, DNS, TLS, HTTP client, or network traffic is performed by the packaged M17.1N source;
- **no live PostgreSQL activation** or database connection, migration, provisioning, or administration occurs;
- application-state initialization against a real provider remains outside this slice;
- **no runtime filesystem asset loading** or discovery occurs;
- no environment-variable or secret loading occurs;
- no browser launch or automation occurs;
- no process/service/background-worker start or restart occurs;
- no Android build, runtime, signing, installation, or distribution occurs;
- no production deployment or other runtime mutation occurs.

Concrete server selection, dependency review/install, actual loopback bind/listen, runtime Web asset loading, real PostgreSQL composition, application initialization, browser acceptance, and any production exposure each remain separate capabilities.

Any real server activation requires **separate runtime authorization** in addition to normal exact-head repository governance. Merging this source contract alone does not authorize a server to run.

## Product meaning

M17.1M established a frozen launch plan without execution. M17.1N establishes the explicit one-call execution seam without selecting the real executor. A later reviewed local-runtime slice can therefore add a concrete provider without rebuilding or bypassing the shared Marketplace Web/API/application graph.
