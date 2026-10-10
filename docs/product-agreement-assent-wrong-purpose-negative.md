# Agreement assent wrong-proof-purpose negative

## Acceptance property

Issue #364 requires a negative test for a wrong proof purpose.

The frozen Marketplace vector is first verified through the reviewed reference
Agreement-assent builder. The resulting standard OLP proof uses the exact
Agreement purpose `assertion`.

The negative fixture then changes only that proof purpose to the different
standard OLP core purpose `authorization` while retaining the original
signature and all other proof material.

Pinned OLP verification is required to report both:

- `purpose_status = MISMATCH` against expected `assertion`; and
- invalid cryptographic validity, because proof purpose is authenticated by the
  signed ProofInput bytes.

The reference Marketplace builder is also required to continue emitting only
`assertion`.

## Boundary

This is a deterministic known-answer negative test plus documentation. It
creates no new signing capability, key material, trust source, persistence,
network/database/runtime activity, Agreement publication, deployment, or
provider administration.
