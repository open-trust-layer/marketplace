"""Exercise the real browser incremental sync batch rollback in an offline Node.js VM."""
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
const start = source.indexOf("async function applySyncPage(documentValue) {");
const end = source.indexOf("\nfunction canonicalIntegerJsonToken(value) {", start);
assert.ok(start >= 0 && end > start, "actual sync handlers unavailable");
const realHandlers = source.slice(start, end) + "\n({applySyncPage, incrementalSync})";

function page(changes, nextCursor, hasMore) {
  return {changes, next_cursor:nextCursor, has_more:hasMore};
}
function upsert(seq, id = "a") {
  return {record_id:id, seq, change_kind:"UPSERT"};
}
function codedError(code) {
  return Object.assign(new Error("redacted"), {code});
}
function fixture(pages, opts = {}) {
  const state = {syncCursor:10, records:new Map([["old", {title:"existing"}]])};
  const requests = [];
  const statuses = [];
  const track = {hydrations:0, fullResyncs:0, cursorAtFallback:null, renders:0};
  const queue = pages.slice();
  const ctx = {
    state, SYNC_LIMIT:64, MAX_SYNC_PAGES:opts.maxPages ?? 4,
    API_SYNC:"/api/sync",
    stableClientError:codedError,
    requireRecordId(value) {
      if (typeof value !== "string" || !value || value.length > 512) throw codedError("RECORD_ID_INVALID");
      return value;
    },
    requireCursor(value) {
      if (!Number.isSafeInteger(value) || value < 0) throw codedError("SYNC_CURSOR_INVALID");
      return value;
    },
    setStatus(key) {statuses.push(key);},
    async apiFetch(url) {
      requests.push(url);
      if (queue.length === 0) throw new Error("unexpected extra fetch");
      const next = queue.shift();
      if (next instanceof Error) throw next;
      return next;
    },
    async hydrateCurrentIntents() {
      track.hydrations++;
      if (opts.hydrateFails) throw codedError("INTENT_LIST_INVALID");
      state.records = new Map([["new", {title:"hydrated"}]]);
    },
    renderList() {track.renders++;},
    renderDetail() {track.renders++;},
    async fullResync() {
      track.fullResyncs++;
      track.cursorAtFallback = state.syncCursor;
      state.syncCursor = 100;
      return "FULL_RESYNC_DONE";
    },
  };
  const functions = vm.runInNewContext(realHandlers, ctx);
  return {state, requests, statuses, track, sync:functions.incrementalSync};
}

async function mustReject(f, code) {
  await assert.rejects(f.sync(), error => error.code === code);
  assert.equal(f.state.syncCursor, 10, "failed batch advanced cursor");
  assert.equal(f.state.records.has("old"), true, "failed batch lost cached list");
  assert.equal(f.track.hydrations, code === "INTENT_LIST_INVALID" ? 1 : 0);
}

async function run() {
  const positive = fixture([
    page([upsert(11)], 12, true),
    page([upsert(13,"b")], 14, false),
  ]);
  await positive.sync();
  assert.equal(positive.state.syncCursor, 14);
  assert.equal(positive.state.records.has("new"), true);
  assert.equal(positive.track.hydrations, 1);
  assert.deepEqual(positive.requests.map(u => u.match(/cursor=(\d+)/)[1]), ["10","12"]);
  assert.equal(positive.statuses.at(-1), "sync.done");

  const empty = fixture([page([], 12, false)]);
  await empty.sync();
  assert.equal(empty.state.syncCursor, 12);
  assert.equal(empty.track.hydrations, 0);

  const lateNetwork = fixture([
    page([upsert(11)], 12, true),
    codedError("NETWORK_FAILED"),
  ]);
  await mustReject(lateNetwork, "NETWORK_FAILED");
  assert.equal(lateNetwork.requests.length, 2);
  // Retrying fetches from the original cursor, not the half-accepted batch.
  const later = fixture([page([upsert(11)], 12, false)]);
  await later.sync();
  assert.ok(later.requests[0].includes("cursor=10&"));

  const lateMalformed = fixture([
    page([upsert(11)], 12, true),
    page([upsert(11,"b")], 13, false),
  ]);
  await mustReject(lateMalformed, "SYNC_PAGE_INVALID");

  const hydrationFailure = fixture([
    page([upsert(11)], 12, false),
  ], {hydrateFails:true});
  await mustReject(hydrationFailure, "INTENT_LIST_INVALID");

  const expired = fixture([
    page([upsert(11)], 12, true),
    codedError("SYNC_CURSOR_EXPIRED"),
  ]);
  assert.equal(await expired.sync(), "FULL_RESYNC_DONE");
  assert.equal(expired.track.fullResyncs, 1);
  assert.equal(expired.track.cursorAtFallback, 10);
  assert.equal(expired.state.syncCursor, 100);

  // Bounded successful sync still accepts pages and emits a paused status.
  const bounded = fixture([
    page([upsert(11)], 12, true),
    page([upsert(13)], 14, true),
  ], {maxPages:2});
  await bounded.sync();
  assert.equal(bounded.state.syncCursor, 14);
  assert.equal(bounded.track.hydrations, 1);
  assert.equal(bounded.statuses.at(-1), "sync.paused");
}
run().then(
  () => console.log("status=SYNC_BATCH_ROLLBACK_TESTED_OFFLINE"),
  error => {console.error(error); process.exitCode = 1;},
);
'''

class WebIncrementalSyncBatchRollbackTests(unittest.TestCase):
    def test_failure_restores_original_cursor_before_expired_fallback(self) -> None:
        source = WEB.read_text(encoding="utf-8")
        block = source.split("async function incrementalSync() {", 1)[1].split(
            "\nfunction canonicalIntegerJsonToken(value) {", 1
        )[0]
        self.assertIn("const startingCursor = state.syncCursor;", block)
        self.assertIn("state.syncCursor = startingCursor;", block)
        self.assertLess(
            block.index("state.syncCursor = startingCursor;"),
            block.index('if (error.code === "SYNC_CURSOR_EXPIRED") return fullResync();'),
        )

    @unittest.skipUnless(shutil.which("node"), "Node.js unavailable")
    def test_real_js_sync_rollback_and_success_paths(self) -> None:
        result = subprocess.run(
            ["node", "-e", NODE_EXERCISE, str(WEB)],
            text=True, capture_output=True, timeout=20, check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr[:2000])
        self.assertIn("SYNC_BATCH_ROLLBACK_TESTED_OFFLINE", result.stdout)

if __name__ == "__main__":
    unittest.main()
