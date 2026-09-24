"use strict";

const PROFILE = "MARKETPLACE_WEB_AGREEMENT_ASSENT_CLIENT_V1";
const MAX_BODY_BYTES = 64 * 1024;
const MAX_SIGNING_INPUT_BYTES = 4096;
const SIGNATURE_BYTES = 64;
const MAX_URI_BYTES = 2048;
const BASE64URL = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_";

function stableAssentClientError(code) {
  const error = new Error("Marketplace Web Agreement assent client operation failed");
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

function reviewedRecordId(value) {
  if (typeof value !== "string" || value.length < 1 || value.length > 512) {
    throw stableAssentClientError("RECORD_ID_INVALID");
  }
  for (const character of value) {
    const code = character.charCodeAt(0);
    if (code < 33 || code > 126 || "/?#".includes(character)) {
      throw stableAssentClientError("RECORD_ID_INVALID");
    }
  }
  return value;
}

function reviewedUri(value) {
  if (typeof value !== "string" || value.length === 0 ||
      utf8Bytes(value) > MAX_URI_BYTES ||
      !/^[A-Za-z][A-Za-z0-9+.-]*:\S+$/.test(value)) {
    throw stableAssentClientError("AGREEMENT_ASSENT_RESPONSE_INVALID");
  }
  return value;
}

function decodeBase64Url(value, maximumBytes) {
  if (typeof value !== "string" || value.length === 0 ||
      value.length % 4 === 1 || value.includes("=")) {
    throw stableAssentClientError("AGREEMENT_ASSENT_RESPONSE_INVALID");
  }
  let buffer = 0;
  let bits = 0;
  const output = [];
  for (const character of value) {
    const digit = BASE64URL.indexOf(character);
    if (digit < 0) throw stableAssentClientError("AGREEMENT_ASSENT_RESPONSE_INVALID");
    buffer = (buffer << 6) | digit;
    bits += 6;
    while (bits >= 8) {
      bits -= 8;
      output.push((buffer >> bits) & 0xff);
      buffer &= (1 << bits) - 1;
      if (output.length > maximumBytes) {
        throw stableAssentClientError("AGREEMENT_ASSENT_RESPONSE_INVALID");
      }
    }
  }
  if (bits !== 0 && buffer !== 0) {
    throw stableAssentClientError("AGREEMENT_ASSENT_RESPONSE_INVALID");
  }
  if (output.length === 0 || output.length > maximumBytes) {
    throw stableAssentClientError("AGREEMENT_ASSENT_RESPONSE_INVALID");
  }
  return Uint8Array.from(output);
}

function encodeBase64Url(value) {
  if (!(value instanceof Uint8Array) || value.length === 0) {
    throw stableAssentClientError("AGREEMENT_ASSENT_SIGNATURE_UNAVAILABLE");
  }
  let buffer = 0;
  let bits = 0;
  let output = "";
  for (const byte of value) {
    buffer = (buffer << 8) | byte;
    bits += 8;
    while (bits >= 6) {
      bits -= 6;
      output += BASE64URL[(buffer >> bits) & 0x3f];
      buffer &= (1 << bits) - 1;
    }
  }
  if (bits !== 0) output += BASE64URL[(buffer << (6 - bits)) & 0x3f];
  return output;
}

function decodeOjveBytes(value, maximumBytes) {
  if (!exactKeys(value, ["$olp", "v"]) || value.$olp !== "bytes") {
    throw stableAssentClientError("AGREEMENT_ASSENT_RESPONSE_INVALID");
  }
  return decodeBase64Url(value.v, maximumBytes);
}

function encodeOjveBytes(value) {
  if (!(value instanceof Uint8Array) || value.length !== SIGNATURE_BYTES) {
    throw stableAssentClientError("AGREEMENT_ASSENT_SIGNATURE_UNAVAILABLE");
  }
  return Object.freeze({ $olp: "bytes", v: encodeBase64Url(value) });
}

function reviewedPreparationResponse(value) {
  if (!exactKeys(
    value,
    ["agreement_record_id", "proof_input", "verification_method"],
  )) {
    throw stableAssentClientError("AGREEMENT_ASSENT_RESPONSE_INVALID");
  }
  return Object.freeze({
    agreementRecordId: reviewedRecordId(value.agreement_record_id),
    verificationMethod: reviewedUri(value.verification_method),
    signingInput: decodeOjveBytes(value.proof_input, MAX_SIGNING_INPUT_BYTES),
  });
}

function reviewedSubmissionResponse(value, agreementRecordId) {
  if (!exactKeys(
    value,
    [
      "accepted_at",
      "agreement_record_id",
      "authorizes_side_effects",
      "disposition",
      "expires_at",
      "publishes_agreement",
    ],
  )) {
    throw stableAssentClientError("AGREEMENT_ASSENT_RESPONSE_INVALID");
  }
  if (reviewedRecordId(value.agreement_record_id) !== agreementRecordId ||
      value.publishes_agreement !== false ||
      value.authorizes_side_effects !== false ||
      !["STORED", "DUPLICATE"].includes(value.disposition) ||
      !Number.isInteger(value.accepted_at) || value.accepted_at < 0 ||
      !Number.isInteger(value.expires_at) || value.expires_at < value.accepted_at) {
    throw stableAssentClientError("AGREEMENT_ASSENT_RESPONSE_INVALID");
  }
  return Object.freeze({
    agreementRecordId,
    disposition: value.disposition,
    acceptedAt: value.accepted_at,
    expiresAt: value.expires_at,
    publishesAgreement: false,
    authorizesSideEffects: false,
  });
}

function reviewedPrincipalCollection(value) {
  if (!Array.isArray(value) || value.length > 16) {
    throw stableAssentClientError("AGREEMENT_ASSENT_RESPONSE_INVALID");
  }
  const reviewed = value.map(reviewedUri);
  if (new Set(reviewed).size !== reviewed.length) {
    throw stableAssentClientError("AGREEMENT_ASSENT_RESPONSE_INVALID");
  }
  return Object.freeze(reviewed);
}

function reviewedFormationStatusResponse(value) {
  if (!exactKeys(
    value,
    [
      "agreement_record_id",
      "authorizes_side_effects",
      "covered_principals",
      "formation_evidence",
      "legal_enforceability",
      "missing_principals",
      "publishes_agreement",
      "required_principals",
      "universal_truth",
    ],
  )) {
    throw stableAssentClientError("AGREEMENT_ASSENT_RESPONSE_INVALID");
  }
  const agreementRecordId = reviewedRecordId(value.agreement_record_id);
  const requiredPrincipals = reviewedPrincipalCollection(value.required_principals);
  const coveredPrincipals = reviewedPrincipalCollection(value.covered_principals);
  const missingPrincipals = reviewedPrincipalCollection(value.missing_principals);
  const required = new Set(requiredPrincipals);
  const covered = new Set(coveredPrincipals);
  const missing = new Set(missingPrincipals);
  if (requiredPrincipals.length === 0 ||
      coveredPrincipals.some((principal) => !required.has(principal)) ||
      missingPrincipals.some((principal) => !required.has(principal)) ||
      coveredPrincipals.some((principal) => missing.has(principal)) ||
      covered.size + missing.size !== required.size ||
      value.legal_enforceability !== "NOT_EVALUATED" ||
      value.universal_truth !== false ||
      value.publishes_agreement !== false ||
      value.authorizes_side_effects !== false ||
      !["EVIDENCE_SUFFICIENT_FOR_PROFILE", "EVIDENCE_INCOMPLETE"].includes(
        value.formation_evidence,
      ) ||
      (value.formation_evidence === "EVIDENCE_SUFFICIENT_FOR_PROFILE") !==
        (missing.size === 0)) {
    throw stableAssentClientError("AGREEMENT_ASSENT_RESPONSE_INVALID");
  }
  return Object.freeze({
    agreementRecordId,
    formationEvidence: value.formation_evidence,
    requiredPrincipals,
    coveredPrincipals,
    missingPrincipals,
    legalEnforceability: "NOT_EVALUATED",
    universalTruth: false,
    publishesAgreement: false,
    authorizesSideEffects: false,
  });
}

function reviewedConfiguration(fetchImpl, session, signer) {
  if (typeof fetchImpl !== "function" || session === null || typeof session !== "object" ||
      typeof session.authorizationFor !== "function" ||
      typeof session.invalidateForServerCode !== "function" ||
      signer === null || typeof signer !== "object" ||
      typeof signer.createAgreementAssentSignature !== "function") {
    throw stableAssentClientError("CLIENT_CONFIGURATION_INVALID");
  }
  return { fetchImpl, session, signer };
}

async function decodeJsonResponse(response, session) {
  let text;
  try {
    text = await response.text();
  } catch {
    throw stableAssentClientError("APPLICATION_HTTP_TRANSPORT_FAILED");
  }
  if (utf8Bytes(text) > MAX_BODY_BYTES) {
    throw stableAssentClientError("AGREEMENT_ASSENT_RESPONSE_INVALID");
  }
  let value;
  try {
    value = JSON.parse(text);
  } catch {
    throw stableAssentClientError("AGREEMENT_ASSENT_RESPONSE_INVALID");
  }
  if (!response.ok) {
    const serverCode = value?.error?.code;
    const code = typeof serverCode === "string" &&
      /^[A-Z0-9_]{1,96}$/.test(serverCode)
      ? serverCode
      : "HTTP_" + response.status;
    session.invalidateForServerCode(code);
    throw stableAssentClientError(code);
  }
  return value;
}

async function postJson(fetchImpl, session, path, documentValue) {
  const authorization = session.authorizationFor("POST", path);
  if (typeof authorization !== "string" || !authorization.startsWith("Bearer ")) {
    throw stableAssentClientError("AUTH_REQUIRED");
  }
  const body = JSON.stringify(documentValue);
  if (utf8Bytes(body) > MAX_BODY_BYTES) {
    throw stableAssentClientError("AGREEMENT_ASSENT_REQUEST_INVALID");
  }
  let response;
  try {
    response = await fetchImpl(path, {
      method: "POST",
      headers: {
        Accept: "application/json",
        Authorization: authorization,
        "Content-Type": "application/json",
      },
      body,
      credentials: "omit",
      cache: "no-store",
      redirect: "error",
      referrerPolicy: "no-referrer",
    });
  } catch {
    throw stableAssentClientError("APPLICATION_HTTP_TRANSPORT_FAILED");
  }
  return decodeJsonResponse(response, session);
}

function createMarketplaceWebAgreementAssentClient({ fetchImpl, session, signer }) {
  const reviewed = reviewedConfiguration(fetchImpl, session, signer);

  async function prepare(proposalRecordIdValue, acceptanceRecordIdValue) {
    const proposalRecordId = reviewedRecordId(proposalRecordIdValue);
    const acceptanceRecordId = reviewedRecordId(acceptanceRecordIdValue);
    const path = "/api/agreements/" + encodeURIComponent(proposalRecordId) +
      "/assent/preparation";
    const response = await postJson(
      reviewed.fetchImpl,
      reviewed.session,
      path,
      { acceptance_record_id: acceptanceRecordId },
    );
    return reviewedPreparationResponse(response);
  }

  async function formationStatus(proposalRecordIdValue, acceptanceRecordIdValue) {
    const proposalRecordId = reviewedRecordId(proposalRecordIdValue);
    const acceptanceRecordId = reviewedRecordId(acceptanceRecordIdValue);
    const path = "/api/agreements/" + encodeURIComponent(proposalRecordId) +
      "/assent/status";
    const response = await postJson(
      reviewed.fetchImpl,
      reviewed.session,
      path,
      { acceptance_record_id: acceptanceRecordId },
    );
    return reviewedFormationStatusResponse(response);
  }

  async function signAndSubmit(proposalRecordIdValue, acceptanceRecordIdValue) {
    const proposalRecordId = reviewedRecordId(proposalRecordIdValue);
    const acceptanceRecordId = reviewedRecordId(acceptanceRecordIdValue);
    const preparation = await prepare(proposalRecordId, acceptanceRecordId);

    let signature;
    try {
      signature = await reviewed.signer.createAgreementAssentSignature({
        verificationMethod: preparation.verificationMethod,
        signingInput: Uint8Array.from(preparation.signingInput),
      });
    } catch {
      throw stableAssentClientError("AGREEMENT_ASSENT_SIGNATURE_UNAVAILABLE");
    }
    if (!(signature instanceof Uint8Array) || signature.length !== SIGNATURE_BYTES) {
      throw stableAssentClientError("AGREEMENT_ASSENT_SIGNATURE_UNAVAILABLE");
    }

    const path = "/api/agreements/" + encodeURIComponent(proposalRecordId) +
      "/assent";
    const response = await postJson(
      reviewed.fetchImpl,
      reviewed.session,
      path,
      {
        acceptance_record_id: acceptanceRecordId,
        signature: encodeOjveBytes(Uint8Array.from(signature)),
      },
    );
    return reviewedSubmissionResponse(response, preparation.agreementRecordId);
  }

  return Object.freeze({ prepare, formationStatus, signAndSubmit });
}

export {
  PROFILE,
  createMarketplaceWebAgreementAssentClient,
};
