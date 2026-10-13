/* Explicit reset must invalidate asynchronous, memory-only authentication work. */
import test from "node:test";
import assert from "node:assert/strict";
import { webcrypto } from "node:crypto";
import { createMarketplaceBrowserAuthBootstrap } from "../web/auth_bootstrap.js";

const subtle = webcrypto.subtle;
const PRINCIPAL = "did:example:marketplace-test-reset";
const METHOD = PRINCIPAL + "#key-1";
const DOMAIN = "https://open-trust-layer.github.io/marketplace/application-auth/v1";
const challenge = "mkc1_" + Buffer.alloc(32, 19).toString("base64url");
const token = "mkt1_" + Buffer.alloc(32, 29).toString("base64url");

function deferred() {
  let resolve;
  const promise = new Promise((accept) => { resolve = accept; });
  return { promise, resolve };
}
function cryptoFacade(generateKey = (...args) => subtle.generateKey(...args)) {
  return Object.freeze({
    generateKey,
    exportKey: (...args) => subtle.exportKey(...args),
    sign: (...args) => subtle.sign(...args),
  });
}
function jsonResponse(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}
function challengeResponse() {
  return jsonResponse({
    challenge, domain: DOMAIN, proof_purpose: "assertion", expires_in_seconds: 120,
  });
}
function sessionResponse() {
  return jsonResponse({
    session_token: token, principal: PRINCIPAL, verification_method: METHOD,
    idle_timeout_seconds: 1800, absolute_timeout_seconds: 28800,
  });
}
function emptyState(bootstrap) {
  assert.deepEqual(bootstrap.state(), {
    keyReady: false, active: false, principal: null, verificationMethod: null,
  });
}

test("overlapping key generations fail closed and reset discards the first late result", async () => {
  const generationGate = deferred();
  let generations = 0;
  const bootstrap = createMarketplaceBrowserAuthBootstrap({
    subtle: cryptoFacade(async (...args) => {
      generations += 1;
      await generationGate.promise;
      return subtle.generateKey(...args);
    }),
    fetchImpl: async () => { throw new Error("No network permitted"); },
  });
  const pending = bootstrap.createAuthenticationKey();
  assert.equal(generations, 1);
  await assert.rejects(bootstrap.createAuthenticationKey(), { code: "AUTH_KEY_ALREADY_CREATED" });
  assert.equal(generations, 1, "never create two keys for one browser context");
  bootstrap.reset();
  emptyState(bootstrap);
  generationGate.resolve();
  await assert.rejects(pending, { code: "AUTH_OPERATION_SUPERSEDED" });
  emptyState(bootstrap);
  assert.equal(generations, 1);
  const fresh = await bootstrap.createAuthenticationKey();
  assert.match(fresh.publicKeyValue, /^mkpk1_[A-Za-z0-9_-]{43}$/);
  assert.equal(bootstrap.state().keyReady, true);
  assert.equal(generations, 2);
});

test("reset during pending challenge refuses signing and session issuance", async () => {
  const gate = deferred();
  let challenges = 0, sessions = 0;
  const bootstrap = createMarketplaceBrowserAuthBootstrap({
    subtle: cryptoFacade(),
    fetchImpl: async (path) => {
      if (path === "/api/auth/challenges") {
        challenges += 1;
        await gate.promise;
        return challengeResponse();
      }
      if (path === "/api/auth/sessions") {
        sessions += 1;
        return sessionResponse();
      }
      throw new Error("Unexpected route");
    },
  });
  await bootstrap.createAuthenticationKey();
  const inFlight = bootstrap.establishSession(PRINCIPAL, METHOD);
  await assert.rejects(
    bootstrap.establishSession(PRINCIPAL, METHOD),
    { code: "AUTH_SESSION_ALREADY_ACTIVE" },
  );
  bootstrap.reset();
  gate.resolve();
  await assert.rejects(inFlight, { code: "AUTH_OPERATION_SUPERSEDED" });
  assert.equal(challenges, 1);
  assert.equal(sessions, 0, "no signing/issuance after canceled challenge");
  emptyState(bootstrap);
  await assert.rejects(bootstrap.structuredAuthoringClient(), {
    code: "STRUCTURED_AUTHORING_AUTH_REQUIRED",
  });
  // The original delayed promise has settled; a new explicitly generated
  // key is allowed, but never an implicit replacement or stale adoption.
  const created = await bootstrap.createAuthenticationKey();
  assert.match(created.publicKeyValue, /^mkpk1_/);
  const authenticated = await bootstrap.establishSession(PRINCIPAL, METHOD);
  assert.equal(authenticated.active, true);
  assert.equal(bootstrap.state().principal, PRINCIPAL);
  assert.equal(challenges, 2);
  assert.equal(sessions, 1);
});

test("reset during pending session response cannot restore a bearer session", async () => {
  const sessionGate = deferred();
  const sessionRequested = deferred();
  let sessions = 0;
  const bootstrap = createMarketplaceBrowserAuthBootstrap({
    subtle: cryptoFacade(),
    fetchImpl: async (path) => {
      if (path === "/api/auth/challenges") return challengeResponse();
      if (path === "/api/auth/sessions") {
        sessions += 1;
        sessionRequested.resolve();
        await sessionGate.promise;
        return sessionResponse();
      }
      throw new Error("Unexpected route");
    },
  });
  await bootstrap.createAuthenticationKey();
  const pending = bootstrap.establishSession(PRINCIPAL, METHOD);
  await sessionRequested.promise;
  bootstrap.reset();
  emptyState(bootstrap);
  sessionGate.resolve();
  await assert.rejects(pending, { code: "AUTH_OPERATION_SUPERSEDED" });
  emptyState(bootstrap);
  assert.equal(sessions, 1);
  await assert.rejects(bootstrap.establishSession(PRINCIPAL, METHOD), {
    code: "AUTH_KEY_REQUIRED",
  });
});
