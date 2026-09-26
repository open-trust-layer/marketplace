# Agreement assent localhost shared composition

## Purpose

The Agreement-assent preflight and execution paths must qualify the same
composition graph. A preflight that reconstructs a different graph would create
configuration drift exactly at the database/server mutation boundary.

This slice removes that duplication.

## Shared composition

Both paths delegate to one internal composition helper after loopback-port
validation.

The helper:

- loads the selected authentication provisioning and configuration;
- constructs the PostgreSQL connection factory without invoking it;
- builds the authenticated PostgreSQL launch plan;
- validates the authenticated application composition;
- builds the Agreement-assent PostgreSQL graph;
- verifies exact coordination-store identity;
- requires coordination to remain uninitialized;
- verifies exact loopback host and port.

It returns the already-validated base application and Agreement graph.

## Preflight path

The preflight returns the graph without initializing either lifecycle or
constructing the server provider.

## Execution path

Execution still requires the exact Agreement-assent execution token before the
shared composition helper is entered. Only after shared composition succeeds
does execution construct the server provider, initialize the base application,
initialize Agreement coordination, and delegate to the foreground runtime.

Therefore a wrong execution token cannot trigger provisioning/configuration
reads through the shared helper.

## Source-delivery boundary

This PR only refactors source and adds synthetic tests. It does not invoke
preflight or execution.

No PostgreSQL connection, migration, expiry, server/socket action, Agreement
signing/publication, deployment, provider administration, or main merge is
performed by this source delivery.
