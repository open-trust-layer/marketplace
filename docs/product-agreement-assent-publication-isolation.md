# Agreement assent publication isolation

## Product invariant

Issue #364 creates, verifies, coordinates, and aggregates Agreement assent
evidence. It does not publish an Agreement.

Agreement publication remains a separate product boundary owned by the staged
publication services and, after the required landing/requalification sequence,
the protected authenticated route planned by issue #363.

## Repository guard

The publication-isolation contract scans the complete
`agreement_assent*.py` application/reference surface and the purpose-specific
Agreement browser signer/client.

It requires the #364 stack not to select:

- `marketplace.application.agreement_publication`;
- `marketplace.application.agreement_publication_write`;
- publication service classes/functions;
- a browser publication operation;
- publication capability from the Agreement localhost bootstrap.

The existing publication modules are required to remain present, making this a
separation assertion rather than an assertion that publication capability does
not exist anywhere in the repository.

## Why this matters

A formation result of `EVIDENCE_SUFFICIENT_FOR_PROFILE` is evidence status,
not publication authority. The Agreement assent workflow deliberately returns
bounded status values with `publishes_agreement=false` and
`authorizes_side_effects=false`.

Keeping the publication modules unselected prevents a future composition
refactor from accidentally turning proof submission, formation-status reads,
preflight, or localhost activation into an Agreement write.

## Boundary

This slice is an additive source-contract test and documentation only. It does
not invoke Agreement signing, coordination initialization, PostgreSQL,
publication, localhost execution, deployment, or provider administration.
