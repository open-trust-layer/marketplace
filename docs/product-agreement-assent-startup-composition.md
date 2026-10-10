# Agreement assent startup overlay

## Purpose

This source-only slice composes the reviewed Agreement-assent HTTP and ASGI
layers over one already-built authenticated Marketplace startup graph.

Profile:

    MARKETPLACE_AGREEMENT_ASSENT_STARTUP_COMPOSITION_V1

The overlay is inert. It does not replace the existing authenticated startup,
launch plan, runtime server, or localhost selection.

## Exact inputs

The composer requires:

- one exact MarketplaceAuthenticatedStartupComposition;
- the exact MarketplaceAuthenticationRuntimeInputs whose material source is
  already bound to that startup session graph;
- one exact MarketplaceAgreementAssentCandidateResolutionService;
- one exact MarketplaceAgreementAssentWorkflowService;
- reviewed signing-input carrier encoder and signature carrier decoder callables.

It first composes the Agreement HTTP overlay over authenticated_startup.http and
then composes the Agreement ASGI overlay over that exact same authenticated HTTP
object and runtime-input object.

## Identity and credential-material coherence

The result fails closed unless:

- Agreement HTTP is bound to authenticated_startup.http;
- Agreement ASGI is bound to authenticated_startup.http;
- Agreement ASGI is bound to the exact Agreement HTTP composition;
- Agreement ASGI retains the exact supplied runtime-input object;
- the ASGI Marketplace handler is the exact Agreement HTTP adapter.

The Agreement ASGI layer independently verifies that challenge/session-token
generation remains bound to the supplied credential-material source and that
the ASGI clock remains bound to the supplied reviewed clock.

## No new runtime consumption

This overlay does not sample the clock, generate challenge/session material,
resolve an Agreement candidate, prepare or verify a proof, store assent
evidence, evaluate formation, handle an HTTP request, initialize the
application, or start a server.

The pre-existing authenticated startup may already have consumed its one
reviewed authentication-time sample when it was built. This overlay adds no new
runtime-input consumption.

## Selection boundary

This PR deliberately does not change MarketplaceAuthenticatedStartupComposition,
MarketplaceAuthenticatedLoopbackLaunchPlan, runtime-server validation, the
reference authenticated launch, or tools/marketplace_localhost.py.

Therefore normal authenticated localhost remains on the pre-existing
authenticated ASGI graph. A later source slice must explicitly select this
overlay before Agreement endpoints can become reachable in that launch path.

## Non-scope

No localhost execution, deployment, database migration, provider mutation,
trust-anchor/key mutation, browser/WebCrypto execution, Agreement signing,
Agreement publication, payment, settlement, escrow, fulfillment, ownership
transfer, or public-network activity is performed or authorized by this slice.

## Rollback

Rollback is source-only: remove this additive startup overlay. No external or
durable state is created by composing it.
