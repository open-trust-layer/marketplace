# M17.1Z reference application Record JSON profile

M17.1Z closes the raw Record JSON composition gap intentionally left by M17.1Y. The reference Marketplace application launch factory now fixes one reviewed **application Record JSON v1** encoder/decoder for the existing raw `/api/intents` and `/api/intents/{id}/responses` record routes instead of asking each caller to choose those codecs.

## Profile

The profile represents one genuine pinned-OLP `RecordV1` as a top-level JSON object using the existing Record fields:

- `envelope_version`
- `type`
- `content`
- `semantic_bindings`
- `profiles`
- `relationships`
- `extensions`

The encoder validates the Record through the existing Marketplace validator, derives its exact OLP Record Identity, and reuses the reviewed record-serving payload preparation before JSON projection. Canonical output contains the complete field set and uses deterministic key ordering, compact separators, strict UTF-8 bytes, and the existing application HTTP body bound.

For client ergonomics, **normal string-keyed maps** remain normal JSON objects. This keeps `record.content`, product terms, presentation location, and other ordinary Marketplace structures directly visible to the current Web and Android product clients.

Values that plain JSON cannot represent safely reuse **pinned OLP OJVE-1** rather than adding a second scalar encoding. In particular, unsafe integers and bytes use the OJVE wrappers already defined by OLP. Ambiguous `{"$olp": ..., "v": ...}` maps and maps requiring non-string keys are represented with the existing OJVE map wrapper so a literal application value cannot impersonate an OJVE scalar wrapper.

A raw integer outside the OJVE safe JSON integer range is rejected on decode unless it uses the reviewed OJVE integer wrapper. This prevents a cross-client JSON parser from silently accepting a precision-losing representation.

## Decode boundary

The decoder accepts strict non-empty bounded UTF-8 JSON bytes, rejects a UTF-8 BOM, rejects duplicate member names at every object depth, rejects malformed/non-finite/floating-point values through the reviewed OJVE boundary, and requires the top level to contain the required Record fields with no unknown Record fields.

Optional `RecordV1` fields may be omitted on input and receive the pinned OLP model defaults. Re-encoding always emits the complete canonical application profile. The reconstructed object must still pass pinned OLP `RecordV1` validation and existing Marketplace semantic validation; the codec does not create a second Record model, identity scheme, or Marketplace semantic path.

## Composition boundary

`build_reference_marketplace_application_launch_plan(...)` now fixes:

- canonical application-state prepare/decode;
- Proposal parent extraction;
- Marketplace intent classification;
- Product Listing and Proposal reference builders; and
- the application Record JSON v1 encoder/decoder.

The generic `marketplace.application` layer remains reference-independent and injection-based. Persistence/store selection, intent querying, host/port metadata, and Web asset bytes remain caller-injected at the reference factory. M17.1Z does not load those resources or activate them.

## Authority boundary

M17.1Z performs deterministic in-process validation and JSON conversion only. It grants **no runtime activation**, performs **no PostgreSQL connection**, migration, provisioning, or administration, performs no filesystem asset loading, environment/secret loading, socket bind/listen/accept/connect, server execution, browser action, Android build/runtime/sign/install, dependency installation, provider selection, deployment, or service/configuration mutation.

It adds no agreement, acceptance, assent, order, payment, settlement, fulfillment, inventory mutation, ownership transfer, ranking, trust, legitimacy, or authorization semantics.

A **merge remains a separate exact-head governance boundary**.
