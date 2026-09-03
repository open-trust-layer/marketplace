# M17.1M — Inert application runtime launch contract

M17.1M adds an **inert application runtime launch contract** above the reviewed M17.1J application composition and M17.1L bounded ASGI HTTP adapter.

The contract prepares one immutable launch plan. It does not launch anything.

## Exact source composition

The plan is built only from caller-supplied application ports, codecs, and exact Web asset bytes. It reuses:

- `compose_marketplace_application(...)` from M17.1J;
- `MarketplaceApplicationComposition` from M17.1J;
- `MarketplaceAsgiHttpAdapter` from M17.1L;
- the existing `MarketplaceSiteHostAdapter` static/API surface.

The plan records the exact loopback host `127.0.0.1` and one validated TCP port as inert metadata. These values are not consumed by a socket or server in M17.1M.

## Initialization and persistence boundary

Building the plan does not call `MarketplaceApplicationComposition.initialize()`. The supplied state/query ports are retained only as part of the existing composition graph.

There is **no live PostgreSQL connection** in this slice. M17.1M does not open a connection, run migrations, provision a database, discover a DSN, or perform PostgreSQL administration.

## Asset boundary

The Web shell remains the exact caller-injected byte surface already reviewed in M17.1I/J:

- `index.html` bytes;
- `app.js` bytes;
- `styles.css` bytes.

There is **no runtime filesystem asset loading**. No path, directory, file discovery, or file-read authority is introduced.

## Runtime authority exclusions

This slice grants and exercises none of the following capabilities:

- **no ASGI server activation**;
- **no socket/network activation**;
- no bind, listen, accept, connect, DNS, HTTP client, or network traffic;
- **no live PostgreSQL connection**;
- **no runtime filesystem asset loading**;
- **no environment or secret loading**;
- no Uvicorn, Hypercorn, Daphne, or other concrete server selection/dependency;
- no process/service start or restart;
- no configuration mutation;
- no Android build/runtime/sign/install/distribution;
- no production deployment or other runtime mutation.

A later server, filesystem, configuration/secrets, PostgreSQL, Android, or deployment slice is a separate capability and requires its own risk review and authorization.

## Product meaning

M17.1M makes the future runtime seam explicit without widening authority. A later authorized launcher can consume the reviewed plan rather than rebuilding a competing Web/API/application graph.
