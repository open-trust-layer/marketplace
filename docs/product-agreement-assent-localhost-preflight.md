# Agreement assent authenticated localhost preflight

## Purpose

The Agreement-assent localhost path has database and server mutation boundaries.
Before either boundary is crossed, this slice defines a read-only composition
preflight:

    --preflight-agreement-assent-localhost

The preflight requires the same explicit authentication provisioning directory
as authenticated execution.

## What the preflight validates

It validates and composes:

1. the reviewed loopback port;
2. the authentication provisioning boundary;
3. the configured PostgreSQL DSN shape;
4. reviewed web assets and authentication web modules;
5. the PostgreSQL connection factory without invoking it;
6. the authenticated PostgreSQL launch plan;
7. the exact Agreement-assent PostgreSQL graph;
8. exact loopback host/port coherence;
9. exact coordination-store identity;
10. coordination remains uninitialized.

## What it does not do

The preflight does not:

- call the PostgreSQL connection factory;
- initialize the base Marketplace application;
- initialize or migrate Agreement-assent coordination;
- expire retained assent evidence;
- construct a Uvicorn provider;
- bind a socket or start a server;
- sign or publish an Agreement.

The preflight does read the selected local provisioning files, environment
configuration, and reviewed web assets. It is therefore distinct from the
existing fully inert metadata-only `--dry-run`.

## Authority boundary

This PR defines the preflight and tests it with synthetic providers. It does
not invoke the preflight against a real environment.

Successful preflight is not authority to execute database initialization or
start the Agreement-assent localhost runtime. Those remain separate runtime
and database-mutation actions.

## Rollback

Rollback is source-only: remove the preflight mode, helper, tests, and this
document. Source delivery creates no external durable state.
