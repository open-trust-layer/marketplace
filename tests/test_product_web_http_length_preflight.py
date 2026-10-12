"""Browser/API response Content-Length early rejection, without widening authority."""
from __future__ import annotations

from pathlib import Path
import shutil
import subprocess
import unittest


ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "web" / "app.js"
SESSION = ROOT / "web" / "client_session.js"

NODE_EXERCISE = r"""
"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");

for (const path of process.argv.slice(1)) {
  const source = fs.readFileSync(path, "utf8");
  const start = source.indexOf("function rejectOversizedDeclaredResponse(response) {");
  assert.ok(start >= 0, "preflight function absent");
  const end = source.indexOf("\n}\n", start);
  assert.ok(end > start, "preflight function unterminated");
  const block = source.slice(start, end + 2);
  const preflight = vm.runInNewContext(
    block + "\nrejectOversizedDeclaredResponse",
    {
      MAX_RESPONSE_JSON_BYTES: 300 * 1024,
      stableClientError: (code) => Object.assign(new Error("redacted"), {code}),
    },
  );
  function expectRejected(declared) {
    let observed;
    try {
      preflight({headers: {get: (name) => {
        assert.equal(name, "content-length");
        return declared;
      }}});
    } catch (error) {
      observed = error?.code;
    }
    assert.equal(observed, "APPLICATION_HTTP_RESPONSE_TOO_LARGE");
  }
  function expectAllowed(declared) {
    assert.doesNotThrow(() => preflight({headers: {get: () => declared}}));
  }
  expectRejected(String(300 * 1024 + 1));
  expectRejected("9999999999999999999999999999999999");
  expectAllowed(String(300 * 1024));
  expectAllowed("0");
  expectAllowed("not-a-valid-length");
  expectAllowed("-1");
  expectAllowed(undefined);
  assert.doesNotThrow(() => preflight({}));
}
console.log("status=CONTENT_LENGTH_PREFLIGHT_TESTED_OFFLINE");
"""


class ProductWebHttpLengthPreflightTests(unittest.TestCase):
    def test_both_web_paths_fail_fast_before_materializing_text(self) -> None:
        for path in (APP, SESSION):
            with self.subTest(path=path.name):
                source = path.read_text(encoding="utf-8")
                self.assertEqual(source.count("function rejectOversizedDeclaredResponse(response) {"), 1)
                self.assertIn(
                    "rejectOversizedDeclaredResponse(response);\n  const text = await readBoundedResponseText(response);",
                    source,
                )
                self.assertIn(
                    "new TextEncoder().encode(text).length > MAX_RESPONSE_JSON_BYTES",
                    source,
                )
                self.assertIn(
                    'throw stableClientError("APPLICATION_HTTP_RESPONSE_TOO_LARGE");',
                    source,
                )
                self.assertIn("const MAX_RESPONSE_JSON_BYTES = 300 * 1024;", source)

    def test_preflight_does_not_add_network_or_credential_authority(self) -> None:
        for path in (APP, SESSION):
            source = path.read_text(encoding="utf-8")
            start = source.index("function rejectOversizedDeclaredResponse(response) {")
            end = source.index("\n}\n", start)
            block = source[start:end]
            for forbidden in (
                "fetch(", "Authorization", "credentials", "localStorage",
                "sessionStorage", "document.cookie", "await", "response.text(",
            ):
                self.assertNotIn(forbidden, block, path.name)
            self.assertIn('response.headers?.get?.("content-length")', block)

    @unittest.skipUnless(shutil.which("node"), "Node.js is unavailable for standalone JS behavior check")
    def test_browser_preflight_both_paths_with_real_js(self) -> None:
        completed = subprocess.run(
            ["node", "-e", NODE_EXERCISE, str(APP), str(SESSION)],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr[:1000])
        self.assertIn("CONTENT_LENGTH_PREFLIGHT_TESTED_OFFLINE", completed.stdout)


if __name__ == "__main__":
    unittest.main()
