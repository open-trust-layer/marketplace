# Marketplace M17.5T - One-shot authenticated startup composition

Profile: `MARKETPLACE_APPLICATION_AUTH_STARTUP_COMPOSITION_V1`

Baseline: exact merged-green Marketplace `main`
`eb17acb5800d61d763d115179d520ce2ec2ce191`.

Authority: owner-authorized **HIGH** trust-activation and time-binding
composition capability recorded on Issue #300. The exact six-file scope is
listed below.

## Purpose

M17.5S supplies one immutable canonical public authentication provisioning
bundle. M17.5Q supplies the reviewed credential-material source and wall clock
without consuming either. M17.5O, P, and R already define the reviewed static
authentication, authenticated HTTP, and authenticated ASGI composition layers.

M17.5T performs the smallest one-shot in-memory startup wiring across those
existing layers. It accepts already-built application, S, and Q objects, reads
the exact Q wall clock exactly once, then composes exact O -> P -> R and returns
one immutable coherent result.

It does not load provisioning from disk, compose runtime inputs, initialize the
application, handle a request, select a host or port, build a launch plan, or
execute a runtime/server/provider.

## Exact input contract

The composer accepts exactly:

1. one exact `MarketplaceApplicationComposition`;
2. one exact M17.5S `MarketplaceAuthenticationStartupProvisioning`;
3. one exact M17.5Q `MarketplaceAuthenticationRuntimeInputs`;
4. one callable `decode_record_json` already required by M17.5P;
5. one callable `record_principal` already required by M17.5P.

All exact types and callability are validated before any clock consumption.
Invalid inputs fail closed before the one authorized time sample.

## Exact composition sequence

A successful composition performs this sequence once and only once:

1. call `runtime_inputs.clock.now()` exactly once;
2. pass that exact integer with the exact S manifest and evidence to M17.5O;
3. pass the exact application, exact O result, exact Q material source, and the
   two injected HTTP callables to M17.5P;
4. pass the exact P result and exact same Q object to M17.5R;
5. return one frozen/slotted result containing the exact O, P, and R objects.

The result verifies identity coherence: P authentication is the exact O object,
and R HTTP is the exact P object. R independently retains and validates the
exact same Q object, including the exact material source and wall clock bindings.

No second or fallback clock source exists. The sampled time is not retained as a
second source of truth and is used only for the existing M17.5O trust/evidence
acceptance operation.

## Failure ordering

Failure is atomic and ordered:

- malformed input or non-callable dependency fails before the clock read;
- clock failure fails before O/P/R construction;
- O failure prevents P and R construction;
- P failure prevents R construction;
- R failure returns no partial startup composition.

All M17.5T-owned failures use one stable, non-reflective public error:

`authenticated Marketplace startup composition failed`

No trust bytes, principals, sampled time, filesystem paths, raw exception text,
provider details, credential material, host/port values, or internal identities
are reflected.

## Consumption and external-I/O boundary

M17.5T introduces exactly one clock read through the already-reviewed M17.5Q
clock. It performs zero credential-material calls. In particular it never calls
`challenge_bytes()` or `session_token_bytes()` during composition.

It also performs zero filesystem I/O because it never invokes the M17.5S loader,
zero environment/config/registry/database/network/provider I/O, zero subprocess
or resolver activity, zero persistence/cache/background work, zero private-key
or signing activity, zero request handling, and zero application initialization.

The two injected HTTP callables are checked for callability only; they are not
invoked during startup composition.

## No launch or runtime authority

M17.5T has no launch authority and no runtime authority. It does not import or
select application `asgi.py`, `launch.py`, `runtime_server.py`, server providers,
host/port metadata, executable entry points, or deployment surfaces.

The predecessor S/Q/O/P/R modules and those runtime entry points remain unchanged
and do not import or select M17.5T.

## Exact six-file scope

Added:

1. `src/marketplace/application/auth_startup_composition.py`
2. `tests/test_m17_5t_auth_startup_composition.py`
3. `tests/test_m17_5t_auth_startup_composition_artifacts.py`
4. `docs/m17-5t-auth-startup-composition.md`

Modified only:

5. `tools/package_artifact_gate.py`
6. `tests/test_package_artifact_gate.py`

No predecessor authentication source, S/Q/O/P/R source, application ASGI,
launch, runtime-server/provider, dependency metadata, workflow, repository
audit, Web, Android, PostgreSQL, configuration, or service file changes are
part of this milestone.

## Qualification

Qualification proves exact profile/types, frozen result, identity coherence,
input validation before clock consumption, exactly one clock read, exact S/Q
object flow through O/P/R, fail-closed stage ordering, stable redacted errors,
zero credential-material calls, zero injected-callable invocation, zero request
handling, zero initialization, no S loading or Q composition, no launch/runtime
selection, predecessor isolation, and package membership.

Full Marketplace conformance retains predecessor M17.5B-S coverage, repository
audit, artifact controls, and the published vector corpus.

## Threat boundary

M17.5T addresses inconsistent trust-acceptance time, duplicate/fallback clock
reads, S/Q/O/P/R graph substitution, hidden credential generation, partial graph
exposure after stage failure, and silent launch/runtime activation.

Deliberately deferred are provisioning-directory selection/loading, operator
trust-file governance, authenticated loopback host/port launch-plan selection,
application initialization, runtime replacement/rollback, trust rotation and
revocation policy, network evidence acquisition, client private-key custody and
signing, and bounded live authentication acceptance.

## Rollback

Rollback is **source-only rollback**: revert the eventual exact M17.5T merge.
Because no launch/runtime entry point selects this composition and it performs no
writes, rollback requires no trust-store mutation, session cleanup, service
restart, port cleanup, database/provider action, or external-data deletion.

## Explicit non-authority

M17.5T does not authorize provisioning-file creation/read/modification/deletion,
trust administration outside the one in-memory O composition, credential
material generation, authentication request execution, application
initialization, host/port selection, launch-plan construction or mutation,
runtime/server/provider selection or execution, environment/config/registry/
database/network intake, persistence/cache/background activity, private-key or
signing capability, Android action, PostgreSQL/config/service mutation,
production/public-network activity, deployment, publishing, distribution, or
merge.

Only a separately authorized later milestone may select this authenticated graph
into an explicit loopback launch plan or perform any runtime activation.