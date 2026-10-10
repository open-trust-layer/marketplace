"""Strict, metadata-only triage of opt-in Marketplace Moon heartbeat files.

This tool NEVER verifies process liveness, starts a service, touches timestamps,
imports a runtime provider, or sends network traffic. No result is HEALTHY.
"""
from __future__ import annotations

import argparse
from datetime import UTC, datetime, timedelta
import json
from pathlib import Path
import re
import stat
import sys
from uuid import UUID

SERVICE_ID = "hello-world-marketplace"
MAX_FILES = 32
MAX_DIRECTORY_ENTRIES = 64
MAX_BYTES = 4096
MAX_FUTURE_SECONDS = 5
FIELDS = frozenset({
    "moon_version", "service_id", "version", "environment", "instance_id",
    "process_id", "started_at", "observed_at",
})


class HeartbeatInspectionError(RuntimeError):
    """Stable, non-content-bearing diagnostic."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def _invalid(_constant: str) -> None:
    raise HeartbeatInspectionError("SOURCE_INVALID")


def _unique_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise HeartbeatInspectionError("SOURCE_INVALID")
        result[key] = value
    return result


def _timestamp(value: object) -> datetime:
    if type(value) is not str or len(value) > 40:
        raise HeartbeatInspectionError("SOURCE_INVALID")
    try:
        result = datetime.fromisoformat(value)
        if result.tzinfo is None or result.utcoffset() != timedelta(0):
            raise ValueError("not UTC")
    except (TypeError, ValueError):
        raise HeartbeatInspectionError("SOURCE_INVALID") from None
    return result.astimezone(UTC)


def _read_record(path: Path) -> tuple[str, datetime]:
    try:
        metadata = path.lstat()
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_size > MAX_BYTES:
            raise HeartbeatInspectionError("SOURCE_INVALID")
        # Bound the actual read as well as lstat: a file may grow after stat.
        with path.open("rb") as handle:
            raw = handle.read(MAX_BYTES + 1)
        if len(raw) > MAX_BYTES:
            raise HeartbeatInspectionError("SOURCE_INVALID")
        value = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_unique_keys,
            parse_constant=_invalid,
        )
        if type(value) is not dict or set(value) != FIELDS:
            raise HeartbeatInspectionError("SOURCE_INVALID")
        if value["moon_version"] != "0.1" or value["service_id"] != SERVICE_ID:
            raise HeartbeatInspectionError("SOURCE_INVALID")
        if (type(value["process_id"]) is not int
                or not 1 <= value["process_id"] <= 2_147_483_647):
            raise HeartbeatInspectionError("SOURCE_INVALID")
        if (type(value["environment"]) is not str
                or not 1 <= len(value["environment"]) <= 64):
            raise HeartbeatInspectionError("SOURCE_INVALID")
        version = value["version"]
        # The producer also supports the metadata-only development default.
        # Such a valid source is classified as RELEASE_MISMATCH when it does
        # not match the exact 40-hex expected release.
        if type(version) is not str or not 1 <= len(version) <= 64:
            raise HeartbeatInspectionError("SOURCE_INVALID")
        instance_id = value["instance_id"]
        if type(instance_id) is not str or len(instance_id) != 36:
            raise HeartbeatInspectionError("SOURCE_INVALID")
        if str(UUID(instance_id)) != instance_id or path.name != instance_id + ".json":
            raise HeartbeatInspectionError("SOURCE_INVALID")
        started = _timestamp(value["started_at"])
        observed = _timestamp(value["observed_at"])
        if observed < started:
            raise HeartbeatInspectionError("SOURCE_INVALID")
        return version, observed
    except HeartbeatInspectionError:
        raise
    except (OSError, ValueError, UnicodeError, json.JSONDecodeError):
        raise HeartbeatInspectionError("SOURCE_INVALID") from None


def inspect_heartbeat_source(
    state_root: Path,
    *,
    expected_release_sha: str,
    at_time: datetime,
    max_age_seconds: int = 45,
) -> tuple[str, int, int]:
    """Return (stable code, observed age, file count); never return HEALTHY."""
    if (not isinstance(state_root, Path) or not state_root.is_absolute()
            or len(str(state_root)) > 4096):
        raise HeartbeatInspectionError("STATE_ROOT_INVALID")
    if (type(expected_release_sha) is not str
            or not re.fullmatch(r"[0-9a-f]{40}", expected_release_sha)):
        raise HeartbeatInspectionError("RELEASE_SHA_INVALID")
    if type(max_age_seconds) is not int or not 1 <= max_age_seconds <= 300:
        raise HeartbeatInspectionError("MAX_AGE_INVALID")
    if (not isinstance(at_time, datetime) or at_time.tzinfo is None
            or at_time.utcoffset() != timedelta(0)):
        raise HeartbeatInspectionError("TIME_INVALID")

    directory = state_root / "heartbeats" / SERVICE_ID
    try:
        if not directory.exists():
            return "SOURCE_MISSING", 0, 0
        if not stat.S_ISDIR(directory.lstat().st_mode):
            raise HeartbeatInspectionError("SOURCE_INVALID")
        source_files: list[Path] = []
        scanned = 0
        for entry in directory.iterdir():
            scanned += 1
            if scanned > MAX_DIRECTORY_ENTRIES:
                raise HeartbeatInspectionError("TOO_MANY_FILES")
            # The relay.json receiver snapshot is NOT a source heartbeat.
            if entry.name == "relay.json" or entry.name.endswith(".tmp"):
                continue
            if not entry.name.endswith(".json"):
                raise HeartbeatInspectionError("SOURCE_INVALID")
            source_files.append(entry)
            if len(source_files) > MAX_FILES:
                raise HeartbeatInspectionError("TOO_MANY_FILES")
        if not source_files:
            return "SOURCE_MISSING", 0, 0
        # Validate every source; an ambiguous malformed record is never ignored.
        records = [_read_record(path) for path in source_files]
    except HeartbeatInspectionError:
        raise
    except OSError:
        raise HeartbeatInspectionError("SOURCE_UNAVAILABLE") from None

    version, observed = max(records, key=lambda item: item[1])
    seconds = (at_time - observed).total_seconds()
    if seconds < -MAX_FUTURE_SECONDS:
        return "SOURCE_FUTURE", 0, len(records)
    age = max(0, int(seconds))
    if seconds > max_age_seconds:
        return "SOURCE_STALE", age, len(records)
    if version != expected_release_sha:
        return "RELEASE_MISMATCH", age, len(records)
    # Fresh metadata still cannot prove PID existence, process start identity,
    # socket provenance, supervisor status or application responsiveness.
    return "FRESH_METADATA_UNVERIFIED", age, len(records)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Read-only Marketplace heartbeat metadata triage; never declares a service healthy."
    )
    parser.add_argument("--state-root", type=Path, required=True)
    parser.add_argument("--expected-release-sha", required=True)
    parser.add_argument("--max-age-seconds", type=int, default=45)
    args = parser.parse_args(argv)
    try:
        code, age, count = inspect_heartbeat_source(
            args.state_root,
            expected_release_sha=args.expected_release_sha,
            max_age_seconds=args.max_age_seconds,
            at_time=datetime.now(UTC),
        )
    except HeartbeatInspectionError as error:
        print(f"status=FAIL code={error.code}", file=sys.stderr)
        return 1
    if code == "FRESH_METADATA_UNVERIFIED":
        print(
            f"status=UNVERIFIED code={code} age_seconds={age} source_files={count} "
            "process_verified=false relay_verified=false server_invoked=false"
        )
        return 2
    print(
        f"status=FAIL code={code} age_seconds={age} source_files={count} "
        "process_verified=false relay_verified=false server_invoked=false",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
