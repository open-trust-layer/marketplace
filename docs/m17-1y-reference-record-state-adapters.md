# M17.1Y canonical application-record state adapters

M17.1Y closes the next source-composition gap after M17.1X by binding four reviewed record semantics at the reference layer: canonical application-state preparation, canonical decode, Proposal `response_to` extraction, and Marketplace intent classification.

## Canonical state boundary

`prepare_marketplace_application_record(...)` accepts only a genuine pinned-OLP `RecordV1` that passes the existing Marketplace semantic validator. It derives the exact OLP Record Identity and reuses the already reviewed `market_record_transport_payload(...)`, `make_record_transport_envelope(...)`, and strict OLP transport-JSON encoder to produce deterministic application-state bytes. No second Record model or serialization format is introduced.

`decode_marketplace_application_record(...)` accepts only the same OLP `record` transport representation, reconstructs `RecordV1`, reruns Marketplace validation and Record Identity derivation, then requires byte-for-byte equality with a fresh deterministic encoding. Alternate whitespace, ordering, or other representation drift therefore does not become a second canonical application-state byte form.

Proposal `response_to` references are converted from validated OLP Record evidence references to exact canonical `r1_...` identities. Intent classification returns true only for a fully valid exact Marketplace `RecordV1` whose type is the existing intent type.

## Composition boundary

`build_reference_marketplace_application_launch_plan(...)` now fixes these four reference semantics together with the Product Listing and Proposal builders reviewed in M17.1X.

Persistence/store selection, intent querying, host/port metadata, Web asset bytes, and **raw Record JSON remains caller-injected**. In particular, M17.1Y does not redefine the M17.1B2 raw `/api/intents` or `/responses` Record JSON wire representation. A later wire-profile decision can review those two JSON codecs separately without coupling it to canonical PostgreSQL-ready state bytes.

The application layer remains independent from `marketplace.reference`.

## Authority boundary

This module performs deterministic in-process validation and encoding only. It grants **no runtime activation**, performs **no PostgreSQL connection**, migration, provisioning, or administration, performs **no filesystem asset loading**, environment/secret loading, socket bind/listen/accept/connect, HTTP server execution, browser action, Android build/runtime/sign/install, dependency installation, provider selection, deployment, or service/configuration mutation.

No agreement, acceptance, assent, order, payment, settlement, fulfillment, inventory mutation, ownership transfer, ranking, trust, legitimacy, or authorization semantics are added.

A **merge remains a separate exact-head governance boundary**.
