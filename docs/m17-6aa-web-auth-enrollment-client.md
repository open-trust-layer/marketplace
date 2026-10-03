# M17.6AA — Unselected Web authenticated enrollment client

Profile: `MARKETPLACE_WEB_AUTH_ENROLLMENT_CLIENT_V1`

Risk: **HIGH authentication** source-only authenticated enrollment HTTP client
capability.

## Purpose

The server already exposes the reviewed M17.6I authenticated enrollment routes,
and M17.6D already defines the exact public Ed25519 enrollment proposal.

M17.6AA adds the missing Web transport contract between those reviewed
boundaries. The new client is **unselected and undistributed**: it is not
imported by the product bootstrap/page and is not served by the authenticated
localhost module bundle.

The active browser flow therefore remains unchanged and continues to use
separately governed **startup-provisioned** evidence.

## Exact input boundary

The client accepts only:

- an injected fetch implementation;
- an existing memory-session surface exposing `requirePrincipal()`,
  `authorizationFor(...)`, and `invalidateForServerCode(...)`;
- one exact M17.6D public proposal with:
  - profile `MARKETPLACE_WEB_AUTH_ED25519_ENROLLMENT_PROPOSAL_V1`;
  - type `MarketplaceAuthenticationEnrollmentProposal`;
  - principal;
  - verification method;
  - canonical `mkp1_` public-key carrier.

The proposal contains no private key, seed, mnemonic, passphrase, signer, bearer
token, authority, lease, attestation, or trust decision.

Before any fetch, the client requires the exact proposal principal to equal the
active session principal.

## Exact authenticated HTTP sequence

The Web memory-session route scope is widened only for these exact POST paths:

- `/api/authentication-enrollment/nonces`
- `/api/authentication-enrollment/evidence`

GET authorization remains unchanged.

For one explicit client invocation:

1. obtain the exact bearer authorization for the nonce route;
2. POST exactly
   `{ profile: "MARKETPLACE_APPLICATION_AUTH_ENROLLMENT_HTTP_V1", proposal }`;
3. validate one 201 nonce response;
4. keep the `mken1_` nonce internal; the nonce remains internal to the client;
5. obtain the exact bearer authorization for the evidence route;
6. POST exactly
   `{ profile: "MARKETPLACE_APPLICATION_AUTH_ENROLLMENT_HTTP_V1", proposal, nonce }`;
7. validate one 201 public-evidence response;
8. return only profile/type plus the `mkec1_` claims and `mkea1_` attestation
   carriers.

Both requests use JSON, `credentials: "omit"`, no-store cache, redirect error,
and no-referrer policy.

There is no retry, fallback, polling, timer, worker, or background behavior.

## Response and error boundary

Response bodies are bounded to 768 KiB, covering the reviewed server maximum
claims and attestation carrier sizes plus JSON overhead.

The nonce must be exact canonical 32-byte `mken1_` base64url material. Claims
and attestation must be non-empty canonical base64url carriers within the
reviewed server maxima.

Server error codes are accepted only under a bounded `AUTH_[A-Z_]+` shape.
Other server failures collapse to `AUTH_ENROLLMENT_HTTP_FAILED`.

The client delegates server-code invalidation to the existing memory session.
Therefore `AUTH_SESSION_INVALID` can clear that session through the already
reviewed session method.

Transport, parser, validation, and server errors do not reflect proposal values,
bearer material, nonce material, public-key material, paths, or response bodies.

## Non-selection and trust boundary

M17.6AA adds **no UI activation**.

The new module remains absent from:

- `auth_bootstrap.js`;
- `app.js`;
- `index.html`;
- site-host static module allow-list;
- localhost Web module list;
- Android source;
- Python startup/runtime composition.

The existing product bootstrap still documents **no mutable enrollment API** and
continues to require separate startup provisioning and restart/relaunch for its
active authentication flow.

M17.6AA itself performs **no trust-store mutation** and does not install the
returned evidence into a running server snapshot.

## Key, persistence, and runtime boundary

M17.6AA performs no key generation, private-key access, signing, key import or
export, persistence, storage API use, key recovery, HSM/vault/keyring access,
database/configuration/service mutation, runtime/provider selection, socket API
use, Android action, public-network activation, deployment, publishing, or
distribution.

Its only external side effect when explicitly invoked by a future reviewed
caller is the exact two authenticated HTTP fetches described above.

## Rollback

**source-only rollback:** revert the exact M17.6AA merge.

Because the module remains unselected and qualification uses source inspection
and injected fake boundaries only, rollback requires no trust cleanup, key
revocation, session cleanup, service restart, browser/device cleanup, or
deployment rollback.
