"use strict";

const PROFILE = "MARKETPLACE_WEB_FULFILLMENT_COMPLETION_CLIENT_V1";
const MAX_RESPONSE_BYTES = 16 * 1024;
const EVIDENCE_KINDS = new Set([
  "CLAIMED_COMPLETE_PERFORMANCE",
  "COMMITMENT_ACCEPTANCE",
  "COMMITMENT_COMPLETION",
]);
const LOCAL_ID = /^[A-Za-z][A-Za-z0-9._-]{0,63}$/;

function stableCompletionClientError(code) {
  const error = new Error("Marketplace Web fulfillment completion client operation failed");
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
    throw stableCompletionClientError("RECORD_ID_INVALID");
  }
  for (const character of value) {
    const code = character.charCodeAt(0);
    if (code < 33 || code > 126 || "/?#".includes(character)) {
      throw stableCompletionClientError("RECORD_ID_INVALID");
    }
  }
  return value;
}

function reviewedCommitmentId(value) {
  if (typeof value !== "string" || !LOCAL_ID.test(value)) {
    throw stableCompletionClientError("COMMITMENT_ID_INVALID");
  }
  return value;
}

function reviewedEvidenceKind(value) {
  if (typeof value !== "string" || !EVIDENCE_KINDS.has(value)) {
    throw stableCompletionClientError("FULFILLMENT_EVIDENCE_KIND_INVALID");
  }
  return value;
}

function reviewedConfiguration(fetchImpl, session) {
  if (typeof fetchImpl !== "function" || session === null || typeof session !== "object" ||
      typeof session.authorizationFor !== "function" ||
      typeof session.invalidateForServerCode !== "function") {
    throw stableCompletionClientError("CLIENT_CONFIGURATION_INVALID");
  }
  return { fetchImpl, session };
}

function reviewedPublicationResponse(
  value,
  expectedAgreementRecordId,
  expectedCommitmentId,
  expectedEvidenceKind,
  status,
) {
  if (!exactKeys(
    value,
    [
      "agreement_record_id",
      "change_seq",
      "commitment_id",
      "disposition",
      "evidence_kind",
      "record_id",
    ],
  )) {
    throw stableCompletionClientError("FULFILLMENT_COMPLETION_RESPONSE_INVALID");
  }
  const recordId = reviewedRecordId(value.record_id);
  const agreementRecordId = reviewedRecordId(value.agreement_record_id);
  const commitmentId = reviewedCommitmentId(value.commitment_id);
  const evidenceKind = reviewedEvidenceKind(value.evidence_kind);
  if (
    agreementRecordId !== expectedAgreementRecordId ||
    commitmentId !== expectedCommitmentId ||
    evidenceKind !== expectedEvidenceKind ||
    !["STORED", "DUPLICATE"].includes(value.disposition) ||
    value.change_seq !== null &&
      (!Number.isSafeInteger(value.change_seq) || value.change_seq < 1) ||
    (value.disposition === "STORED" && status !== 201) ||
    (value.disposition === "DUPLICATE" && status !== 200)
  ) {
    throw stableCompletionClientError("FULFILLMENT_COMPLETION_RESPONSE_INVALID");
  }
  return Object.freeze({
    recordId,
    agreementRecordId,
    commitmentId,
    evidenceKind,
    disposition: value.disposition,
    changeSeq: value.change_seq,
  });
}

async function decodeResponse(
  response,
  session,
  expectedAgreementRecordId,
  expectedCommitmentId,
  expectedEvidenceKind,
) {
  let text;
  try {
    text = await response.text();
  } catch {
    throw stableCompletionClientError("APPLICATION_HTTP_TRANSPORT_FAILED");
  }
  if (utf8Bytes(text) > MAX_RESPONSE_BYTES) {
    throw stableCompletionClientError("FULFILLMENT_COMPLETION_RESPONSE_INVALID");
  }
  let value;
  try {
    value = JSON.parse(text);
  } catch {
    throw stableCompletionClientError("FULFILLMENT_COMPLETION_RESPONSE_INVALID");
  }
  if (!response.ok) {
    const serverCode = value?.error?.code;
    const code = typeof serverCode === "string" && /^[A-Z0-9_]{1,96}$/.test(serverCode)
      ? serverCode
      : "HTTP_" + response.status;
    session.invalidateForServerCode(code);
    throw stableCompletionClientError(code);
  }
  if (![200, 201].includes(response.status)) {
    throw stableCompletionClientError("FULFILLMENT_COMPLETION_RESPONSE_INVALID");
  }
  return reviewedPublicationResponse(
    value,
    expectedAgreementRecordId,
    expectedCommitmentId,
    expectedEvidenceKind,
    response.status,
  );
}

function createMarketplaceWebFulfillmentCompletionClient({ fetchImpl, session }) {
  const reviewed = reviewedConfiguration(fetchImpl, session);

  async function publishEvidence(
    agreementRecordIdValue,
    commitmentIdValue,
    evidenceKindValue,
  ) {
    const agreementRecordId = reviewedRecordId(agreementRecordIdValue);
    const commitmentId = reviewedCommitmentId(commitmentIdValue);
    const evidenceKind = reviewedEvidenceKind(evidenceKindValue);
    const path = "/api/agreements/" + encodeURIComponent(agreementRecordId) +
      "/commitments/" + encodeURIComponent(commitmentId) + "/completion-evidence";
    const authorization = reviewed.session.authorizationFor("POST", path);
    if (typeof authorization !== "string" || !authorization.startsWith("Bearer ")) {
      throw stableCompletionClientError("AUTH_REQUIRED");
    }
    const body = JSON.stringify({ evidence_kind: evidenceKind });
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
      throw stableCompletionClientError("APPLICATION_HTTP_TRANSPORT_FAILED");
    }
    return decodeResponse(
      response,
      reviewed.session,
      agreementRecordId,
      commitmentId,
      evidenceKind,
    );
  }

  return Object.freeze({ publishEvidence });
}

export {
  PROFILE,
  createMarketplaceWebFulfillmentCompletionClient,
};
