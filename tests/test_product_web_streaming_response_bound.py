"""Source and live-JS behavioral tests for bounded Web response streaming."""
from __future__ import annotations

from pathlib import Path
import shutil
import subprocess
import unittest


NODE_EXERCISE = r'''
"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const enc = new TextEncoder();
async function run() {
for (const file of process.argv.slice(1)) {
  const src = fs.readFileSync(file, "utf8");
  const start = src.indexOf("async function readBoundedResponseText(response) {");
  assert.ok(start >= 0);
  const end = src.indexOf("\n}\n", start);
  assert.ok(end > start);
  const block = src.slice(start, end + 2);
  const readText = vm.runInNewContext(block + "\nreadBoundedResponseText", {
    TextDecoder, TextEncoder, Uint8Array,
    MAX_RESPONSE_JSON_BYTES: 300 * 1024,
    stableClientError: (code) => Object.assign(new Error("redacted"), {code}),
  });
  function stream(parts, {throwOnRead = false} = {}) {
    let next = 0, reads = 0, cancelled = 0, released = 0;
    const reader = {
      async read() {
        reads++;
        if (throwOnRead) throw new Error("private transport error");
        if (next >= parts.length) return {done: true};
        return {done: false, value: parts[next++]};
      },
      cancel() {cancelled++; return Promise.resolve();},
      releaseLock() {released++;},
    };
    return {
      body: {getReader() {return reader;}},
      text() {throw new Error("text() should never be called on stream path");},
      counters() {return {reads, cancelled, released};},
    };
  }
  {
    const normal = stream([enc.encode("{"),enc.encode("\"ok\":true}")]);
    assert.equal(await readText(normal), "{\"ok\":true}");
    assert.deepEqual(normal.counters(), {reads:3,cancelled:0,released:1});
    const multi = enc.encode("€🌙");
    const multibyte = stream([multi.subarray(0,1),multi.subarray(1,3),multi.subarray(3,5),multi.subarray(5)]);
    assert.equal(await readText(multibyte), "€🌙");
    const boundary = stream([new Uint8Array(150 * 1024),new Uint8Array(150 * 1024)]);
    assert.equal((await readText(boundary)).length, 300 * 1024);
    const oversize = stream([new Uint8Array(300 * 1024),new Uint8Array([65])]);
    await assert.rejects(readText(oversize), error => error.code === "APPLICATION_HTTP_RESPONSE_TOO_LARGE");
    assert.equal(oversize.counters().cancelled, 1);
    assert.equal(oversize.counters().released, 1);
    const dishonest = stream([new Uint8Array(300 * 1024 + 1)]);
    await assert.rejects(readText(dishonest), error => error.code === "APPLICATION_HTTP_RESPONSE_TOO_LARGE");
    const failing = stream([], {throwOnRead:true});
    await assert.rejects(readText(failing), error => error.code === "RESPONSE_BODY_READ_FAILED");
    assert.equal(failing.counters().cancelled, 1);
    const malformed = stream(["not a Uint8Array"]);
    await assert.rejects(readText(malformed), error => error.code === "RESPONSE_BODY_READ_FAILED");
    const noBody = {body:null,async text(){return "{\"legacy\":true}";}};
    assert.equal(await readText(noBody), "{\"legacy\":true}");
    const noStream = {async text(){return "x";}};
    assert.equal(await readText(noStream), "x");
    const tooLongFallback = {body:null,async text(){return "a".repeat(300 * 1024 + 1);}};
    await assert.rejects(readText(tooLongFallback), error => error.code === "APPLICATION_HTTP_RESPONSE_TOO_LARGE");
  }
}
console.log("status=STREAMED_RESPONSE_READER_TESTED_OFFLINE");
}
run().catch(error => {console.error(error); process.exitCode=1;});
'''
APP = ROOT / "web" / "app.js"
SESSION = ROOT / "web" / "client_session.js"

