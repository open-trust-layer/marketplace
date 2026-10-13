/* In-process two-browser handoff: no browser, listener, database, or runtime secrets. */
import test from "node:test";
import assert from "node:assert/strict";
import { webcrypto } from "node:crypto";
import { createMarketplaceBrowserAuthBootstrap } from "../web/auth_bootstrap.js";

const subtle = webcrypto.subtle;
const DOMAIN = "https://open-trust-layer.github.io/marketplace/application-auth/v1";
const SUITE = "https://open-trust-layer.github.io/marketplace/application-auth/eddsa-ed25519-v1";
const PURPOSE = "assertion";
const ROLES = Object.freeze([
  Object.freeze({ principal: "did:example:marketplace-local-evaluator-seller", method: "did:example:marketplace-local-evaluator-seller#key-1", nonce: 17 }),
  Object.freeze({ principal: "did:example:marketplace-local-evaluator-buyer", method: "did:example:marketplace-local-evaluator-buyer#key-1", nonce: 23 }),
]);

function carrier(prefix, byte) {
  return prefix + Buffer.alloc(32, byte).toString("base64url");
}
function prefixed(value) {
  const b = Buffer.from(value, "utf8");
  assert.ok(b.length < 65536);
  return Buffer.concat([Buffer.from([b.length >>> 8, b.length & 255]), b]);
}
function transcript(method, nonce) {
  return Buffer.concat([
    Buffer.from("MARKETPLACE-AUTH"), Buffer.from([0, 1]),
    prefixed(SUITE), prefixed(PURPOSE), prefixed(method),
    prefixed(DOMAIN), Buffer.alloc(32, nonce),
  ]);
}
function response(data, status = 200) {
  return new Response(JSON.stringify(data), { status, headers: { "Content-Type": "application/json" } });
}
function makeContext(role) {
  let stage = "preview", key = null, publicCarrier = null, exports = 0;
  const requests = [];
  const guardedSubtle = {
    async generateKey(algorithm, extractable, usages) {
      assert.deepEqual(algorithm, { name: "Ed25519" });
      assert.equal(extractable, false);
      assert.deepEqual(usages, ["sign", "verify"]);
      const keys = await subtle.generateKey(algorithm, extractable, usages);
      assert.equal(keys.privateKey.extractable, false);
      assert.equal(keys.publicKey.extractable, true);
      key = keys.privateKey;
      return keys;
    },
    async exportKey(format, selected) {
      assert.equal(format, "raw");
      assert.equal(selected.type, "public");
      assert.equal(selected.extractable, true);
      exports += 1;
      return subtle.exportKey(format, selected);
    },
    async sign(algorithm, selected, bytes) {
      assert.deepEqual(algorithm, { name: "Ed25519" });
      assert.strictEqual(selected, key);
      assert.equal(selected.extractable, false);
      return subtle.sign(algorithm, selected, bytes);
    },
  };
  const fetchImpl = async (path, init) => {
    assert.ok(typeof path === "string" && path.startsWith("/api/"));
    assert.equal(init.credentials, "omit");
    assert.equal(init.redirect, "error");
    requests.push(path);
    if (stage === "preview") return response({}, 404);
    assert.equal(stage, "runtime");
    if (path === "/api/auth/challenges") {
      assert.deepEqual(JSON.parse(init.body), { principal: role.principal, verification_method: role.method });
      return response({
        challenge: carrier("mkc1_", role.nonce), domain: DOMAIN,
        proof_purpose: PURPOSE, expires_in_seconds: 120,
      });
    }
    if (path === "/api/auth/sessions") {
      const data = JSON.parse(init.body);
      assert.equal(data.challenge, carrier("mkc1_", role.nonce));
      assert.equal(data.proof.verificationMethod, role.method);
      assert.equal(data.proof.domain, DOMAIN);
      assert.equal(data.proof.proofPurpose, PURPOSE);
      assert.equal(data.proof.cryptosuite, SUITE);
      assert.match(data.proof.proofValue, /^mks1_[A-Za-z0-9_-]{86}$/);
      const publicRaw = Buffer.from(publicCarrier.slice(6), "base64url");
      assert.equal(publicRaw.length, 32);
      const publicKey = await subtle.importKey("raw", publicRaw, "Ed25519", true, ["verify"]);
      assert.equal(await subtle.verify(
        "Ed25519", publicKey,
        Buffer.from(data.proof.proofValue.slice(5), "base64url"),
        transcript(role.method, role.nonce),
      ), true);
      return response({
        session_token: carrier("mkt1_", role.nonce), principal: role.principal,
        verification_method: role.method, idle_timeout_seconds: 1800,
        absolute_timeout_seconds: 28800,
      });
    }
    if (path === "/api/product-listings" || path.endsWith("/proposals")) {
      assert.equal(init.headers.Authorization, "Bearer " + carrier("mkt1_", role.nonce));
      const submitted = JSON.parse(init.body);
      assert.equal(submitted[path === "/api/product-listings" ? "seller_principal" : "buyer_principal"], role.principal);
      return response({ accepted: true }, 201);
    }
    throw new Error("Unexpected in-process mock route");
  };
  const bootstrap = createMarketplaceBrowserAuthBootstrap({ subtle: guardedSubtle, fetchImpl });
  return Object.freeze({
    role, bootstrap, requests,
    get signingKey() { return key; },
    get exports() { return exports; },
    setPublic(value) { publicCarrier = value; },
    startRuntime() { stage = "runtime"; },
  });
}

