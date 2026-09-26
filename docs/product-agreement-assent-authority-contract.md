# Agreement assent caller-authority exclusion

## Invariant

Agreement assent callers provide the exact candidate binding, authenticated
principal/method context through the reviewed application path, and the
resulting signature. They do not provide trust.

In particular, no public key, attribution decision, trust flag, or proof
purpose is accepted as caller authority.

## Frozen contracts

The application proof-service operations expose no parameter for:

- public key material;
- attribution or attribution-accepted state;
- caller trust flags;
- proof purpose.

The public key used by finalization is obtained only from the already-reviewed
verification-method snapshot after current principal/method/time binding is
revalidated.

The reference OLP boundary fixes Agreement assent proof purpose to
`assertion` for both ProofInput construction and proof verification. Neither
reference operation accepts a caller-supplied purpose or expected-purpose
override.

The acceptance contract also freezes a literal one-byte mutation of an already
reviewed signing preparation: finalization must reject it before the proof
builder is invoked.

## Boundary

This slice adds contract tests and documentation only. It does not add key
material, trust configuration, signing capability, persistence, database
activity, Agreement publication, localhost execution, deployment, or provider
administration.
