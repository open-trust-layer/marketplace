"""Fail-closed cleanup after unsuccessful Marketplace response-detail inspection."""
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
const start = source.indexOf("async function inspectIntent(recordId) {");
const end = source.indexOf("\nasync function captureSyncWatermark", start);
assert.ok(start >= 0 && end > start);
const isolated = source.slice(start, end) + "\ninspectIntent";

function fixture(fetchResult) {
  const calls = [];
  const state = {
    detailRequestSerial: 8,
    selectedId: "listing",
    selectedRecord: {id:"listing"},
    responseParentId: "listing",
    responseIds: ["old-child"],
    responseErrorCode: "HTTP_502",
    responseLoading: true,
  };
  const responseList = {
    replaceChildren() {calls.push("clear-list");},
  };
  const ctx = {
    state, responseList,
    requireRecordId(value) {return value;},
    stableClientError(code) {return Object.assign(new Error("redacted"), {code});},
    apiFetch: fetchResult,
    API_INTENTS: "/api/intents",
    renderList() {calls.push("render-list");},
    renderDetail() {calls.push("render-detail");},
    async renderResponses(id) {calls.push("render-responses:" + id);return true;},
    setStatus(key, variables, kind) {calls.push(key + ":" + variables.code + ":" + kind);},
  };
  return {inspect: vm.runInNewContext(isolated, ctx),state,calls};
}

async function run() {
  const failure = fixture(async () => {
    throw Object.assign(new Error("private backend detail"), {code:"HTTP_404"});
  });
  assert.equal(await failure.inspect("child"), true);
  assert.equal(failure.state.selectedId, null);
  assert.equal(failure.state.selectedRecord, null);
  assert.equal(failure.state.responseParentId, null);
  assert.deepEqual(Array.from(failure.state.responseIds), []);
  assert.equal(failure.state.responseErrorCode, null);
  assert.equal(failure.state.responseLoading, false);
  assert.deepEqual(failure.calls, [
    "clear-list","render-list","render-detail","detail.failed:HTTP_404:error",
  ]);

  let stale;
  stale = fixture(async () => {
    stale.state.detailRequestSerial += 1;
    throw Object.assign(new Error("obsolete private data"), {code:"HTTP_409"});
  });
  assert.equal(await stale.inspect("child"), false);
  assert.equal(stale.state.selectedId, "listing");
  assert.equal(stale.state.responseParentId, "listing");
  assert.deepEqual(Array.from(stale.state.responseIds), ["old-child"]);
  assert.equal(stale.state.responseErrorCode, "HTTP_502");
  assert.equal(stale.state.responseLoading, true);
  assert.deepEqual(stale.calls, []);

  const success = fixture(async () => ({id:"child"}));
  assert.equal(await success.inspect("child"), true);
  assert.equal(success.state.selectedId, "child");
  assert.equal(success.state.selectedRecord.id, "child");
  assert.equal(success.state.responseParentId, "listing");
  assert.equal(success.state.responseErrorCode, null);
  assert.deepEqual(Array.from(success.state.responseIds), []);
  assert.equal(success.state.responseLoading, false);
  assert.deepEqual(success.calls, [
    "render-list","render-detail","render-responses:child",
  ]);

  const matching = fixture(async () => ({record_id:"child",kind:"proposal"}));
  assert.equal(await matching.inspect("child"), true);
  assert.equal(matching.state.selectedId, "child");
  assert.equal(matching.state.selectedRecord.record_id, "child");
  assert.deepEqual(matching.calls, [
    "render-list","render-detail","render-responses:child",
  ]);

  for (const invalid of [{record_id:"different"}, {record_id:1}, null, [], "raw-json"]) {
    const mismatch = fixture(async () => invalid);
    assert.equal(await mismatch.inspect("child"), true);
    assert.equal(mismatch.state.selectedId, null);
    assert.equal(mismatch.state.selectedRecord, null);
    assert.equal(mismatch.state.responseParentId, null);
    assert.deepEqual(Array.from(mismatch.state.responseIds), []);
    assert.equal(mismatch.state.responseErrorCode, null);
    assert.equal(mismatch.state.responseLoading, false);
    assert.deepEqual(mismatch.calls, [
      "clear-list","render-list","render-detail","detail.failed:INTENT_DETAIL_INVALID:error",
    ]);
  }
}
run().then(
  () => console.log("status=FAILED_INSPECTION_STATE_CLEANUP_TESTED_OFFLINE"),
  error => {console.error(error);process.exitCode=1;},
);
'''


class MarketplaceFailedInspectionStateTests(unittest.TestCase):
    def test_failure_clears_parent_and_response_state_after_stale_guard(self) -> None:
        source = APP.read_text(encoding="utf-8")
        block = source.split("async function inspectIntent(recordId) {", 1)[1].split(
            "\nasync function captureSyncWatermark", 1
        )[0]
        catch = block.split("} catch (error) {", 1)[1]
        stale = "if (state.detailRequestSerial !== requestSerial) return false;"
        self.assertIn(stale, catch)
        for marker in (
            "state.selectedId = null;",
            "state.selectedRecord = null;",
            "state.responseParentId = null;",
            "state.responseIds = [];",
            "state.responseErrorCode = null;",
            "state.responseLoading = false;",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, catch)
                self.assertLess(catch.index(stale), catch.index(marker))
        self.assertLess(
            catch.index("state.responseParentId = null;"),
            catch.index("renderDetail();"),
        )

    def test_optional_embedded_record_id_must_match_requested_detail(self) -> None:
        source = APP.read_text(encoding="utf-8")
        success = source.split("async function inspectIntent(recordId) {", 1)[1].split(
            "} catch (error) {", 1
        )[0]
        self.assertIn('Object.prototype.hasOwnProperty.call(record, "record_id")', success)
        self.assertIn("record.record_id !== reviewed", success)
        self.assertIn('throw stableClientError("INTENT_DETAIL_INVALID");', success)
        self.assertLess(success.index("record.record_id !== reviewed"), success.index("state.selectedId = reviewed;"))
        self.assertLess(success.index("if (state.detailRequestSerial !== requestSerial) return false;"), success.index("record.record_id !== reviewed"))

    def test_success_retains_exact_parent_and_updates_record(self) -> None:
        source = APP.read_text(encoding="utf-8")
        success = source.split("async function inspectIntent(recordId) {", 1)[1].split(
            "} catch (error) {", 1
        )[0]
        self.assertIn("state.selectedId = reviewed;", success)
        self.assertIn("state.selectedRecord = record;", success)
        self.assertNotIn("state.responseParentId = null;", success)

    @unittest.skipUnless(shutil.which("node"), "Node.js unavailable")
    def test_real_js_failed_stale_and_successful_inspections(self) -> None:
        result = subprocess.run(
            ["node", "-e", NODE_EXERCISE, str(APP)],
            capture_output=True, text=True, timeout=15, check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr[:1200])
        self.assertIn(
            "FAILED_INSPECTION_STATE_CLEANUP_TESTED_OFFLINE",
            result.stdout,
        )


if __name__ == "__main__":
    unittest.main()
