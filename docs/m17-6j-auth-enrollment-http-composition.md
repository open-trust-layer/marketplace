# M17.6J — Static authenticated enrollment HTTP composition

Profile: \`MARKETPLACE_APPLICATION_AUTH_ENROLLMENT_HTTP_COMPOSITION_V1\`

Exact implementation baseline: \`d828db5d6e016850b3af73c877c36fcb1e42fff9\`

Risk classification: **HIGH security/privacy / authenticated enrollment object-graph composition capability**.

M17.6J composes the reviewed M17.6I authenticated enrollment HTTP adapter with the existing M17.5P authenticated HTTP object graph. It is source-only, static, non-consuming, and deliberately unselected by ASGI, startup/runtime, Web, Android, and launch code.

## Exact scope

Added:

1. \`src/marketplace/application/auth_enrollment_http_composition.py\`
2. \`tests/test_m17_6j_auth_enrollment_http_composition.py\`
3. \`tests/test_m17_6j_auth_enrollment_http_composition_artifacts.py\`
4. \`docs/m17-6j-auth-enrollment-http-composition.md\`

Modified only for package membership:

5. \`tools/package_artifact_gate.py\`
6. \`tests/test_package_artifact_gate.py\`

No dependency, workflow, existing HTTP composition, ASGI, Web, Android, PostgreSQL, configuration, service, or deployment source is changed.

## Exact inputs

Composition accepts:

- one exact existing \`MarketplaceAuthenticatedHttpComposition\`;
- one exact existing M17.6H \`MarketplaceAuthenticationEnrollmentNonceAuthority\`;
- one injected M17.6F approval policy;
- one injected M17.6E attestor;
- one trusted authority URI;
- one M17.5L-bounded evidence lease duration.

It constructs exactly one M17.6I \`MarketplaceAuthenticationEnrollmentHttpAdapter\`.

## Same auth-service authority

M17.6J proves that the **same exact auth-service instance** is shared by:

- \`http.authentication.auth_service\`;
- \`http.application_http\`;
- \`http.session_http\`;
- authenticated product-listing authoring;
- authenticated proposal authoring;
- authenticated proposal-acceptance authoring when present;
- the newly composed enrollment HTTP adapter.

This identity check is performed without invoking any session or authentication operation.

A caller cannot compose enrollment HTTP against a different auth-service instance while presenting an otherwise valid M17.5P graph.

## Exact collaborator identity

The resulting immutable composition retains the exact supplied:

- M17.5P HTTP composition;
- M17.6H nonce authority;
- M17.6F policy;
- M17.6E attestor;
- trusted authority URI;
- evidence lease duration;
- M17.6I enrollment HTTP adapter.

The M17.6I adapter is checked to hold those same exact object references and exact authority/lease values.

## Zero-consumption composition

There are **zero collaborator calls** during composition.

Specifically, M17.6J does not call:

- challenge material source;
- session-token material source;
- enrollment nonce material source;
- nonce issuance;
- nonce consumption;
- policy approval;
- attestation/signing;
- authentication/session methods;
- M17.6G coordination.

Purpose-specific collaborator methods are inspected only for callable presence.

## Stable failure

Invalid exact type, incoherent existing HTTP auth ownership, missing policy/attestor callable, invalid authority URI, or invalid evidence lease collapses to:

\`MarketplaceAuthenticationEnrollmentHttpCompositionError("authenticated enrollment HTTP composition failed")\`

Nested collaborator/provider details are not reflected.

## Explicit non-authority

M17.6J adds no:

- existing M17.5P mutation;
- ASGI route or selection;
- startup/runtime selection;
- browser/Web activation;
- Android action;
- concrete nonce randomness/material source;
- persistent/shared nonce authority;
- concrete policy implementation;
- signer/private-key custody;
- trust-anchor mutation;
- network/filesystem/environment/database persistence;
- PostgreSQL/config/service mutation;
- background worker or retry;
- deployment, publishing, distribution, or public-network activity.

There is **no ASGI** selection in this milestone.

## Qualification

Qualification freezes:

- exact M17.6J profile;
- exact composed input/output types;
- same-auth-service object identity across M17.5P and M17.6I;
- exact nonce-authority/policy/attestor object identity;
- exact trusted authority/lease retention;
- zero collaborator/material calls during composition;
- stable non-reflective failure;
- continued ASGI/startup/Web/Android non-selection;
- package membership coverage;
- FULL Marketplace conformance.

## Rollback and later gates

Rollback is **source-only rollback**: revert the exact M17.6J merge. Because the composition remains unselected and non-consuming, rollback requires no service restart, nonce cleanup, database migration, key revocation, or deployment action.

Later separately governed work may define an enrollment-aware ASGI selection seam, select a concrete nonce material source, activate browser enrollment, select a deployment-appropriate shared nonce authority, select concrete policy/provider/signer custody, or perform bounded localhost acceptance.
