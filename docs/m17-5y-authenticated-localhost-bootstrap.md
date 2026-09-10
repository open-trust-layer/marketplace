# M17.5Y authenticated localhost bootstrap

## Status and baseline

M17.5Y adds the first explicit repo-only wiring from the existing localhost
bootstrap to the reviewed authenticated Marketplace launch/runtime chain.

Implementation baseline is exact merged-green `main`:
`48aee6a85c44b053788b69b423aed99c11ffd5a6`.

That baseline contains M17.5X from PR #309. Its main-push Marketplace
conformance run `34484267463` and acceptance job `102894463992` succeeded.

## Existing behavior retained

The M17.2B modes remain the existing interfaces:

- `--dry-run` remains external-I/O inert;
- `--execute-localhost EXECUTE_MARKETPLACE_LOCALHOST_MVP_V1` remains the
  unauthenticated foreground path;
- loopback host remains exactly `127.0.0.1`;
- existing PostgreSQL DSN, Web-asset and Uvicorn provider boundaries are reused.

M17.5Y does not replace or silently upgrade the M17.2B live mode.

## Authenticated mode

Authenticated execution is a distinct, exact opt-in:

`--execute-authenticated-localhost EXECUTE_AUTHENTICATED_MARKETPLACE_LOCALHOST_MVP_V1`

It also requires one explicit absolute local provisioning directory via
`--authentication-provisioning-directory`.

The authenticated-only argument is not a modifier for dry-run or the existing
unauthenticated live mode. The modes remain mutually exclusive.

## Reviewed authority ordering

The authenticated path is deliberately ordered as follows:

1. validate loopback port, exact M17.5Y token and CLI shape;
2. validate and load M17.5S startup provisioning;
3. compose M17.5Q authentication runtime inputs once;
4. reuse M17.2B DSN, bounded Web assets and lazy PostgreSQL factory;
5. build the authenticated PostgreSQL launch plan once through M17.5X;
6. validate the authenticated launch graph and identity links;
7. select the existing reviewed Uvicorn loopback provider;
8. initialize `plan.startup.http.application` exactly once;
9. delegate once to M17.5V with its exact foreground execution token.

## Fail-closed and non-reflective boundary

Malformed port/token/CLI values fail before provisioning, environment, asset,
PostgreSQL or server providers are selected. Provisioning validation occurs before
DSN and Web-asset access on the authenticated path.

Provider and composition failures collapse to stable M17.5Y bootstrap codes. DSN
text, filesystem paths, provisioning bytes, key/authentication material and provider
exception text are not reflected by the bootstrap.

The M17.5S loader remains authoritative for canonical-directory, reparse/symlink,
stable-file-identity, bounded-read and provisioning-content validation. M17.5Y does
not duplicate or weaken those checks.

## Source/CI boundary

This milestone wires a live-capable source path but does not activate it. Tests and
CI use mocks/synthetic inputs and do not authorize real provisioning mutation,
credential/challenge/session generation, PostgreSQL I/O, socket/server execution,
localhost activation, live authentication acceptance, browser/WebCrypto/wallet or
Android activity, service/configuration mutation, deployment, publishing,
distribution or production/public-network access.

Any real authenticated localhost execution is a separate runtime authorization after
this source change is reviewed, merged and verified on `main`.
