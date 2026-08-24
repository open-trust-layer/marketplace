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

Both Milestone 3 and Milestone 4 vector sets pin the OLP source commit used for reproducibility:

```text
41b768e50b6cb9cc8e516ad7b6c40969f9ed7b6c
```

A future Marketplace release MUST bind to a released OLP compatibility target rather than this draft source pin.

## Acceptance workflow

A milestone acceptance pass regenerates vectors, requires byte-for-byte equality with the committed files, validates every positive and negative case, compiles the Python tooling, checks Markdown links/fences/encoding, and runs `git diff --check` before merge.
