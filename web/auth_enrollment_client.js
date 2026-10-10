"use strict";

const PROFILE = "MARKETPLACE_WEB_AUTH_ENROLLMENT_CLIENT_V1";
const SERVER_PROFILE = "MARKETPLACE_APPLICATION_AUTH_ENROLLMENT_HTTP_V1";
const PROPOSAL_PROFILE = "MARKETPLACE_WEB_AUTH_ED25519_ENROLLMENT_PROPOSAL_V1";
const PROPOSAL_TYPE = "MarketplaceAuthenticationEnrollmentProposal";
const NONCE_TYPE = "MarketplaceAuthenticationEnrollmentNonce";
const EVIDENCE_TYPE = "MarketplaceAuthenticationVerificationMethodEvidenceEnvelope";
const NONCE_ROUTE = "/api/authentication-enrollment/nonces";
const EVIDENCE_ROUTE = "/api/authentication-enrollment/evidence";
const PUBLIC_KEY_PREFIX = "mkp1_";
const NONCE_PREFIX = "mken1_";
const CLAIMS_PREFIX = "mkec1_";
const ATTESTATION_PREFIX = "mkea1_";
const NONCE_PAYLOAD_CHARS = 43;
const PUBLIC_KEY_PAYLOAD_CHARS = 43;
const MAX_URI_BYTES = 2048;
const MAX_REQUEST_BYTES = 16 * 1024;
const MAX_RESPONSE_BYTES = 768 * 1024;
const MAX_CLAIMS_PAYLOAD_CHARS = 699051;
const MAX_ATTESTATION_PAYLOAD_CHARS = 21846;
const BASE64URL = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_";
const URI = /^[A-Za-z][A-Za-z0-9+.-]*:\S+$/;
const AUTHORIZATION = /^Bearer mkt1_[A-Za-z0-9_-]{43}$/;
const SERVER_ERROR_CODE = /^AUTH_[A-Z_]{1,80}$/;

function stableEnrollmentClientError(code) {
  const error = new Error("Marketplace Web authentication enrollment client operation failed");
  error.code = code;
  return error;
}

function utf8Bytes(value) {
  return new TextEncoder().encode(value).length;
}

function exactKeys(value, expected) {
  if (value === null || typeof value !== "object" || Array.isArray(value)) return false;
  const keys = Object.keys(value).sort();
  const wanted = [...expected].sort();
  return keys.length === wanted.length &&
    keys.every((key, index) => key === wanted[index]);
}

function reviewedUri(value) {
  if (typeof value !== "string" || value.length === 0 ||
      utf8Bytes(value) > MAX_URI_BYTES || !URI.test(value)) {
    throw stableEnrollmentClientError("AUTH_ENROLLMENT_PROPOSAL_INVALID");
  }
  return value;
}

function base64UrlIndex(character) {
  const value = BASE64URL.indexOf(character);
  if (value < 0) throw stableEnrollmentClientError("AUTH_ENROLLMENT_RESPONSE_INVALID");
  return value;
}

function reviewedCanonicalPayload(payload, maximumChars, code) {
  if (typeof payload !== "string" || payload.length === 0 ||
      payload.length > maximumChars || payload.length % 4 === 1) {
    throw stableEnrollmentClientError(code);
  }
  for (const character of payload) {
    if (!BASE64URL.includes(character)) throw stableEnrollmentClientError(code);
  }
  const remainder = payload.length % 4;
  const finalValue = base64UrlIndex(payload[payload.length - 1]);
  if ((remainder === 2 && (finalValue & 0x0f) !== 0) ||
      (remainder === 3 && (finalValue & 0x03) !== 0)) {
    throw stableEnrollmentClientError(code);
  }
  return payload;
}

function reviewedCarrier(value, prefix, maximumChars, code) {
  if (typeof value !== "string" || !value.startsWith(prefix)) {
    throw stableEnrollmentClientError(code);
  }
  reviewedCanonicalPayload(value.slice(prefix.length), maximumChars, code);
  return value;
}

function reviewedProposal(value) {
  if (!exactKeys(value, ["profile", "type", "principal", "verificationMethod", "publicKey"]) ||
      value.profile !== PROPOSAL_PROFILE || value.type !== PROPOSAL_TYPE) {
    throw stableEnrollmentClientError("AUTH_ENROLLMENT_PROPOSAL_INVALID");
  }
  const principal = reviewedUri(value.principal);
  const verificationMethod = reviewedUri(value.verificationMethod);
  reviewedCarrier(
    value.publicKey,
    PUBLIC_KEY_PREFIX,
    PUBLIC_KEY_PAYLOAD_CHARS,
    "AUTH_ENROLLMENT_PROPOSAL_INVALID",
  );
  if (value.publicKey.length !== PUBLIC_KEY_PREFIX.length + PUBLIC_KEY_PAYLOAD_CHARS) {
    throw stableEnrollmentClientError("AUTH_ENROLLMENT_PROPOSAL_INVALID");
  }
  return Object.freeze({
    profile: PROPOSAL_PROFILE,
    type: PROPOSAL_TYPE,
    principal,
    verificationMethod,
    publicKey: value.publicKey,
  });
}

function reviewedConfiguration(fetchImpl, session) {
  if (typeof fetchImpl !== "function" || session === null || typeof session !== "object" ||
      typeof session.requirePrincipal !== "function" ||
      typeof session.authorizationFor !== "function" ||
      typeof session.invalidateForServerCode !== "function") {
    throw stableEnrollmentClientError("CLIENT_CONFIGURATION_INVALID");
  }
  return { fetchImpl, session };
}

