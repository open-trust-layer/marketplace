# M17.1F source-only Android Gradle wiring

M17.1F adds the minimum repository-owned Gradle Kotlin DSL declarations around the existing M17.1D Kotlin/Compose source and the reviewed M17.1E toolchain profile.

This checkpoint is **declared build configuration** only. It is **not resolved dependency evidence**, compilation evidence, package evidence, or runtime evidence.

## Declared project shape

- `android/settings.gradle.kts` declares one `:app` module and only standard Gradle/Google/Maven Central repository selectors.
- `android/build.gradle.kts` pins AGP 9.4.0 and Kotlin/Compose plugins 2.4.10.
- `android/app/build.gradle.kts` binds namespace/application ID to `org.opentrustlayer.marketplace`.
- compileSdk / targetSdk are 37 and Build Tools is 36.0.0.
- Java/Kotlin bytecode target is JDK 17.
- Compose is enabled and direct UI dependencies use the reviewed M17.1E versions.

The declarations must remain aligned with `android/toolchain.toml`; deterministic source tests fail closed on drift.

## Evidence boundary

No Gradle command is executed by this milestone. No repository/plugin dependency is resolved or downloaded, and no Gradle wrapper is added or bootstrapped.

The existing M17.1E validator remains the authority for whether the local JDK/Gradle/Android SDK matches the reviewed toolchain. A future compile CI capability must independently prove the resolved dependency graph and actual compiler/package outputs before any Android build claim is permitted.

Accordingly M17.1F makes **no APK/AAB claim** and grants **no signing, installation, distribution, or runtime authority**. It does not authorize emulator/device execution, live Marketplace network access, Play Console use, updater/self-install behavior, production deployment, or runtime mutation.

The Gradle repository selectors are inert source declarations in this checkpoint; activating dependency resolution is a separate reviewed execution capability.
