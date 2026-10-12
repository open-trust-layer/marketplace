"""Offline real-JavaScript regression for fail-closed full-list hydration identity."""
from __future__ import annotations

from pathlib import Path
import shutil
import subprocess
import unittest


ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "web" / "app.js"

NODE_EXERCISE = r'''
"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const source = fs.readFileSync(process.argv[1], "utf8");
const start = source.indexOf("async function hydrateCurrentIntents() {");
const end = source.indexOf("\nasync function fullResync()", start);
assert.ok(start >= 0 && end > start);
const isolated = source.slice(start, end) + "\nhydrateCurrentIntents";

function fixture(fetchImpl, selectedId = "previous") {
  const oldRecord = {kind:"previous"};
  const old = new Map([["previous", oldRecord]]);
  let cleared = 0;
  const state = {
    records:old,selectedId,selectedRecord:oldRecord,truncated:true,
  };
  const ctx = {
    state,
    MAX_LIST_PAGES:4,
    PAGE_LIMIT:64,
    API_INTENTS:"/api/intents",
    apiFetch:fetchImpl,
    requireRecordId(value) {
      if (typeof value !== "string" || !value.length || value.length > 512) {
        throw Object.assign(new Error("redacted"), {code:"RECORD_ID_INVALID"});
      }
      return value;
    },
    stableClientError(code) {return Object.assign(new Error("redacted"), {code});},
    responseList:{replaceChildren(){cleared++;}},
  };
  return {hydrate:vm.runInNewContext(isolated,ctx),state,old,oldRecord,get cleared(){return cleared;}};
}

async function assertBlocked(records) {
  const paths = [];
  const test = fixture(async path => {
    paths.push(path);
    if (path === "/api/intents?limit=64") return {record_ids:["a","b"],next_cursor:null};
    if (path === "/api/intents/a") return {record_id:"a",kind:"listing"};
    if (path === "/api/intents/b") return records;
    throw new Error("unexpected path");
  });
  await assert.rejects(test.hydrate(), error => error?.code === "INTENT_LIST_INVALID");
  assert.equal(test.state.records, test.old);
  assert.equal(test.state.selectedId, "previous");
  assert.equal(test.state.selectedRecord, test.oldRecord);
  assert.equal(test.state.truncated, true);
  assert.equal(test.cleared, 0);
  assert.deepEqual(paths, [
    "/api/intents?limit=64","/api/intents/a","/api/intents/b",
  ]);
}

async function run() {
  const calls = [];
  const good = fixture(async path => {
    calls.push(path);
    if (path === "/api/intents?limit=64") return {record_ids:["a","b"],next_cursor:null};
    if (path === "/api/intents/a") return {record_id:"a",kind:"listing"};
    if (path === "/api/intents/b") return {kind:"canonical-document"};
    throw new Error("unexpected path");
  });
  await good.hydrate();
  assert.deepEqual(calls, [
    "/api/intents?limit=64","/api/intents/a","/api/intents/b",
  ]);
  assert.equal(good.state.records.size, 2);
  assert.equal(good.state.records.get("a").record_id, "a");
  assert.equal(good.state.records.get("b").kind, "canonical-document");
  assert.equal(good.state.truncated, false);
  assert.equal(good.state.selectedId, null);
  assert.equal(good.state.selectedRecord, null);
  assert.equal(good.cleared, 1);

  await assertBlocked({record_id:"different",kind:"listing"});
  await assertBlocked({record_id:123});
  await assertBlocked(null);
  await assertBlocked([]);
  await assertBlocked("invalid-string");

  const secondPage = fixture(async path => {
    if (path === "/api/intents?limit=64") return {record_ids:["a"],next_cursor:"cursor123"};
    if (path === "/api/intents/a") return {record_id:"a"};
    if (path === "/api/intents?cursor=cursor123&limit=64") return {record_ids:["b"],next_cursor:null};
    if (path === "/api/intents/b") return {record_id:"elsewhere"};
    throw new Error("unexpected path");
  });
  await assert.rejects(secondPage.hydrate(), e => e?.code === "INTENT_LIST_INVALID");
  assert.equal(secondPage.state.records,secondPage.old);
  assert.equal(secondPage.state.truncated,true);
  assert.equal(secondPage.cleared,0);
}
run().then(
  () => console.log("status=HYDRATION_DETAIL_IDENTITY_CONSISTENCY_TESTED_OFFLINE"),
  error => {console.error(error);process.exitCode=1;},
);
'''


class MarketplaceHydrationDetailIdentityTests(unittest.TestCase):
    def test_identity_guard_precedes_caching_and_final_commit(self) -> None:
        code = APP.read_text(encoding="utf-8").split(
            "async function hydrateCurrentIntents() {", 1
        )[1].split("\nasync function fullResync()", 1)[0]
        self.assertIn('Object.prototype.hasOwnProperty.call(record, "record_id")', code)
        self.assertIn("record.record_id !== recordId", code)
        self.assertIn('throw stableClientError("INTENT_LIST_INVALID");', code)
        self.assertLess(code.index("record.record_id !== recordId"),code.index("next.set(recordId, record);"))
        self.assertLess(code.index("next.set(recordId, record);"),code.index("state.records = next;"))
        self.assertIn("if (next.has(recordId))",code)

    def test_stored_detail_mismatch_uses_same_contract_as_direct_inspection(self) -> None:
        source = APP.read_text(encoding="utf-8")
        inspect = source.split("async function inspectIntent(recordId) {",1)[1].split(
            "\nasync function captureSyncWatermark",1
        )[0]
        self.assertIn("record.record_id !== reviewed",inspect)
        self.assertIn('throw stableClientError("INTENT_DETAIL_INVALID");',inspect)

    @unittest.skipUnless(shutil.which("node"), "Node.js unavailable")
    def test_real_js_single_page_cross_page_and_legacy_records(self) -> None:
        completed = subprocess.run(
            ["node", "-e", NODE_EXERCISE, str(APP)],
            capture_output=True,text=True,timeout=20,check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr[:1500])
        self.assertIn("HYDRATION_DETAIL_IDENTITY_CONSISTENCY_TESTED_OFFLINE",completed.stdout)


if __name__ == "__main__":
    unittest.main()
