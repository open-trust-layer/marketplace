"""Evidence V1 JS projection must use own data properties, not inherited/getter values."""
from __future__ import annotations

from pathlib import Path
import shutil
import subprocess
import unittest


ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "web" / "authenticated_local_flight_evidence.js"

NODE_TEST = r"""
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

const script = await readFile(process.argv[1], "utf8");
const mod = await import("data:text/javascript;base64," + Buffer.from(script).toString("base64"));
const project = mod.createMarketplaceAuthenticatedLocalFlightEvidence;

function fixture() {
  return {
    mainCommit: "a".repeat(40),
    ciRunNumber: 958,
    runtimeHost: "127.0.0.1",
    sellerAuthenticated: true,
    buyerAuthenticated: true,
    listingRecordId: "record_listing_01",
    proposalRecordId: "record_proposal_01",
    acceptanceRecordId: "record_acceptance_01",
    formation: {
      agreementRecordId: "record_agreement_01",
      formationEvidence: "EVIDENCE_SUFFICIENT_FOR_PROFILE",
      missingPrincipals: [],
      requiredPrincipals: ["seller", "buyer"],
    },
    publication: {
      agreementRecordId: "record_agreement_01",
      disposition: "STORED",
      changeSeq: 21,
    },
    completion: {
      recordId: "record_completion_01",
      agreementRecordId: "record_agreement_01",
      commitmentId: "seller-delivery",
      evidenceKind: "CLAIMED_COMPLETE_PERFORMANCE",
      disposition: "STORED",
      changeSeq: 22,
    },
  };
}

const accepted = project(fixture());
assert.equal(accepted.profile, "MARKETPLACE_AUTHENTICATED_LOCAL_FLIGHT_EVIDENCE_V1");
assert.equal(accepted.agreement_publication.change_seq, 21);
assert.equal(accepted.completion.change_seq, 22);

for (const [field, code] of [
  ["formation", "EVIDENCE_FORMATION_INVALID"],
  ["publication", "EVIDENCE_PUBLICATION_INVALID"],
  ["completion", "EVIDENCE_COMPLETION_INVALID"],
]) {
  // An otherwise-valid object cannot inherit critical evidence from prototype.
  const inherited = fixture();
  inherited[field] = Object.create(inherited[field]);
  assert.throws(() => project(inherited), err => err?.code === code);

  // Accessors must not execute or contribute forged evidence values.
  const getters = fixture();
  const entry = Object.entries(getters[field])[0];
  let getterCalls = 0;
  Object.defineProperty(getters[field], entry[0], {
    enumerable: true,
    configurable: true,
    get() { getterCalls++; return entry[1]; },
  });
  assert.throws(() => project(getters), err => err?.code === code);
  assert.equal(getterCalls, 0);

  // Proxy descriptor traps may not propagate an attacker-provided error.
  const proxyInput = fixture();
  proxyInput[field] = new Proxy(proxyInput[field], {
    getOwnPropertyDescriptor() { throw new Error("UNTRUSTED_PROXY_SECRET"); },
  });
  assert.throws(
    () => project(proxyInput),
    err => err?.code === code && !String(err).includes("UNTRUSTED_PROXY_SECRET"),
  );

  // A Proxy can advertise valid own data descriptors but swap or throw on
  // subsequent property reads. Snapshot descriptor.value exactly once.
  const readTrapInput = fixture();
  let proxyGetCalls = 0;
  readTrapInput[field] = new Proxy(readTrapInput[field], {
    get() {
      proxyGetCalls++;
      throw new Error("UNTRUSTED_PROXY_GET_SECRET");
    },
  });
  assert.deepEqual(project(readTrapInput), accepted);
  assert.equal(proxyGetCalls, 0);

  // One missing own property fails even if the property is present on a
  // prototype; no value may be backfilled from Object.prototype.
  const missing = fixture();
  const key = Object.keys(missing[field])[0];
  const original = missing[field][key];
  delete missing[field][key];
  Object.setPrototypeOf(missing[field], { [key]: original });
  assert.throws(() => project(missing), err => err?.code === code);
}

// Plain and null-prototype own data records remain accepted.
const nullProto = fixture();
for (const field of ["formation", "publication", "completion"]) {
  nullProto[field] = Object.assign(Object.create(null), nullProto[field]);
}
assert.equal(project(nullProto).completion.evidence_kind, "CLAIMED_COMPLETE_PERFORMANCE");
console.log("OWN_DATA_PROPERTY_CHECKS_PASS");
"""


@unittest.skipUnless(shutil.which("node"), "Node.js is required for browser-module contract tests")
class MarketplaceEvidenceOwnFieldTests(unittest.TestCase):
    def test_browser_projection_rejects_inherited_and_accessor_evidence(self) -> None:
        result = subprocess.run(
            ["node", "--input-type=module", "-e", NODE_TEST, str(MODULE)],
            capture_output=True,
            text=True,
            check=False,
            timeout=15,
            cwd=ROOT,
        )
        self.assertEqual(result.returncode, 0, result.stderr[-1800:])
        self.assertEqual(result.stdout.strip(), "OWN_DATA_PROPERTY_CHECKS_PASS")


if __name__ == "__main__":
    unittest.main()
