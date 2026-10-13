/* Stream-bounded Web auth HTTP responses: in-process only, no sockets. */
import test from "node:test";
import assert from "node:assert/strict";
import { createMarketplaceWebAuthEstablishment } from "../web/auth_establishment.js";

const LIMIT = 64 * 1024;
const PRINCIPAL = "did:example:evaluator";
const METHOD = PRINCIPAL + "#key-1";
const CHALLENGE = "mkc1_" + "A".repeat(43);
const TOKEN = "mkt1_" + "B".repeat(43);
const DOMAIN = "https://open-trust-layer.github.io/marketplace/application-auth/v1";
const SUITE = "https://open-trust-layer.github.io/marketplace/application-auth/eddsa-ed25519-v1";

function makeClient(fetchImpl) {
  const adopted = [];
  let proofs = 0;
  const client = createMarketplaceWebAuthEstablishment({
    fetchImpl,
    session: {
      adoptEstablishedSession(principal, token) {
        adopted.push({ principal, token });
      },
    },
    proofProvider: {
      async createAuthenticationProof(request) {
        proofs += 1;
        return {
          type: "MarketplaceAuthenticationProof",
          version: 1,
          cryptosuite: SUITE,
          proofPurpose: "assertion",
          verificationMethod: request.verificationMethod,
          domain: DOMAIN,
          challenge: request.challenge,
          proofValue: "mks1_" + "C".repeat(86),
        };
      },
    },
  });
  return {
    client,
    adopted,
    get proofs() { return proofs; },
    establish() { return client.establishSession(PRINCIPAL, METHOD); },
  };
}

function chunkedResponse(data, splits = [6, 23], status = 200) {
  const bytes = new TextEncoder().encode(JSON.stringify(data));
  const chunks = [];
  let last = 0;
  for (const split of splits) {
    chunks.push(bytes.slice(last, Math.min(split, bytes.length)));
    last = split;
  }
  chunks.push(bytes.slice(last));
  const stream = new ReadableStream({
    start(controller) {
      for (const chunk of chunks) controller.enqueue(chunk);
      controller.close();
    },
  });
  return new Response(stream, { status, headers: { "Content-Type": "application/json" } });
}

test("declared oversized challenge fails before touching the body or signing", async () => {
  let bodyTouched = false;
  let requests = 0;
  const oversized = {
    ok: true,
    headers: { get(name) { return name === "content-length" ? String(LIMIT + 1) : null; } },
    get body() { bodyTouched = true; throw new Error("body may not be inspected"); },
    async text() { bodyTouched = true; throw new Error("text may not be called"); },
  };
  const harness = makeClient(async (path, init) => {
    requests += 1;
    assert.equal(path, "/api/auth/challenges");
    assert.equal(init.credentials, "omit");
    assert.equal(init.redirect, "error");
    return oversized;
  });
  await assert.rejects(harness.establish(), { code: "AUTH_RESPONSE_INVALID" });
  assert.equal(bodyTouched, false);
  assert.equal(requests, 1);
  assert.equal(harness.proofs, 0);
  assert.deepEqual(harness.adopted, []);
});

test("missing length still enforces bounded streamed bytes and cancels after overflow", async () => {
  let cancelled = false;
  const body = new ReadableStream({
    start(controller) {
      controller.enqueue(new Uint8Array(LIMIT));
      controller.enqueue(new Uint8Array([123]));
    },
    cancel() { cancelled = true; },
  });
  const harness = makeClient(async () => ({
    ok: true, status: 200,
    headers: { get() { return null; } },
    body,
    async text() { throw new Error("unbounded text fallback must not run"); },
  }));
  await assert.rejects(harness.establish(), { code: "AUTH_RESPONSE_INVALID" });
  assert.equal(cancelled, true);
  assert.equal(harness.proofs, 0);
  assert.deepEqual(harness.adopted, []);
});

test("stream read errors normalize to safe code without session adoption", async () => {
  const body = new ReadableStream({
    start(controller) { controller.error(new Error("untrusted source detail")); },
  });
  const harness = makeClient(async () => ({
    ok: true, status: 200,
    headers: { get() { return null; } },
    body,
  }));
  await assert.rejects(harness.establish(), { code: "AUTH_RESPONSE_INVALID" });
  assert.equal(harness.proofs, 0);
  assert.deepEqual(harness.adopted, []);
});

test("legacy text-only response retains the bounded fallback", async () => {
  const harness = makeClient(async () => ({
    ok: true, status: 200,
    headers: { get() { return "n/a"; } },
    body: undefined,
    async text() { return "X".repeat(LIMIT + 1); },
  }));
  await assert.rejects(harness.establish(), { code: "AUTH_RESPONSE_INVALID" });
  assert.equal(harness.proofs, 0);
  assert.deepEqual(harness.adopted, []);
});

test("bounded multipart stream preserves challenge/proof/session and its safe metadata", async () => {
  const paths = [];
  const harness = makeClient(async (path, options) => {
    paths.push(path);
    assert.equal(options.credentials, "omit");
    assert.equal(options.redirect, "error");
    assert.equal(options.referrerPolicy, "no-referrer");
    if (path === "/api/auth/challenges") {
      return chunkedResponse({
        challenge: CHALLENGE, domain: DOMAIN,
        proof_purpose: "assertion", expires_in_seconds: 120,
      });
    }
    if (path === "/api/auth/sessions") {
      const proof = JSON.parse(options.body).proof;
      assert.equal(proof.verificationMethod, METHOD);
      assert.equal(proof.challenge, CHALLENGE);
      return chunkedResponse({
        session_token: TOKEN, principal: PRINCIPAL,
        verification_method: METHOD,
        idle_timeout_seconds: 1800,
        absolute_timeout_seconds: 28800,
      }, [1, 11, 64, 128]);
    }
    throw new Error("Unexpected route");
  });
  const session = await harness.establish();
  assert.equal(session.active, true);
  assert.equal(session.principal, PRINCIPAL);
  assert.equal(session.verificationMethod, METHOD);
  assert.equal(Object.hasOwn(session, "session_token"), false);
  assert.deepEqual(harness.adopted, [{ principal: PRINCIPAL, token: TOKEN }]);
  assert.equal(harness.proofs, 1);
  assert.deepEqual(paths, ["/api/auth/challenges", "/api/auth/sessions"]);
});

test("short streamed auth error retains reviewed code but no session", async () => {
  const harness = makeClient(async () => chunkedResponse({
    error: { code: "AUTH_SIGNATURE_INVALID" },
  }, [1, 5, 20], 401));
  await assert.rejects(harness.establish(), { code: "AUTH_SIGNATURE_INVALID" });
  assert.deepEqual(harness.adopted, []);
});
