"""Unified Marketplace conformance and repository acceptance gate."""
from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Protocol, Sequence

from conformance_manifest import EXPECTED_TOTAL, SUITES, read_olp_pin
from repository_audit import RepositoryAuditError, audit_repository

DEFAULT_TIMEOUT_SECONDS = 90.0
REVIEWED_BUILD_BACKEND_VERSION = "80.9.0"


class GateError(RuntimeError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


class CommandExecutor(Protocol):
    def run(
        self,
        argv: Sequence[str],
        *,
        cwd: Path,
        env: Mapping[str, str],
        timeout: float,
    ) -> subprocess.CompletedProcess[str]: ...


class SubprocessExecutor:
    def run(
        self,
        argv: Sequence[str],
        *,
        cwd: Path,
        env: Mapping[str, str],
        timeout: float,
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            list(argv),
            cwd=cwd,
            env=dict(env),
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )


@dataclass(frozen=True)
class GateConfig:
    repo_root: Path
    olp_root: Path
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS
    replay_generators: bool = True


def _command_text(argv: Sequence[str]) -> str:
    return " ".join(str(part) for part in argv)


def run_checked(
    executor: CommandExecutor,
    argv: Sequence[str],
    *,
    cwd: Path,
    env: Mapping[str, str],
    timeout: float,
    label: str,
) -> subprocess.CompletedProcess[str]:
    if timeout <= 0:
        raise GateError("INVALID_TIMEOUT", "command timeout MUST be greater than zero")
    try:
        result = executor.run(argv, cwd=cwd, env=env, timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        raise GateError(
            "COMMAND_TIMEOUT",
            f"{label} exceeded {timeout:g}s timeout: {_command_text(argv)}",
        ) from exc
    except OSError as exc:
        raise GateError(
            "COMMAND_START_FAILED",
            f"{label} could not start: {_command_text(argv)}: {exc}",
        ) from exc
    if result.returncode != 0:
        details = "\n".join(part for part in (result.stdout.strip(), result.stderr.strip()) if part)
        suffix = f"\n{details}" if details else ""
        raise GateError(
            "COMMAND_FAILED",
            f"{label} failed with exit code {result.returncode}: {_command_text(argv)}{suffix}",
        )
    return result


def _build_environment(config: GateConfig, repo_root: Path | None = None) -> dict[str, str]:
    effective_repo = (repo_root or config.repo_root).resolve()
    env = dict(os.environ)
    python_paths = [
        str((config.olp_root / "src").resolve()),
        str((effective_repo / "src").resolve()),
        str((effective_repo / "tools").resolve()),
    ]
    existing = env.get("PYTHONPATH")
    if existing:
        python_paths.append(existing)
    env["PYTHONPATH"] = os.pathsep.join(python_paths)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return env


def _isolated_install_environment() -> dict[str, str]:
    env = dict(os.environ)
    env.pop("PYTHONPATH", None)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PIP_NO_INDEX"] = "1"
    env["PIP_NO_INPUT"] = "1"
    env["PIP_DISABLE_PIP_VERSION_CHECK"] = "1"
    env["PYTHONNOUSERSITE"] = "1"
    return env


def verify_olp_pin(config: GateConfig, executor: CommandExecutor) -> str:
    olp_root = config.olp_root.resolve()
    if not olp_root.is_dir():
        raise GateError("OLP_ROOT_MISSING", f"OLP root does not exist: {olp_root}")
    if not (olp_root / "src" / "olp").is_dir():
        raise GateError("OLP_SOURCE_MISSING", f"OLP Python source package not found under: {olp_root / 'src'}")
    try:
        expected_pin = read_olp_pin(config.repo_root.resolve())
    except ValueError as exc:
        raise GateError("OLP_PIN_CONFIG", str(exc)) from exc
    result = run_checked(
        executor,
        ("git", "-C", str(olp_root), "rev-parse", "HEAD"),
        cwd=config.repo_root.resolve(),
        env=dict(os.environ),
        timeout=config.timeout_seconds,
        label="OLP source pin check",
    )
    actual_pin = result.stdout.strip()
    if actual_pin != expected_pin:
        raise GateError(
            "OLP_PIN_MISMATCH",
            f"OLP checkout is {actual_pin!r}; Marketplace requires {expected_pin}",
        )
    return expected_pin


def _print_command_output(result: subprocess.CompletedProcess[str]) -> None:
    if result.stdout.strip():
        print(result.stdout.rstrip())
    if result.stderr.strip():
        print(result.stderr.rstrip(), file=sys.stderr)


def _verify_reviewed_build_backend(
    config: GateConfig,
    executor: CommandExecutor,
    *,
    cwd: Path,
    env: Mapping[str, str],
) -> None:
    backend_probe = (
        "import importlib.metadata as m; "
        f"expected={REVIEWED_BUILD_BACKEND_VERSION!r}; "
        "actual=m.version('setuptools'); "
        "raise SystemExit(0 if actual == expected else "
        "f'reviewed setuptools mismatch: expected {expected}, got {actual}')"
    )
    result = run_checked(
        executor,
        (sys.executable, "-I", "-c", backend_probe),
        cwd=cwd,
        env=env,
        timeout=config.timeout_seconds,
        label="reviewed build backend check",
    )
    _print_command_output(result)


def _pip_install_to_target(
    config: GateConfig,
    executor: CommandExecutor,
    *,
    source: Path,
    target: Path,
    cwd: Path,
    env: Mapping[str, str],
    label: str,
) -> None:
    result = run_checked(
        executor,
        (
            sys.executable,
            "-m",
            "pip",
            "install",
            "--no-deps",
            "--no-build-isolation",
            "--target",
            str(target),
            str(source),
        ),
        cwd=cwd,
        env=env,
        timeout=config.timeout_seconds,
        label=label,
    )
    _print_command_output(result)


def run_unit_tests(config: GateConfig, executor: CommandExecutor) -> None:
    print("=== Unit tests ===")
    result = run_checked(
        executor,
        (sys.executable, "-m", "unittest", "discover", "-s", "tests", "-p", "test_*.py", "-v"),
        cwd=config.repo_root.resolve(),
        env=_build_environment(config),
        timeout=config.timeout_seconds,
        label="unit tests",
    )
    _print_command_output(result)


def run_artifact_gate(config: GateConfig, executor: CommandExecutor) -> None:
    """Run the M23 reproducible wheel/content/provenance gate as one isolated subprocess."""
    print("=== Reproducible distribution artifact gate ===")
    env = _isolated_install_environment()
    result = run_checked(
        executor,
        (
            sys.executable,
            str(config.repo_root / "tools" / "package_artifact_gate.py"),
            "--repo-root",
            str(config.repo_root.resolve()),
            "--timeout",
            f"{config.timeout_seconds:g}",
        ),
        cwd=config.repo_root.resolve(),
        env=env,
        timeout=config.timeout_seconds * 3,
        label="reproducible distribution artifact gate",
    )
    _print_command_output(result)


def run_package_smoke(config: GateConfig, executor: CommandExecutor) -> None:
    """Install/import the base runtime without repository import-path leakage."""
    print("=== Isolated runtime package smoke ===")
    repo_root = config.repo_root.resolve()
    with tempfile.TemporaryDirectory(prefix="marketplace-package-smoke-") as temp_dir:
        temp_root = Path(temp_dir).resolve()
        install_target = temp_root / "installed"
        install_target.mkdir()
        install_env = _isolated_install_environment()

        _verify_reviewed_build_backend(config, executor, cwd=temp_root, env=install_env)
        _pip_install_to_target(
            config,
            executor,
            source=repo_root,
            target=install_target,
            cwd=temp_root,
            env=install_env,
            label="isolated runtime package install",
        )

        smoke = """import pathlib, sys
root = pathlib.Path(sys.argv[1]).resolve()
sys.path.insert(0, str(root))
import marketplace
import marketplace.runtime as runtime
for module in (marketplace, runtime):
    origin = pathlib.Path(module.__file__).resolve()
    try:
        origin.relative_to(root)
    except ValueError as exc:
        raise SystemExit(f\"module escaped install target: {module.__name__} -> {origin}\") from exc
for name in (\"MarketplaceRuntime\", \"compose_runtime\", \"create_in_memory_runtime\"):
    if not hasattr(runtime, name):
        raise SystemExit(f\"missing installed runtime API: {name}\")
print(\"isolated runtime import PASS\")
"""
        import_env = dict(os.environ)
        import_env.pop("PYTHONPATH", None)
        import_env["PYTHONDONTWRITEBYTECODE"] = "1"
        import_env["PYTHONNOUSERSITE"] = "1"
        result = run_checked(
            executor,
            (sys.executable, "-I", "-c", smoke, str(install_target)),
            cwd=temp_root,
            env=import_env,
            timeout=config.timeout_seconds,
            label="isolated runtime package import",
        )
        _print_command_output(result)
    print("isolated runtime package smoke PASS")


def run_reference_package_smoke(config: GateConfig, executor: CommandExecutor) -> None:
    """Prove installed reference semantics compose with the exact local OLP source."""
    print("=== Isolated reference-adapter package smoke ===")
    repo_root = config.repo_root.resolve()
    olp_root = config.olp_root.resolve()
    with tempfile.TemporaryDirectory(prefix="marketplace-reference-smoke-") as temp_dir:
        temp_root = Path(temp_dir).resolve()
        install_target = temp_root / "installed"
        install_target.mkdir()
        install_env = _isolated_install_environment()

        _verify_reviewed_build_backend(config, executor, cwd=temp_root, env=install_env)
        _pip_install_to_target(
            config,
            executor,
            source=olp_root,
            target=install_target,
            cwd=temp_root,
            env=install_env,
            label="isolated pinned OLP package install",
        )
        _pip_install_to_target(
            config,
            executor,
            source=repo_root,
            target=install_target,
            cwd=temp_root,
            env=install_env,
            label="isolated Marketplace reference package install",
        )

        smoke = """import pathlib, sys
root = pathlib.Path(sys.argv[1]).resolve()
sys.path.insert(0, str(root))
import olp
import marketplace.reference as reference
import marketplace.runtime as runtime
for module in (olp, reference, runtime):
    origin = pathlib.Path(module.__file__).resolve()
    try:
        origin.relative_to(root)
    except ValueError as exc:
        raise SystemExit(f\"module escaped install target: {module.__name__} -> {origin}\") from exc
from olp import RecordV1

def intent(principal, action):
    return RecordV1.from_mapping({
        \"envelope_version\": 1,
        \"type\": reference.TYPE_INTENT,
        \"content\": {
            \"version\": 1,
            \"issuer\": {\"principal\": principal},
            \"subjects\": [{\"uri\": \"urn:example:item:installed-reference\"}],
            \"action\": {\"id\": action},
            \"terms\": {},
        },
        \"profiles\": [reference.CORE_PROFILE],
    })

with runtime.create_in_memory_runtime(
    validate_record=reference.validate_market_record,
    record_identity_text=reference.record_identity_text,
    evaluate_discovery=reference.evaluate_discovery,
    evaluate_match=reference.evaluate_match,
    max_entries=8,
) as app:
    buy = intent(\"did:example:alice\", \"https://example.test/actions/buy\")
    sell = intent(\"did:example:bob\", \"https://example.test/actions/sell\")
    buy_id = app.node.ingest(buy).record_id
    sell_id = app.node.ingest(sell).record_id
    discovery = app.discovery.discover(
        {\"version\": 1, \"action_ids_any\": [\"https://example.test/actions/sell\"]},
        source=\"urn:example:source:installed-reference\",
        completeness=\"COMPLETE_FOR_DECLARED_SOURCE\",
        freshness=\"FRESH\",
        max_records=8,
    )
    if discovery[\"result_refs\"] != [sell_id]:
        raise SystemExit(\"installed reference discovery result mismatch\")
    match = app.matching.evaluate(
        buy_id,
        sell_id,
        method=\"https://example.test/method/exact-v1\",
        base_status=\"SATISFIED\",
        observations=(),
        evidence_completeness=\"COMPLETE_FOR_METHOD_INPUTS\",
    )
    if match[\"conclusion\"] != \"COMPATIBLE_UNDER_METHOD\":
        raise SystemExit(\"installed reference match conclusion mismatch\")
    if match[\"protocol_truth\"] is not False or match[\"creates_agreement\"] is not False:
        raise SystemExit(\"installed reference match exceeded semantic authority\")
print(\"isolated reference adapter composition PASS\")
"""
        import_env = dict(os.environ)
        import_env.pop("PYTHONPATH", None)
        import_env["PYTHONDONTWRITEBYTECODE"] = "1"
        import_env["PYTHONNOUSERSITE"] = "1"
        result = run_checked(
            executor,
            (sys.executable, "-I", "-c", smoke, str(install_target)),
            cwd=temp_root,
            env=import_env,
            timeout=config.timeout_seconds,
            label="isolated reference-adapter composition",
        )
        _print_command_output(result)
    print("isolated reference-adapter package smoke PASS")


def run_validators(config: GateConfig, executor: CommandExecutor) -> None:
    env = _build_environment(config)
    for suite in SUITES:
        print(f"=== {suite.key.upper()} {suite.title} ===")
        result = run_checked(
            executor,
            (sys.executable, str(config.repo_root / "tools" / suite.validator)),
            cwd=config.repo_root.resolve(),
            env=env,
            timeout=config.timeout_seconds,
            label=f"{suite.key} validator",
        )
        _print_command_output(result)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def replay_generators(config: GateConfig, executor: CommandExecutor) -> None:
    print("=== Deterministic generator replay ===")
    original_hashes = {
        suite.key: _sha256(config.repo_root / "conformance" / "vectors" / suite.vector_file)
        for suite in SUITES
    }
    with tempfile.TemporaryDirectory(prefix="marketplace-conformance-") as temp_dir:
        replay_root = Path(temp_dir) / "marketplace"
        shutil.copytree(
            config.repo_root,
            replay_root,
            ignore=shutil.ignore_patterns(".git", "__pycache__", ".pytest_cache", ".mypy_cache"),
        )
        env = _build_environment(config, repo_root=replay_root)
        for suite in SUITES:
            result = run_checked(
                executor,
                (sys.executable, str(replay_root / "tools" / suite.generator)),
                cwd=replay_root,
                env=env,
                timeout=config.timeout_seconds,
                label=f"{suite.key} deterministic generator",
            )
            if result.stdout.strip():
                print(result.stdout.rstrip())
            generated_path = replay_root / "conformance" / "vectors" / suite.vector_file
            actual_hash = _sha256(generated_path)
            expected_hash = original_hashes[suite.key]
            if actual_hash != expected_hash:
                raise GateError(
                    "NONDETERMINISTIC_VECTOR_REPLAY",
                    f"{suite.key} generator changed {suite.vector_file}: expected {expected_hash}, got {actual_hash}",
                )
            print(f"{suite.key}: deterministic replay PASS ({actual_hash})")


def run_diff_check(config: GateConfig, executor: CommandExecutor) -> None:
    print("=== Git whitespace check ===")
    checks = (
        (("git", "diff", "--check"), "working-tree diff"),
        (("git", "diff", "--cached", "--check"), "staged diff"),
        (("git", "diff", "--check", "HEAD^", "HEAD"), "committed HEAD diff"),
    )
    for argv, label in checks:
        result = run_checked(
            executor,
            argv,
            cwd=config.repo_root.resolve(),
            env=dict(os.environ),
            timeout=config.timeout_seconds,
            label=label,
        )
        _print_command_output(result)
    print("git whitespace checks PASS")


def run_gate(config: GateConfig, executor: CommandExecutor | None = None) -> None:
    if config.timeout_seconds <= 0:
        raise GateError("INVALID_TIMEOUT", "timeout MUST be greater than zero")
    config = GateConfig(
        repo_root=config.repo_root.resolve(),
        olp_root=config.olp_root.resolve(),
        timeout_seconds=config.timeout_seconds,
        replay_generators=config.replay_generators,
    )
    executor = executor or SubprocessExecutor()

    pin = verify_olp_pin(config, executor)
    print(f"OLP source pin PASS: {pin}")

    print("=== Repository audit ===")
    try:
        report = audit_repository(config.repo_root)
    except RepositoryAuditError as exc:
        detail = "\n".join(exc.findings)
        raise GateError("REPOSITORY_AUDIT_FAILED", detail) from exc
    print(
        "Repository audit PASS: "
        f"{report.markdown_files} Markdown / {report.python_files} Python / "
        f"{report.vector_files} vector files / {report.vector_cases} vectors"
    )

    run_unit_tests(config, executor)
    run_artifact_gate(config, executor)
    run_package_smoke(config, executor)
    run_reference_package_smoke(config, executor)
    run_validators(config, executor)
    if config.replay_generators:
        replay_generators(config, executor)
    run_diff_check(config, executor)
    print(f"Marketplace acceptance gate PASS: {EXPECTED_TOTAL}/{EXPECTED_TOTAL} vectors")


def _parser() -> argparse.ArgumentParser:
    repo_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description="Run the complete Marketplace conformance acceptance gate.")
    parser.add_argument(
        "--olp-root",
        type=Path,
        default=Path(os.environ.get("MARKETPLACE_OLP_ROOT", repo_root.parent / "protocol")),
        help="path to an OLP checkout at the pinned source commit",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=DEFAULT_TIMEOUT_SECONDS,
        help=f"per-command timeout in seconds (default: {DEFAULT_TIMEOUT_SECONDS:g})",
    )
    parser.add_argument(
        "--skip-generator-replay",
        action="store_true",
        help="skip byte-for-byte generator replay (for focused local diagnostics only)",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    config = GateConfig(
        repo_root=Path(__file__).resolve().parents[1],
        olp_root=args.olp_root,
        timeout_seconds=args.timeout,
        replay_generators=not args.skip_generator_replay,
    )
    try:
        run_gate(config)
    except GateError as exc:
        print(f"Marketplace acceptance gate FAIL [{exc.code}]: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
