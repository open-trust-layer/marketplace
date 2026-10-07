"use strict";

const PROFILE = "MARKETPLACE_AUTHENTICATED_LOCAL_FLIGHT_EVIDENCE_V1";
const LOOPBACK_HOST = "127.0.0.1";
const FORMATION_SUFFICIENT = "EVIDENCE_SUFFICIENT_FOR_PROFILE";
const COMMITMENT_ID = "seller-delivery";
const EVIDENCE_KIND = "CLAIMED_COMPLETE_PERFORMANCE";
const DISPOSITIONS = new Set(["STORED", "DUPLICATE"]);
const COMMIT_SHA = /^[0-9a-f]{40}$/;

function stableProjectionError(code) {
  const error = new Error("Marketplace authenticated local-flight evidence projection failed");
  error.code = code;
  return error;
}

function reviewedRecordId(value) {
  if (typeof value !== "string" || value.length < 1 || value.length > 512) {
    throw stableProjectionError("EVIDENCE_RECORD_ID_INVALID");
  }
  for (const character of value) {
    const point = character.charCodeAt(0);
    if (point < 33 || point > 126 || "/?#".includes(character)) {
      throw stableProjectionError("EVIDENCE_RECORD_ID_INVALID");
    }
  }
  return value;
}

function reviewedChangeSeq(value) {
  if (value === null) return null;
  if (!Number.isSafeInteger(value) || value < 1) {
    throw stableProjectionError("EVIDENCE_CHANGE_SEQ_INVALID");
  }
  return value;
}

function reviewedDisposition(value) {
  if (typeof value !== "string" || !DISPOSITIONS.has(value)) {
    throw stableProjectionError("EVIDENCE_DISPOSITION_INVALID");
  }
  return value;
}

function reviewedObject(value, code) {
  if (value === null || typeof value !== "object" || Array.isArray(value)) {
    throw stableProjectionError(code);
  }
  return value;
}

function createMarketplaceAuthenticatedLocalFlightEvidence({
  mainCommit,
  ciRunNumber,
  runtimeHost,
  sellerAuthenticated,
  buyerAuthenticated,
  listingRecordId,
  proposalRecordId,
  acceptanceRecordId,
  formation,
  publication,
  completion,
}) {
  if (typeof mainCommit !== "string" || !COMMIT_SHA.test(mainCommit)) {
    throw stableProjectionError("EVIDENCE_MAIN_COMMIT_INVALID");
  }
  if (!Number.isSafeInteger(ciRunNumber) || ciRunNumber < 1) {
    throw stableProjectionError("EVIDENCE_CI_RUN_INVALID");
  }
  if (runtimeHost !== LOOPBACK_HOST) {
    throw stableProjectionError("EVIDENCE_RUNTIME_HOST_INVALID");
  }
  if (sellerAuthenticated !== true) {
    throw stableProjectionError("EVIDENCE_SELLER_AUTH_INVALID");
  }
  if (buyerAuthenticated !== true) {
    throw stableProjectionError("EVIDENCE_BUYER_AUTH_INVALID");
  }

  const listing = reviewedRecordId(listingRecordId);
  const proposal = reviewedRecordId(proposalRecordId);
  const acceptance = reviewedRecordId(acceptanceRecordId);
  const formationValue = reviewedObject(formation, "EVIDENCE_FORMATION_INVALID");
  const agreement = reviewedRecordId(formationValue.agreementRecordId);
  const lifecycleIds = [listing, proposal, acceptance, agreement];
  if (new Set(lifecycleIds).size !== lifecycleIds.length) {
    throw stableProjectionError("EVIDENCE_RECORD_ID_COLLISION");
  }
  if (
    formationValue.formationEvidence !== FORMATION_SUFFICIENT ||
    !Array.isArray(formationValue.missingPrincipals) ||
    formationValue.missingPrincipals.length !== 0
  ) {
    throw stableProjectionError("EVIDENCE_FORMATION_INVALID");
  }

  const publicationValue = reviewedObject(publication, "EVIDENCE_PUBLICATION_INVALID");
  if (reviewedRecordId(publicationValue.agreementRecordId) !== agreement) {
    throw stableProjectionError("EVIDENCE_AGREEMENT_MISMATCH");
  }
  const publicationDisposition = reviewedDisposition(publicationValue.disposition);
  const publicationChangeSeq = reviewedChangeSeq(publicationValue.changeSeq);

  const completionValue = reviewedObject(completion, "EVIDENCE_COMPLETION_INVALID");
  const completionRecordId = reviewedRecordId(completionValue.recordId);
  if (lifecycleIds.includes(completionRecordId)) {
    throw stableProjectionError("EVIDENCE_RECORD_ID_COLLISION");
  }
  if (reviewedRecordId(completionValue.agreementRecordId) !== agreement) {
    throw stableProjectionError("EVIDENCE_AGREEMENT_MISMATCH");
  }
  if (completionValue.commitmentId !== COMMITMENT_ID) {
    throw stableProjectionError("EVIDENCE_COMMITMENT_INVALID");
  }
  if (completionValue.evidenceKind !== EVIDENCE_KIND) {
    throw stableProjectionError("EVIDENCE_KIND_INVALID");
  }
  const completionDisposition = reviewedDisposition(completionValue.disposition);
  const completionChangeSeq = reviewedChangeSeq(completionValue.changeSeq);

  return Object.freeze({
    profile: PROFILE,
    main_commit: mainCommit,
    ci_run_number: ciRunNumber,
    runtime_host: LOOPBACK_HOST,
    seller_authenticated: true,
    buyer_authenticated: true,
    listing_record_id: listing,
    proposal_record_id: proposal,
    acceptance_record_id: acceptance,
    agreement_record_id: agreement,
    formation_evidence: FORMATION_SUFFICIENT,
    missing_principals: Object.freeze([]),
    agreement_publication: Object.freeze({
      agreement_record_id: agreement,
      disposition: publicationDisposition,
      change_seq: publicationChangeSeq,
    }),
    completion: Object.freeze({
      record_id: completionRecordId,
      agreement_record_id: agreement,
      commitment_id: COMMITMENT_ID,
      evidence_kind: EVIDENCE_KIND,
      disposition: completionDisposition,
      change_seq: completionChangeSeq,
    }),
    universal_truth: false,
    payment_or_settlement_evaluated: false,
    public_network_exposed: false,
    public_deployment: false,
  });
}

export {
  PROFILE,
  createMarketplaceAuthenticatedLocalFlightEvidence,
};
