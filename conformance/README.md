# Marketplace Conformance Vectors

Marketplace conformance is executable and transport-neutral. Vector files use OLP's implementation-neutral conformance projection; they are not normative Marketplace wire formats.

## Milestone 3 — Record Representation

`vectors/record-representation-v1.json` contains 33 positive/negative record and reusable-structure vectors.

Generate and validate with:

```text
python tools/generate_record_vectors.py
python tools/validate_record_vectors.py
```

Record identities and identity-preimage bytes are derived exclusively through OLP APIs.

## Milestone 4 — Lifecycle & Negotiation

`vectors/lifecycle-negotiation-v1.json` contains 26 positive/evaluation and negative vectors covering proposal graphs, response events, withdrawal, temporal applicability, agreement formation, amendments, supersession conflicts, incomplete history, and concurrent lifecycle evidence.

Generate and validate with:

```text
python tools/generate_lifecycle_vectors.py
python tools/validate_lifecycle_vectors.py
```
The formation vectors use deterministic Ed25519 keys only for conformance reproducibility and validate real detached OLP proofs over the exact Agreement records.

## Milestone 5 — Matching & Discovery

`vectors/matching-discovery-v1.json` contains 31 positive/evaluation and negative vectors covering exact discovery filters, zero-result/open-world behavior, verified index projections, method-relative constraint aggregation, ranking plurality, federated deduplication/provenance, resource limits, and cursor binding.

Generate and validate with:

```text
python tools/generate_matching_vectors.py
python tools/validate_matching_vectors.py
```

The matching/discovery helpers define deterministic processing boundaries only. They do not create a universal Match, ranking, recommendation, global index, or Marketplace wire format.

## Milestone 6 — Fulfillment & Performance

`vectors/fulfillment-performance-v1.json` contains 47 positive/evaluation and negative vectors covering exact Commitment targeting, performance/delivery extent, inspection criteria, acceptance/rejection, completion/failure assertions, disputes, critical semantics, deduplication, resource limits, and settlement separation.

Generate and validate with:

```text
python tools/generate_fulfillment_vectors.py
python tools/validate_fulfillment_vectors.py
```

The fulfillment helper defines deterministic method-relative processing boundaries only. It does not create universal fulfillment truth, mutable Agreement state, settlement semantics, or dispute adjudication.

## Milestone 7 — Settlement Interfaces & Economic Exchange

`vectors/settlement-interfaces-v1.json` contains 57 positive/evaluation and negative vectors covering exact Commitment targeting, rail-neutral settlement outcomes, attempt/completion/failure, reversal/refund causality, escrow hold/release, asset transfer, preference constraints, external rail verification, multi-rail preservation, disputes, critical semantics, deduplication, and resource limits.

Generate and validate with:

```text
python tools/generate_settlement_vectors.py
python tools/validate_settlement_vectors.py
```

The settlement helper evaluates evidence only. It does not execute payments, custody assets, establish ownership/title, define a mandatory rail, perform cross-rail arithmetic, or establish universal legal finality.

## Milestone 8 — Federation Transport & Interoperability APIs

`vectors/federation-transport-v1.json` contains 93 positive/evaluation and negative vectors covering capability negotiation, explicit federation scopes, snapshot/sync requests and results, opaque cursor binding, canonical result fingerprints/Record identities, source-scoped page completeness, Record-Identity replay deduplication, submission idempotency, receiver outcomes, exact M8 core OLP extension message types, exact version typing, and adversarial resource/scope/replay cases.

Generate and validate with:

```text
python tools/generate_federation_vectors.py
python tools/validate_federation_vectors.py
```

The federation helper profiles OLP transport/capability primitives. It does not create a global Marketplace server, global index, canonical peer graph, deletion-by-absence semantics, exactly-once transport, or a second Marketplace evidence envelope.

## Milestone 9 — Trust Evaluation & Evidence Query Semantics

`vectors/trust-evaluation-v1.json` contains 56 positive/evaluation and negative/adversarial vectors covering query targets, purpose/context/source/profile scope, exact Record-Identity selection, provenance, exclusion reasons, replay deduplication, proof/identity/authority/lifecycle/domain observation separation, method-relative support/opposition/conflict/dispute/indeterminate results, unknown critical semantics, explainable traces, deterministic fingerprints, and resource/error boundaries.

Generate and validate with:

```text
python tools/generate_trust_evaluation_vectors.py
python tools/validate_trust_evaluation_vectors.py
```

The trust-evaluation helper standardizes one reproducible reference method only. It does not create a universal trust score, reputation object, ranking, recommendation, numeric confidence standard, source authority, or protocol truth.

All Milestone 3–9 vector sets pin the OLP source commit used for reproducibility:

```text
41b768e50b6cb9cc8e516ad7b6c40969f9ed7b6c
```

A future Marketplace release MUST bind to a released OLP compatibility target rather than this draft source pin.
## Acceptance workflow

A milestone acceptance pass regenerates every applicable vector file, requires byte-for-byte equality with the committed artifact, validates every positive and negative case, compiles the Python tooling, checks Markdown links/fences/encoding, validates JSON, and runs `git diff --check` before merge.

Milestone 9 acceptance additionally requires all earlier Marketplace vector suites to remain green.
