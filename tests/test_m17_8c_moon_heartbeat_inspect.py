"""M17.8C: Moon heartbeat triage must never manufacture a healthy state."""
from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
from datetime import UTC, datetime, timedelta
import io
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from uuid import uuid4

from tools.marketplace_moon_heartbeat_inspect import (
    HeartbeatInspectionError,
    SERVICE_ID,
    inspect_heartbeat_source,
    main,
)

SHA = "a" * 40
OLD_SHA = "b" * 40
NOW = datetime(2026, 10, 10, 14, 30, tzinfo=UTC)


class MarketplaceMoonHeartbeatInspectTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.directory = self.root / "heartbeats" / SERVICE_ID

    def record(
        self, *, observed: datetime = NOW, version: str = SHA,
        pid: int = 1234, **overrides,
    ) -> Path:
        self.directory.mkdir(parents=True, exist_ok=True)
        instance = str(uuid4())
        body = {
            "moon_version": "0.1",
            "service_id": SERVICE_ID,
            "version": version,
            "environment": "development",
            "instance_id": instance,
            "process_id": pid,
            "started_at": (observed - timedelta(minutes=1)).isoformat(),
            "observed_at": observed.isoformat(),
        }
        body.update(overrides)
        path = self.directory / (instance + ".json")
        path.write_text(json.dumps(body), encoding="utf-8")
        return path

    def check(self, max_age_seconds: int = 45):
        return inspect_heartbeat_source(
            self.root,
            expected_release_sha=SHA,
            max_age_seconds=max_age_seconds,
            at_time=NOW,
        )

    def test_missing_source_not_healthy(self) -> None:
        self.assertEqual(self.check(), ("SOURCE_MISSING", 0, 0))
        self.directory.mkdir(parents=True)
        (self.directory / "relay.json").write_text("{}", encoding="utf-8")
        self.assertEqual(self.check(), ("SOURCE_MISSING", 0, 0))

    def test_fresh_matching_metadata_still_unverified(self) -> None:
        self.record(observed=NOW - timedelta(seconds=12))
        self.assertEqual(self.check(), ("FRESH_METADATA_UNVERIFIED", 12, 1))

    def test_exact_age_boundary(self) -> None:
        self.record(observed=NOW - timedelta(seconds=45))
        self.assertEqual(self.check(), ("FRESH_METADATA_UNVERIFIED", 45, 1))

    def test_stale_record_never_becomes_healthy(self) -> None:
        self.record(observed=NOW - timedelta(days=3))
        code, age, count = self.check()
        self.assertEqual((code, count), ("SOURCE_STALE", 1))
        self.assertGreater(age, 45)

    def test_fresh_wrong_release_is_rejected(self) -> None:
        self.record(version=OLD_SHA)
        self.assertEqual(self.check(), ("RELEASE_MISMATCH", 0, 1))

    def test_future_observation_is_rejected(self) -> None:
        self.record(observed=NOW + timedelta(seconds=6))
        self.assertEqual(self.check(), ("SOURCE_FUTURE", 0, 1))

    def test_valid_development_version_is_mismatched_not_malformed(self) -> None:
        self.record(version="0.0.1.dev0")
        self.assertEqual(self.check(), ("RELEASE_MISMATCH", 0, 1))

    def test_older_stale_record_does_not_erase_newer_fresh_record(self) -> None:
        self.record(observed=NOW - timedelta(days=2), version=OLD_SHA)
        self.record(observed=NOW - timedelta(seconds=5))
        self.assertEqual(self.check(), ("FRESH_METADATA_UNVERIFIED", 5, 2))

    def test_wrong_identity_and_boolean_pid_fail_without_reflection(self) -> None:
        for override in ({"service_id": "other"},
                         {"process_id": True},
                         {"environment": ""},
                         {"instance_id": "invalid"}):
            with self.subTest(override=override):
                for file in self.directory.glob("*.json"):
                    file.unlink()
                self.record(**override)
                with self.assertRaises(HeartbeatInspectionError) as caught:
                    self.check()
                self.assertEqual(caught.exception.code, "SOURCE_INVALID")
                self.assertNotIn("other", str(caught.exception))

    def test_invalid_json_duplicate_member_and_nonfinite_constant_rejected(self) -> None:
        for mutate in (
            lambda s: s[:-1],
            lambda s: s.replace('"process_id": 1234', '"process_id": 99, "process_id": 1234'),
            lambda s: s.replace('"process_id": 1234', '"process_id": NaN'),
        ):
            with self.subTest(mutate=mutate):
                for file in self.directory.glob("*.json"):
                    file.unlink()
                path = self.record()
                path.write_text(mutate(path.read_text(encoding="utf-8")), encoding="utf-8")
                with self.assertRaises(HeartbeatInspectionError) as caught:
                    self.check()
                self.assertEqual(caught.exception.code, "SOURCE_INVALID")

    def test_oversize_record_rejected(self) -> None:
        path = self.record()
        path.write_bytes(b"x" * 4097)
        with self.assertRaises(HeartbeatInspectionError) as caught:
            self.check()
        self.assertEqual(caught.exception.code, "SOURCE_INVALID")

    def test_invalid_source_is_not_hidden_by_fresh_source(self) -> None:
        self.record()
        self.record(pid=True)
        with self.assertRaises(HeartbeatInspectionError) as caught:
            self.check()
        self.assertEqual(caught.exception.code, "SOURCE_INVALID")

    def test_bounded_source_file_count(self) -> None:
        for _ in range(33):
            self.record()
        with self.assertRaises(HeartbeatInspectionError) as caught:
            self.check()
        self.assertEqual(caught.exception.code, "TOO_MANY_FILES")

    def test_bounded_directory_entries_including_temporary_files(self) -> None:
        self.directory.mkdir(parents=True)
        for index in range(65):
            (self.directory / f"old-{index}.tmp").write_bytes(b"")
        with self.assertRaises(HeartbeatInspectionError) as caught:
            self.check()
        self.assertEqual(caught.exception.code, "TOO_MANY_FILES")

    def test_inputs_rejected(self) -> None:
        cases = (
            ({"expected_release_sha": "wrong"}, "RELEASE_SHA_INVALID"),
            ({"max_age_seconds": 0}, "MAX_AGE_INVALID"),
            ({"max_age_seconds": True}, "MAX_AGE_INVALID"),
            ({"at_time": NOW.replace(tzinfo=None)}, "TIME_INVALID"),
            ({"state_root": Path("relative")}, "STATE_ROOT_INVALID"),
        )
        for changes, error_code in cases:
            with self.subTest(changes=changes):
                inputs = {
                    "state_root": self.root, "expected_release_sha": SHA,
                    "max_age_seconds": 45, "at_time": NOW,
                }
                inputs.update(changes)
                with self.assertRaises(HeartbeatInspectionError) as caught:
                    inspect_heartbeat_source(**inputs)
                self.assertEqual(caught.exception.code, error_code)

    def test_cli_never_says_pass_for_fresh_metadata(self) -> None:
        self.record(observed=datetime.now(UTC) - timedelta(seconds=2))
        stdout = io.StringIO()
        stderr = io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            code = main(["--state-root", str(self.root), "--expected-release-sha", SHA])
        self.assertEqual(code, 2)
        self.assertIn("status=UNVERIFIED code=FRESH_METADATA_UNVERIFIED", stdout.getvalue())
        self.assertIn("process_verified=false", stdout.getvalue())
        self.assertNotIn("PASS", stdout.getvalue())
        self.assertEqual(stderr.getvalue(), "")

    def test_cli_reports_stale_without_any_content_or_path(self) -> None:
        self.record(observed=NOW - timedelta(days=3))
        stdout = io.StringIO()
        stderr = io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            code = main(["--state-root", str(self.root), "--expected-release-sha", SHA])
        self.assertEqual(code, 1)
        self.assertIn("status=FAIL code=SOURCE_STALE", stderr.getvalue())
        self.assertEqual(stdout.getvalue(), "")
        self.assertNotIn(str(self.root), stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