function reviewedAuthorization(value) {
  if (typeof value !== "string" || !AUTHORIZATION.test(value)) {
    throw stableEnrollmentClientError("AUTH_REQUIRED");
  }
  return value;
}

async function decodeJsonResponse(response, session) {
  let text;
  try {
    text = await response.text();
  } catch {
    throw stableEnrollmentClientError("APPLICATION_HTTP_TRANSPORT_FAILED");
  }
  if (utf8Bytes(text) > MAX_RESPONSE_BYTES) {
    throw stableEnrollmentClientError("AUTH_ENROLLMENT_RESPONSE_INVALID");
  }

  let value;
  try {
    value = JSON.parse(text);
  } catch {
    throw stableEnrollmentClientError("AUTH_ENROLLMENT_RESPONSE_INVALID");
  }

  if (!response.ok) {
    const serverCode = value?.error?.code;
    const code = typeof serverCode === "string" && SERVER_ERROR_CODE.test(serverCode)
      ? serverCode
      : "AUTH_ENROLLMENT_HTTP_FAILED";
    session.invalidateForServerCode(code);
    throw stableEnrollmentClientError(code);
  }
  if (response.status !== 201) {
    throw stableEnrollmentClientError("AUTH_ENROLLMENT_RESPONSE_INVALID");
  }
  return value;
}

async function postAuthenticatedJson(reviewed, path, value) {
  const authorization = reviewedAuthorization(
    reviewed.session.authorizationFor("POST", path),
  );
  const body = JSON.stringify(value);
  if (utf8Bytes(body) > MAX_REQUEST_BYTES) {
    throw stableEnrollmentClientError("AUTH_ENROLLMENT_REQUEST_INVALID");
  }

  let response;
  try {
    response = await reviewed.fetchImpl(path, {
      method: "POST",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
        Authorization: authorization,
      },
      body,
      credentials: "omit",
      cache: "no-store",
      redirect: "error",
      referrerPolicy: "no-referrer",
    });
  } catch {
    throw stableEnrollmentClientError("APPLICATION_HTTP_TRANSPORT_FAILED");
  }
  return decodeJsonResponse(response, reviewed.session);
}

function reviewedNonceResponse(value) {
  if (!exactKeys(value, ["expiresAt", "issuedAt", "nonce", "profile", "type"]) ||
      value.profile !== SERVER_PROFILE || value.type !== NONCE_TYPE ||
      !Number.isSafeInteger(value.issuedAt) || value.issuedAt < 0 ||
      !Number.isSafeInteger(value.expiresAt) || value.expiresAt <= value.issuedAt) {
    throw stableEnrollmentClientError("AUTH_ENROLLMENT_RESPONSE_INVALID");
  }
  reviewedCarrier(
    value.nonce,
    NONCE_PREFIX,
    NONCE_PAYLOAD_CHARS,
    "AUTH_ENROLLMENT_RESPONSE_INVALID",
  );
  if (value.nonce.length !== NONCE_PREFIX.length + NONCE_PAYLOAD_CHARS) {
    throw stableEnrollmentClientError("AUTH_ENROLLMENT_RESPONSE_INVALID");
  }
  return value;
}

function reviewedEvidenceResponse(value) {
  if (!exactKeys(value, ["attestation", "claims", "profile", "type"]) ||
      value.profile !== SERVER_PROFILE || value.type !== EVIDENCE_TYPE) {
    throw stableEnrollmentClientError("AUTH_ENROLLMENT_RESPONSE_INVALID");
  }
  const claims = reviewedCarrier(
    value.claims,
    CLAIMS_PREFIX,
    MAX_CLAIMS_PAYLOAD_CHARS,
    "AUTH_ENROLLMENT_RESPONSE_INVALID",
  );
  const attestation = reviewedCarrier(
    value.attestation,
    ATTESTATION_PREFIX,
    MAX_ATTESTATION_PAYLOAD_CHARS,
    "AUTH_ENROLLMENT_RESPONSE_INVALID",
  );
  return Object.freeze({
    profile: SERVER_PROFILE,
    type: EVIDENCE_TYPE,
    claims,
    attestation,
  });
}

function createMarketplaceWebAuthEnrollmentClient({ fetchImpl, session }) {
  const reviewed = reviewedConfiguration(fetchImpl, session);

  async function enrollAuthenticationProposal(proposalValue) {
    const proposal = reviewedProposal(proposalValue);
    let principal;
    try {
      principal = reviewed.session.requirePrincipal();
    } catch {
      throw stableEnrollmentClientError("AUTH_REQUIRED");
    }
    if (principal !== proposal.principal) {
      throw stableEnrollmentClientError("AUTH_PRINCIPAL_MISMATCH");
    }

    const nonceResponse = reviewedNonceResponse(await postAuthenticatedJson(
      reviewed,
      NONCE_ROUTE,
      { profile: SERVER_PROFILE, proposal },
    ));

    const evidenceResponse = reviewedEvidenceResponse(await postAuthenticatedJson(
      reviewed,
      EVIDENCE_ROUTE,
      {
        profile: SERVER_PROFILE,
        proposal,
        nonce: nonceResponse.nonce,
      },
    ));
    return evidenceResponse;
  }

  return Object.freeze({ enrollAuthenticationProposal });
}

export {
  PROFILE,
  createMarketplaceWebAuthEnrollmentClient,
};
