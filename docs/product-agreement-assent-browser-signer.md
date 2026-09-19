# Product Agreement assent browser signer

## Purpose

This source-only slice provides the smallest browser-side Ed25519 signing
boundary for the Agreement assent flow.

It accepts exact signing bytes prepared by the reviewed server/application
boundary and signs those bytes with an already-supplied non-extractable Ed25519
private CryptoKey.

The provider is deliberately unselected and undelivered in this slice.

## Profile

The module exposes:

    MARKETPLACE_WEB_AGREEMENT_ED25519_ASSENT_PROVIDER_V1

and one purpose-specific operation:

    createAgreementAssentSignature(preparation)

The preparation shape is exact:

    agreementRecordId
    verificationMethod
    signingInput

No principal or attribution decision enters the browser signer.

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

This slice does not add the source to the localhost/authenticated Web module
allowlist and does not import it from index.html, app.js, auth bootstrap,
session code or Android.

Source presence is not browser activation.

A later reviewed slice must separately authorize same-origin delivery and any
explicit user action that selects the signer.

## Rollback

Rollback is source-only rollback: revert this additive source/test/doc change.
No browser state, key material, persistent data, server state or Agreement
record is created by this slice.