test("distinct browser Ed25519 keys survive preview errors and authenticate after same-origin handoff", async () => {
  const contexts = ROLES.map(makeContext);
  const browserPublicKeys = [];
  for (const context of contexts) {
    const created = await context.bootstrap.createAuthenticationKey();
    assert.match(created.publicKeyValue, /^mkpk1_[A-Za-z0-9_-]{43}$/);
    assert.equal(created.evidencePublicKeyValue, created.publicKeyValue.replace(/^mkpk1_/, "mkp1_"));
    context.setPublic(created.publicKeyValue);
    browserPublicKeys.push(created.publicKeyValue);
    assert.equal(context.exports, 1);
    assert.equal(context.signingKey.extractable, false);
    await assert.rejects(
      context.bootstrap.establishSession(context.role.principal, context.role.method),
      { code: "HTTP_404" },
    );
    assert.equal(context.bootstrap.state().keyReady, true);
    assert.equal(context.bootstrap.state().active, false);
    await assert.rejects(context.bootstrap.createAuthenticationKey(), { code: "AUTH_KEY_ALREADY_CREATED" });
  }
  assert.notEqual(browserPublicKeys[0], browserPublicKeys[1]);
  assert.notStrictEqual(contexts[0].signingKey, contexts[1].signingKey);
  for (const context of contexts) {
    context.startRuntime(); // Existing page, bootstrap, key and relative-path fetch retained.
    const session = await context.bootstrap.establishSession(context.role.principal, context.role.method);
    assert.equal(session.active, true);
    assert.equal(session.principal, context.role.principal);
    assert.equal(context.bootstrap.state().active, true);
    assert.equal(context.bootstrap.state().keyReady, true);
    assert.equal(context.exports, 1);
    assert.equal(context.signingKey.extractable, false);
    assert.deepEqual(context.requests.slice(0, 3), [
      "/api/auth/challenges", "/api/auth/challenges", "/api/auth/sessions",
    ]);
  }
  const listing = await contexts[0].bootstrap.structuredAuthoringClient().createProductListing({
    subject_uri: "https://example.invalid/item",
  });
  assert.equal(listing.accepted, true);
  const proposal = await contexts[1].bootstrap.structuredAuthoringClient().createProposal("record-parent", {
    subject_uri: "https://example.invalid/item",
  });
  assert.equal(proposal.accepted, true);
});
