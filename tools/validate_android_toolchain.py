from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import tomllib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "android" / "toolchain.toml"
EXPECTED = {
    "schema_version": 1,
    "jdk_major": 17,
    "gradle": "9.6.0",
    "android_gradle_plugin": "9.4.0",
    "kotlin": "2.4.10",
    "compile_sdk": 37,
    "target_sdk": 37,
    "build_tools": "36.0.0",
    "compose": "1.12.0",
    "material3": "1.4.0",
    "activity_compose": "1.13.0",
}


def load_manifest() -> dict[str, object]:
    data = tomllib.loads(MANIFEST.read_text(encoding="utf-8"))
    if data != EXPECTED:
        raise ValueError("ANDROID_TOOLCHAIN_MANIFEST_DRIFT")
    return data


def command_text(executable: str, *args: str) -> str | None:
    try:
        completed = subprocess.run(
            [executable, *args],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return (completed.stdout + "\n" + completed.stderr).strip()


def validate_environment(data: dict[str, object]) -> int:
    java = shutil.which("java")
    gradle = shutil.which("gradle")
    sdk_text = os.environ.get("ANDROID_SDK_ROOT") or os.environ.get("ANDROID_HOME")
    missing = []
    if java is None:
        missing.append("jdk")
    if gradle is None:
        missing.append("gradle")
    if not sdk_text:
        missing.append("android-sdk")
    if missing:
        print("ANDROID_TOOLCHAIN_UNAVAILABLE:" + ",".join(missing))
        return 2

    java_text = command_text(java, "-version")
    gradle_text = command_text(gradle, "--version")
    sdk_root = Path(sdk_text)
    expected_java = str(data["jdk_major"])
    expected_gradle = str(data["gradle"])
    platform_dir = sdk_root / "platforms" / f"android-{data['compile_sdk']}"
    build_tools_dir = sdk_root / "build-tools" / str(data["build_tools"])

    mismatches = []
    if java_text is None or (
        f'"{expected_java}' not in java_text and f" {expected_java}." not in java_text
    ):
        mismatches.append("jdk")
    if gradle_text is None or f"Gradle {expected_gradle}" not in gradle_text:
        mismatches.append("gradle")
    if not platform_dir.is_dir():
        mismatches.append("platform")
    if not build_tools_dir.is_dir():
        mismatches.append("build-tools")
    if mismatches:
        print("ANDROID_TOOLCHAIN_MISMATCH:" + ",".join(mismatches))
        return 3

    print("ANDROID_TOOLCHAIN_OK")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest-only", action="store_true")
    args = parser.parse_args()
    try:
        data = load_manifest()
    except (OSError, ValueError, tomllib.TOMLDecodeError):
        print("ANDROID_TOOLCHAIN_MANIFEST_INVALID")
        return 1
    if args.manifest_only:
        print("ANDROID_TOOLCHAIN_MANIFEST_OK")
        return 0
    return validate_environment(data)


if __name__ == "__main__":
    raise SystemExit(main())
