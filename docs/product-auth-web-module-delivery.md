# Product auth Web module delivery

Risk classification: HIGH authentication delivery surface.

This change makes the already-reviewed Marketplace browser authentication modules retrievable as exact same-origin JavaScript assets only when an authenticated localhost composition explicitly supplies them.

## Exact delivered routes

- `/client_session.js` -> `web/client_session.js`
- `/auth_establishment.js` -> `web/auth_establishment.js`
- `/auth_ed25519_proof_provider.js` -> `web/auth_ed25519_proof_provider.js`
- `/auth_ed25519_key_creation.js` -> `web/auth_ed25519_key_creation.js`
- `/agreement_ed25519_assent_provider.js` -> `web/agreement_ed25519_assent_provider.js`
- `/agreement_assent_client.js` -> `web/agreement_assent_client.js`

The normal and in-memory demo compositions continue to pass the default empty module tuple, so their static surface remains `/`, `/index.html`, `/app.js`, and `/styles.css` only.

## Selection boundary

Delivery is not execution. `web/index.html` and `web/app.js` do not import, reference, instantiate, or call the delivered Agreement-assent signer or client in this change. `web/auth_bootstrap.js` also imports neither module. No Agreement WebCrypto signing operation, Agreement preparation/submission workflow, Agreement publication, payment, settlement, or fulfillment is activated by delivery alone. Existing authentication behavior is unchanged.

The authenticated localhost bootstrap already requires its exact execution opt-in and explicit startup provisioning directory. This change only injects exact reviewed source bytes into that existing loopback composition. It creates no public-network route, CORS widening, filesystem write, database mutation, service change, dependency change, persistence, retry, timer, worker, or background activity.

## Trust and enrollment boundary

The server authentication graph remains based on the existing immutable startup-provisioned verification-method evidence snapshot. This change does not create a mutable key-enrollment API and does not bypass signed evidence or principal-binding verification.

A later separately reviewed product capability may let the browser create a non-extractable Ed25519 key, display its public `mkpk1_...` enrollment carrier, and establish a session only after that public material has been provisioned through the existing reviewed trust path.

## Rollback

Rollback is source-only: revert this delivery change. Because the active page still selects none of these modules, rollback requires no credential revocation, key cleanup, session cleanup, database migration, service restart, or external-data repair.

## Later activation note

The later Product browser authentication bootstrap may select `/auth_bootstrap.js` only after an explicit user action. The four lower-level reviewed authentication modules remain free of direct `app.js` imports and are composed only by that bootstrap boundary.
