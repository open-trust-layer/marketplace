# Product Agreement candidate authoring

This slice moves the product flow one step beyond seller Proposal acceptance without
collapsing acceptance evidence into Agreement formation.

The new reference authoring path deterministically constructs one `MarketAgreement`
candidate from one exact structured product listing, one exact buyer Proposal
targeting that listing, and one exact seller Proposal-acceptance event targeting
that Proposal.

The candidate binds the seller and buyer, listing subject and terms, one reviewed
seller-delivery commitment, and exact source-record references.

## Authority boundary

This slice deliberately does **not** publish the Agreement candidate, create or verify
party proofs, claim `EVIDENCE_SUFFICIENT_FOR_PROFILE`, claim legal enforceability or
universal truth, or activate HTTP, Web, Android, database, network, payment,
settlement, or fulfillment.

The application service performs read-only source resolution through `peek()`.
Its result is explicitly `published=false` and
`formation_evidence=NOT_EVALUATED`.

Agreement formation remains a separate step requiring detached assent evidence for
the candidate under the existing agreement-formation profile.
