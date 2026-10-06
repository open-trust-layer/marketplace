"use strict";

const PROFILE = "MARKETPLACE_WEB_AGREEMENT_PUBLICATION_CLIENT_V1";
const MAX_RESPONSE_BYTES = 16 * 1024;

function stablePublicationClientError(code) {
  const error = new Error("Marketplace Web Agreement publication client operation failed");
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
    throw stablePublicationClientError("RECORD_ID_INVALID");
  }
  for (const character of value) {
    const code = character.charCodeAt(0);
    if (code < 33 || code > 126 || "/?#".includes(character)) {
      throw stablePublicationClientError("RECORD_ID_INVALID");
    }
  }
  return value;
}

function reviewedConfiguration(fetchImpl, session) {
  if (typeof fetchImpl !== "function" || session === null || typeof session !== "object" ||
      typeof session.authorizationFor !== "function" ||
      typeof session.invalidateForServerCode !== "function") {
    throw stablePublicationClientError("CLIENT_CONFIGURATION_INVALID");
  }
  return { fetchImpl, session };
}

function reviewedPublicationResponse(value, expectedAgreementRecordId, status) {
  if (!exactKeys(
    value,
    ["agreement_record_id", "change_seq", "disposition"],
  )) {
    throw stablePublicationClientError("AGREEMENT_PUBLICATION_RESPONSE_INVALID");
  }
  const agreementRecordId = reviewedRecordId(value.agreement_record_id);
  if (
    agreementRecordId !== expectedAgreementRecordId ||
    !["STORED", "DUPLICATE"].includes(value.disposition) ||
    value.change_seq !== null &&
      (!Number.isSafeInteger(value.change_seq) || value.change_seq < 1) ||
    (value.disposition === "STORED" && status !== 201) ||
    (value.disposition === "DUPLICATE" && status !== 200)
  ) {
    throw stablePublicationClientError("AGREEMENT_PUBLICATION_RESPONSE_INVALID");
  }
  return Object.freeze({
    agreementRecordId,
    disposition: value.disposition,
    changeSeq: value.change_seq,
  });
}

async function decodeResponse(response, session, expectedAgreementRecordId) {
  let text;
  try {
    text = await response.text();
  } catch {
    throw stablePublicationClientError("APPLICATION_HTTP_TRANSPORT_FAILED");
  }
  if (utf8Bytes(text) > MAX_RESPONSE_BYTES) {
    throw stablePublicationClientError("AGREEMENT_PUBLICATION_RESPONSE_INVALID");
  }
  let value;
  try {
    value = JSON.parse(text);
  } catch {
    throw stablePublicationClientError("AGREEMENT_PUBLICATION_RESPONSE_INVALID");
  }
  if (!response.ok) {
    const serverCode = value?.error?.code;
    const code = typeof serverCode === "string" && /^[A-Z0-9_]{1,96}$/.test(serverCode)
      ? serverCode
      : "HTTP_" + response.status;
    session.invalidateForServerCode(code);
    throw stablePublicationClientError(code);
  }
  if (![200, 201].includes(response.status)) {
    throw stablePublicationClientError("AGREEMENT_PUBLICATION_RESPONSE_INVALID");
  }
  return reviewedPublicationResponse(
    value,
    expectedAgreementRecordId,
    response.status,
  );
}

function createMarketplaceWebAgreementPublicationClient({ fetchImpl, session }) {
  const reviewed = reviewedConfiguration(fetchImpl, session);

  async function publishAgreement(
    proposalRecordIdValue,
    acceptanceRecordIdValue,
    expectedAgreementRecordIdValue,
  ) {
    const proposalRecordId = reviewedRecordId(proposalRecordIdValue);
    const acceptanceRecordId = reviewedRecordId(acceptanceRecordIdValue);
    const expectedAgreementRecordId = reviewedRecordId(
      expectedAgreementRecordIdValue,
    );
    const path = "/api/agreements/" + encodeURIComponent(proposalRecordId);
    const authorization = reviewed.session.authorizationFor("POST", path);
    if (typeof authorization !== "string" || !authorization.startsWith("Bearer ")) {
      throw stablePublicationClientError("AUTH_REQUIRED");
    }
    const body = JSON.stringify({
      acceptance_record_id: acceptanceRecordId,
    });
    let response;
    try {
      response = await reviewed.fetchImpl(path, {
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
      throw stablePublicationClientError("APPLICATION_HTTP_TRANSPORT_FAILED");
    }
    return decodeResponse(
      response,
      reviewed.session,
      expectedAgreementRecordId,
    );
  }

  return Object.freeze({ publishAgreement });
}

export {
  PROFILE,
  createMarketplaceWebAgreementPublicationClient,
};
