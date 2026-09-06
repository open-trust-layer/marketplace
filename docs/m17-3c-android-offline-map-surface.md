# M17.3C Android offline map surface

M17.3C is a source-only Android presentation change on top of the proven physical-device read/write MVP loop.

## Product goal

Replace the previous Android map placeholder with a real local WGS84 projection that visibly places Marketplace product listings on a bounded map surface.

The Android map intentionally mirrors the reviewed M73 offline web-map contract:

- deterministic equirectangular projection;
- WGS84 microdegree inputs;
- 720 × 360 reference fixture;
- at most 64 rendered listing markers;
- issuer-attributed coordinates remain display data, not verified physical truth.

## Authority boundary

This change adds no external map provider, tile service, device location authority, geocoder, WebView, or map SDK.

It does not change the Marketplace API, loopback endpoint, persistence model, application identity, Android SDK pins, signing, or dependency versions.
## Rendering behavior

Validated local product-listing records are defensively decoded from the existing canonical record JSON already held by `MarketplaceUiState`.

Only records with the reviewed product-listing sell action and exact WGS84-e6 location scheme become markers. Coordinates outside latitude/longitude bounds or non-integer JSON coordinates are ignored rather than projected.

Each marker has a stable local index and can select the same intent detail path already used by the intent list. A textual marker legend keeps title and exact six-decimal coordinates visible even where multiple listings share a projected point.

An empty map explicitly means only that this bounded local view contains no projectable listings; it does not claim global nonexistence.

## Explicitly out of scope

- no Android build;
- no Android runtime;
- no APK install or device action;
- no adb or port forwarding;
- no server or PostgreSQL mutation;
- no network/config/service mutation;
- no dependency installation or update;
- no signing, publishing, distribution, or production deployment.

A later exact-head gate may separately authorize build and physical-device acceptance after source review and CI.
