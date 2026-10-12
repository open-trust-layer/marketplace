"""Ensure rejected Web synchronization pages cannot advance the retained cursor."""
from __future__ import annotations

from pathlib import Path
import shutil
import subprocess
import unittest


ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web" / "app.js"

NODE_EXERCISE = r'''
"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");

const source = fs.readFileSync(process.argv[1], "utf8");
const begin = source.indexOf("async function applySyncPage(documentValue) {");
const end = source.indexOf("\nasync function incrementalSync()", begin);
assert.ok(begin >= 0 && end > begin);
const code = source.slice(begin, end) + "\napplySyncPage";

function fixture(cursor = 10) {
  const state = {syncCursor:cursor};
  const ctx = {
    state,
    SYNC_LIMIT:64,
    stableClientError(code) {return Object.assign(new Error("redacted"), {code});},
    requireRecordId(id) {
      if (typeof id !== "string" || id.length === 0 || id.length > 512) {
        throw Object.assign(new Error("redacted"), {code:"RECORD_ID_INVALID"});
      }
      return id;
    },
    requireCursor(next) {
      if (!Number.isSafeInteger(next) || next < 0) {
        throw Object.assign(new Error("redacted"), {code:"SYNC_CURSOR_INVALID"});
      }
      return next;
    },
  };
  return {state, apply:vm.runInNewContext(code, ctx)};
}

async function rejected(page, initial = 10, expectedCode = "SYNC_PAGE_INVALID") {
  const test = fixture(initial);
  await assert.rejects(test.apply(page), err => err.code === expectedCode);
  assert.equal(test.state.syncCursor, initial, "rejected page advanced the cursor");
}

async function run() {
  const success = fixture();
  assert.equal(await success.apply({
    changes:[
      {record_id:"a",seq:11,change_kind:"UPSERT"},
      {record_id:"b",seq:13,change_kind:"DELETE"},
    ],
    next_cursor:15,has_more:true,
  }), true);
  assert.equal(success.state.syncCursor,15);
  assert.equal(await success.apply({changes:[],next_cursor:15,has_more:false}),false);
  assert.equal(success.state.syncCursor,15);
  const empty = fixture();
  assert.equal(await empty.apply({changes:[],next_cursor:10,has_more:false}),false);
  assert.equal(empty.state.syncCursor,10);

  const good = {record_id:"a",seq:11,change_kind:"UPSERT"};
  await rejected({changes:[good,{record_id:"b",seq:11,change_kind:"DELETE"}],next_cursor:20,has_more:false});
  await rejected({changes:[good,{record_id:"b",seq:12,change_kind:"UNKNOWN"}],next_cursor:20,has_more:false});
  await rejected({changes:[good,null],next_cursor:20,has_more:false});
  await rejected({changes:[good,[]],next_cursor:20,has_more:false});
  await rejected({changes:[good,{record_id:"",seq:12,change_kind:"UPSERT"}],next_cursor:20,has_more:false},10,"RECORD_ID_INVALID");
  await rejected({changes:[good],next_cursor:10,has_more:false});
  await rejected({changes:[good],next_cursor:14,has_more:"false"});
  await rejected({changes:[good],next_cursor:-1,has_more:false},10,"SYNC_CURSOR_INVALID");
  await rejected({changes:[good],next_cursor:11.5,has_more:false},10,"SYNC_CURSOR_INVALID");
  await rejected({changes:[good],next_cursor:11,has_more:null});
  await rejected({changes:[good],next_cursor:11});
  await rejected({changes:null,next_cursor:11,has_more:false});
  await rejected({changes:new Array(65).fill(good),next_cursor:100,has_more:false});
  await rejected(null);
  await rejected([]);
  await rejected("malformed");
}
run().then(
  () => console.log("status=SYNC_PAGE_ATOMIC_CURSOR_TESTED_OFFLINE"),
  error => {console.error(error);process.exitCode=1;},
);
'''


class WebAtomicSyncPageCursorTests(unittest.TestCase):
    def test_cursor_only_committed_after_complete_validation(self) -> None:
        source = WEB.read_text(encoding="utf-8")
        block = source.split("async function applySyncPage(documentValue) {", 1)[1].split(
            "\nasync function incrementalSync()", 1
        )[0]
        self.assertIn("let candidateCursor = state.syncCursor;", block)
        self.assertIn("candidateCursor = change.seq;", block)
        self.assertIn("change.seq <= candidateCursor", block)
        self.assertIn("nextCursor < candidateCursor", block)
        self.assertIn("typeof documentValue.has_more !== \"boolean\"", block)
        self.assertEqual(block.count("state.syncCursor ="), 1)
        self.assertLess(block.index("typeof documentValue.has_more"), block.index("state.syncCursor = nextCursor;"))

    @unittest.skipUnless(shutil.which("node"), "Node.js unavailable")
    def test_real_js_rejected_pages_preserve_cursor(self) -> None:
        result = subprocess.run(
            ["node", "-e", NODE_EXERCISE, str(WEB)],
            text=True,capture_output=True,timeout=20,check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr[:1700])
        self.assertIn("SYNC_PAGE_ATOMIC_CURSOR_TESTED_OFFLINE", result.stdout)


if __name__ == "__main__":
    unittest.main()
