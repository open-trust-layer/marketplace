# Agreement assent coordination initialization seam

## Purpose

This source-only slice defines the explicit one-shot lifecycle boundary that
would initialize the reviewed PostgreSQL Agreement-assent coordination graph.

Profile:

    MARKETPLACE_REFERENCE_AGREEMENT_ASSENT_COORDINATION_INITIALIZATION_V1

Exact execution token:

    INITIALIZE_ONE_AGREEMENT_ASSENT_COORDINATION

Defining this function does not invoke it.

## Why initialization is separate

The selected PostgresAgreementAssentCoordinationStore performs two mutating
startup operations when initialized:

1. apply its dedicated schema migrations;
2. expire due retained Agreement-assent evidence.

Those operations may open PostgreSQL connections and mutate database state.
They therefore remain separate from inert source composition.

## Exact preconditions

Before the coordination service is called, the initialization seam requires:

- one exact MarketplaceReferenceAgreementAssentPostgres graph;
- the exact execution token;
- the coordination service to retain the exact selected PostgreSQL store;
- coordination to be explicitly uninitialized.

An already initialized graph is rejected before another initialization call.

## Single-call semantics

After all guards pass, the seam calls exactly:

    graph.launch.services.coordination.initialize()

once.

The result must be an exact AgreementAssentExpiryResult and the coordination
service must report initialized state afterward.

Underlying failures are collapsed to one stable non-reflective error and are
not retried.

## Source versus activation

This PR only defines the guarded function and tests it with patched synthetic
initialization.

It does not call the function from localhost, startup, launch, CLI, or runtime
code. It does not open PostgreSQL, apply migrations, expire evidence, or start a
server during source delivery.

Actual invocation is a database/runtime mutation and requires separate explicit
authority.

## Non-scope

No database initialization or migration is executed. No localhost/server
execution, deployment, provider administration, trust/key mutation,
browser/WebCrypto execution, Agreement signing/publication, payment,
settlement, escrow, fulfillment, ownership transfer, or public-network activity
is performed or authorized.

## Rollback

Rollback is source-only: remove this additive lifecycle seam, tests, and
documentation. No external or durable state is created by defining it.
