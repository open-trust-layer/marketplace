# M17.2A — Inert PostgreSQL reference application composition root

M17.2A closes the next composition gap after M17.1Z without activating any runtime authority.

The new reference factory binds the existing `PostgresApplicationStateStore` and `PostgresIntentQuery` to the existing reviewed reference application launch plan. Both adapters receive the **same injected connection factory and clock** so Web, Android, and later agents continue to observe one application-state coordination boundary rather than independently assembled stores or queries.

## What this slice does

`build_reference_postgres_marketplace_application_launch_plan(...)`:

- accepts an injected PostgreSQL connection factory and clock;
- constructs the existing reviewed PostgreSQL state store;
- constructs the existing reviewed bounded root-intent query adapter;
- preserves the existing `MARKETPLACE_APPLICATION_STATE_MVP` retention profile without exposing a new override;
- delegates to `build_reference_marketplace_application_launch_plan(...)` so the M17.1Y state adapters, M17.1Z Record JSON profile, product-listing builder, proposal builder, HTTP adapter, same-origin site host, and ASGI adapter remain the only reviewed semantic path;
- accepts already-supplied `index_html`, `app_js`, and `styles_css` bytes instead of selecting or loading files.

## Inert authority boundary

Calling the M17.2A factory performs:

- **no PostgreSQL connection**;
- **no schema migration**;
- no application initialization or retention sweep;
- no environment or secret loading;
- **no filesystem asset loading**;
- no PostgreSQL driver selection;
- no Uvicorn import or provider selection;
- **no server activation** or socket operation;
- no browser or Android runtime action;
- no dependency installation;
- no deployment, service, configuration, or production mutation.

The injected connection factory and clock are retained by the already-reviewed adapters and are not called during composition.

## Remaining runtime steps

A future localhost acceptance path still needs separately reviewed authority to provide concrete database connectivity, perform explicit application initialization/migration, supply or load the web assets, select the reviewed Uvicorn provider, and invoke the foreground loopback execution boundary. Those steps are intentionally not collapsed into M17.2A.

Production database provisioning, external hosting, public network exposure, credentials, Android build/sign/install, and deployment remain separate capabilities.

## Governance

M17.2A is a MODERATE source-only composition change. CI and maintainer self-review are not independent human review. If independent review is unavailable, the repository standing solo-maintainer procedure applies. Merge remains a **separate exact-head governance boundary** and source merge does not authorize any runtime activation.
