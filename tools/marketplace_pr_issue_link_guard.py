"""Prevent negated GitHub issue-closing references in Marketplace PR descriptions.

GitHub can interpret a closing keyword even when the surrounding text negates
it. This best-effort, read-only PR event check prevents that known footgun;
it does not decide whether a positively worded closure is justified.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re

MAX_EVENT_BYTES = 256 * 1024

_NEGATED_CLOSURE = re.compile(
    r"\b(?:"
    r"(?:do|does|did|will|would|should|can|could|must)\s+not"
    r"|not|never|cannot|can't|won't|don't|doesn't"
    r")\s+(?:[A-Za-z-]+\s+){0,3}"
    r"(?:close|closes|closed|fix|fixes|fixed|resolve|resolves|resolved)"
    r"\s+(?:(?:[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)?#[0-9]+"
    r"|https://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+/issues/[0-9]+)\b",
    re.IGNORECASE,
)


def has_negated_issue_closure(text: str) -> bool:
    """Detect a proven ambiguous class, without displaying the PR body."""
    return bool(_NEGATED_CLOSURE.search(text))


def check_event_file(path: Path) -> str:
    """Return a stable status; never reflect event contents, paths or errors."""
    try:
        if not path.is_file():
            return "EVENT_UNAVAILABLE"
        with path.open("rb") as stream:
            raw = stream.read(MAX_EVENT_BYTES + 1)
        if len(raw) > MAX_EVENT_BYTES:
            return "EVENT_TOO_LARGE"
        data = json.loads(raw)
        if not isinstance(data, dict):
            return "EVENT_INVALID"
        pull_request = data.get("pull_request")
        if not isinstance(pull_request, dict):
            return "EVENT_INVALID"
        body = pull_request.get("body")
        if body is None:
            body = ""
        if not isinstance(body, str):
            return "EVENT_INVALID"
        if has_negated_issue_closure(body):
            return "NEGATED_ISSUE_CLOSING_REFERENCE"
        return "PASS"
    except (OSError, ValueError, UnicodeError, TypeError):
        return "EVENT_INVALID"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--event-file", default=os.environ.get("GITHUB_EVENT_PATH"))
    args = parser.parse_args()
    result = check_event_file(Path(args.event_file)) if args.event_file else "EVENT_UNAVAILABLE"
    if result != "PASS":
        print(f"status=BLOCKED code={result}")
        return 1
    print("status=PR_ISSUE_LINKS_CHECKED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
