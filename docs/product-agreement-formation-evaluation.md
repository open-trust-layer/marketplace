# Product Agreement formation evidence evaluation

This slice packages the existing Marketplace M4 detached-assent semantics for use by
the product application layer.

The evaluator accepts an already-built `MarketAgreement` candidate plus bounded
detached proof observations. It verifies proof binding, supported proof semantics,
assertion purpose, verification-method resolution/compatibility, cryptographic
validity, and caller-supplied attribution acceptance for each required Agreement
party.

A result of `EVIDENCE_SUFFICIENT_FOR_PROFILE` means only that every required party
is covered by acceptable detached assent evidence under the reviewed Marketplace
formation profile.

It explicitly does **not** mean:

- the Agreement has been published;
- a proof has been created or a private key has been used by this evaluator;
- legal enforceability has been established;
- the result is universal truth;
- payment, settlement, fulfillment, ownership transfer, or another side effect is
  authorized.

The application seam is transport-neutral and state-free. HTTP, Web, Android,
database, signing, key management, network, service, and deployment activation are
outside this slice.
