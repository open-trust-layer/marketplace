"""Offline contract checks for GitHub's negated PR issue-closure footgun."""

from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from tools.marketplace_pr_issue_link_guard import (
    MAX_EVENT_BYTES,
    check_event_file,
    has_negated_issue_closure,
)


class MarketplacePRIssueLinkGuardTests(unittest.TestCase):
    def test_negated_closing_keywords_are_rejected(self) -> None:
        for body in (
            "This documentation PR does not close #525.",
            "This patch will not fix #528.",
            "This does not resolve open-trust-layer/marketplace#525.",
            "We do not intend to close #525.",
            "Not closing this yet; this change does not close #7.",
            "Please never close https://github.com/open-trust-layer/marketplace/issues/525.",
            "This doesn't fix #123.",
        ):
            with self.subTest(body=body):
                self.assertTrue(has_negated_issue_closure(body))

    def test_neutral_and_genuine_positive_references_are_allowed(self) -> None:
        for body in (
            "Tracks #525; browser acceptance remains pending.",
            "Related: https://github.com/open-trust-layer/marketplace/issues/525",
            "Fixes #28 after validating all criteria.",
            "Resolves open-trust-layer/marketplace#42.",
            "No runtime activation; fixes #23.",
            "No changes to auth. Closes #19.",
            "",
        ):
            with self.subTest(body=body):
                self.assertFalse(has_negated_issue_closure(body))

    def test_safe_event_passes_without_emitting_body(self) -> None:
        with TemporaryDirectory() as tmp:
            file = Path(tmp) / "event.json"
            file.write_text(
                json.dumps({"pull_request": {"body": "Tracks #525; not yet accepted."}}),
                encoding="utf-8",
            )
            self.assertEqual(check_event_file(file), "PASS")

    def test_negated_event_is_blocked(self) -> None:
        with TemporaryDirectory() as tmp:
            file = Path(tmp) / "event.json"
            file.write_text(
                json.dumps({"pull_request": {"body": "This does not close #525."}}),
                encoding="utf-8",
            )
            self.assertEqual(check_event_file(file), "NEGATED_ISSUE_CLOSING_REFERENCE")

    def test_missing_or_malformed_event_fails_closed(self) -> None:
        with TemporaryDirectory() as tmp:
            file = Path(tmp) / "event.json"
            self.assertEqual(check_event_file(file), "EVENT_UNAVAILABLE")
            for content in ('[1, 2]', '{"pull_request": []}', "{", '{"pull_request":{"body":123}}'):
                with self.subTest(content=content):
                    file.write_text(content, encoding="utf-8")
                    self.assertEqual(check_event_file(file), "EVENT_INVALID")

    def test_bounded_file_read(self) -> None:
        with TemporaryDirectory() as tmp:
            file = Path(tmp) / "event.json"
            file.write_bytes(b"x" * (MAX_EVENT_BYTES + 1))
            self.assertEqual(check_event_file(file), "EVENT_TOO_LARGE")


if __name__ == "__main__":
    unittest.main()
