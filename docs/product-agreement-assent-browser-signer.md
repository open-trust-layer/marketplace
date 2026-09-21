# Product Agreement assent browser signer

## Purpose

This source-only slice provides the smallest browser-side Ed25519 signing
boundary for the Agreement assent flow.

It accepts exact signing bytes prepared by the reviewed server/application
boundary and signs those bytes with an already-supplied non-extractable Ed25519
private CryptoKey.

The provider was deliberately unselected and undelivered in its original
source slice. Later reviewed slices now deliver it and allow composition only
inside auth_bootstrap.js; app.js and index.html still cannot invoke it directly.

## Profile

The module exposes:

    MARKETPLACE_WEB_AGREEMENT_ED25519_ASSENT_PROVIDER_V1

and one purpose-specific operation:

    createAgreementAssentSignature(preparation)

The preparation shape is exact:

    verificationMethod
    signingInput

No Agreement identity, principal or attribution decision enters the browser signer.

## Signing contract

The provider is constructed with:

- injected SubtleCrypto-compatible signer;
- already-supplied non-extractable Ed25519 private CryptoKey;
- one pinned verification-method URI.

The key must be:

    type        private
    extractable false
    algorithm   Ed25519
    usages      ["sign"]

The signer deliberately receives no Agreement Record Identity. Record binding is
owned by the exact OLP signing bytes and is re-verified by the server.

The preparation verification method must equal the pinned method.

The signing input must be an exact Uint8Array between 1 and 4096 bytes. The
provider copies those bytes once before the asynchronous signing call and sends
that exact copy to:

    subtle.sign({ name: "Ed25519" }, privateKey, exactSigningBytes)

The provider requires an exact 64-byte ArrayBuffer signature result and returns
only a new Uint8Array containing those signature bytes.

## Frozen product vector

The upstream Agreement-assent reference slice freezes the exact product vector:

    Agreement:
    r1_grS0_HlLNS2A1VqdELEa_daC4IJl_SBGzxcAO6esM5A

    verification method:
    urn:example:olp:test-key-1

    ProofInput:
    106 bytes

    signature:
    64 bytes

The browser signer does not construct or reinterpret ProofInput, CBOR,
RecordCommitment, OLPProof, proof purpose, cryptosuite or proof identity.

Cross-runtime acceptance is:

    pinned Python/OLP prepares exact signing bytes
    -> browser WebCrypto signs exact bytes
    -> pinned Python/OLP verifies reconstructed proof

## Security and authority boundary

This module has:

- no key generation;
- no key import;
- no key export;
- no credential persistence;
- no storage APIs;
- no ambient crypto selection;
- no network;
- no timers/workers/background activity;
- no OLP/CBOR construction;
- no principal attribution authority;
- no formation-sufficiency decision;
- no Agreement publication;
- no payment/settlement/escrow/fulfillment capability.

Errors are stable and non-reflective.

## Delivery and activation

A later reviewed delivery slice adds the source to the authenticated same-origin
module allowlist. The reviewed authentication bootstrap is now the only module
that imports the provider and may compose it with the existing non-extractable
browser key after authentication.

index.html and app.js still do not import the provider, and auth_bootstrap.js
does not call createAgreementAssentSignature directly. It only constructs the
purpose-specific signer when agreementAssentClient() is explicitly requested
after key/session verification. No current page control requests that factory.

Delivery and composition are not browser signing activation. Any active user
action that calls Agreement prepare/sign/submit remains a later reviewed slice.

## Rollback

Rollback is source-only rollback: revert this additive source/test/doc change.
No browser state, key material, persistent data, server state or Agreement
record is created by this slice.
