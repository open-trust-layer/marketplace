# Product M17.6X — Bounded local Ed25519 enrollment attestor keyfile intake

Profile: `MARKETPLACE_REFERENCE_AUTHENTICATION_ENROLLMENT_ED25519_KEYFILE_V1`

Risk: **HIGH security/privacy** source-only local private-key acquisition capability.

## Purpose

M17.6T accepts exactly 32 caller-supplied Ed25519 private-key bytes and creates
one purpose-specific enrollment attestor. M17.6U/V/W deliberately do not define
where those bytes come from.

M17.6X adds one explicit local reference intake:

`canonical local directory → fixed keyfile → exact M17.6T attestor`

The loader returns only the exact existing attestor. It does not return raw
private-key bytes.

## Exact local file contract

The caller supplies one exact non-empty canonical absolute local directory.

The loader reads one fixed direct-child name only:

`authentication-enrollment-ed25519.key`

There is no caller-selected filename, recursion, glob, search path, home
expansion, current-directory fallback, environment/configuration lookup,
registry lookup, URL interpretation, network retrieval, keyring, vault, HSM,
database, or cloud-secret source.

The file must contain **exactly 32 bytes**.

The loader performs one read-only binary open and one bounded read of at most
33 bytes. Empty, short, oversized, non-regular, symlink, reparse, redirected,
or unstable input fails closed.

## Path and identity safety

The directory must resolve canonically to itself and must be a real directory,
not a symlink or reparse point. Windows UNC paths are rejected.

The fixed child must resolve canonically inside that exact directory and must be
a real regular file. File identity is checked by path before open, against the
opened handle, after the bounded read, and by path after close. Directory
identity and canonical resolution are checked again after the read.

There are no retries, sleeps, polling loops, watchers, refreshes, caches,
temporary files, writes, permission changes, ownership changes, renames, or
deletes.

## Private-key handling

The exact 32 bytes are transient process-local construction input to the
existing M17.6T attestor.

Python immutable-byte zeroization is not claimed.

M17.6X does not return those bytes, retain a second raw-key field, serialize
them, log them, persist them, cache them, transmit them, derive another key,
export a public key, generate a key, or perform signing during loading.

Qualification uses only **synthetic non-secret** 32-byte fixtures created in
temporary test directories.

## Failure boundary

All X-owned failures collapse to:

`reference authentication enrollment Ed25519 keyfile unavailable`

Filesystem paths, usernames, OS errors, file identifiers, raw key material,
provider details, and nested exception text are not reflected.

## Non-selection boundary

M17.6X remains **unselected**.

M17.6U, M17.6V, M17.6W, existing startup/launch paths, localhost tooling,
Web, Android, configuration, services, and Moon Company runtime/control-plane
do not import or invoke X.

Therefore this milestone acquires no production secret and activates no
runtime, listener, provider, browser path, Android path, or network surface.

## Explicit non-authority

M17.6X does not authorize creating or generating a real private key, writing or
modifying a keyfile, changing file permissions/ownership/ACLs, choosing a
production directory, reading a production secret during qualification,
environment/config-driven secret discovery, OS keychain/keyring/HSM/vault/cloud
secret integration, runtime/provider activation, Web/Android activation,
PostgreSQL/config/service mutation, publishing, or deployment.

## Moon Company boundary

X is a replaceable Moon Commerce local reference custody intake only.

It grants Moon Company no secret access, key administration, identity/policy
control, runtime execution, provider administration, deployment authority, or
production control.

## Rollback

**source-only rollback:** revert the exact M17.6X merge.

Because X remains unselected and qualification uses synthetic temporary bytes
only, rollback requires no key revocation, secret cleanup, listener shutdown,
database rollback, service restart, browser/device cleanup, provider action, or
deployment rollback.
