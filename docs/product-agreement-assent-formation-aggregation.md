# Product Agreement assent formation aggregation

## Purpose

This slice closes the read-only bridge from retained verified Agreement assent
coordination evidence into the existing Agreement formation evaluator.

It does not publish an Agreement, expose HTTP, activate a browser signer, apply
a database migration, or authorize any protected side effect.

## Trust rule

Persistence is not authority.

Every retained proof used for formation is re-evaluated against the exact
current unpublished Agreement candidate, the retained Agreement Record Identity,
the current injected principal-to-verification-method snapshot, the current
public key from that same snapshot, the retained proof bytes and Proof Identity,
and the standard pinned OLP proof verifier.

Only after all checks succeed does the application create a fresh
VerifiedAgreementAssent and project it into the already-reviewed formation
evidence input.

## Current-method behavior

A retained proof whose verification method is no longer currently accepted by
the injected snapshot does not contribute coverage. The result therefore stays
EVIDENCE_INCOMPLETE.

A malformed, corrupted, identity-mismatched, or cryptographically invalid
retained proof is different: aggregation fails with a stable non-reflective
error instead of silently hiding storage corruption as missing assent.

## Layering

The application module stays OLP-neutral.

The flow is coordination read, current snapshot binding check, injected
reference proof re-verifier, fresh VerifiedAgreementAssent, injected reference
formation-evidence adapter, then the existing formation evaluation service.

The reference module owns OLP decoding, ResolvedVerificationMethod projection,
standard proof verification, and exact formation evidence construction.

## Side-effect boundary

Aggregation performs reads only. It does not insert, update, expire, or delete
coordination evidence; refresh retention; publish an Agreement; create or sign
a proof; mutate trust evidence; generate/import/export keys; perform payment,
settlement, escrow, fulfillment, or ownership transfer; start background work;
or activate a database or network service.

## Rollback

Rollback is source-only: revert this additive slice. No migration, retained
content, browser state, server state, or Agreement publication is created by
this code.
