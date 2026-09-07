# M17.5G — Bounded CSPRNG credential-material source qualification

Profile: `MARKETPLACE_APPLICATION_CREDENTIAL_MATERIAL_SOURCE_V1`

Exact implementation baseline: `042b1c09e9c024d527c10d169b7cc2c1dc48f340`

Risk classification: **HIGH security/privacy source capability**. This milestone introduces the first production-suitable source of authentication challenge/session-token bytes, but does not select that source into any runtime or client composition.

## Scope

M17.5G is additive-only and consists of exactly:

- `src/marketplace/application/auth_material.py`
- `tests/test_m17_5g_auth_material.py`
- `tests/test_m17_5g_auth_material_artifacts.py`
- `docs/m17-5g-auth-material.md`

No existing Marketplace source, dependency manifest, workflow, configuration, Web source, Android source, runtime entry point, database path, or service definition is modified.

## Concrete authority

`MarketplaceCredentialMaterialSource` is a stateless implementation of the already-reviewed M17.5D `CredentialMaterialSource` shape.

It uses the Python standard-library OS CSPRNG via `secrets.token_bytes` and provides only two operations:

- `challenge_bytes()` returns exact 32-byte challenge material;
- `session_token_bytes()` returns exact 32-byte session-token material.

Every successful method call performs a fresh CSPRNG request. The adapter retains no generated material after return and has no instance state.

There is no deterministic seed, timestamp/PID/counter derivation, UUID substitution, hash-expansion substitute, retry loop, alternate entropy provider, or other fallback. In particular, there is **no fallback PRNG**.

If the underlying CSPRNG raises, the exception propagates from this narrow source without retry or fallback. If the provider seam returns a malformed test value, the adapter fails closed with a stable local error that does not include the material. The existing M17.5D HTTP adapter catches material-source failures and maps them to stable non-reflective `AUTH_MATERIAL_UNAVAILABLE` behavior.

## Threat and failure boundary

M17.5G owns only concrete unpredictable material generation and exact output shape. Existing M17.5B/D contracts continue to own:

- one-use challenge registration and consumption;
- challenge expiry;
- collision rejection;
- outstanding-challenge and active-session capacity bounds;
- digest-only server session retention;
- idle and absolute session lifetimes;
- principal-binding decisions;
- stable HTTP failure mapping.

This qualification makes no statistical certification claim about operating-system entropy beyond the Python standard-library/OS CSPRNG contract. It adds no entropy health test and does not expose or persist generated production material for testing.

## Explicit non-authority

M17.5G grants:

- no private-key handling: no key generation, import, storage, custody, browser-wallet access, Android Keystore access, or equivalent key authority;
- no proof/signature creation;
- no real proof verification;
- no principal-binding policy change;
- no resolver/provider/network activity;
- no OAuth, OIDC, password, JWT, cookie, callback, redirect, or cross-origin credential capability;
- no persistence of challenge, session-token, credential, or generated material;
- no logging, telemetry, cache, file, environment-variable, database, or remote-provider side effect;
- no runtime activation and no selection by `tools/marketplace_localhost.py` or any ASGI runtime composition;
- no Web authentication/login selection;
- no Android authentication/login selection and no Android build, Gradle, install, emulator, adb, or device action;
- no PostgreSQL access, schema/data mutation, configuration/secret mutation, or service restart;
- no production/public-network activity;
- no deployment, publishing, or distribution.

The concrete source remains unselected after this milestone. Merely importing the module does not issue a challenge or session token; material is generated only when one of its two explicit methods is called by a future separately authorized composition.

## Validation

Focused qualification:

```text
python -m unittest \
  tests.test_m17_5g_auth_material \
  tests.test_m17_5g_auth_material_artifacts
```

The tests verify exact output type/size, independent fresh calls, malformed-provider fail-closed behavior, underlying CSPRNG exception propagation without retry/fallback, existing HTTP non-reflective failure mapping, statelessness, no runtime/client selection, no dependency widening, and the documented authority boundary.

The repository's existing `Marketplace conformance` workflow remains the authoritative exact-head acceptance gate and already discovers all `test_*.py` tests. No workflow modification is required.

Existing M17.5B-F security/conformance suites must remain green.

## Rollback and blast radius

Rollback is a **source-only rollback**: revert the exact M17.5G merge if a later merge is separately authorized.

Because this milestone adds only one stateless, unselected generator plus tests/documentation, rollback requires no credential revocation, session cleanup, database migration, provider administration, service restart, configuration rollback, Android cleanup, network action, or deployment action.

Blast radius is limited to the new unselected credential-material module and its qualification artifacts.

## Later decision gate

The next authentication milestone must separately review the exact proof/signature format and private-key custody boundary before any real client proof creation, proof verifier, resolver/provider policy, runtime composition, Web/Android login activation, or localhost/device live authentication is authorized.

M17.5G establishes only the server-side CSPRNG material source. It does not make the Marketplace authentication path live.
