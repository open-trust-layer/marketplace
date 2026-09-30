# Product M17.6S — Reference enrollment launch with nonce authority and exact-binding policy

Profile: `MARKETPLACE_REFERENCE_AUTHENTICATION_ENROLLMENT_LAUNCH_POLICY_NONCE_V1`

Risk: **HIGH security/privacy** source-only reference composition.

## Purpose

The reviewed enrollment chain now contains three separately governed reference capabilities:

- M17.6Q provides the process-local reference nonce authority;
- M17.6R provides the immutable exact-binding approval policy;
- M17.6O provides the inert reference enrollment launch that accepts caller-supplied collaborators.

M17.6S joins those capabilities only:

`Q + R → O`

The builder accepts one exact authenticated loopback launch plan, one exact immutable tuple of M17.6R approval bindings, one caller-supplied enrollment attestor, one explicit authority value, and one finite evidence lease.

It constructs exactly one Q nonce-authority composition, exactly one R approval policy from the exact caller tuple, and exactly one O launch using the exact Q nonce authority and exact R policy.

## Frozen identity graph

The result retains:

- the exact authenticated launch plan;
- the exact caller binding tuple;
- the exact caller-supplied attestor;
- the exact authority value and evidence lease;
- the exact Q nonce-authority composition;
- the exact R approval policy;
- the exact O reference enrollment launch.

The R policy retains the exact caller binding tuple. O retains the exact authenticated plan, exact Q nonce authority, exact R policy, exact caller attestor, exact authority, and exact evidence lease.

Q remains bound to its exact M17.6P material source and M17.6H nonce authority.

## Zero-consumption boundary

Construction consumes **zero entropy** and performs no nonce issuance or consumption.

It performs no policy decision. It performs no attestation or signing. It samples no runtime clock. It handles no HTTP or ASGI request. It invokes no provider and opens no socket.

The Q replay maps remain empty after construction.

Any dependency or validation failure collapses to the stable non-reflective error:

`reference authentication enrollment launch policy nonce composition failed`

## Authority boundary

M17.6S selects a reviewed process-local nonce authority and a reviewed immutable exact-binding approval policy for one inert reference enrollment launch.

The attestor remains **caller-supplied**. M17.6S does not create or select an attestor implementation, signer, private key, key provider, trust anchor, identity directory, role/group lookup, or policy-administration source.

The reference policy performs only the exact-binding semantics already frozen by M17.6R. M17.6S does not add wildcard, prefix, normalization, directory, membership, or ambient-configuration behavior.

The process-memory nonce semantics and bounds already defined by M17.6H/Q remain unchanged. No persistent, shared, or distributed replay store is introduced.

## Runtime boundary

M17.6S remains **unselected** by M17.6N foreground runtime, Uvicorn/provider paths, startup/CLI/services, Web, Android, configuration, and Moon Company runtime/control-plane.

There is no runtime execution, server-provider invocation, socket creation, bind/listen/accept, localhost smoke run, public-network activity, background worker, service activation, or deployment.

## Data and platform boundary

No filesystem, environment, database, PostgreSQL, SQLite, network, DNS, or provider lookup is introduced. No dependency or workflow widening is required.

No private-key generation, import, export, storage, custody, or use is introduced.

## Moon Company boundary

M17.6S is a replaceable Moon Commerce reference composition only.

It adds no Moon Company runtime/control-plane dependency and grants Moon Company no identity authority, approval-administration authority, signing authority, key custody, session authority, runtime authority, or production authority.

A later separately reviewed milestone may address an attestor implementation or an explicit runtime selection. M17.6S does neither.

## Rollback

**source-only rollback:** revert the exact M17.6S merge.

Because S is inert, unselected, and zero-consumption at construction, rollback requires no nonce/session cleanup, key revocation, trust-store mutation, database rollback, service restart, provider administration, browser/device cleanup, or deployment rollback.
