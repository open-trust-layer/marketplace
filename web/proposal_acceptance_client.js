"use strict";

const PROFILE = "MARKETPLACE_WEB_PROPOSAL_ACCEPTANCE_CLIENT_V1";
const MAX_RESPONSE_BYTES = 16 * 1024;

function stableAcceptanceClientError(code) {
  const error = new Error("Marketplace Web Proposal acceptance client operation failed");
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
    throw stableAcceptanceClientError("RECORD_ID_INVALID");
  }
  for (const character of value) {
    const code = character.charCodeAt(0);
    if (code < 33 || code > 126 || "/?#".includes(character)) {
      throw stableAcceptanceClientError("RECORD_ID_INVALID");
    }
  }
  return value;
}

function reviewedConfiguration(fetchImpl, session) {
  if (typeof fetchImpl !== "function" || session === null || typeof session !== "object" ||
      typeof session.authorizationFor !== "function" ||
      typeof session.invalidateForServerCode !== "function") {
    throw stableAcceptanceClientError("CLIENT_CONFIGURATION_INVALID");
  }
  return { fetchImpl, session };
}

function reviewedAcceptanceResponse(value) {
  if (!exactKeys(value, ["change_seq", "disposition", "record_id"])) {
    throw stableAcceptanceClientError("PROPOSAL_ACCEPTANCE_RESPONSE_INVALID");
  }
  const recordId = reviewedRecordId(value.record_id);
  if (!["STORED", "DUPLICATE"].includes(value.disposition)) {
    throw stableAcceptanceClientError("PROPOSAL_ACCEPTANCE_RESPONSE_INVALID");
  }
  if (value.change_seq !== null &&
      (!Number.isSafeInteger(value.change_seq) || value.change_seq < 1)) {
    throw stableAcceptanceClientError("PROPOSAL_ACCEPTANCE_RESPONSE_INVALID");
  }
  return Object.freeze({
    recordId,
    disposition: value.disposition,
    changeSeq: value.change_seq,
  });
}

async function decodeResponse(response, session) {
  let text;
  try {
    text = await response.text();
  } catch {
    throw stableAcceptanceClientError("APPLICATION_HTTP_TRANSPORT_FAILED");
  }
  if (utf8Bytes(text) > MAX_RESPONSE_BYTES) {
    throw stableAcceptanceClientError("PROPOSAL_ACCEPTANCE_RESPONSE_INVALID");
  }
  let value;
  try {
    value = JSON.parse(text);
  } catch {
    throw stableAcceptanceClientError("PROPOSAL_ACCEPTANCE_RESPONSE_INVALID");
  }
  if (!response.ok) {
    const serverCode = value?.error?.code;
    const code = typeof serverCode === "string" && /^[A-Z0-9_]{1,96}$/.test(serverCode)
      ? serverCode
      : "HTTP_" + response.status;
    session.invalidateForServerCode(code);
    throw stableAcceptanceClientError(code);
  }
  if (response.status !== 201) {
    throw stableAcceptanceClientError("PROPOSAL_ACCEPTANCE_RESPONSE_INVALID");
  }
  return reviewedAcceptanceResponse(value);
}

function createMarketplaceWebProposalAcceptanceClient({ fetchImpl, session }) {
  const reviewed = reviewedConfiguration(fetchImpl, session);

  async function acceptProposal(proposalRecordIdValue) {
    const proposalRecordId = reviewedRecordId(proposalRecordIdValue);
    const path = "/api/intents/" + encodeURIComponent(proposalRecordId) + "/acceptance";
    const authorization = reviewed.session.authorizationFor("POST", path);
    if (typeof authorization !== "string" || !authorization.startsWith("Bearer ")) {
      throw stableAcceptanceClientError("AUTH_REQUIRED");
    }
    let response;
    try {
      response = await reviewed.fetchImpl(path, {
        method: "POST",
        headers: {
          Accept: "application/json",
          Authorization: authorization,
        },
        credentials: "omit",
        cache: "no-store",
        redirect: "error",
        referrerPolicy: "no-referrer",
      });
    } catch {
      throw stableAcceptanceClientError("APPLICATION_HTTP_TRANSPORT_FAILED");
    }
    return decodeResponse(response, reviewed.session);
  }

  return Object.freeze({ acceptProposal });
}

export {
  PROFILE,
  createMarketplaceWebProposalAcceptanceClient,
};