NODE_EXERCISE = """"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const enc = new TextEncoder();
async function run() {
for (const file of process.argv.slice(1)) {
  const src = fs.readFileSync(file, "utf8");
  const start = src.indexOf("async function readBoundedResponseText(response) {");
  assert.ok(start >= 0);
  const end = src.indexOf("\
}\
", start);
  assert.ok(end > start);
  const block = src.slice(start, end + 2);
  const readText = vm.runInNewContext(block + "\
readBoundedResponseText", {
    TextDecoder, TextEncoder, Uint8Array,
    MAX_RESPONSE_JSON_BYTES: 300 * 1024,
    stableClientError: (code) => Object.assign(new Error("redacted"), {code}),
  });
  function stream(parts, {throwOnRead = false} = {}) {
    let next = 0, reads = 0, cancelled = 0, released = 0;
    const reader = {
      async read() {
        reads++;
        if (throwOnRead) throw new Error("private transport error");
        if (next >= parts.length) return {done: true};
        return {done: false, value: parts[next++]};
      },
      cancel() {cancelled++; return Promise.resolve();},
      releaseLock() {released++;},
    };
    return {
      body: {getReader() {return reader;}},
      text() {throw new Error("text() should never be called on stream path");},
      counters() {return {reads, cancelled, released};},
    };
  }
  {
    const normal = stream([enc.encode("{"),enc.encode("\\"ok\\":true}")]);
    assert.equal(await readText(normal), "{\\"ok\\":true}");
    assert.deepEqual(normal.counters(), {reads:3,cancelled:0,released:1});
    const multi = enc.encode("€🌙");
    const multibyte = stream([multi.subarray(0,1),multi.subarray(1,3),multi.subarray(3,5),multi.subarray(5)]);
    assert.equal(await readText(multibyte), "€🌙");
    const boundary = stream([new Uint8Array(150 * 1024),new Uint8Array(150 * 1024)]);
    assert.equal((await readText(boundary)).length, 300 * 1024);
    const oversize = stream([new Uint8Array(300 * 1024),new Uint8Array([65])]);
    await assert.rejects(readText(oversize), error => error.code === "APPLICATION_HTTP_RESPONSE_TOO_LARGE");
    assert.equal(oversize.counters().cancelled, 1);
    assert.equal(oversize.counters().released, 1);
    const dishonest = stream([new Uint8Array(300 * 1024 + 1)]);
    await assert.rejects(readText(dishonest), error => error.code === "APPLICATION_HTTP_RESPONSE_TOO_LARGE");
    const failing = stream([], {throwOnRead:true});
    await assert.rejects(readText(failing), error => error.code === "RESPONSE_BODY_READ_FAILED");
    assert.equal(failing.counters().cancelled, 1);
    const malformed = stream(["not a Uint8Array"]);
    await assert.rejects(readText(malformed), error => error.code === "RESPONSE_BODY_READ_FAILED");
    const noBody = {body:null,async text(){return "{\\"legacy\\":true}";}};
    assert.equal(await readText(noBody), "{\\"legacy\\":true}");
    const noStream = {async text(){return "x";}};
    assert.equal(await readText(noStream), "x");
    const tooLongFallback = {body:null,async text(){return "a".repeat(300 * 1024 + 1);}};
    await assert.rejects(readText(tooLongFallback), error => error.code === "APPLICATION_HTTP_RESPONSE_TOO_LARGE");
  }
}
console.log("status=STREAMED_RESPONSE_READER_TESTED_OFFLINE");
}
run().catch(error => {console.error(error); process.exitCode=1;});"""


class ProductWebStreamingResponseBoundTests(unittest.TestCase):
    def test_both_web_clients_prefer_stream_and_preserve_fallback_bound(self) -> None:
        for path in (APP, SESSION):
            with self.subTest(client=path.name):
                source = path.read_text(encoding="utf-8")
                self.assertEqual(source.count("async function readBoundedResponseText(response) {"), 1)
                self.assertIn("const text = await readBoundedResponseText(response);", source)
                self.assertIn("chunk.value.byteLength > MAX_RESPONSE_JSON_BYTES - receivedBytes", source)
                self.assertIn("decoder.decode(chunk.value, { stream: true })", source)
                self.assertIn("new TextEncoder().encode(text).length > MAX_RESPONSE_JSON_BYTES", source)
                self.assertIn("const text = await response.text();", source)
                self.assertLess(source.index("rejectOversizedDeclaredResponse(response);"), source.index("const text = await readBoundedResponseText(response);"))

    @unittest.skipUnless(shutil.which("node"), "Node.js unavailable")
    def test_real_js_bounded_stream_across_both_web_clients(self) -> None:
        completed = subprocess.run(
            ["node", "-e", NODE_EXERCISE, str(APP), str(SESSION)],
            capture_output=True, text=True, timeout=20, check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr[:1400])
        self.assertIn("STREAMED_RESPONSE_READER_TESTED_OFFLINE", completed.stdout)


if __name__ == "__main__":
    unittest.main()
