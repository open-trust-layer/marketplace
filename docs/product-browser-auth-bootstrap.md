# Product browser authentication bootstrap

Risk classification: HIGH authentication and browser-key activation surface.

This slice turns the already-reviewed Web authentication modules into one explicit, user-driven authenticated-localhost flow. It does not change the server trust model and does not publish Marketplace acceptance or agreement records.

## User flow

1. The operator clicks **Start local authentication**.
2. Only then does `app.js` dynamically import `/auth_bootstrap.js`.
3. The operator explicitly clicks **Generate browser key**.
4. WebCrypto creates one Ed25519 private signing key that is non-extractable and memory-only.
5. The page displays only public enrollment material.
6. Keeping this page open, the operator separately provisions that public material through the existing startup-provisioned verification-method evidence path.
7. Because the server trust snapshot is immutable after startup, the authenticated localhost process must be separately relaunched/restarted against that updated evidence before authentication can succeed. This source change does not perform or authorize that operational mutation.
8. The operator enters the exact seller principal URI and verification-method URI bound by the newly loaded evidence.
9. The operator explicitly clicks **Establish authenticated session**. If the page was reloaded during provisioning/restart, its memory-only private key is gone and a new key must be generated and provisioned instead.

## Public-key carrier bridge

The reviewed browser key-creation module exposes public key bytes as:

`mkpk1_<43 canonical base64url characters>`

The existing server evidence intake freezes the same 32-byte Ed25519 public key as:

`mkp1_<43 canonical base64url characters>`

`auth_bootstrap.js` validates the browser carrier and changes only that profile prefix. The 43-character payload is preserved byte-for-byte. No raw private or public byte array is exposed to the product page.

## Trust boundary

There is no mutable enrollment API. The browser cannot add, replace, or revoke server trust evidence. Authentication succeeds only when the immutable startup-provisioned evidence loaded by the current server process already binds the exact public key to the entered principal and verification method. Updating provisioning files alone does not mutate a running trust snapshot.

## Custody and activity boundary

The private key remains inside the reviewed non-extractable WebCrypto handle. This slice adds no private-key export/import, seed, mnemonic, passphrase, persistence, recovery, backup, rotation, background worker, timer, retry loop, storage API, service worker, Android custody, or external key provider.

Module selection, key creation, and network authentication each require a separate explicit user action. A page load performs none of them.

The bearer token remains inside `MarketplaceMemorySession`; it is not returned to `app.js`, rendered, logged, persisted, or copied into application state.

## Product boundary

Successful authentication proves only that the reviewed server accepted the challenge/proof against its current trust snapshot. The existing **Accept Proposal** control remains disabled. This slice grants no Proposal acceptance, assent, agreement formation, payment, settlement, fulfillment, deployment, public-network exposure, database mutation, configuration mutation, or service restart.

## Reset and rollback

**Reset in-memory authentication** clears the memory session and drops the page's references to the generated key handle and public carriers. A page reload also loses this memory-only state.

Repository rollback is source-only: revert this change. Server evidence provisioning remains separately governed and is not modified by this slice.
