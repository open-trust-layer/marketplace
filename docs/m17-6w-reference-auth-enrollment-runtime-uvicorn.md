# Product M17.6W — Reference enrollment Uvicorn runtime selection

Profile: `MARKETPLACE_REFERENCE_AUTHENTICATION_ENROLLMENT_UVICORN_RUNTIME_V1`

Risk: **HIGH security/privacy** source-only concrete-provider selection.

## Purpose

M17.6V accepts an exact M17.6U enrollment graph plus an injected server provider
and exact M17.6N execution token.

M17.6W adds the smallest reviewed reference provider selection:

`U → W → V → N`

W validates the exact existing execution token, accepts only the exact U result
type, constructs exactly one already-reviewed lazy
`UvicornLoopbackServerProvider`, and delegates exactly once to V.

## Exact existing execution token

W defines no new execution token.

It imports and reuses:

`EXECUTE_ONE_AUTHENTICATION_ENROLLMENT_MARKETPLACE_LOOPBACK_SERVER`

Wrong token type or value fails before provider construction or V delegation.
The exact caller token is passed unchanged to V.

## Provider selection boundary

W selects only the already-reviewed `UvicornLoopbackServerProvider`.

It performs no dynamic provider discovery, fallback, retry, configuration lookup,
environment lookup, or launch-plan rebuilding.

Provider construction itself is inert: the provider lazily imports Uvicorn only
inside its existing `run(...)` method.

## Qualification boundary

In M17.6W qualification, **real Uvicorn is never run**.

Tests patch provider selection and/or V delegation. A dedicated inert-constructor
test uses the real provider constructor while forcing any Uvicorn import or
socket construction to fail if attempted.

No test invokes the real provider `run(...)` method.

## Failure boundary

M17.6W-owned failure collapses to:

`reference authentication enrollment Uvicorn runtime failed`

Provider-constructor and V failures are not reflected and are never retried.

## Non-selection boundary

M17.6W remains **unselected**.

M17.6U, M17.6V, existing startup/launch code, CLI/services, Web, Android,
configuration, and Moon Company runtime/control-plane do not import or invoke W.

Therefore this source milestone does not activate a listener, open a socket,
perform public-network activity, provision a key, mutate trust, or deploy a
runtime.

## Explicit non-authority

This milestone does not authorize operational invocation of W against the real
provider, production runtime activation, external key custody/provisioning,
HSM/vault/keyring operations, browser/Android activation, PostgreSQL/config
mutation, service changes, publishing, or deployment.

## Moon Company boundary

W is a replaceable Moon Commerce reference provider selector only.

It grants Moon Company no runtime execution authority, provider administration,
key custody, identity/policy administration, deployment authority, or
production control.

## Rollback

**source-only rollback:** revert the exact M17.6W merge.

Because W stays unselected and qualification does not run the real provider,
rollback requires no listener shutdown, key revocation, nonce/session cleanup,
trust-store change, database rollback, service restart, browser/device cleanup,
or deployment rollback.
