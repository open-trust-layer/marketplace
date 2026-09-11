"use strict";

const PROFILE = "MARKETPLACE_WEB_AUTH_SESSION_ESTABLISHMENT_V1";
const AUTH_DOMAIN = "https://open-trust-layer.github.io/marketplace/application-auth/v1";
const AUTH_PURPOSE = "assertion";
const PROOF_TYPE = "MarketplaceAuthenticationProof";
const PROOF_VERSION = 1;
const PROOF_CRYPTOSUITE = "https://open-trust-layer.github.io/marketplace/application-auth/eddsa-ed25519-v1";
const CHALLENGE = /^mkc1_[A-Za-z0-9_-]{43}$/;
const SESSION_TOKEN = /^mkt1_[A-Za-z0-9_-]{43}$/;
const PROOF_VALUE = /^mks1_[A-Za-z0-9_-]{86}$/;
const URI = /^[A-Za-z][A-Za-z0-9+.-]*:\S+$/;
const MAX_URI_BYTES = 2048;
const MAX_AUTH_BODY_BYTES = 64 * 1024;
const MAX_PROOF_JSON_BYTES = 48 * 1024;
const CHALLENGE_EXPIRES_SECONDS = 120;
const SESSION_IDLE_SECONDS = 1800;
const SESSION_ABSOLUTE_SECONDS = 28800;

function stableClientError(code) {
  const error = new Error("Marketplace Web authentication operation failed");
  error.code = code;
  return error;
}

function utf8Bytes(value) {
  return new TextEncoder().encode(value).length;
}
function reviewedUri(value) {
  if (typeof value !== "string" || utf8Bytes(value) > MAX_URI_BYTES || !URI.test(value)) {
    throw stableClientError("AUTH_REQUEST_INVALID");
  }
  return value;
}

function exactKeys(value, expected) {
  if (value === null || typeof value !== "object" || Array.isArray(value)) return false;
  const keys = Object.keys(value).sort();
  const wanted = [...expected].sort();
  return keys.length === wanted.length && keys.every((key, index) => key === wanted[index]);
}

function reviewedChallengeResponse(value) {
  if (!exactKeys(value, ["challenge", "domain", "proof_purpose", "expires_in_seconds"])) {
    throw stableClientError("AUTH_RESPONSE_INVALID");
  }
  if (!CHALLENGE.test(value.challenge) || value.domain !== AUTH_DOMAIN ||
      value.proof_purpose !== AUTH_PURPOSE || value.expires_in_seconds !== CHALLENGE_EXPIRES_SECONDS) {
    throw stableClientError("AUTH_RESPONSE_INVALID");
  }
  return value;
}

function reviewedProof(value, verificationMethod, challenge) {
  const keys = ["type", "version", "cryptosuite", "proofPurpose", "verificationMethod", "domain", "challenge", "proofValue"];
  if (!exactKeys(value, keys)) throw stableClientError("AUTH_PROOF_INVALID");
  if (value.type !== PROOF_TYPE || value.version !== PROOF_VERSION ||
      value.cryptosuite !== PROOF_CRYPTOSUITE || value.proofPurpose !== AUTH_PURPOSE ||
      value.verificationMethod !== verificationMethod || value.domain !== AUTH_DOMAIN ||
      value.challenge !== challenge || !PROOF_VALUE.test(value.proofValue)) {
    throw stableClientError("AUTH_PROOF_INVALID");
  }
  const encoded = JSON.stringify(value);
  if (utf8Bytes(encoded) > MAX_PROOF_JSON_BYTES) throw stableClientError("AUTH_PROOF_INVALID");
  return value;
}

function reviewedSessionResponse(value, principal, verificationMethod) {
  const keys = ["session_token", "principal", "verification_method", "idle_timeout_seconds", "absolute_timeout_seconds"];
  if (!exactKeys(value, keys)) throw stableClientError("AUTH_RESPONSE_INVALID");
  if (!SESSION_TOKEN.test(value.session_token) || value.principal !== principal ||
      value.verification_method !== verificationMethod || value.idle_timeout_seconds !== SESSION_IDLE_SECONDS ||
      value.absolute_timeout_seconds !== SESSION_ABSOLUTE_SECONDS) {
    throw stableClientError("AUTH_RESPONSE_INVALID");
  }
  return value;
}

async function decodeJsonResponse(response) {
  const text = await response.text();
  if (utf8Bytes(text) > MAX_AUTH_BODY_BYTES) throw stableClientError("AUTH_RESPONSE_INVALID");
  let value;
  try {
    value = JSON.parse(text);
  } catch {
    throw stableClientError("AUTH_RESPONSE_INVALID");
  }
  if (!response.ok) {
    const code = value?.error?.code;
    if (typeof code === "string" && /^AUTH_[A-Z_]+$/.test(code)) throw stableClientError(code);
    throw stableClientError(`HTTP_${response.status}`);
  }
  return value;
}

async function postJson(fetchImpl, path, value) {
  const body = JSON.stringify(value);
  if (utf8Bytes(body) > MAX_AUTH_BODY_BYTES) throw stableClientError("AUTH_REQUEST_INVALID");
  let response;
  try {
    response = await fetchImpl(path, {
      method: "POST",
      headers: { Accept: "application/json", "Content-Type": "application/json" },
      body,
      credentials: "omit",
      cache: "no-store",
      redirect: "error",
      referrerPolicy: "no-referrer",
    });
  } catch {
    throw stableClientError("APPLICATION_HTTP_TRANSPORT_FAILED");
  }
  return decodeJsonResponse(response);
}

function createMarketplaceWebAuthEstablishment({ fetchImpl, session, proofProvider }) {
  if (typeof fetchImpl !== "function" || session === null || typeof session !== "object" ||
      typeof session.adoptEstablishedSession !== "function" || proofProvider === null ||
      typeof proofProvider !== "object" || typeof proofProvider.createAuthenticationProof !== "function") {
    throw stableClientError("CLIENT_CONFIGURATION_INVALID");
  }
  async function establishSession(principalValue, verificationMethodValue) {
    const principal = reviewedUri(principalValue);
    const verificationMethod = reviewedUri(verificationMethodValue);
    const challengeResponse = reviewedChallengeResponse(await postJson(
      fetchImpl,
      "/api/auth/challenges",
      { principal, verification_method: verificationMethod },
    ));

    let proof;
    try {
      proof = await proofProvider.createAuthenticationProof(Object.freeze({
        profile: PROFILE,
        principal,
        verificationMethod,
        challenge: challengeResponse.challenge,
        domain: AUTH_DOMAIN,
        proofPurpose: AUTH_PURPOSE,
      }));
    } catch {
      throw stableClientError("AUTH_PROOF_UNAVAILABLE");
    }
    const reviewed = reviewedProof(proof, verificationMethod, challengeResponse.challenge);
    const sessionResponse = reviewedSessionResponse(await postJson(
      fetchImpl,
      "/api/auth/sessions",
      { challenge: challengeResponse.challenge, proof: reviewed },
    ), principal, verificationMethod);

    session.adoptEstablishedSession(principal, sessionResponse.session_token);
    return Object.freeze({
      active: true,
      principal,
      verificationMethod,
      idleTimeoutSeconds: sessionResponse.idle_timeout_seconds,
      absoluteTimeoutSeconds: sessionResponse.absolute_timeout_seconds,
    });
  }

  return Object.freeze({ establishSession });
}

export {
  PROFILE,
  createMarketplaceWebAuthEstablishment,
};
