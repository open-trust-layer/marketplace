# M17.6I — Authenticated enrollment HTTP carrier

Profile: \`MARKETPLACE_APPLICATION_AUTH_ENROLLMENT_HTTP_V1\`

Exact implementation baseline: \`1f94d59e3a66074b6fc57d2316cc572fdda68ec5\`

Risk classification: **HIGH security/privacy / authenticated identity-enrollment HTTP source capability**.

M17.6I introduces a framework-neutral, source-only HTTP adapter over the reviewed M17.6D/G/H enrollment boundaries. It defines exact request/response carriers without selecting existing authenticated HTTP composition, ASGI routing, startup/runtime composition, browser code, or deployment.

## Exact scope

Added:

1. \`src/marketplace/application/auth_enrollment_http.py\`
2. \`tests/test_m17_6i_auth_enrollment_http.py\`
3. \`tests/test_m17_6i_auth_enrollment_http_artifacts.py\`
4. \`docs/m17-6i-auth-enrollment-http.md\`

Modified only for package membership:

5. \`tools/package_artifact_gate.py\`
6. \`tests/test_package_artifact_gate.py\`

No dependency, workflow, existing HTTP composition, ASGI, Web, Android, PostgreSQL, configuration, service, or deployment source is changed.

## Trusted composition

The adapter constructor freezes:

- exact existing \`MarketplaceApplicationAuthService\`;
- exact M17.6H \`MarketplaceAuthenticationEnrollmentNonceAuthority\`;
- one M17.6F approval policy;
- one M17.6E attestor;
- one bounded absolute authority URI;
- one evidence lease duration within the existing M17.5L maximum.

The authority URI and evidence lease are **trusted composition inputs**. They are not request fields and cannot be overridden by the HTTP caller.

M17.6I still does not select any concrete material source, policy implementation, attestor provider, signer key, persistence mechanism, or runtime.

## Exact routes

The adapter owns exactly:

- \`POST /api/authentication-enrollment/nonces\`
- \`POST /api/authentication-enrollment/evidence\`

Unknown paths return 404. A different method on either exact path returns 405 with \`Allow: POST\`.

The routes are source-only and **unselected** by the current HTTP composition and ASGI adapter.

## Authentication order

Both exact routes require one already-framed bearer session token.

Authentication/session validity is checked before request JSON parsing. Therefore malformed unauthenticated bodies do not become an enrollment parser oracle.

After parsing an exact M17.6D proposal, the adapter compares its principal to the validated session principal.

For nonce issuance, the adapter then calls the existing \`authorize_principal\` path to perform the authenticated session touch before nonce issuance.

For enrollment completion, the pre-check remains non-mutating; M17.6G performs the authoritative \`authorize_principal\` touch immediately before replay consumption.

## Exact proposal

Both routes accept exactly:

\`\`\`json
{
  "profile": "MARKETPLACE_WEB_AUTH_ED25519_ENROLLMENT_PROPOSAL_V1",
  "type": "MarketplaceAuthenticationEnrollmentProposal",
  "principal": "<exact absolute URI>",
  "verificationMethod": "<exact absolute URI>",
  "publicKey": "mkp1_<43 canonical base64url characters>"
}
\`\`\`

The adapter converts this only into the already-reviewed M17.6E \`MarketplaceAuthenticationEnrollmentProposal\`. It does not normalize or infer identity relationships.

## Nonce issuance

Request:

\`\`\`json
{
  "profile": "MARKETPLACE_APPLICATION_AUTH_ENROLLMENT_HTTP_V1",
  "proposal": { "...": "exact proposal above" }
}
\`\`\`

No authority or lease field is accepted.

After exact session-principal authorization, M17.6H is invoked exactly once with the trusted composition authority and lease.

Successful response:

\`\`\`json
{
  "expiresAt": 221,
  "issuedAt": 101,
  "nonce": "mken1_<43 canonical base64url characters>",
  "profile": "MARKETPLACE_APPLICATION_AUTH_ENROLLMENT_HTTP_V1",
  "type": "MarketplaceAuthenticationEnrollmentNonce"
}
\`\`\`

\`mken1_\` decodes canonically to the exact 32-byte M17.6H nonce.

## Enrollment completion

Request:

\`\`\`json
{
  "nonce": "mken1_<43 canonical base64url characters>",
  "profile": "MARKETPLACE_APPLICATION_AUTH_ENROLLMENT_HTTP_V1",
  "proposal": { "...": "exact proposal above" }
}
\`\`\`

After canonical nonce decoding and a non-mutating session-principal match, the adapter delegates exactly once to M17.6G with:

- exact session token;
- exact proposal;
- exact decoded nonce;
- current time;
- trusted composition authority;
- trusted composition lease;
- exact M17.6H nonce authority;
- exact policy;
- exact attestor.

M17.6G remains responsible for the authoritative session touch, atomic replay consumption, burn-before-policy ordering, policy gate, and evidence issuance.

## Evidence transport

Successful completion returns the exact M17.5L envelope bytes:

\`\`\`json
{
  "attestation": "mkea1_<canonical base64url of exact attestation bytes>",
  "claims": "mkec1_<canonical base64url of exact claims_json bytes>",
  "profile": "MARKETPLACE_APPLICATION_AUTH_ENROLLMENT_HTTP_V1",
  "type": "MarketplaceAuthenticationVerificationMethodEvidenceEnvelope"
}
\`\`\`

The adapter does not parse, normalize, or reserialize \`claims_json\` before transport.

All HTTP responses continue to use the existing Marketplace \`no-store\` response policy.

## Failure semantics

- missing bearer: 401 \`AUTH_REQUIRED\`;
- invalid/malformed/expired session: 401 \`AUTH_SESSION_INVALID\`;
- session/proposal principal mismatch: 403 \`AUTH_PRINCIPAL_MISMATCH\`;
- malformed JSON/request/proposal/nonce: 400 \`AUTH_ENROLLMENT_REQUEST_INVALID\`;
- wrong content type: 415 \`UNSUPPORTED_MEDIA_TYPE\`;
- wrong method: 405 \`METHOD_NOT_ALLOWED\`;
- nonce issuance failure/capacity/material failure: 503 \`AUTH_ENROLLMENT_NONCE_UNAVAILABLE\`;
- M17.6G coordination failure: 409 \`AUTH_ENROLLMENT_UNAVAILABLE\`;
- unknown path: 404 \`NOT_FOUND\`.

The 409 completion failure deliberately does not distinguish replay rejection, policy rejection, or attestor failure.

No error reflects session token, nonce, proposal values, authority, policy/provider result, signer detail, or nested exception text.

## Explicit non-authority

M17.6I adds no:

- ASGI route selection;
- existing authenticated HTTP composition selection;
- startup/runtime selection;
- concrete nonce material source or randomness;
- network/filesystem/environment/database persistence;
- shared/distributed nonce authority;
- concrete policy implementation;
- signer/private-key custody;
- trust-anchor mutation;
- Web/browser activation;
- Android action;
- PostgreSQL/config/service mutation;
- background worker or retry;
- deployment, publishing, distribution, or public-network activity.

## Qualification

Qualification freezes:

- exact profile, routes, request shapes, response types, and carrier prefixes;
- authentication before body parsing;
- exact M17.6D proposal conversion;
- no client authority/lease input;
- exact trusted authority/lease delegation;
- canonical \`mken1_\` nonce encoding/decoding;
- exact M17.5L evidence-byte preservation via \`mkec1_\` / \`mkea1_\`;
- stable status/code semantics;
- replay/policy/signer cause non-disclosure;
- continued HTTP-composition/ASGI/Web/Android non-selection;
- package membership coverage;
- FULL Marketplace conformance.

## Rollback and later gates

Rollback is **source-only rollback**: revert the exact M17.6I merge. Because the adapter remains unselected, rollback requires no service restart, database migration, nonce cleanup, key revocation, or deployment action.

Later separately governed work may compose the adapter into the authenticated HTTP graph, add exact ASGI routing, select a concrete nonce material source, activate browser enrollment, select deployment-appropriate shared nonce authority, select concrete policy/provider/signer custody, or perform bounded localhost acceptance.
