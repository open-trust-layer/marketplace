# M17.8D — Reject malformed Unicode in unselected Web enrollment URIs

Profile: `MARKETPLACE_WEB_AUTH_ED25519_ENROLLMENT_PROPOSAL_V1`.

## Finding

The M17.6D source-only Ed25519 enrollment-proposal handoff accepts exact
caller-provided `principal` and `verificationMethod` URI strings, preserving
their contents without identity inference or normalization. Its URI validation
checks that a supplied JavaScript string is nonempty, has an absolute
scheme, contains no whitespace, and encodes within 2048 UTF-8 bytes.

JavaScript `TextEncoder` silently converts an **unpaired surrogate** code
unit (such as U+D800 or U+DC00) into the Unicode replacement character.
This means the earlier byte-length test accepted malformed input even
though it did not have a well-defined unchanged UTF-8 identity representation.

## Narrow change

Before the unchanged 2048-byte UTF-8 length check, a bounded, allocation-free
UTF-16 scalar-sequence walk rejects:

- a high surrogate without a following low surrogate;
- a lone low surrogate;
- multiple consecutive high surrogates or other broken pairs.

A **valid surrogate pair** representing a supplementary Unicode scalar remains
accepted if the existing absolute URI and UTF-8 bounds also pass.
Ordinary ASCII and valid Unicode strings are returned **exactly unchanged**.
No normalization, transcoding, replacement, DID/controller inference,
verification-method selection or public-key transformation is introduced.

Both URI fields share the same check. The error remains the reviewed,
nonreflective `AUTH_ENROLLMENT_PROPOSAL_UNAVAILABLE`.

## Strict boundaries

The public key is still the same exact canonical 32-byte `mkpk1_` source
material re-encoded only as **non-authoritative** `mkp1_` proposal data.
The exact M17.6D profile, frozen result type and fields remain unchanged.

The module remains **unselected** by active Web entry points. This change
adds **no network** communication, WebCrypto/private-key capability,
persistence, authority attestation, enrollment registration, trust mutation,
session authentication, PostgreSQL access, runtime launch, payment, customer
operation or deployment authority.

## Qualification and rollback

Run the exact-head Python source-contract/regression suites and an independent
Node ESM behavioral matrix covering valid ASCII, a valid surrogate pair,
isolated high and low surrogates, malformed adjacent surrogates, both URI
fields, byte-length boundaries and stable nonreflective errors. Full required
Marketplace CI must pass before any merge.

A **source-only rollback** reverts the helper, its test and this document;
no runtime, credential or database change is involved.
