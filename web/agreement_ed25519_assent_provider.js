"use strict";

const PROFILE = "MARKETPLACE_WEB_AGREEMENT_ED25519_ASSENT_PROVIDER_V1";
const PREPARATION_PROFILE = "MARKETPLACE_AGREEMENT_ASSENT_SIGNING_PREPARATION_V1";
const MAX_SIGNING_INPUT_BYTES = 4096;
const ED25519_SIGNATURE_BYTES = 64;
const MAX_URI_BYTES = 2048;
const RECORD_ID = /^r1_[A-Za-z0-9_-]{43}$/;
const URI = /^[A-Za-z][A-Za-z0-9+.-]*:\S+$/;

function stableAssentError() {
  const error = new Error("Marketplace Web Agreement assent signing failed");
  error.code = "AGREEMENT_ASSENT_SIGNING_UNAVAILABLE";
  return error;
}

function reviewedUri(value) {
  if (typeof value !== "string" || value.length === 0 ||
      new TextEncoder().encode(value).length > MAX_URI_BYTES || !URI.test(value)) {
    throw stableAssentError();
  }
  return value;
}

function exactKeys(value, expected) {
  if (value === null || typeof value !== "object" || Array.isArray(value)) return false;
  const keys = Object.keys(value).sort();
  const wanted = [...expected].sort();
  return keys.length === wanted.length &&
    keys.every((key, index) => key === wanted[index]);
}

function reviewedPrivateKey(privateKey) {
  if (privateKey === null || typeof privateKey !== "object" ||
      privateKey.type !== "private" || privateKey.extractable !== false ||
      privateKey.algorithm === null || typeof privateKey.algorithm !== "object" ||
      privateKey.algorithm.name !== "Ed25519" || !Array.isArray(privateKey.usages) ||
      privateKey.usages.length !== 1 || privateKey.usages[0] !== "sign") {
    throw stableAssentError();
  }
  return privateKey;
}

function reviewedSubtle(subtle) {
  if (subtle === null || typeof subtle !== "object" || typeof subtle.sign !== "function") {
    throw stableAssentError();
  }
  return subtle;
}

function reviewedSigningInput(value) {
  if (!(value instanceof Uint8Array) ||
      value.length < 1 || value.length > MAX_SIGNING_INPUT_BYTES) {
    throw stableAssentError();
  }
  return new Uint8Array(value);
}

function reviewedPreparation(value, verificationMethod) {
  if (!exactKeys(
    value,
    ["profile", "agreementRecordId", "verificationMethod", "proofInput"],
  )) {
    throw stableAssentError();
  }
  if (value.profile !== PREPARATION_PROFILE ||
      value.verificationMethod !== verificationMethod ||
      typeof value.agreementRecordId !== "string" ||
      !RECORD_ID.test(value.agreementRecordId)) {
    throw stableAssentError();
  }
  const proofInput = reviewedSigningInput(value.proofInput);
  return Object.freeze({
    profile: value.profile,
    agreementRecordId: value.agreementRecordId,
    verificationMethod: value.verificationMethod,
    proofInput,
  });
}

function createMarketplaceWebAgreementEd25519AssentProvider({
  subtle,
  privateKey,
  verificationMethod,
}) {
  const reviewedSigner = reviewedSubtle(subtle);
  reviewedPrivateKey(privateKey);
  const pinnedVerificationMethod = reviewedUri(verificationMethod);

  async function createAgreementAssentSignature(preparationValue) {
    const preparation = reviewedPreparation(
      preparationValue,
      pinnedVerificationMethod,
    );
    reviewedPrivateKey(privateKey);

    let signatureResult;
    try {
      signatureResult = await reviewedSigner.sign(
        { name: "Ed25519" },
        privateKey,
        preparation.proofInput,
      );
    } catch {
      throw stableAssentError();
    }
    if (!(signatureResult instanceof ArrayBuffer)) throw stableAssentError();

    const signature = new Uint8Array(signatureResult);
    if (signature.length !== ED25519_SIGNATURE_BYTES) throw stableAssentError();

    return Object.freeze({
      profile: PROFILE,
      agreementRecordId: preparation.agreementRecordId,
      verificationMethod: pinnedVerificationMethod,
      signature,
    });
  }

  return Object.freeze({ createAgreementAssentSignature });
}

export {
  PROFILE,
  PREPARATION_PROFILE,
  createMarketplaceWebAgreementEd25519AssentProvider,
};
