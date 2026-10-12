"""Non-reflective browser error-code shape checks on untrusted API responses."""
from __future__ import annotations

from pathlib import Path
import shutil
import subprocess
import unittest


ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "web" / "app.js"
SESSION = ROOT / "web" / "client_session.js"

NODE_EXERCISE = r'''
"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");

for (const path of process.argv.slice(1)) {
  const source = fs.readFileSync(path, "utf8");
  const start = source.indexOf("function reviewedServerErrorCode(code, status) {");
  assert.ok(start >= 0);
  const end = source.indexOf("\n}\n", start);
  assert.ok(end > start);
  const block = source.slice(start, end + 2);
  const normalize = vm.runInNewContext(block + "\nreviewedServerErrorCode", {});

  assert.equal(normalize("AUTH_SESSION_INVALID", 401), "AUTH_SESSION_INVALID");
  assert.equal(normalize("SYNC_CURSOR_EXPIRED", 409), "SYNC_CURSOR_EXPIRED");
  assert.equal(normalize("APPLICATION_HTTP_RESPONSE_TOO_LARGE", 413), "APPLICATION_HTTP_RESPONSE_TOO_LARGE");
  assert.equal(normalize("NOT_FOUND", 404), "NOT_FOUND");
  assert.equal(normalize("R2D2_401", 400), "R2D2_401");
  const invalid = [
    "secret:Bearer mkt1_sensitive",
    "line1\nline2", "error from /private/provisioning",
    "Ошибка", "<script>alert(1)</script>", "", "a_lower_case",
    "TOO-LONG-ERROR", "x".repeat(81), "A" + "B".repeat(80),
    1, null, {}, [], true,
  ];
  for (const value of invalid) {
    assert.equal(normalize(value, 401), "HTTP_401");
  }
  assert.equal(normalize("server issue", 503), "HTTP_503");
  assert.equal(normalize("bad", 0), "APPLICATION_HTTP_FAILED");
  assert.equal(normalize(undefined, NaN), "APPLICATION_HTTP_FAILED");
  assert.equal(normalize(null, "private/internal"), "APPLICATION_HTTP_FAILED");
  assert.equal(normalize(null, 600), "APPLICATION_HTTP_FAILED");
  assert.equal(normalize(null, 100), "HTTP_100");
}
console.log("status=WEB_SERVER_ERROR_CODE_SHAPE_TESTED_OFFLINE");
'''


class ProductWebServerErrorCodeShapeTests(unittest.TestCase):
    def test_both_web_clients_bound_untrusted_server_error_codes(self) -> None:
        for path in (APP, SESSION):
            with self.subTest(client=path.name):
                source = path.read_text(encoding="utf-8")
                self.assertEqual(source.count("function reviewedServerErrorCode(code, status) {"), 1)
                self.assertIn('/^[A-Z][A-Z0-9_]{1,79}$/.test(code)', source)
                self.assertIn('return "APPLICATION_HTTP_FAILED";', source)
                self.assertIn("Number.isInteger(status)", source)
                self.assertIn("return `HTTP_${status}`;", source)
                self.assertNotIn('typeof code === "string" ? code : `HTTP_${response.status}`', source)

    def test_call_sites_preserve_session_invalidation_and_redaction(self) -> None:
        app = APP.read_text(encoding="utf-8")
        session = SESSION.read_text(encoding="utf-8")
        self.assertIn(
            "throw stableClientError(reviewedServerErrorCode(code, response.status));",
            app,
        )
        self.assertIn(
            "const stableCode = reviewedServerErrorCode(code, response.status);",
            session,
        )
        self.assertIn("session.invalidateForServerCode(stableCode);", session)
        self.assertIn('if (code === "AUTH_SESSION_INVALID") this.clear();', session)
        self.assertLess(
            session.index("const stableCode = reviewedServerErrorCode("),
            session.index("session.invalidateForServerCode(stableCode);"),
        )

    def test_error_code_review_adds_no_io_or_secret_reflection(self) -> None:
        for path in (APP, SESSION):
            source = path.read_text(encoding="utf-8")
            first = source.index("function reviewedServerErrorCode(code, status) {")
            last = source.index("\n}\n", first)
            block = source[first:last]
            for forbidden in (
                "console.", "fetch(", "Bearer", "Authorization", "token",
                "localStorage", "sessionStorage", "document.cookie",
                "JSON.stringify(", "response.text(", "window.", "crypto.",
            ):
                self.assertNotIn(forbidden, block, path.name)

    @unittest.skipUnless(shutil.which("node"), "Node.js unavailable")
    def test_actual_javascript_error_code_fallbacks(self) -> None:
        completed = subprocess.run(
            ["node", "-e", NODE_EXERCISE, str(APP), str(SESSION)],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr[:800])
        self.assertIn(
            "WEB_SERVER_ERROR_CODE_SHAPE_TESTED_OFFLINE",
            completed.stdout,
        )


if __name__ == "__main__":
    unittest.main()
