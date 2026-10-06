# Marketplace Moon runtime heartbeat primitive

This repository contains a metadata-only Moon heartbeat primitive for a future explicitly authorized
Marketplace localhost runtime.

## Current activation state

The primitive is **not wired into the accepted localhost bootstrap in this slice** and the root
`moon.manifest.yaml` intentionally remains on `workspace` health. Therefore this source change does
not claim that a Marketplace runtime is active, deployed, production-ready, or observable by Moon.

Runtime activation, server/socket startup, Moon bridge promotion, and deployment remain separate
authorization boundaries.

## Admission semantics

The provider wrapper is intentionally conservative:

1. constructing the wrapper creates no heartbeat;
2. calling the underlying foreground provider creates no heartbeat by itself;
3. the first real HTTP request starts the heartbeat;
4. normal provider return or failure closes the lease and removes the active record.

This means a provider failure before request handling, including a socket-bind failure, cannot create
a false healthy signal. An idle server that has never served a request also remains unobserved.

## Data boundary

The record contains only OPERATIONAL_METADATA:

- Moon schema version;
- service id `hello-world-marketplace`;
- release/version label;
- environment label;
- random runtime instance id;
- process id;
- process start timestamp;
- latest observation timestamp.

It contains no listings, proposals, identities, records, agreement terms, authentication material,
credentials, keys, settlement/payment data, prompts, responses, or participant content.

Records are bounded below 4096 bytes, written atomically, refreshed every 15 seconds by default, and
removed on normal close. Write failure is observability loss only and does not alter Marketplace
runtime behavior.

## Opt-in configuration

The primitive accepts:

- `MARKETPLACE_MOON_HEARTBEAT_ENABLED=1`;
- optional absolute `MARKETPLACE_MOON_STATE_ROOT`;
- optional `MARKETPLACE_RELEASE_SHA`;
- optional `MARKETPLACE_MOON_ENVIRONMENT`.

Unset or `0` heartbeat enablement is inert. Other enablement values fail closed.

## Future integration gate

Before the root Moon manifest can move from `workspace` to heartbeat health, a reviewed runtime
entrypoint must wire this primitive into an explicitly authorized loopback server, and a real HTTP-serving run
must prove end-to-end heartbeat delivery to Moon Core. Until then, Moon should continue reporting
Marketplace runtime health as not declared.
