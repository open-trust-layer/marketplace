"""Deterministic, side-effect-free repository audits for Marketplace acceptance."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import unquote

from conformance_manifest import SUITES, read_olp_pin

_LINK_RE = re.compile(r"(?<!!)\[[^\]]+\]\(([^)]+)\)")
_FENCE_RE = re.compile(r"^\s*(`{3,}|~{3,})")
_URI_SCHEME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:")
_ALLOWED_CONTROLS = {"\n", "\r", "\t"}
_REQUIRED_GOVERNANCE_FILES = (
    Path("DEVELOPMENT_POLICY.md"),
    Path("docs/RETENTION_POLICY.md"),
    Path("docs/REPOSITORY_GOVERNANCE.md"),
    Path(".github/CODEOWNERS"),
    Path(".github/pull_request_template.md"),
)


@dataclass(frozen=True)
class AuditReport:
    markdown_files: int
    python_files: int
    vector_files: int
    vector_cases: int


class RepositoryAuditError(ValueError):
    def __init__(self, findings: list[str]):
        super().__init__("repository audit failed")
        self.findings = tuple(findings)


def _read_utf8(path: Path, findings: list[str]) -> str | None:
    try:
        raw = path.read_bytes()
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        findings.append(f"UTF8_DECODE {path}: {exc}")
        return None
    if "\ufffd" in text:
        findings.append(f"UTF8_REPLACEMENT {path}: contains replacement character")
    for index, ch in enumerate(text):
        if ord(ch) < 32 and ch not in _ALLOWED_CONTROLS:
            findings.append(f"CONTROL_CHARACTER {path}: U+{ord(ch):04X} at character {index}")
            break
    return text


def _audit_fences(path: Path, text: str, findings: list[str]) -> None:
    active_char: str | None = None
    active_len = 0
    active_line = 0
    for line_number, line in enumerate(text.splitlines(), start=1):
        match = _FENCE_RE.match(line)
        if not match:
            continue
        token = match.group(1)
        char = token[0]
        if active_char is None:
            active_char = char
            active_len = len(token)
            active_line = line_number
        elif char == active_char and len(token) >= active_len:
            active_char = None
            active_len = 0
            active_line = 0
    if active_char is not None:
        findings.append(f"UNBALANCED_FENCE {path}:{active_line}")


def _audit_links(repo_root: Path, path: Path, text: str, findings: list[str]) -> None:
    for match in _LINK_RE.finditer(text):
        raw_target = match.group(1).strip()
        if not raw_target or raw_target.startswith(("#", "<")) or _URI_SCHEME_RE.match(raw_target):
            continue
        target = raw_target.split("#", 1)[0].split("?", 1)[0]
        if not target:
            continue
        target_path = Path(unquote(target.replace("\\", "/")))
        resolved = (path.parent / target_path).resolve()
        try:
            resolved.relative_to(repo_root.resolve())
        except ValueError:
            findings.append(f"LINK_ESCAPES_REPOSITORY {path}: {raw_target}")
            continue
        if not resolved.exists():
            findings.append(f"BROKEN_LINK {path}: {raw_target}")


def _audit_required_governance_files(repo_root: Path, findings: list[str]) -> None:
    for relative_path in _REQUIRED_GOVERNANCE_FILES:
        path = repo_root / relative_path
        if not path.is_file():
            findings.append(f"MISSING_GOVERNANCE_FILE {relative_path.as_posix()}")


def _collect_top_level_case_ids(document: object, path: Path, findings: list[str]) -> list[str]:
    if not isinstance(document, dict):
        findings.append(f"VECTOR_ROOT {path}: top-level JSON value MUST be an object")
        return []
    ids: list[str] = []
    for key, value in document.items():
        if not isinstance(value, list) or not value:
            continue
        if not all(isinstance(item, dict) and "id" in item for item in value):
            continue
        for item in value:
            case_id = item.get("id")
            if not isinstance(case_id, str) or not case_id:
                findings.append(f"VECTOR_ID {path}: {key} contains a non-text/empty id")
                continue
            ids.append(case_id)
    return ids


def _audit_vector(path: Path, expected_pin: str, expected_count: int, findings: list[str]) -> int:
    text = _read_utf8(path, findings)
    if text is None:
        return 0
    try:
        document = json.loads(text)
    except json.JSONDecodeError as exc:
        findings.append(f"JSON_PARSE {path}: {exc}")
        return 0
    if not isinstance(document, dict):
        findings.append(f"VECTOR_ROOT {path}: top-level JSON value MUST be an object")
        return 0
    if document.get("olp_reference_source_commit") != expected_pin:
        findings.append(f"OLP_PIN_MISMATCH {path}: vector pin does not match {expected_pin}")
    fmt = document.get("format")
    if not isinstance(fmt, str) or not fmt:
        findings.append(f"VECTOR_FORMAT {path}: missing non-empty format discriminator")
    ids = _collect_top_level_case_ids(document, path, findings)
    if len(ids) != len(set(ids)):
        findings.append(f"DUPLICATE_VECTOR_ID {path}: case ids MUST be unique within the vector file")
    if len(ids) != expected_count:
        findings.append(f"VECTOR_COUNT {path}: expected {expected_count}, found {len(ids)}")
    return len(ids)


def _audit_python(path: Path, text: str, findings: list[str]) -> None:
    try:
        compile(text, str(path), "exec", dont_inherit=True)
    except SyntaxError as exc:
        findings.append(f"PYTHON_COMPILE {path}:{exc.lineno}: {exc.msg}")


def audit_repository(repo_root: Path) -> AuditReport:
    """Audit deterministic repository invariants without mutating the worktree."""
    repo_root = repo_root.resolve()
    findings: list[str] = []
    try:
        expected_pin = read_olp_pin(repo_root)
    except ValueError as exc:
        raise RepositoryAuditError([f"OLP_PIN_CONFIG {exc}"]) from exc

    _audit_required_governance_files(repo_root, findings)

    markdown_files = sorted(
        path for path in repo_root.rglob("*.md")
        if ".git" not in path.parts and "__pycache__" not in path.parts
    )
    for path in markdown_files:
        text = _read_utf8(path, findings)
        if text is None:
            continue
        _audit_fences(path, text, findings)
        _audit_links(repo_root, path, text, findings)

    python_files = sorted(
        [*repo_root.glob("tools/*.py"), *repo_root.glob("tests/*.py")]
    )
    for path in python_files:
        text = _read_utf8(path, findings)
        if text is None:
            continue
        _audit_python(path, text, findings)

    vector_cases = 0
    for suite in SUITES:
        path = repo_root / "conformance" / "vectors" / suite.vector_file
        if not path.is_file():
            findings.append(f"MISSING_VECTOR_FILE {path}")
            continue
        vector_cases += _audit_vector(path, expected_pin, suite.expected_count, findings)

    if findings:
        raise RepositoryAuditError(findings)
    return AuditReport(
        markdown_files=len(markdown_files),
        python_files=len(python_files),
        vector_files=len(SUITES),
        vector_cases=vector_cases,
    )


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    try:
        report = audit_repository(repo_root)
    except RepositoryAuditError as exc:
        for finding in exc.findings:
            print(f"ERROR: {finding}")
        return 1
    print(
        "Repository audit PASS: "
        f"{report.markdown_files} Markdown / "
        f"{report.python_files} Python / "
        f"{report.vector_files} vector files / "
        f"{report.vector_cases} vectors"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
