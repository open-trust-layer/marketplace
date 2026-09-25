# Agreement assent foreground runtime seam

## Purpose

This source-only slice defines an explicit foreground execution seam for the
reviewed Agreement-assent loopback launch plan.

Profile:

    MARKETPLACE_AGREEMENT_ASSENT_FOREGROUND_RUNTIME_V1

Execution requires the exact token:

    EXECUTE_ONE_AGREEMENT_ASSENT_MARKETPLACE_LOOPBACK_SERVER

Defining this seam does not invoke it.

## Exact authority checks

Before the injected provider is inspected, the seam requires:

- one exact MarketplaceAgreementAssentLoopbackLaunchPlan;
- exact IPv4 loopback host;
- reviewed loopback port range;
- exact selected Agreement ASGI object;
- exact Agreement HTTP Marketplace handler;
- exact authenticated session HTTP handler;
- the exact execution token above.

A wrong token or forged/substituted plan fails closed before provider
inspection.

## Provider boundary

The provider is injected. Its `run` method is inspected exactly once and,
after all authority checks pass, invoked exactly once with:

- application = plan.asgi;
- host = plan.host;
- port = plan.port.

Provider exceptions are collapsed to one stable non-reflective runtime error
and are not retried.

## Source versus activation

This PR adds only the execution function and its guards.

It does not:

- invoke the execution function;
- select a concrete server provider;
- modify tools/marketplace_localhost.py;
- alter current authenticated runtime selection;
- start a socket or server;
- initialize the application;
- perform a database migration;
- create Agreement assent evidence.

A later source slice may wire this exact seam into an explicitly gated
localhost command path. Actual invocation remains a separate runtime authority
and is not authorized by source delivery alone.

## Non-scope

No runtime activation, localhost execution, deployment, provider
administration, database migration, trust/key mutation, browser/WebCrypto
execution, Agreement signing/publication, payment, settlement, escrow,
fulfillment, ownership transfer, or public-network activity is performed or
authorized.

## Rollback

Rollback is source-only: remove this module/tests/document. No persistent or
external state is created by defining the execution seam.
