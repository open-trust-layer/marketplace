# Product Agreement assent proof serialization

## Purpose

This slice defines the reference boundary that converts one already verified
Agreement assent result into the bounded public bytes accepted by the
coordination store.

It does not perform signing, principal attribution, persistence, network I/O, or
Agreement publication.

## Encoding

The proof is encoded through the existing Marketplace strict transport JSON
adapter over pinned OLP OJVE.

The envelope is the core OLP transport message:

    ("OLP-TRANSPORT", 1, "proof", payload)

The payload freezes the first Agreement-assent profile:

- OLPProof v1;
- eddsa-ed25519-v1;
- proofPurpose assertion;
- exact verification method;
- exact RecordCommitment;
- exact proofValue;
- empty critical tuple;
- empty extensions map.

No created, expires, domain, challenge, nonce, or extension metadata is admitted
by this first coordination profile.

## Stored identity

Prepared coordination evidence stores both:

- canonical transport JSON proof bytes;
- the exact 32-byte OLP Proof Identity digest.

The Agreement Record Identity, attributed principal, and verification method
remain separate explicit key/binding fields.

## Decode boundary

Stored bytes are never trusted merely because they came from the coordination
store.

Decode:

1. requires the exact OLP proof transport envelope shape;
2. reconstructs an exact OLPProof;
3. revalidates the minimal proof profile;
4. requires the proof verificationMethod to match the stored method;
5. recomputes Proof Identity;
6. requires it to match the stored 32-byte identity.

Any mismatch fails closed with a stable non-reflective error.

## Trust boundary

The serializer accepts only an exact VerifiedAgreementAssent whose proof member
is the reviewed VerifiedAgreementAssentProof reference result.

The serializer does not create or upgrade principal attribution. Attribution was
already established by the application snapshot binding before this boundary.

Likewise, successful decode does not make stored evidence trusted for current
formation. A later aggregation slice must re-resolve current trusted
verification-method evidence and re-run formation verification.

## Authority boundary

This slice adds no:

- PostgreSQL schema or migration;
- database connection or mutation;
- private-key handling;
- browser activation;
- HTTP route;
- background task;
- Agreement publication;
- payment, settlement, escrow, fulfillment, or ownership transfer.

Rollback is source-only.
