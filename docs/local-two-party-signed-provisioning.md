# Two-party local evaluator: signed short-lived test provisioning

Tracking: [authenticated PostgreSQL localhost flight #525](https://github.com/open-trust-layer/marketplace/issues/525).

**Scope:** this is a separately invoked operator tool for a disposable, **non-production, local-only** authentication trust bundle. It addresses the `LEASE_EXPIRED` finding for the existing evaluator bundles without modifying, renewing, copying, or bypassing any of those old bundles. It does **not** run the application, start or connect PostgreSQL, generate browser private keys, authenticate either actor, or imply the acceptance flight passed.

## Inputs and the browser-key boundary

The existing Web UI's **Generate authentication key** action creates a non-extractable Ed25519 private key in the current page and shows its **browser public key** (prefix `mkpk1_`) and matching evidence public key (`mkp1_`). Generate **two different keys** in separate seller/buyer browser contexts that will remain alive throughout the flight. The browser private keys must never be copied or exported. These contexts must use the **same intended localhost origin** and retain their key objects: reloading or navigating discards the in-memory keys. The current repository does not provide an operator-ready pre-auth Web hosting/key-harvest workflow; until one is established and reviewed, this source-only tool by itself **does not remove that remaining runtime blocker**.

The operator must provide the *two public browser key carriers only*. Never put public key carriers together with private keys, tokens, database DSNs, or any existing production identity material in GitHub, log output or screenshots. Public keys are not secrets, but keep evaluator identity provenance local.

The tool deliberately pins distinct demo identities:

| Role | Controller principal | Verification method |
|---|---|---|
| Seller | `did:example:marketplace-local-evaluator-seller` | `did:example:marketplace-local-evaluator-seller#key-1` |
| Buyer | `did:example:marketplace-local-evaluator-buyer` | `did:example:marketplace-local-evaluator-buyer#key-1` |

## Explicit local invocation

Use the reviewed Python with its pinned `auth-verify` dependency, and execute from a **clean checked-out Marketplace repo**. The `--output-directory` must be an **absolute path that does not exist** and whose parent already exists **outside any Git worktree**. Do not supply a production-trusted authority or production principal.

```powershell
$env:PYTHONPATH = "src;tools"
python tools/marketplace_local_two_party_provisioning.py `
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
$env:PYTHONPATH = "src;tools"
python tools/marketplace_authentication_lease_preflight.py `
  --authentication-provisioning-directory "D:\MarketplaceEvaluator\fresh-signed-browser-keys" `
  --minimum-remaining-seconds 1800 `
  --minimum-distinct-principals 2
```

A valid signed bundle is reported only if the signature, canonical trust anchor, signed controller bindings, lease and two distinct principals all verify at the sampled time. Recheck immediately before startup. If expired, never extend times in place; generate and verify a **new, separately reviewed** test bundle.

Remaining independent gates: exact clean main and pinned OLP provenance, reviewed optional dependency versions, isolated **non-Johnny** PostgreSQL connection/DB, a free **127.0.0.1** evaluator port, inert `--preflight-fulfillment-completion-localhost` success, and a separately authorized real buyer/seller browser flight. The evidence must include explicit Agreement publication and seller `CLAIMED_COMPLETE_PERFORMANCE` for `seller-delivery`, validated with `tools/marketplace_authenticated_local_flight_evidence.py`. The source-only bundle creation is not that acceptance.

**No** public endpoint, payments, settlement, production secrets, browser automations, running service mutation or Moon heartbeat are part of this change. Rollback is revert of source/tool/docs; local test artifacts are managed manually by the evaluator owner.
