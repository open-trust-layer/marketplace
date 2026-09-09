# Marketplace M17.5R — Static authenticated ASGI composition

Profile: `MARKETPLACE_APPLICATION_AUTH_ASGI_COMPOSITION_V1`

Baseline: exact merged-green Marketplace `main`
`7073f432654f4bc064ce6c752ced9969f2104c98`.

Authority: owner-authorized **HIGH** authentication-routing capability recorded
on Issue #294. Implementation is restricted to the exact six-file scope below.

## Purpose

M17.5P freezes one coherent authenticated HTTP graph. M17.5Q selects the exact
reviewed credential-material source and wall clock without consuming either.

M17.5R binds those exact predecessor objects to the already-reviewed
`MarketplaceSessionEstablishmentAsgiHttpAdapter`. It creates an inert ASGI
object graph only. It does not select or execute any launch/runtime path.

## Exact composition

`compose_marketplace_authenticated_asgi(*, http, runtime_inputs)` accepts only:

1. one exact M17.5P `MarketplaceAuthenticatedHttpComposition`;
2. one exact M17.5Q `MarketplaceAuthenticationRuntimeInputs`.

Before constructing ASGI it verifies that both material callables retained by
M17.5P session HTTP are bound to the exact M17.5Q material-source instance.

It then constructs exactly one existing
`MarketplaceSessionEstablishmentAsgiHttpAdapter` with:

- `site=http.application.site`;
- `marketplace_http=http.application_http`;
- `auth_http=http.session_http`;
- `now=runtime_inputs.clock.now`.

The returned `MarketplaceAuthenticatedAsgiComposition` is frozen/slotted and
retains the exact M17.5P composition, exact M17.5Q inputs, and exact ASGI object.

No second application, authentication, material, clock, HTTP, or ASGI graph is
created.

## Identity and coherence invariant

The composition proves:

- `asgi._site is http.application.site`;
- `asgi._marketplace_http is http.application_http`;
- `asgi._auth_http is http.session_http`;
- the bound `asgi._now` owner is the exact M17.5Q clock;
- both session material bound-method owners are the exact M17.5Q material source.

A mismatch fails closed before an ASGI object is returned.

## Consumption boundary

Composition performs **zero credential-material calls** and
**zero wall-clock reads**.

It also performs **zero request handling**, zero HTTP handler calls, zero ASGI
calls, zero application initialization, and zero store/provider/runtime calls.

Credential material and wall-clock time can be consumed only later by an
explicit caller invoking the composed ASGI object.

## Failure boundary

M17.5R-owned validation and constructor failures use one stable public error:

`authenticated Marketplace ASGI composition failed`

Raw exception text, credentials, session tokens, principals, proof content,
verification methods, trust material, filesystem paths, environment values,
host/port values, and provider details are not reflected.

Composition is atomic and returns no partially usable object on failure.

## ASGI behavior ownership

M17.5R does not reimplement ASGI parsing, bearer handling, body limits, clock
validation, authentication routing, or HTTP response conversion.

Those behaviors remain owned by the existing reviewed
`MarketplaceSessionEstablishmentAsgiHttpAdapter`.

Tests may invoke the inert composition deterministically after construction to
prove that ordinary site delivery reads no authentication clock and an
authentication/API request reads the exact M17.5Q clock once. Such tests do not
select launch/runtime authority.

## External-I/O and activation boundary

M17.5R performs no filesystem access, environment lookup, database access,
socket/HTTP/DNS/network activity, subprocess, resolver/provider acquisition,
configuration loading, persistence/cache/background work, or application
initialization.

There is **no launch** selection and **no runtime** activation in this profile.

`asgi.py`, `launch.py`, `runtime_server.py`, provider code, and executable
entry points remain unchanged and do not import or select M17.5R.

Calling the composition function alone does not generate a challenge, generate
a session token, read wall-clock time, handle a request, authenticate a client,
select a host/port, bind a socket, or start a server.

## exact six-file scope

Added:

1. `src/marketplace/application/auth_asgi_composition.py`
2. `tests/test_m17_5r_auth_asgi_composition.py`
3. `tests/test_m17_5r_auth_asgi_composition_artifacts.py`
4. `docs/m17-5r-auth-asgi-composition.md`

Modified only:

5. `tools/package_artifact_gate.py`
6. `tests/test_package_artifact_gate.py`

No predecessor authentication source, `auth_session_asgi.py`, `asgi.py`,
`launch.py`, `runtime_server.py`, provider/runtime source, dependency metadata,
workflow, repository audit, Web, Android, PostgreSQL, configuration, or service
file is changed.

## Qualification
Qualification proves exact profile/types, predecessor identity retention,
material-source coherence, exact ASGI member identity, exact clock ownership,
stable mismatch failure, zero consumption at composition, deterministic
post-composition routing behavior, no runtime entry-point selection, and package
membership.

Predecessor M17.5B-Q conformance remains part of the full Marketplace acceptance
gate.

## Threat boundary

M17.5R addresses:

- authenticated ASGI wired to a different application/site graph;
- session and protected-write routing using different HTTP graphs;
- an independently selected authentication clock;
- session material differing from the reviewed M17.5Q source;
- credential generation or clock reads caused merely by composition;
- alternate/fallback ASGI adapters bypassing the reviewed graph;
- convenience composition silently acquiring launch/runtime authority.

It deliberately defers trust/evidence provisioning, authenticated loopback
launch-plan selection, runtime replacement/rollback, trust/evidence rotation,
revocation/freshness administration, network acquisition, client private-key
custody/signing, and live authentication acceptance.

## Rollback

Rollback is **source-only rollback**: revert the exact eventual M17.5R merge.

Because M17.5R only defines and composes inert process-local objects and does
not select a launch/runtime entry point, rollback requires no session cleanup,
key revocation, trust-store administration, provider action, database migration,
service restart, Android cleanup, configuration rollback, port cleanup, or
external-data mutation.

## Explicit non-authority

M17.5R does not authorize trust-anchor/evidence provisioning, authentication
request execution during composition, credential generation during composition,
wall-clock reads during composition, localhost/host/port selection, launch-plan
replacement, server execution, runtime/client authentication activation, live
authentication, snapshot/composition replacement, rotation/revocation/expiry
administration, resolver/provider acquisition, network activity, persistence,
cache/background work, production private-key generation/import/export/storage/
custody/use/signing, Android action, PostgreSQL/config/service mutation,
production/public-network activity, deployment, publishing, distribution, or
merge.

## Later gates

Only separately authorized later milestones may select:

1. a bounded startup provisioning source for canonical N/L bytes;
2. an authenticated loopback launch plan using exact M17.5R;
3. immutable runtime composition replacement/rollback and trust lifecycle policy;
4. any bounded evidence acquisition provider;
5. bounded live authentication and client signing/custody policy.
