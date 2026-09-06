# M17.3A Android loopback client wiring

Status: source-only implementation checkpoint.

## Product purpose

M17.3A turns the existing Android Compose/API/state skeleton into launchable application source that consumes the same Marketplace application API as the Web MVP.

The Android client does not define a second Marketplace model. It uses the existing `/api/intents`, `/api/product-listings`, `/api/sync`, `/responses`, and `/proposals` application routes and keeps the application sync cursor local to Marketplace coordination.

## Source wiring

`MainActivity` composes:

```text
MainActivity
  -> LoopbackMarketplaceTransport
  -> AndroidMarketplaceJsonCodec
  -> MarketplaceApiClient
  -> MarketplaceState
  -> MarketplaceScreen
```

The Activity performs an initial bounded full resync and maps user actions onto the existing in-memory state operations. UI failures expose only stable client error codes; raw exception/server details are not reflected.

## Development loopback boundary

The concrete source transport has one exact origin:

```text
http://localhost:18080
```

It rejects absolute/network-path request targets, arbitrary hosts, alternate ports, URL fragments, redirects, oversized request/response bodies, and malformed UTF-8 responses.

Android cleartext is denied by default. `network_security_config.xml` grants a cleartext exception only to `localhost`, with subdomains disabled. This narrow exception exists solely for a future explicitly authorized development acceptance using `adb reverse` to the already reviewed Marketplace localhost server.

M17.3A does not authorize `adb reverse` or any other network execution.

## Record identity boundary

Canonical Marketplace application Record JSON intentionally omits `record_id`; Record Identity is not a mutable JSON field.

The Android JSON codec therefore validates the reviewed top-level application Record JSON field profile while retaining the record identity supplied by the reviewed list/route. It does not claim to recompute OLP Record Identity on Android and does not invent a second identity algorithm.

## State and retention

Android Marketplace state remains in-memory only. No SharedPreferences, DataStore, Room database, background worker/service, offline cache, or durable user-content storage is introduced by this slice.

## Dependency boundary

No new Android dependency is declared. M17.3A uses the already reviewed Compose/Activity declarations plus Android/JDK platform APIs and the coroutine types already exposed by the reviewed Compose dependency graph.

No dependency resolution or download is performed by this source-only checkpoint.

## Explicit authority exclusions

This checkpoint provides source wiring only and makes:

- no Android build or APK/AAB claim;
- no Android runtime, emulator, or device claim;
- no install or package-update claim;
- no signing or distribution authority;
- no external/public endpoint authority;
- no external map-provider authority;
- no production deployment authority;
- no payment, settlement, or fulfillment authority.

Android build/runtime/network acceptance requires a separate exact scope authorization after this source change passes repository governance.
