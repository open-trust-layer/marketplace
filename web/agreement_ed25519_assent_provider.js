"use strict";

const PROFILE = "MARKETPLACE_WEB_AGREEMENT_ED25519_ASSENT_PROVIDER_V1";
const MAX_SIGNING_INPUT_BYTES = 4096;
const MAX_URI_BYTES = 2048;
const RECORD_ID_PATTERN = /^r1_[A-Za-z0-9_-]{43}$/;

function stableAssentError() {
  const error = new Error("Marketplace Web Agreement assent signing operation failed");
  error.code = "AGREEMENT_ASSENT_SIGNATURE_UNAVAILABLE";
  return error;
}

function utf8(value) {
  return new TextEncoder().encode(value);
}

function reviewedUri(value) {
  if (typeof value !== "string" || value.length === 0 ||
      utf8(value).length > MAX_URI_BYTES ||
      !/^[A-Za-z][A-Za-z0-9+.-]*:\S+$/.test(value)) {
    throw stableAssentError();
  }
  return value;
}

function reviewedRecordId(value) {
  if (typeof value !== "string" || !RECORD_ID_PATTERN.test(value)) {
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
  if (subtle === null || typeof subtle !== "object" ||
      typeof subtle.sign !== "function") {
    throw stableAssentError();
  }
  return subtle;
}

function reviewedPreparation(preparation, verificationMethod) {
  if (!exactKeys(
    preparation,
    ["agreementRecordId", "verificationMethod", "signingInput"],
  )) {
    throw stableAssentError();
  }
  const agreementRecordId = reviewedRecordId(preparation.agreementRecordId);
  if (preparation.verificationMethod !== verificationMethod) {
    throw stableAssentError();
  }
  reviewedUri(preparation.verificationMethod);
  if (!(preparation.signingInput instanceof Uint8Array) ||
      preparation.signingInput.length < 1 ||
      preparation.signingInput.length > MAX_SIGNING_INPUT_BYTES) {
    throw stableAssentError();
  }
  const signingBytes = Uint8Array.from(preparation.signingInput);
  return Object.freeze({
    agreementRecordId,
    verificationMethod,
    signingBytes,
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
        preparation.signingBytes,
      );
    } catch {
      throw stableAssentError();
    }
    if (!(signatureResult instanceof ArrayBuffer) ||
        signatureResult.byteLength !== 64) {
      throw stableAssentError();
    }
    return new Uint8Array(signatureResult);
  }

  return Object.freeze({ createAgreementAssentSignature });
}

export {
  PROFILE,
  createMarketplaceWebAgreementEd25519AssentProvider,
};
