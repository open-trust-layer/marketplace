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

## Proposal acceptance composition boundary

The bootstrap may now compose the reviewed Proposal-acceptance Web client only
after an application session is active. It does not expose the bearer token.

The active page may request that client only from the explicit **Accept Proposal**
click path. Before enabling the control, the page requires the exact selected
Proposal, its exact parent listing, and equality between the authenticated
session principal and the listing seller. The server independently rechecks the
same seller authority before publishing the immutable acceptance record.

No page load, authentication completion, navigation, or rendering step publishes
acceptance automatically. Only the exact returned acceptance Record Identity,
store disposition, and local change sequence are retained in page memory.

## Agreement assent composition boundary

The reviewed authentication bootstrap now also contains the only browser
composition point for the delivered Agreement-assent signer and Web client.

The factory is named `agreementAssentClient()`. It fails closed unless the same
memory-only browser key still exists, the Marketplace session is active, and the
verification-method URI is the exact method that established that session.

The factory passes the existing non-extractable private CryptoKey only to the
purpose-specific Agreement signer, and passes the existing in-memory session
only to the reviewed Agreement client. It returns neither the private key nor
the bearer token.

The page still does not import the Agreement modules directly. It reaches the
reviewed capability only through `agreementAssentClient()`.

The active product may now select two explicit operations from that composition:
read-only formation-status inspection and a separate explicit Agreement-assent
signing action. The bootstrap itself never calls `prepare`,
`formationStatus`, `signAndSubmit`, or the signer; it only composes the
reviewed client after the existing key/session/method preconditions hold.

Resetting authentication clears the key/session state checked by the factory, so
new Agreement client composition fails closed after reset.

## Product boundary

Successful authentication proves only that the reviewed server accepted the challenge/proof against its current trust snapshot. A later reviewed source slice may enable the existing **Accept Proposal** control only for the exact authenticated seller and explicit user click. Authentication alone grants no Proposal acceptance, assent, agreement formation, payment, settlement, fulfillment, deployment, public-network exposure, database mutation, configuration mutation, or service restart.

## Reset and rollback

**Reset in-memory authentication** clears the memory session and drops the page's references to the generated key handle and public carriers. A page reload also loses this memory-only state.

Repository rollback is source-only: revert this change. Server evidence provisioning remains separately governed and is not modified by this slice.
