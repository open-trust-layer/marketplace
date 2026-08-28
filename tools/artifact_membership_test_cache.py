"""Shared real-wheel build for unit-test artifact membership assertions.

This helper only deduplicates identical membership builds inside one unittest
process. The independent reproducible-artifact acceptance gate still performs
its own builds and audits.
"""
from __future__ import annotations

import tempfile
import zipfile
from functools import lru_cache
from pathlib import Path

from package_artifact_gate import _build_wheel


@lru_cache(maxsize=1)
def _cached_distribution_names(repo_root_text: str) -> frozenset[str]:
    repo_root = Path(repo_root_text)
    with tempfile.TemporaryDirectory() as temp_dir:
        wheel = _build_wheel(
            repo_root,
            Path(temp_dir),
            90.0,
            "shared artifact membership wheel",
        )
        with zipfile.ZipFile(wheel, "r") as archive:
            return frozenset(archive.namelist())


def built_distribution_names(repo_root: Path) -> frozenset[str]:
    """Return names from one real wheel build shared by membership tests."""
    return _cached_distribution_names(str(repo_root.resolve()))
