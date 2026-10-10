# M17.8E — Strict Unicode scalars in active Web authentication identifiers

Profiles: `MARKETPLACE_WEB_AUTH_SESSION_ESTABLISHMENT_V1` and
`MARKETPLACE_WEB_AUTH_ED25519_PROOF_PROVIDER_V1`.

## Reproduced issue

The three active Web authentication URI entrypoints — browser authentication
bootstrap, session-establishment transport, and Ed25519 proof provider — were
validating identifiers using `TextEncoder` byte length and an absolute URI
regex. `TextEncoder` silently replaces an **unpaired surrogate** (malformed
UTF-16), so an invalid identity string was accepted and might be transmitted
or become part of a cryptographic transcript under different UTF-8 bytes.
The public proof-provider constructor was directly reproduced accepting lone
high and low surrogates before this source change.

## Narrow fix

Each existing `reviewedUri` rejects unpaired high or low surrogate code units
**before** UTF-8 encoding. Valid high+low surrogate pairs and valid ASCII are
accepted unchanged; no normalization, identity inference, URI rewriting,
public-key representation or change to cryptographic construction is made.
The existing maximum 2048 UTF-8 byte bound and exact identity URI regex remain
authoritative. Existing error codes are unchanged.

- Bootstrap rejects before creating the proof provider or calling session
  establishment.
- Establishment rejects before making either authentication HTTP request.
- Proof provider rejects verification methods at provider creation and checks
  the request's exact principal and method before cryptographic signing.

## Authority and scope

This is a source-only fail-closed identity input guard in existing active code.
It adds **no network** capability, new endpoint, WebCrypto algorithm, key
generation, attestation, enrollment authority, session bypass, storage,
database access, dependency, user-facing UI, runtime launch or deployment.
It does not fix any separately governed enrollment, agreement assent or
server-side URI-validation paths. The external transport and signature
capabilities already exist; for malformed identifiers the new behavior is
to reject **before** either external side effect.

## Qualification / rollback

Validate exact-head source-contract/regression suites and execute the actual
Node ESM modules with fake in-memory providers to show malformed identity
input does not invoke HTTP `fetch` or Ed25519 `sign`, valid surrogate
pairs remain accepted, original error codes remain stable, and the exact
2048-byte limit persists. Full Marketplace CI must pass on the reviewed head
before any guarded merge.

A **source-only rollback** reverts the three guarded JS modules, regression
test, and this document. No credential, runtime, PostgreSQL, payment or
public network state is changed.
