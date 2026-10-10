# Agreement assent authenticated localhost wiring

## Purpose

This source slice wires the reviewed PostgreSQL Agreement-assent graph into the
existing authenticated loopback bootstrap behind a new exact mode-specific
execution token.

Exact token:

    EXECUTE_AGREEMENT_ASSENT_AUTHENTICATED_MARKETPLACE_LOCALHOST_V1

CLI mode:

    --execute-agreement-assent-localhost TOKEN

The mode is mutually exclusive with every existing localhost execution mode.

## Defined runtime order

If separately authorized and invoked, the path:

1. validates loopback port and the exact Agreement-assent token;
2. loads the existing authentication provisioning boundary;
3. resolves the existing PostgreSQL and reviewed web-asset inputs;
4. constructs and validates the authenticated PostgreSQL launch plan;
5. constructs the exact Agreement-assent PostgreSQL graph;
6. initializes the base Marketplace application;
7. initializes Agreement-assent coordination through the one-shot seam;
8. starts the Agreement-assent loopback foreground adapter.

Base-application initialization failure blocks Agreement initialization.
Agreement initialization failure blocks server start.

## Source-delivery boundary

This PR only defines the path and validates its token, helper selection, and CLI
mutual exclusion. It does not invoke the new mode.

Actual invocation may open PostgreSQL, apply Marketplace and Agreement-assent
schema migrations, expire retained evidence, and bind a loopback server.
Those are runtime/database mutations and remain separate authority.

## Non-scope

No PostgreSQL connection, migration, expiry, localhost/server execution,
Agreement signing/publication, payment, settlement, escrow, fulfillment,
ownership transfer, deployment, provider administration, or public-network
activity is performed by this source delivery.

## Rollback

Rollback is source-only: remove the additive mode, helper wiring, tests, and
this document. Source delivery itself creates no external durable state.
