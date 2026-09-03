# M17.1E Android build contract

M17.1E adds a reviewed, source-level Android toolchain contract after M17.1D. It deliberately makes **no APK/AAB build claim** on a workstation or CI runner until the pinned toolchain is actually present and verified.

## Reviewed pins

The exact version pins live in `android/toolchain.toml` and are the only reviewed M17.1E toolchain profile:

- JDK 17;
- Gradle 9.6.0;
- Android Gradle Plugin 9.4.0;
- Kotlin 2.4.10;
- compileSdk / targetSdk 37;
- Android SDK Build Tools 36.0.0;
- Compose 1.12.0;
- Material3 1.4.0;
- Activity Compose 1.13.0.

These pins are configuration facts, not proof that the software is installed. There is no automatic toolchain installation in this milestone.

## Validator boundary

`tools/validate_android_toolchain.py --manifest-only` checks only the reviewed manifest and is deterministic and network-inert. The default mode additionally inspects the local PATH and Android SDK directories and fails closed when required components are absent or version-mismatched.

The validator does not download, install, bootstrap, sign, publish, execute an Android device, or contact a live Marketplace backend.

## Future compile CI

A future compile CI lane may claim Android compilation only after it proves the exact reviewed JDK, Gradle, Android SDK platform/build-tools, AGP, Kotlin, and UI dependency versions. That lane must also preserve ordinary Marketplace FULL conformance and merged-main verification.

Adding a Gradle wrapper, dependency resolution, SDK provisioning, APK/AAB packaging, emulator/device execution, or cache policy is a separate reviewed capability. Reproducibility evidence must distinguish source configuration from resolved/downloaded artifacts.

## Authority boundary

M17.1E changes no Marketplace/OLP semantics and adds no transport authority. The M17.1D client remains an injected-transport, raw-reviewed-record JSON boundary with in-memory application state.

This milestone grants **no signing or distribution authority**, no keystore creation/use, no Play Console access, no updater or self-install path, no production deployment, and no runtime mutation.

The current source-only acceptance therefore means: exact version pins are reviewed; the validation contract is deterministic and fail-closed; actual Android compilation remains unproven until a separately reviewed toolchain is available.
