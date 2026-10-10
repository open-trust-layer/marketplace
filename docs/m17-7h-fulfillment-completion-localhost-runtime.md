# M17.7H — Explicit fulfillment completion localhost runtime selection

Profile: `MARKETPLACE_FULFILLMENT_COMPLETION_FOREGROUND_RUNTIME_V1`

Risk: **HIGH local runtime execution**, loopback-only and explicitly gated.

## Purpose

M17.7G provides one coherent inert reference launch object for the reviewed
fulfillment-completion chain. M17.7H makes that exact graph selectable by the
existing repo-only localhost bootstrap.

This slice does not start a server by import, help, dry-run, preflight, or
ordinary authenticated modes. Live fulfillment execution requires a new exact
mode-specific opt-in.

## Exact CLI modes

Preflight:

```text
--preflight-fulfillment-completion-localhost
```

Preflight requires the existing explicit authentication provisioning directory.
It composes the existing PostgreSQL/authentication/Agreement-assent graph and
M17.7G reference fulfillment graph, but performs:

- zero PostgreSQL connection calls;
- zero application-state initialization;
- zero Agreement coordination initialization;
- zero server/provider execution.

Live execution:

```text
--execute-fulfillment-completion-localhost EXECUTE_FULFILLMENT_COMPLETION_AUTHENTICATED_MARKETPLACE_LOCALHOST_V1
```

The exact bootstrap opt-in is separate from the lower-level runtime token.

## Execution sequence

After the exact CLI token is validated, the bootstrap:

1. validates the loopback port;
2. loads the existing authentication provisioning;
3. composes the existing authentication runtime inputs;
4. reads the existing bounded PostgreSQL DSN and reviewed Web assets;
5. builds the existing authenticated PostgreSQL launch plan;
6. builds the existing Agreement-assent PostgreSQL graph;
7. builds the exact M17.7G reference fulfillment launch;
8. verifies that Agreement publication and fulfillment publication share the
   exact existing application-state service;
9. selects the existing Uvicorn loopback provider and existing optional Moon
   heartbeat wrapper;
10. initializes the existing Marketplace application state;
11. initializes the existing Agreement-assent coordination store;
12. calls the new fulfillment-specific foreground runtime seam exactly once.

## Runtime seam

The fulfillment runtime accepts only an exact
`MarketplaceFulfillmentCompletionLoopbackLaunchPlan` and exact execution token
`EXECUTE_ONE_FULFILLMENT_COMPLETION_MARKETPLACE_LOOPBACK_SERVER`.

Before delegating to the provider it revalidates:

- host is exactly the reviewed IPv4 loopback host;
- port is inside the existing reviewed range;
- startup is the exact M17.7E type;
- ASGI is the exact session-aware adapter owned by the startup;
- site belongs to the exact authenticated application;
- selected Marketplace HTTP is the exact M17.7C fulfillment adapter;
- auth-session HTTP is the exact existing authenticated session adapter.

The provider is invoked exactly once with the reviewed ASGI value, host, and
port.

## Network and deployment boundary

M17.7H does not widen binding beyond `127.0.0.1`.

It adds no public-network listener, reverse proxy, cloud hosting, production
deployment, service installation, daemonization, background worker, or
production-health claim.

The optional Moon heartbeat wrapper remains operational metadata only and does
not change Marketplace authorization or product semantics.

## Product semantics

The reachable route remains the reviewed M17.7C route:

`POST /api/agreements/{agreement_record_id}/commitments/{commitment_id}/completion-evidence`

It authors attributable fulfillment evidence only. It does not establish
universal completion, payment, settlement, legal effect, or absence of dispute.

## Web boundary

M17.7H does **not** add or activate a Web completion button. Browser UX remains
a separate reviewed slice.

## Rollback

Stop the explicitly started local process if one is running, then revert the
exact M17.7H merge. No public deployment, schema migration, or payment/settlement
rollback is involved.
