"""Regression: failed response load clears stale loading UI without fetching again."""
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
const start = source.indexOf("async function renderResponses(recordId) {");
const end = source.indexOf("\nfunction selectIntent", start);
assert.ok(start >= 0 && end > start);
const isolated = source.slice(start, end) + "\nrenderResponses";

function makeFixture(fetchImplementation) {
  const calls = [];
  const responseList = {
    nodes: [],
    replaceChildren(...nodes) {this.nodes = nodes; calls.push("replace");},
    append(node) {this.nodes.push(node); calls.push("append");},
  };
  const state = {
    selectedId: "current-record",
    responseRequestSerial: 0,
    responseLoading: false,
    responseIds: ["old-response"],
    responseErrorCode: null,
  };
  const context = {
    state,
    responseList,
    PAGE_LIMIT: 64,
    API_INTENTS: "/api/intents",
    RESPONSES_SUFFIX: "/responses",
    document: {
      createElement(type) {return {type, className:"", textContent:""};},
    },
    i18n: {
      t(key, variables) {return key + ":" + (variables?.code ?? "");},
    },
    renderResponseLoading() {
      responseList.replaceChildren({type: "p", className: "muted", textContent:"loading"});
    },
    renderResponseItems(_recordId, ids) {
      responseList.replaceChildren({type: "items", ids});
    },
    requireRecordId(value) {return value;},
    apiFetch: fetchImplementation,
    stableClientError(code) {return Object.assign(new Error("redacted"), {code});},
  };
  return {call:vm.runInNewContext(isolated, context),state,responseList,calls};
}

async function run() {
  const failure = makeFixture(async () => {
    throw Object.assign(new Error("private provider details"), {code:"HTTP_503"});
  });
  assert.equal(await failure.call("current-record"), true);
  assert.equal(failure.state.responseLoading, false);
  assert.equal(failure.state.responseErrorCode, "HTTP_503");
  assert.equal(failure.state.responseIds.length, 0);
  assert.equal(failure.responseList.nodes.length, 1);
  assert.equal(failure.responseList.nodes[0].className, "error");
  assert.equal(failure.responseList.nodes[0].textContent, "responses.unavailable:HTTP_503");
  assert.deepEqual(failure.calls, ["replace", "replace"]);

  const stale = makeFixture(async () => {
    stale.state.selectedId = "different-record";
    throw Object.assign(new Error("old request failed"), {code:"HTTP_500"});
  });
  assert.equal(await stale.call("current-record"), false);
  assert.equal(stale.state.responseErrorCode, null);
  assert.equal(stale.responseList.nodes.length, 1);
  assert.equal(stale.responseList.nodes[0].textContent, "loading");
  assert.deepEqual(stale.calls, ["replace"]);

  const success = makeFixture(async () => ({record_ids: ["child"]}));
  assert.equal(await success.call("current-record"), true);
  assert.equal(success.state.responseErrorCode, null);
  assert.equal(success.state.responseLoading, false);
  assert.equal(success.responseList.nodes.length, 1);
  assert.equal(success.responseList.nodes[0].type, "items");
  assert.deepEqual(Array.from(success.state.responseIds), ["child"]);

  const distinct = makeFixture(async () => ({record_ids: ["first", "second"]}));
  assert.equal(await distinct.call("current-record"), true);
  assert.equal(distinct.state.responseErrorCode, null);
  assert.deepEqual(Array.from(distinct.state.responseIds), ["first", "second"]);
  assert.equal(distinct.responseList.nodes[0].type, "items");

  const duplicates = makeFixture(async () => ({record_ids: ["child", "child"]}));
  assert.equal(await duplicates.call("current-record"), true);
  assert.equal(duplicates.state.responseErrorCode, "RESPONSE_LIST_INVALID");
  assert.deepEqual(Array.from(duplicates.state.responseIds), []);
  assert.equal(duplicates.state.responseLoading, false);
  assert.equal(duplicates.responseList.nodes.length, 1);
  assert.equal(duplicates.responseList.nodes[0].className, "error");
  assert.equal(duplicates.responseList.nodes[0].textContent,
    "responses.unavailable:RESPONSE_LIST_INVALID");
  assert.deepEqual(duplicates.calls, ["replace", "replace"]);
}
run().then(
  () => console.log("status=RESPONSE_LOADING_ERROR_STATE_TESTED_OFFLINE"),
  error => {console.error(error); process.exitCode=1;},
);
'''


class MarketplaceResponseLoadingErrorStateTests(unittest.TestCase):
    def test_terminal_failure_replaces_loading_marker(self) -> None:
        source = APP.read_text(encoding="utf-8")
        block = source.split("async function renderResponses(recordId) {", 1)[1].split(
            "\nfunction selectIntent", 1
        )[0]
        self.assertIn("renderResponseLoading();", block)
        self.assertIn("responseList.replaceChildren(message);", block)
        self.assertNotIn("responseList.append(message);", block)
        self.assertEqual(
            block.count(
                "if (state.selectedId !== recordId || state.responseRequestSerial !== requestSerial) return false;"
            ),
            2,
        )
        self.assertLess(
            block.rindex("if (state.selectedId !== recordId"),
            block.index("responseList.replaceChildren(message);"),
        )

    def test_response_ids_are_unique_before_rendering_cards(self) -> None:
        source = APP.read_text(encoding="utf-8")
        block = source.split("async function renderResponses(recordId) {", 1)[1].split(
            "\nfunction selectIntent", 1
        )[0]
        self.assertIn(
            'if (new Set(ids).size !== ids.length) throw stableClientError("RESPONSE_LIST_INVALID");',
            block,
        )
        self.assertLess(
            block.index("for (const value of ids) requireRecordId(value);"),
            block.index("new Set(ids).size"),
        )
        self.assertLess(
            block.index("new Set(ids).size"),
            block.index("state.responseIds = ids;"),
        )

    def test_language_switch_error_render_remains_single_terminal_status(self) -> None:
        source = APP.read_text(encoding="utf-8")
        language = source.split("i18n.onChange(() => {", 1)[1].split(
            "\n\nrenderSyncStatus();", 1
        )[0]
        self.assertIn("responseList.replaceChildren();", language)
        self.assertIn('i18n.t("responses.unavailable", { code: state.responseErrorCode })', language)
        self.assertNotIn("apiFetch(", language)

    @unittest.skipUnless(shutil.which("node"), "Node.js unavailable")
    def test_real_js_failure_stale_and_success_states(self) -> None:
        completed = subprocess.run(
            ["node", "-e", NODE_EXERCISE, str(APP)],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr[:1200])
        self.assertIn("RESPONSE_LOADING_ERROR_STATE_TESTED_OFFLINE", completed.stdout)


if __name__ == "__main__":
    unittest.main()
