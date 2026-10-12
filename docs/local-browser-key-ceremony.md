# Local browser-owned seller/buyer key ceremony preview

Tracks authenticated PostgreSQL localhost acceptance [#525](https://github.com/open-trust-layer/marketplace/issues/525).

**Purpose:** To bind newly generated **non-extractable browser private keys** to freshly signed **public-key** test provisioning (provided by `tools/marketplace_local_two_party_provisioning.py`), the seller and buyer must first create keys in two real browser contexts before the authenticated server starts. The same two live pages must survive the switch to the authenticated server; a reload destroys their key objects. This preview solves only that handoff problem—not database access, authentication verification, application startup, evidence acceptance or production hosting.

## Safety and scope

The preview serves only the exact current checkout's `web/index.html`, `web/app.js`, `web/styles.css` and pinned ES modules, all under **IPv4 `127.0.0.1`**. No directory listing, rewrite, path traversal, query-string alias, API response or stateful endpoint. Requests for `/api/...` return 404. All POST/PUT/PATCH/DELETE/OPTIONS return 405. No database, credentials, sessions, or key material is read by the preview. It sets no-store and restrictive browser response headers.

The preview must bind **the exact host and port intended for the authenticated runtime**, by default `127.0.0.1:18080`. **Do not** use a preview on `18081` then switch browsers to `18080`: the browser origin changes and keys cannot be transferred. In the existing Windows evaluator, port 18080 is already occupied by an older Marketplace service. This tool will **fail closed** on that conflict; it does not authorize stopping, restarting or replacing that service. Do not use an existing service's browser page or stale bundle as a substitute for fresh source provenance.

## Inert preflight before touching a socket

From a **clean, exact reviewed Marketplace** checkout (with all static assets from the same commit), run:

```powershell
python -m tools.marketplace_local_browser_key_ceremony --preflight-static-assets
```

This checks only bounded local static asset bytes. A result of `LOCAL_BROWSER_KEY_CEREMONY_ASSETS_PRESENT` does not establish port availability, browser functionality, an authenticated lease or runtime authority. Confirm exact source, pinned OLP, reviewed dependencies and the separate runtime authorization for #525 independently.

## Explicit loopback execution: only when port is freely allocated

```powershell
python -m tools.marketplace_local_browser_key_ceremony `
  --port 18080 `
  --execute-browser-key-ceremony EXECUTE_MARKETPLACE_LOCAL_BROWSER_KEY_CEREMONY_V1
```

The tool starts only after the exact explicit acknowledgment and binds only `127.0.0.1`; occupied ports return `LOOPBACK_BIND_UNAVAILABLE`. No alternate interface or public binding option exists.

Open **two independent browser contexts** (e.g. separate seller and buyer windows) to the **exact same** `http://127.0.0.1:18080/` origin. In each context, select **Load local authentication** and **Generate authentication key**. Confirm both show different `mkpk1_` public keys. Use only the public browser key carriers as inputs to the [local two-party signed provisioning tool](local-two-party-signed-provisioning.md); never extract, copy, log or transmit either browser private key, or reuse expired test bundles. The tool fixes the corresponding seller/buyer principal and verification-method names in its documentation.

Run the real signature/lease preflight against the **new** bundle. Also verify approved isolated PostgreSQL access, full inert fulfillment-completion graph composition and the exact host/port; the static preview provides **none** of these results.

**Handoff:** After both pages have their public keys, keep both pages open and do **not** navigate, reload, close or reset authentication. Stop **only this preview foreground process** cleanly with Ctrl+C; confirm port 18080 is released. Separately launch the authorized, already-preflighted authenticated fulfillment-completion runtime on the **same exact** `127.0.0.1:18080` origin. In each existing open page, enter the fixed principal and verification-method value corresponding to its previously created key, then establish the authenticated session. If either context loses its in-memory private key, terminate the test; create a **new** signed short-lived bundle from newly generated browser public keys instead of faking/reusing identity bindings.

Once both real identities are authenticated, complete and document the entire listing → proposal → acceptance → Agreement formation → explicit **Publish Agreement** → seller **Claim delivery complete** for `seller-delivery` / `CLAIMED_COMPLETE_PERFORMANCE` flight. Run the non-secret Evidence V1 offline validator. Neither preview success nor signed provisioning equals that acceptance.

**Boundary:** This preview is test-only, never payment/settlement or production identity activation. Nothing here authorizes modifying Johnny 5 PostgreSQL on 5432, the older Marketplace service on 18080, production network exposure, trust-anchor replacement or bypassing a credential/SQL tool safety check. If these environmental gates remain blocked, leave #525 open and record only non-secret blocker codes.
