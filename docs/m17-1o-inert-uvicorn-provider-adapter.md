# Product M17.1O — reviewed inert Uvicorn loopback provider adapter

Parent roadmap: #175. Work item: #208. Draft implementation PR: #209.

Baseline is exact merged-green `main` `b1921cb6c744e68f9d2ee8d9c83f5c44bbede4c2` from M17.1N.

## Purpose

M17.1N introduced an explicit foreground execution boundary that accepts an injected ASGI server provider. M17.1O supplies one reviewed concrete provider adapter without installing or activating that provider.

The adapter is source-only and inert until its `run()` method is called by a separately authorized runtime action. Importing `marketplace.application` or `marketplace.application.uvicorn_provider` does not import Uvicorn, bind a socket, read environment configuration, discover files, or start a process.

## Reviewed optional dependency closure

The base package continues to declare `dependencies = []`.

The optional `local-server` extra is exact-pinned to the minimal Uvicorn closure:

- `uvicorn==0.52.4`
- `click==8.5.0`
- `h11==0.16.0`

The Uvicorn `standard` extra is deliberately excluded. In particular, this slice does not admit `httptools`, `python-dotenv`, `PyYAML`, `uvloop`, `watchfiles`, or `websockets` through Uvicorn's standard extra.

The repository audit and reproducible-wheel artifact gate both fail closed against this exact reviewed optional dependency set and wheel metadata. Declaring another optional dependency or changing a version requires a new reviewed source change.

## Provider boundary

`UvicornLoopbackServerProvider` implements the M17.1N provider shape and revalidates the invocation before any third-party import:

- application must be callable;
- host must be exact `127.0.0.1`;
- port must be an exact integer in the reviewed launch range.

Only after validation does the provider lazily import `uvicorn`. Missing, malformed, or failing provider behavior is translated into stable Marketplace errors without reflecting third-party details.

The delegated Uvicorn call is locked to:

- foreground single-worker execution;
- IPv4 loopback only;
- `asyncio` loop and `h11` HTTP implementation;
- ASGI3 interface;
- WebSocket disabled;
- lifespan disabled;
- reload disabled;
- proxy headers disabled and forwarded-address trust empty;
- environment-file loading disabled;
- app-directory mutation disabled;
- TLS inputs absent;
- access log disabled;
- server/date identification headers disabled;
- bounded concurrency `32` and backlog `64`;
- keep-alive timeout `5` seconds;
- graceful-shutdown timeout `10` seconds;
- h11 incomplete-event bound `16384` bytes;
- no arbitrary caller-provided Uvicorn option mapping.

## Tests-first provenance

- initial RED test-only commit: `594cdc6ca8fef8728c916230a816795c2327acd0`;
- exact dependency/provider hardening: `9d3d61496b14bbbd27dac4ecb1c41ebe81fd134a`;
- repository-audit allowlist hardening: `c28220f01d2f18080e7bca99bd3d4eab5db34f9f`;
- wheel metadata/member hardening: `ed14980439b549e5e5279eb9eb00e18b43aaf9fe`.

The initial RED run failed only because `marketplace.application.uvicorn_provider` did not yet exist. All M17.1O hardening above preceded implementation.

## Explicit non-authority

M17.1O does not authorize or perform dependency installation, real Uvicorn import/execution, socket bind/listen/accept/connect, network traffic, browser launch, PostgreSQL activation/migration/provisioning, runtime filesystem asset loading, environment/secret loading, configuration change, service/process restart, Android build/runtime/sign/install/distribution, production deployment, TLS/public exposure, proxy-header trust, multiprocess/reloader/background-worker activation, or any other runtime mutation.

Actual provider installation and first real loopback server activation remain separate capabilities requiring their own risk review and explicit authorization.
