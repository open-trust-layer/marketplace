"""Evidence V1 browser CI labels must be canonical decimal-safe integers."""
from __future__ import annotations

from pathlib import Path
import shutil
import subprocess
import unittest


ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "web" / "app.js"

NODE_TEST = r"""
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import vm from "node:vm";

const app = await readFile(process.argv[1], "utf8");
const begin = app.indexOf("function reviewedEvidenceCiRunNumber() {");
const end = app.indexOf("\nfunction renderAuthenticatedFlightEvidencePreview()", begin);
assert.ok(begin >= 0 && end > begin);
const helper = app.slice(begin, end);

function parse(value) {
  return vm.runInNewContext(
    helper + "\nreviewedEvidenceCiRunNumber()",
    { evidenceCiRunNumberInput: { value } },
    { timeout: 1000 },
  );
}

for (const [value, expected] of [
  ["1", 1],
  ["958", 958],
  ["9007199254740991", Number.MAX_SAFE_INTEGER],
  ["0", null],
  ["00", null],
  ["01", null],
  ["1e2", null],
  ["0x10", null],
  ["1.0", null],
  ["1.5", null],
  ["+1", null],
  ["-1", null],
  [" 1", null],
  ["1 ", null],
  ["", null],
  ["9007199254740992", null],
  ["12345678901234567", null],
  ["Infinity", null],
  ["١", null],
]) {
  assert.equal(parse(value), expected, "wrong result for " + JSON.stringify(value));
}
assert.ok(app.includes("const ciRunNumber = reviewedEvidenceCiRunNumber();"));
assert.ok(app.includes("const ciReady = ciRunNumber !== null;"));
assert.ok(app.includes("reviewedEvidenceCiRunNumber() !== ciRunNumber"));
assert.ok(app.includes("documentValue.ci_run_number === reviewedEvidenceCiRunNumber()"));
assert.ok(!app.includes("Number(evidenceCiRunNumberInput.value)"));
console.log("REVIEWED_DECIMAL_CI_RUN_NUMBER_PASS");
"""


@unittest.skipUnless(shutil.which("node"), "Node.js required for executable Web contract")
class EvidenceCiDecimalLiteralTests(unittest.TestCase):
    def test_browser_only_accepts_canonical_positive_decimal_run_numbers(self) -> None:
        result = subprocess.run(
            ["node", "--input-type=module", "-e", NODE_TEST, str(APP)],
            cwd=ROOT,
            text=True,
            capture_output=True,
            timeout=15,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr[-1700:])
        self.assertEqual(result.stdout.strip(), "REVIEWED_DECIMAL_CI_RUN_NUMBER_PASS")


if __name__ == "__main__":
    unittest.main()
