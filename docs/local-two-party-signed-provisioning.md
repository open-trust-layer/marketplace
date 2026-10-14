# Two-party local evaluator: signed short-lived test provisioning

Tracking: [authenticated PostgreSQL localhost flight #525](https://github.com/open-trust-layer/marketplace/issues/525).

**Scope:** this is a separately invoked operator tool for a disposable, **non-production, local-only** authentication trust bundle. It addresses the `LEASE_EXPIRED` finding for the existing evaluator bundles without modifying, renewing, copying, or bypassing any of those old bundles. It does **not** run the application, start or connect PostgreSQL, generate browser private keys, authenticate either actor, or imply the acceptance flight passed.

## Inputs and the browser-key boundary

The existing Web UI's **Generate authentication key** action creates a non-extractable Ed25519 private key in the current page and shows its **browser public key** (prefix `mkpk1_`) and matching evidence public key (`mkp1_`). Generate **two different keys** in separate seller/buyer browser contexts that will remain alive throughout the flight. The browser private keys must never be copied or exported. These contexts must use the **same intended localhost origin** and retain their key objects: reloading or navigating discards the in-memory keys. The merged [explicit local browser-key ceremony preview](local-browser-key-ceremony.md) now supplies a static, loopback-only pre-auth page at the **exact future authenticated-runtime origin**. It does not collect or harvest private keys and does not authenticate users, provide PostgreSQL access, or complete the live acceptance. The two browser pages must stay open with their in-memory keys after preview shutdown; a reload invalidates their bindings.

The operator must provide the *two public browser key carriers only*. Never put public key carriers together with private keys, tokens, database DSNs, or any existing production identity material in GitHub, log output or screenshots. Public keys are not secrets, but keep evaluator identity provenance local.

The tool deliberately pins distinct demo identities:

| Role | Controller principal | Verification method |
|---|---|---|
| Seller | `did:example:marketplace-local-evaluator-seller` | `did:example:marketplace-local-evaluator-seller#key-1` |
| Buyer | `did:example:marketplace-local-evaluator-buyer` | `did:example:marketplace-local-evaluator-buyer#key-1` |

## Explicit local invocation

Use the reviewed Python with its pinned `auth-verify` dependency, and execute **from the clean checked-out Marketplace repository root**. Run the generator and lease verifier as `python -m tools.<module>` with both `src` and `.` (the repository root) on `PYTHONPATH`, so the required `tools` import package resolves. Calling the generator by direct script path with only `src;tools` on `PYTHONPATH` fails with `ModuleNotFoundError: No module named 'tools'` and does not create a bundle. The `--output-directory` must be an **absolute path that does not exist** and whose parent already exists **outside any Git worktree**. Do not supply a production-trusted authority or production principal.

```powershell
$env:PYTHONPATH = "src;."
python -m tools.marketplace_local_two_party_provisioning `
  --output-directory "D:\MarketplaceEvaluator\fresh-signed-browser-keys" `
  --seller-browser-public-key "<seller browser mkpk1_ public carrier>" `
  --buyer-browser-public-key "<buyer browser mkpk1_ public carrier>" `
  --lease-seconds 7200 `
  --execute-local-test-provisioning EXECUTE_MARKETPLACE_LOCAL_TWO_PARTY_TEST_PROVISIONING_V1
```

The command requires exact explicit execution opt-in, canonical 32-byte Ed25519 public key carriers, distinct keys, and a lease between **1,800 and 86,400 seconds**. It generates a fresh in-memory Ed25519 **attestation signer** (which is never written), and writes only the public trust-anchor manifest, canonical two-entry signed claims and signed attestation to three exclusively created files. The generated authority is restricted to the example-domain test identity; the tool does not issue keys or sessions for either user.

**Security:** no overwrites. On POSIX, creation uses owner-only directory/file modes; on Windows, the directory inherits the parent ACL, so the operator must verify the selected parent is access-restricted before execution. A failure after creating the destination may leave partial files; treat these as unusable, remove them only after manual verification, and choose a fresh new output path. Never place the bundle in a repository, CI workspace, shared download location or publicly served directory.

## Verify before any live runtime

Run the **existing signature-verifying** local preflight (not just a superficial presence check):

```powershell
$env:PYTHONPATH = "src;."
python -m tools.marketplace_authentication_lease_preflight `
  --authentication-provisioning-directory "D:\MarketplaceEvaluator\fresh-signed-browser-keys" `
  --minimum-remaining-seconds 1800 `
  --minimum-distinct-principals 2
```

A valid signed bundle is reported only if the signature, canonical trust anchor, signed controller bindings, lease and two distinct principals all verify at the sampled time. Recheck immediately before startup. If expired, never extend times in place; generate and verify a **new, separately reviewed** test bundle.

### Check exact current browser-to-bundle key binding (offline)

The lease preflight proves that the signed provisioning is valid, but **does not compare it to the browser public keys currently displayed in the two living pages**. Before stopping the static preview, use the separate read-only binding check with the current seller and buyer `mkpk1_` carriers. Obtain them from the original, still-open browser pages at the intended localhost origin; never substitute keys generated outside those pages.

```powershell
$env:PYTHONPATH = "src;."
python -m tools.marketplace_browser_bundle_binding_preflight `
  --authentication-provisioning-directory "D:\MarketplaceEvaluatorFresh\two-party-signed-test" `
  --seller-browser-public-key "<seller current mkpk1_ public carrier>" `
  --buyer-browser-public-key "<buyer current mkpk1_ public carrier>" `
  --minimum-remaining-seconds 1800
```

Expected non-secret output: `status=BROWSER_BINDING_VERIFIED` with `signature_verified=true public_keys_bound=true` and the remaining lease. Swapped/stale keys, duplicate/noncanonical carriers, tampered claims and insufficient remaining lease all fail closed with stable codes, without printing public keys, paths, exception text or provisioning bytes. The verifier cryptographically verifies the exact bounded claims it compares; it does **not** open private keys, launch browsers/servers, or access PostgreSQL or the network.

This proves only current public-key consistency, not that a page possesses the private key or that either browser session authenticated. Keep both original pages open without reload, confirm their exact origin, and repeat the check before any separately authorized handoff. Expiry or a changed browser key requires a newly approved ceremony and new signed bundle—not weaker lease limits.


Remaining independent gates: exact clean main and pinned OLP provenance, reviewed optional dependency versions, isolated **non-Johnny** PostgreSQL connection/DB, a free **127.0.0.1** evaluator port (e.g. inspected but **not reserved** port `18480`, consistently for both preview and authenticated runtime), inert `--preflight-fulfillment-completion-localhost` success, and a separately authorized real buyer/seller browser flight. The evidence must include explicit Agreement publication and seller `CLAIMED_COMPLETE_PERFORMANCE` for `seller-delivery`, validated with `tools/marketplace_authenticated_local_flight_evidence.py`. The source-only bundle creation is not that acceptance.

**No** public endpoint, payments, settlement, production secrets, browser automations, running service mutation or Moon heartbeat are part of this change. Rollback is revert of source/tool/docs; local test artifacts are managed manually by the evaluator owner.
