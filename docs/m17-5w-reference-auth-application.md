# M17.5W — Inert reference authenticated launch composition

Profile: `MARKETPLACE_REFERENCE_AUTHENTICATED_LAUNCH_V1`.

Baseline: exact merged-green `9d646ad72f9d609686e73c8de2446b353af1aa73`.

M17.5W adds one reference-layer adapter that binds an already-built reviewed
Marketplace application launch plan into the existing M17.5T/U authenticated
composition chain. It is source-only trust composition, not runtime activation.

## Contract

The adapter accepts exactly:

- an exact existing `MarketplaceApplicationLaunchPlan`;
- an exact existing M17.5S `MarketplaceAuthenticationStartupProvisioning`;
- an exact existing M17.5Q `MarketplaceAuthenticationRuntimeInputs`.

Before any clock use, it revalidates the exact launch-plan type, exact IPv4
loopback host, reviewed TCP port bounds, exact application composition type, and
the unauthenticated ASGI-to-site identity binding. It then validates exact S and
Q types.

The caller cannot inject record decoding or principal extraction. M17.5W binds
exactly the existing reference functions `decode_marketplace_application_record_json`
and `marketplace_record_issuer_principal`.

## Composition and authority ordering

After all W-owned validation succeeds, M17.5W calls M17.5T exactly once with the
original application composition, supplied S/Q objects, and those exact reference
callables. Only the existing T implementation may sample the authentication clock,
and it does so exactly once on the successful path.

M17.5W then calls M17.5U exactly once with the original launch plan's exact host
and port and the exact T result. The returned plan must keep the authenticated
ASGI adapter by identity and its startup HTTP graph must point to the original
application composition by identity.

The unauthenticated ASGI adapter is validated only as evidence that the supplied
application launch plan is coherent. It is never retained, invoked, or substituted
as the authenticated runtime adapter.

## Capability boundary

There is zero credential-material consumption. Challenge/session material methods
are not called. Provisioning is supplied in memory and is neither loaded nor
mutated. Q is supplied and is not composed by this module.

The adapter performs no application rebuilding or initialization, HTTP/ASGI request
handling, PostgreSQL connection or mutation, environment/configuration lookup,
filesystem access, provider selection, M17.5V invocation, socket/network action,
subprocess/background work, private-key/signing activity, Android action, deployment,
publishing, or distribution.

All M17.5W-owned failures normalize to one stable non-reflective error. The failure
order is application-plan/coherence validation, S validation, Q validation, T
composition/clock, then U launch composition. No partially usable authenticated
launch plan is returned on failure.

## Exact scope and activation boundary

The exact six-file scope is:

1. `src/marketplace/reference/auth_application_v1.py`
2. `tests/test_m17_5w_reference_auth_application.py`
3. `tests/test_m17_5w_reference_auth_application_artifacts.py`
4. `docs/m17-5w-reference-auth-application.md`
5. `tools/package_artifact_gate.py`
6. `tests/test_package_artifact_gate.py`

Existing M17.5S/T/U/V source, reference application builders, launch/runtime/provider
source, localhost bootstrap, dependencies, workflows, Web, Android, PostgreSQL,
configuration, services, and executable entry points remain unchanged.

No runtime activation is performed or implied. A later milestone must separately
review provisioning-directory selection, Q selection, PostgreSQL/environment and
Web-asset loading, initialization, concrete provider selection, M17.5V invocation,
real loopback execution, rollback/replacement policy, and live authentication
acceptance.

Rollback is source-only revert of a separately authorized merge; this milestone
creates no persistent or runtime state.
