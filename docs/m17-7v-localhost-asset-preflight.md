# M17.7V/W — Exact-checkout localhost asset preflight

Profile: `MARKETPLACE_LOCALHOST_STATIC_ASSET_PREFLIGHT_V1`

Linked acceptance: #510.

## Motivation

The live Windows Marketplace on `127.0.0.1:18080` answered HTTP 200 but served the older `39153a27` browser asset bundle while the accepted `main` release was `edd822b6`. The stale page did not include the explicit M17.7U evidence export control, and the old server returned an error for the authenticated-flight evidence JavaScript module.

A successful GitHub conformance run and a clean newer checkout do **not** prove that the running service uses that exact checkout. M17.7V added a small, read-only fail-closed asset parity check for the release flight. M17.7W extends that check from seven files to **all 14 currently served public Web assets**. Neither change activates any new server functionality.

## Operator usage

From the *exact expected release checkout* (and using a Python 3.11+ interpreter):

```powershell
python tools/marketplace_localhost_asset_preflight.py --port 18080 --expected-main-sha edd822b6574230ddd846985708a2011ae8cb8634
```

Replace the expected SHA with the **freshly verified full merged-main SHA** when the target release changes. The check first requires that the current Git checkout has precisely that SHA **and that none of the 14 served tracked assets has staged or unstaged modifications relative to HEAD**. It then performs bounded unauthenticated static GETs on **`127.0.0.1` only**, without proxy or redirect following, for:

- `/` ↔ `web/index.html`
- `/app.js` ↔ `web/app.js`
- `/styles.css` ↔ `web/styles.css`
- `/client_session.js` ↔ `web/client_session.js`
- `/auth_establishment.js` ↔ `web/auth_establishment.js`
- `/auth_ed25519_proof_provider.js` ↔ `web/auth_ed25519_proof_provider.js`
- `/auth_ed25519_key_creation.js` ↔ `web/auth_ed25519_key_creation.js`
- `/agreement_ed25519_assent_provider.js` ↔ `web/agreement_ed25519_assent_provider.js`
- `/agreement_assent_client.js` ↔ `web/agreement_assent_client.js`
- `/proposal_acceptance_client.js` ↔ `web/proposal_acceptance_client.js`
- `/agreement_publication_client.js` ↔ `web/agreement_publication_client.js`
- `/fulfillment_completion_client.js` ↔ `web/fulfillment_completion_client.js`
- `/authenticated_local_flight_evidence.js` ↔ `web/authenticated_local_flight_evidence.js`
- `/auth_bootstrap.js` ↔ `web/auth_bootstrap.js`

A source-level regression reads (but does not import or execute) the localhost bootstrap's reviewed `_AUTH_WEB_MODULE_ASSETS` mapping and verifies that this preflight's exact 14-route list is identical. Future additions to that mapping require updating this preflight before CI can pass.

The checker compares SHA-256 digests over **exact raw bytes**. Each response is bounded to 2 MiB with a 5-second request timeout. It sends no auth headers, cookies, credentials, request body, or application mutation. It neither prints nor saves served response bodies.

On parity, output is `status=PASS host=127.0.0.1 port=18080 checked_assets=14 public_static_only=true runtime_activated=false`.

Missing routes, HTTP failure, redirect, non-identity content encoding, oversize content, a stale or locally modified checkout asset, or any byte mismatch produces a stable non-zero `status=FAIL` outcome and the public asset path only. The check must fail rather than silently fallback to an old runtime.

## Acceptance boundary

A PASS confirms **only** that all 14 reviewed, allowlisted public static responses match their exact local checkout files at check time. It does not independently establish server/process origin, future changes to the asset allowlist without updating this check, active browser cache state, database readiness, correct PostgreSQL schema, authenticated sessions, actual two-party workflow, Agreement publication, seller delivery completion, or live-runtime acceptance.

Use this as one pre-browser gate **after** any separately authorized, Marketplace-only localhost cutover. Continue to require the separately authorized two-party flight, M17.7U explicit evidence download, and the M17.7R offline evidence validator.

## Isolation and non-authority

This additive source-only utility invokes no privileged operation. It does not stop or start any process, bind a listener, read environment credentials, access PostgreSQL, generate a key, sign, write to the server, provision identities, follow redirects, use network proxies, access public network endpoints, install dependencies, or publish/pay/settle/deploy. The only network reads are fixed unauthenticated GETs to the exact IPv4 loopback host and operator-provided port. The local Git SHA check uses a bounded read-only subprocess.

**Risk for source change:** LOW, with read-only localhost diagnostic network access on deliberate invocation. **Runtime cutover and live flight:** remain separately authorized HIGH capability boundaries.

## Recovery

There are no side effects to roll back from invoking the checker. If it fails, stop the flight before authentication or publication and re-verify the exact Marketplace process tree, port, served assets, and approved runtime provisioning. Do not stop every Python process or the separate SupportBot listener bound to a different interface.

Source-only rollback: revert this narrow preflight PR. No runtime or database rollback is introduced.
