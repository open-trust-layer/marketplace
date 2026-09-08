# Marketplace M17.5Q — Reviewed authentication runtime inputs

Profile: `MARKETPLACE_APPLICATION_AUTH_RUNTIME_INPUTS_V1`

Baseline: exact merged-green Marketplace `main`
`cd6eaf2f94721e9b3a71ec756ceb4755460d6670`.

Authority: owner-authorized **HIGH** authentication runtime-input selection
capability recorded on Issue #292. Implementation is restricted to the exact
six-file scope below.

## Purpose

M17.5P freezes a coherent authenticated HTTP graph but deliberately leaves two
operational inputs unselected:

1. credential-material generation;
2. authentication wall-clock time.

M17.5Q selects only the already-reviewed M17.5G OS-CSPRNG material source and a
small standard-library wall-clock adapter. It does not connect either input to
ASGI, launch, localhost, a server, or any runtime entry point.

## Exact composition

`compose_marketplace_authentication_runtime_inputs()` constructs exactly:

1. one exact existing `MarketplaceCredentialMaterialSource`;
2. one exact `MarketplaceAuthenticationUnixClock`;
3. one frozen/slotted `MarketplaceAuthenticationRuntimeInputs` containing both.

Composition performs **zero credential-material calls** and **zero wall-clock
reads**. It does not call `challenge_bytes()`, `session_token_bytes()`, or
`MarketplaceAuthenticationUnixClock.now()`.

## Clock semantics

`MarketplaceAuthenticationUnixClock.now()` reads Python's standard-library
`time.time_ns()` exactly once per explicit call and reduces it to whole Unix
seconds by integer floor division by `1_000_000_000`.

The result must be a non-negative exact `int`. A provider exception, bool,
negative value, or other malformed result fails closed through one stable
non-reflective `MarketplaceAuthenticationRuntimeInputError`.

M17.5Q keeps no monotonicity cache or second time-policy state machine. Existing
authentication challenge/session state remains responsible for rejecting clock
movement before recorded issuance/use state.

There is no timezone parsing, datetime formatting, NTP, network synchronization,
skew correction, retry, sleep, scheduler, or background clock activity.

## Credential-material semantics

M17.5Q reuses the existing M17.5G `MarketplaceCredentialMaterialSource`
unchanged. That source uses the standard-library OS CSPRNG and returns exact
32-byte challenge/session material only after an explicit later method call.

M17.5Q adds no deterministic production generator, custom PRNG, seed/state,
private-key generation, signing, key custody, serialization, persistence, or
credential logging.

## Failure boundary

M17.5Q-owned source/clock validation failures use one stable public error:
`authentication runtime input is invalid or unavailable`.

Raw OS/provider exception text and authentication material are never reflected.
Composition is atomic and returns no partially usable bundle on failure.

## Activation and external-I/O boundary

M17.5Q performs no filesystem access, environment lookup, database access,
socket/HTTP/DNS/network activity, subprocess, resolver/provider acquisition,
configuration loading, persistence/cache/background work, ASGI selection,
launch-plan mutation, or runtime/server execution.

There is **no ASGI** activation and **no runtime** activation in this profile.
Authenticated ASGI, launch, localhost and runtime entry points remain unchanged
and do not import or select M17.5Q.

Calling the composition function alone generates no challenge, creates no
session token, reads no clock, handles no request, and performs no authentication.

## exact six-file scope

Added:

1. `src/marketplace/application/auth_runtime_inputs.py`
2. `tests/test_m17_5q_auth_runtime_inputs.py`
3. `tests/test_m17_5q_auth_runtime_inputs_artifacts.py`
4. `docs/m17-5q-auth-runtime-inputs.md`

Modified only:

5. `tools/package_artifact_gate.py`
6. `tests/test_package_artifact_gate.py`

No auth predecessor source, authenticated HTTP/ASGI source, launch/runtime
source, dependency metadata, workflow, repository-audit, Web, Android,
PostgreSQL, configuration, or service file is changed.

## Qualification

Tests prove exact profile/types, immutable bundle identity, zero consumption at
composition, nanosecond-to-whole-second conversion, stable malformed/exceptional
clock failures, and exact M17.5G material bounds under a test-only patched OS
token primitive.

## Threat boundary

M17.5Q addresses:

- ambiguous or hidden production credential-material selection;
- accidental substitution of deterministic/weak production material;
- ambiguous authentication wall-clock selection;
- credential or clock consumption merely from object composition;
- convenience factories silently acquiring ASGI/launch/runtime authority;
- a second mutable time-policy state machine diverging from auth state.

It deliberately defers trust/evidence provisioning, authenticated ASGI routing,
launch-plan selection, runtime replacement/rollback, trust/evidence rotation or
revocation, network acquisition, client private-key custody/signing, and live
authentication acceptance.

## Rollback

Rollback is **source-only rollback**: revert the exact eventual M17.5Q merge.

Because composition only selects inert process-local objects and performs zero
runtime-input consumption, rollback requires no session cleanup, key revocation,
trust-store administration, provider action, database migration, service restart,
Android cleanup, configuration rollback, or external-data mutation.

## Explicit non-authority

M17.5Q does not authorize trust-anchor/evidence provisioning, authentication
request handling, credential generation at composition time, ASGI/localhost/
launch/runtime/client authentication activation, live authentication, private-key
or signing activity, resolver/provider acquisition, network activity, persistence,
cache/background work, Android action, PostgreSQL/config/service mutation,
deployment, publishing, distribution, production/public-network activity, or
merge.

## Later gates

Only a separately authorized later milestone may compose exact M17.5P plus exact
M17.5Q into authenticated ASGI. Provisioning, launch/runtime selection, trust
replacement/rotation, network acquisition, and live authentication remain
separate gates.

## Qualification invariants

Composition invariant: zero wall-clock reads.
Clock output invariant: whole Unix seconds.
