"""Source-only regressions for the reviewed Linux CPython 3.14 evaluator lock."""
from __future__ import annotations

from pathlib import Path
import re
import tomllib
import unittest


ROOT = Path(__file__).resolve().parents[1]
LOCK = ROOT / "docs/evaluator-linux-cp314-requirements.txt"
GUIDE = ROOT / "docs/evaluator-linux-cp314-wheel-lock.md"

# Exact independently observed immutable Linux cp314/x86_64 wheel digests.
EXPECTED = {
    "cffi": ("2.1.1", "b0431303acaea1089ad4b3e9ce4e6518193def1118d4073ca848635ee4ea2e96"),
    "click": ("8.5.0", "255bc9599cf7748b4b1a446ccc735421bd08a2ae529a8b88597d3de5664ee360"),
    "cryptography": ("50.0.1", "51afcfceb15597cf2635068e4ac9a56b2abde622edde17f37d85fd7b5306497a"),
    "h11": ("0.16.0", "63cf8bbe7522de3bf65932fda1d9c2772064ffb3dae62d55932da54b31cb6c86"),
    "psycopg": ("3.3.5", "ce5aa5cdb4f9379f00f487590e5890bfa7df9a164648c969ffa628505e21af4e"),
    "psycopg-binary": ("3.3.5", "f45d77e398542ce0937d9fa3cd9d84e9c5fc6b34c50a66404ae840bada312750"),
    "pycparser": ("3.12", "a076f3f489b39b43ed13563a1dafe42447445bec2e294154ec5c57fcdda4c85e"),
    "uvicorn": ("0.52.4", "f86e41a149d7d05a9969337e3946a9c171c06a5d42680896daaba624aeac8da1"),
}
LINE = re.compile(r"([a-z][a-z0-9-]*)==([0-9]+(?:\.[0-9]+){1,3}) --hash=sha256:([0-9a-f]{64})\Z")


class LinuxCp314EvaluatorWheelLockTests(unittest.TestCase):
    def test_exact_hashed_closure_without_unreviewed_options(self) -> None:
        contents = LOCK.read_text(encoding="utf-8")
        entries = [line.strip() for line in contents.splitlines() if line.strip() and not line.startswith("#")]
        matches = [LINE.fullmatch(line) for line in entries]
        self.assertTrue(all(matches), "unreviewed requirement directive or missing hash")
        parsed = {match.group(1): (match.group(2), match.group(3)) for match in matches if match}
        self.assertEqual(len(parsed), len(entries), "duplicate wheel requirement")
        self.assertEqual(parsed, EXPECTED)
        self.assertEqual(list(parsed), sorted(parsed))

    def test_optional_manifest_pins_are_covered(self) -> None:
        with (ROOT / "pyproject.toml").open("rb") as handle:
            groups = tomllib.load(handle)["project"]["optional-dependencies"]
        self.assertEqual(groups["postgres"], ["psycopg[binary]==3.3.5"])
        self.assertEqual(groups["local-server"], [
            "uvicorn==0.52.4", "click==8.5.0", "h11==0.16.0",
        ])
        self.assertEqual(groups["auth-verify"], ["cryptography==50.0.1"])
        self.assertEqual(EXPECTED["psycopg"][0], EXPECTED["psycopg-binary"][0])

    def test_guide_requires_pinned_offline_install_and_no_authority(self) -> None:
        guide = GUIDE.read_text(encoding="utf-8")
        self.assertIn("--require-hashes", guide)
        self.assertIn("--no-index", guide)
        self.assertIn("--only-binary=:all:", guide)
        self.assertIn("pip check", guide)
        self.assertIn("127.0.0.1", guide)
        self.assertIn("separately authorized", guide)
        self.assertIn("Python versions or architectures", guide)

    def test_lock_does_not_embed_credentials_or_fallback_indexes(self) -> None:
        contents = LOCK.read_text(encoding="utf-8").lower()
        for forbidden in (
            "--extra-index-url", "--trusted-host", "--no-deps",
            "postgresql://", "postgres://", "token=", "password=",
            "http://", "https://", "-e ", "git+",
        ):
            self.assertNotIn(forbidden, contents)


if __name__ == "__main__":
    unittest.main()
