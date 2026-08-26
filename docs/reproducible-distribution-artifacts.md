# Reproducible Distribution Artifact & Provenance Gate

Status: Milestone 23 reference implementation

## Purpose

Milestone 23 hardens the local Python distribution boundary established in Milestones 21 and 22 before any package-registry publication or external federation transport is introduced.

The gate answers one bounded question:

> Given one exact clean Marketplace source checkout, do two independent controlled wheel builds produce the same bytes, and can the resulting wheel be audited and bound to local provenance without registry access, signing credentials, or new runtime authority?

The answer is intentionally narrower than release security.

```text
build success              != reproducible artifact
same package version       != same artifact bytes
wheel filename             != trusted provenance
artifact hash              != semantic authority
reproducible wheel         != published release
provenance report          != cryptographic signature
```

## Unified acceptance integration

`tools/conformance_gate.py` invokes `tools/package_artifact_gate.py` after unit tests and before package-install smokes and semantic validators.

The same unified command remains the acceptance entry point:

```text
python tools/conformance_gate.py --olp-root <path-to-pinned-olp-checkout>
```

M23 does not introduce a second CI policy path. GitHub Actions remains an adapter around the repository-local acceptance command.

## Clean-source provenance precondition

Before building, the artifact gate requires the Marketplace checkout to be clean according to Git status, including untracked files.

This is a provenance integrity rule. Without it, an artifact containing local modifications could be incorrectly labeled with the current `HEAD` commit.

```text
HEAD commit + dirty worktree != exact source provenance
```

A dirty checkout fails closed before artifact creation.

The gate records the exact Git commit checked out by the acceptance environment. In pull-request CI this may be GitHub's synthetic merge commit because that is the exact source tree being tested. On merged `main`, it is the exact merged-main commit being verified.

## Controlled build environment

The wheel is built twice in independent temporary roots from independent copies of the same clean source checkout.

Each copied source tree has filesystem mtimes normalized to the project-fixed epoch:

```text
SOURCE_DATE_EPOCH = 946684800
                    2000-01-01T00:00:00Z
```

The original repository worktree is not mutated.

The build environment fixes or constrains:

```text
setuptools             = 80.9.0 exactly
PIP_NO_INDEX            = 1
PIP_NO_INPUT            = 1
PIP_DISABLE_VERSION_CHECK = 1
PYTHONHASHSEED          = 0
PYTHONNOUSERSITE        = 1
PYTHONDONTWRITEBYTECODE = 1
TZ                      = UTC
LANG                    = C.UTF-8
LC_ALL                  = C.UTF-8
SOURCE_DATE_EPOCH       = 946684800
```

Both wheel builds use:

```text
python -m pip wheel
    --no-deps
    --no-build-isolation
```

No public package-index dependency resolution is permitted by the gate.

## Reproducibility requirement

Each independent build must produce exactly one wheel.

The two outputs must agree on all of the following:

- exact wheel filename;
- SHA-256 digest;
- complete artifact bytes;
- independently derived wheel-audit result.

Any difference fails acceptance.

The expected current wheel filename is derived from the reviewed package metadata and pure-Python platform tag. M23 does not accept a reproducible artifact under an unexpected filename.

## Wheel content audit

The gate opens the wheel with Python standard-library ZIP tooling and rejects unsafe or unexpected archive structure.

The audit requires:

- canonical POSIX member paths;
- no absolute paths;
- no `.` or `..` path components;
- no backslash archive paths;
- no duplicate member names;
- no symlink entries;
- exactly one expected `.dist-info` root;
- only the `marketplace/` package and expected `.dist-info/` top-level roots;
- required runtime modules;
- required packaged M3/M5 reference-adapter modules;
- no console-script or plugin entry-point metadata.

Repository-only material such as `tools/`, `tests/`, `docs/`, `conformance/`, `.github/`, and governance files therefore cannot appear as top-level wheel payload.

## Distribution metadata audit

The built wheel is audited independently of `pyproject.toml`.

Its `METADATA` must report:

```text
Name: open-layer-marketplace
Version: current experimental 0.0.N.devN version
Requires-Dist: absent
Provides-Extra: absent
```

Its `WHEEL` metadata must report a pure-Python distribution with exactly:

```text
Root-Is-Purelib: true
Tag: py3-none-any
```

A platform-specific wheel or dependency-bearing wheel fails acceptance even if the source metadata looked correct.

## RECORD integrity

The gate parses `.dist-info/RECORD` and verifies every non-directory wheel member.

For every member except `RECORD` itself, the gate verifies:

- the recorded algorithm is SHA-256;
- the URL-safe base64 digest matches the actual member bytes;
- the recorded byte size matches the actual member length.

The `RECORD` self-entry must omit its own hash and size.

The set of RECORD entries must exactly cover the wheel's non-directory members. Missing, extra, repeated, tampered, or malformed entries fail closed.

## Normalized payload digest

In addition to the complete wheel SHA-256, M23 derives a normalized payload digest over sorted member names and member-content SHA-256 values, excluding only RECORD itself.

This digest is useful as local acceptance evidence for the verified package payload while the complete wheel digest remains the byte-for-byte artifact identity.

Neither digest is a protocol truth statement or cryptographic signature.

## Local provenance report

After both builds and both audits agree, the gate emits canonical compact JSON with sorted keys.

The current provenance schema includes:

```text
provenance_schema
provenance_version
marketplace_source_commit
olp_source_commit
package_name
package_version
wheel_filename
artifact_sha256
payload_sha256
build_backend.name
build_backend.version
source_date_epoch
declared_runtime_dependency_count
reference_adapters_present
signed
published
verification_scope
```

The source and OLP commit identifiers must be lowercase 40-hex Git commit IDs. The runtime dependency count must remain zero.

The report explicitly states:

```text
signed    = false
published = false
```

Therefore the report must not be described as a signature, third-party attestation, release certificate, registry provenance, or proof of protocol authority.

## Reference semantic boundary

The wheel contains the packaged non-normative M3/M5 helpers established by Milestone 22.

Their presence in a reproducible artifact does not change their authority:

```text
packaged reference validator != protocol authority
packaged reference discovery != global marketplace view
packaged reference match     != protocol truth
compatible under method      != agreement
```

OLP remains the RecordV1 / Record Identity authority at the pinned source boundary, and Marketplace semantic conformance remains governed by the specifications and vector corpus.

## Retention and security impact

M23 does not change Marketplace runtime evidence retention.

The in-memory reference runtime remains EPHEMERAL with the existing default and maximum 10-second post-use retention policy.

Artifact-gate files exist only inside temporary build directories and are removed when the gate exits. The gate does not:

- persist Marketplace records;
- open sockets;
- start servers or background workers;
- read deployment secrets;
- create publishing credentials;
- upload artifacts;
- sign artifacts;
- create GitHub Releases;
- contact package registries;
- execute settlement, fulfillment, agreement formation, or other protected side effects.

## Publication boundary

Milestone 23 intentionally stops before publication.

A future publication milestone must separately review at least:

- release authority;
- registry namespace ownership;
- artifact signing or OIDC/Sigstore provenance;
- credential and token handling;
- release version policy;
- dependency publication/provenance for OLP;
- rollback/yank policy;
- artifact retention and release-record policy.

Likewise, the first external federation transport remains a separate higher-risk milestone requiring authentication, TLS, SSRF/egress restrictions, bounded retries, rate limits, remote-retention rules, and abuse controls.
