# Marketplace M17.5S — Bounded local authentication startup provisioning

Profile: `MARKETPLACE_APPLICATION_AUTH_STARTUP_PROVISIONING_V1`

Baseline: exact merged-green Marketplace `main`
`9f3ad26537ee346583989fa6d81b8997fd51b38b`.

Authority: owner-authorized **HIGH** local-filesystem trust-material acquisition
capability recorded on Issue #296 and limited to the exact six-file scope below.

## Purpose

M17.5N and M17.5L validate canonical public authentication material, while
M17.5O still requires those bytes to be supplied by a caller. M17.5S defines
one explicit local startup source for those public inputs before any later
startup composition, ASGI selection, launch plan, or server execution.

M17.5S reads exactly three fixed direct-child files from one exact absolute
local directory and returns one immutable provisioning bundle.

It performs no trust verification, no clock read, no credential generation,
no authentication request handling, no application initialization, and
no launch or runtime selection.

## Exact file contract

The loader accepts one exact absolute local directory only. Lexically
non-canonical paths, relative paths, and Windows UNC paths fail closed.

It reads exactly these three fixed names and no caller-selected alternatives:

1. `trust-anchor-manifest.json`
2. `verification-method-claims.json`
3. `verification-method-attestation.bin`

There is no globbing, recursion, current-directory fallback, home expansion,
environment lookup, registry lookup, URL interpretation, package fallback,
or search path.

## Path and identity safety

The supplied directory must resolve canonically to itself. The directory and
each direct child must not be a symlink/reparse object. Every resolved child
must remain canonically contained inside the supplied directory.

Each file is checked before opening, against the opened handle, after its
bounded read, and again by path. A change in stable identity metadata causes
the whole load to fail as unstable file identity.

## Bounded read semantics

Each successful input uses one read-only binary open and one explicit bounded
`max + 1` read. The exact existing predecessor ceilings are reused:

- trust-anchor manifest: 256 KiB;
- verification-method claims: 512 KiB;
- verification-method attestation: 16 KiB.

Empty or oversized inputs fail closed. There are no retries, sleeps, polling,
watchers, refresh loops, caches, temporary files, writes, chmod/chown actions,
or other persistence.

## Canonical validation

After acquisition, the exact M17.5N manifest decoder validates the trust-anchor
bytes and the exact M17.5L claims decoder validates the claims bytes. The exact
claims and attestation bytes are then retained in the existing immutable
`MarketplaceAuthenticationVerificationMethodEvidenceEnvelope`.

Decoded values are validation-only and are not retained as a second source of
truth. Direct construction of the M17.5S bundle repeats canonical validation so
a caller cannot bypass the invariant.

M17.5S does not instantiate the Ed25519 evidence trust verifier, perform
current-time lease acceptance, call M17.5O static authentication composition,
consume M17.5Q runtime inputs, or construct M17.5P/M17.5R HTTP/ASGI objects.

## Failure boundary

All M17.5S-owned failures use one stable public message:

`authentication startup provisioning is invalid or unavailable`

Raw filesystem paths, usernames, OS error text, file identifiers, trust bytes,
attestations, principals, verification methods, host/port values, and provider
details are not reflected. Loading is atomic and returns no partial bundle.

## External-I/O boundary

The only production external I/O introduced by M17.5S is the three bounded,
read-only local file opens/reads described above, plus fail-closed filesystem
metadata checks required to prove path containment and stable identity.

There is no environment, database, socket, HTTP, DNS, subprocess, resolver,
provider, configuration, remote retrieval, redirect, persistence, cache,
background, private-key, signing, ASGI, launch, or runtime/server capability.

## Exact six-file scope

Added:

1. `src/marketplace/application/auth_startup_provisioning.py`
2. `tests/test_m17_5s_auth_startup_provisioning.py`
3. `tests/test_m17_5s_auth_startup_provisioning_artifacts.py`
4. `docs/m17-5s-auth-startup-provisioning.md`

Modified only:

5. `tools/package_artifact_gate.py`
6. `tests/test_package_artifact_gate.py`

No predecessor authentication source, ASGI, launch, runtime-server/provider,
dependency metadata, workflow, repository audit, Web, Android, PostgreSQL,
configuration, or service file changes are authorized or required.

## Qualification

Qualification covers exact types/profile, exact three fixed filenames, exact
predecessor byte ceilings, bounded reads, canonical validation, immutable byte
retention, stable errors, path containment, symlink/reparse rejection, unstable
identity rejection, no alternate acquisition path, and package membership.

Predecessor M17.5B-R conformance remains part of the full Marketplace acceptance
gate. The local workstation may omit the existing optional reviewed
`cryptography` dependency; exact-head CI supplies that reviewed dependency.

## Threat boundary

M17.5S addresses arbitrary-file read authority, fallback search, path traversal,
symlink/reparse substitution, unbounded trust-material reads, unstable file
identity, malformed/non-canonical N/L bytes, path/OS error reflection, and
silent refresh/cache behavior.

It deliberately defers operator directory permissions, trust-anchor rotation
and revocation governance, evidence freshness/replacement policy beyond existing
L lease semantics, one-shot S+Q+O+P+R startup composition, authenticated loopback
launch selection, runtime replacement/rollback, network evidence acquisition,
client private-key custody/signing, and bounded live authentication acceptance.

## Rollback

Rollback is **source-only rollback**: revert the exact eventual M17.5S merge.
The source never writes provisioning material and no launch/runtime entry point
selects it, so rollback requires no trust-store mutation, session cleanup,
service restart, port cleanup, provider action, or external-data deletion.

## Explicit non-authority

M17.5S does not authorize creation, modification, replacement, deletion,
permission changes, or ownership changes for provisioning files. It does not
activate trust, perform trust verification, consume the clock, generate
credentials, execute authentication requests, select ASGI/localhost/host/port,
replace a launch plan, execute a server, or activate any runtime/provider.

It also does not authorize environment/config/registry/database/network intake,
private-key generation/import/export/storage/custody/use/signing, Android action,
PostgreSQL/config/service mutation, production/public-network activity,
deployment, publishing, distribution, or merge.

## Later gates

Only separately authorized later milestones may decide:

1. one-shot startup composition consuming exact S provisioning plus exact Q
   runtime inputs to build exact O -> P -> R without launch/runtime selection;
2. authenticated loopback launch-plan selection using that exact composition;
3. immutable runtime replacement/rollback and trust lifecycle policy;
4. bounded network evidence acquisition under explicit transport policy;
5. bounded live authentication and client signing/custody policy.
