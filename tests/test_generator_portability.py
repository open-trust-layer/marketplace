from __future__ import annotations

import ast
import unittest
from pathlib import Path


class GeneratorPortabilityTests(unittest.TestCase):
    def test_vector_generators_pin_lf_newlines(self) -> None:
        root = Path(__file__).resolve().parents[1]
        generators = tuple(sorted((root / "tools").glob("generate_*vectors.py")))
        self.assertGreater(len(generators), 0)

        checked = 0
        for path in generators:
            tree = ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))
            calls = [
                node
                for node in ast.walk(tree)
                if isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "write_text"
                and isinstance(node.func.value, ast.Name)
                and node.func.value.id == "OUT"
            ]
            self.assertEqual(len(calls), 1, path.name)
            newline_keywords = [
                keyword
                for keyword in calls[0].keywords
                if keyword.arg == "newline"
            ]
            self.assertEqual(len(newline_keywords), 1, path.name)
            value = newline_keywords[0].value
            self.assertIsInstance(value, ast.Constant, path.name)
            self.assertEqual(value.value, "\n", path.name)
            checked += 1

        self.assertEqual(checked, len(generators))


if __name__ == "__main__":
    unittest.main()
