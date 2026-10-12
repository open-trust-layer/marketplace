# Local browser-owned seller/buyer key ceremony preview

Tracks authenticated PostgreSQL localhost acceptance [#525](https://github.com/open-trust-layer/marketplace/issues/525).

**Purpose:** To bind newly generated **non-extractable browser private keys** to freshly signed **public-key** test provisioning (provided by `tools/marketplace_local_two_party_provisioning.py`), the seller and buyer must first create keys in two real browser contexts before the authenticated server starts. The same two live pages must survive the switch to the authenticated server; a reload destroys their key objects. This preview solves only that handoff problem—not database access, authentication verification, application startup, evidence acceptance or production hosting.

## Safety and scope

The preview serves only the exact current checkout's `web/index.html`, `web/app.js`, `web/styles.css` and pinned ES modules, all under **IPv4 `127.0.0.1`**. No directory listing, rewrite, path traversal, query-string alias, API response or stateful endpoint. Requests for `/api/...` return 404. All POST/PUT/PATCH/DELETE/OPTIONS return 405. No database, credentials, sessions, or key material is read by the preview. It sets no-store and restrictive browser response headers.

The preview must bind **the exact host and port intended for the authenticated runtime**. Both reviewed command-line interfaces accept an explicit `--port`; their defaults/examples do **not** reserve an address. In the Windows evaluator an older Marketplace service occupies `127.0.0.1:18080`, so the example below instead selects **`127.0.0.1:18480`**, previously observed without a listener but **not reserved or guaranteed available**. Verify port availability immediately before execution; if unavailable, select a different free **single** loopback port for **both** preview and authenticated runtime. Do **not** use a preview on one port and switch to a different runtime port: the browser origin changes and the private-key objects cannot be transferred. A port conflict fails closed; it does not authorize stopping, restarting, or replacing another service. Never reuse an existing service's browser page or expired bundle as a substitute for fresh identities.

## Inert preflight before touching a socket

From a **clean, exact reviewed Marketplace** checkout (with all static assets from the same commit), run:

```powershell
python -m tools.marketplace_local_browser_key_ceremony --preflight-static-assets
```

This checks only bounded local static asset bytes. A result of `LOCAL_BROWSER_KEY_CEREMONY_ASSETS_PRESENT` does not establish port availability, browser functionality, an authenticated lease or runtime authority. Confirm exact source, pinned OLP, reviewed dependencies and the separate runtime authorization for #525 independently.

## Explicit loopback execution: only when port is freely allocated

```powershell
python -m tools.marketplace_local_browser_key_ceremony `
  --port 18480 `
  --execute-browser-key-ceremony EXECUTE_MARKETPLACE_LOCAL_BROWSER_KEY_CEREMONY_V1
```

The tool starts only after the exact explicit acknowledgment and binds only `127.0.0.1`; occupied ports return `LOOPBACK_BIND_UNAVAILABLE`. No alternate interface or public binding option exists.

Open **two independent live browser contexts** (e.g. separate seller and buyer windows or profiles) to the **exact same** `http://127.0.0.1:18480/` origin. In each, click **Load local authentication**, then **Generate authentication key**. The Web form is labeled *Seller authentication* in the current interface, but the second independent context will be the **buyer**; do not put the seller's identity into both. Confirm that they show two **different** `mkpk1_` public keys. Use **only** those public browser key carriers as the seller/buyer inputs to the [local two-party signed provisioning tool](local-two-party-signed-provisioning.md); never extract, copy, log, or transmit either browser private key, or reuse expired test bundles. The signer fixes the corresponding seller/buyer principals and verification-method names in its documentation. The preview intentionally cannot satisfy API requests, so its initial background synchronization may report unavailable until the authenticated runtime is started; this is **not** a successful user session.

Run the real signature/lease preflight against the **new** bundle. Also verify approved isolated PostgreSQL access, full inert fulfillment-completion graph composition and the exact host/port; the static preview provides **none** of these results.

**Handoff:** After both pages have their public keys, keep both pages open and do **not** navigate, reload, close, or reset authentication. Stop **only the preview foreground process that you started** with Ctrl+C; confirm port `18480` was released without stopping any other service. Using the **same port** and the existing approved provisioning/isolated database configuration, first run the reviewed **inert** `--preflight-fulfillment-completion-localhost` gate, then launch the separately authorized `--execute-fulfillment-completion-localhost` runtime on **the same** `127.0.0.1:18480` origin. In each **already open** page, enter the fixed principal and verification-method URI corresponding to that page's original key, then establish the authenticated session. Do not refresh those pages even after the new server binds the same port. Once authentication succeeds, click **Sync now** to retry the preview's intentionally failed initial synchronization before starting listing/proposal actions. If either context loses its in-memory private key, terminate the test; create a **new** signed short-lived bundle from newly generated browser public keys instead of fabricating or reusing identity bindings.

The pinned authenticated-run command in [MARKETPLACE_MVP_ACCEPTANCE.md](../MARKETPLACE_MVP_ACCEPTANCE.md) must therefore be invoked with `--port 18480` instead of that document's example `--port 18080` **for this evaluator**, for both the inert graph preflight and authorized runtime. This is a **port parameter adjustment only**: do not change the exact reviewed execution opt-in token, selected mode, trust identity bundle, OLP pin, or PostgreSQL boundaries. If another port was chosen, substitute that exact one everywhere. The signed trust bundle remains short-lived and must still verify at handoff.

Once both real identities are authenticated, complete and document the entire listing → proposal → acceptance → Agreement formation → explicit **Publish Agreement** → seller **Claim delivery complete** for `seller-delivery` / `CLAIMED_COMPLETE_PERFORMANCE` flight. Run the non-secret Evidence V1 offline validator. Neither preview success nor signed provisioning equals that acceptance.

**Boundary:** This preview is test-only, never payment/settlement or production identity activation. Nothing here authorizes modifying Johnny 5 PostgreSQL on 5432, the older Marketplace service on 18080, production network exposure, trust-anchor replacement or bypassing a credential/SQL tool safety check. If these environmental gates remain blocked, leave #525 open and record only non-secret blocker codes.
