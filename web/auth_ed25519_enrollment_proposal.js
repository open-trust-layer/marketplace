"use strict";

const PROFILE = "MARKETPLACE_WEB_AUTH_ED25519_ENROLLMENT_PROPOSAL_V1";
const PROPOSAL_TYPE = "MarketplaceAuthenticationEd25519EnrollmentProposal";
const WEB_PUBLIC_KEY_PREFIX = "mkpk1_";
const EVIDENCE_PUBLIC_KEY_PREFIX = "mkp1_";
const PUBLIC_KEY_BYTES = 32;
const PUBLIC_KEY_PAYLOAD_CHARS = 43;
const MAX_URI_BYTES = 2048;
const BASE64URL = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_";

function stableEnrollmentProposalError() {
  const error = new Error("Marketplace Web authentication enrollment proposal failed");
  error.code = "AUTH_ENROLLMENT_PROPOSAL_UNAVAILABLE";
  return error;
}

function utf8(value) {
  return new TextEncoder().encode(value);
}

function exactKeys(value, expected) {
  if (value === null || typeof value !== "object" || Array.isArray(value)) return false;
  const keys = Object.keys(value).sort();
  const wanted = [...expected].sort();
  return keys.length === wanted.length && keys.every((key, index) => key === wanted[index]);
}

function reviewedUri(value) {
  if (typeof value !== "string" || value.length === 0 || utf8(value).length > MAX_URI_BYTES ||
      !/^[A-Za-z][A-Za-z0-9+.-]*:\S+$/.test(value)) {
    throw stableEnrollmentProposalError();
  }
  return value;
}

function base64UrlIndex(character) {
  const value = BASE64URL.indexOf(character);
  if (value < 0) throw stableEnrollmentProposalError();
  return value;
}

function encodeBase64Url(bytes) {
  let output = "";
  let buffer = 0;
  let bits = 0;
  for (const byte of bytes) {
    buffer = (buffer << 8) | byte;
    bits += 8;
    while (bits >= 6) {
      bits -= 6;
      output += BASE64URL[(buffer >> bits) & 0x3f];
      buffer &= bits === 0 ? 0 : (1 << bits) - 1;
    }
  }
  if (bits > 0) output += BASE64URL[(buffer << (6 - bits)) & 0x3f];
  return output;
}

function decodeBase64Url(payload, expectedBytes) {
  let buffer = 0;
  let bits = 0;
  const output = [];
  for (const character of payload) {
    buffer = (buffer << 6) | base64UrlIndex(character);
    bits += 6;
    if (bits >= 8) {
      bits -= 8;
      output.push((buffer >> bits) & 0xff);
      buffer &= bits === 0 ? 0 : (1 << bits) - 1;
    }
  }
  if (bits > 0 && buffer !== 0) throw stableEnrollmentProposalError();
  const bytes = Uint8Array.from(output);
  if (bytes.length !== expectedBytes || encodeBase64Url(bytes) !== payload) {
    throw stableEnrollmentProposalError();
  }
  return bytes;
}

function reviewedPublicKeyValue(value) {
  if (typeof value !== "string" || !value.startsWith(WEB_PUBLIC_KEY_PREFIX)) {
    throw stableEnrollmentProposalError();
  }
  const payload = value.slice(WEB_PUBLIC_KEY_PREFIX.length);
  if (payload.length !== PUBLIC_KEY_PAYLOAD_CHARS) throw stableEnrollmentProposalError();
  return decodeBase64Url(payload, PUBLIC_KEY_BYTES);
}

function createMarketplaceWebAuthEd25519EnrollmentProposal(requestValue) {
  if (!exactKeys(requestValue, ["profile", "principal", "verificationMethod", "publicKeyValue"]) ||
      requestValue.profile !== PROFILE) {
    throw stableEnrollmentProposalError();
  }

  const principal = reviewedUri(requestValue.principal);
  const verificationMethod = reviewedUri(requestValue.verificationMethod);
  const publicKeyBytes = reviewedPublicKeyValue(requestValue.publicKeyValue);
  const publicKey = EVIDENCE_PUBLIC_KEY_PREFIX + encodeBase64Url(publicKeyBytes);

  return Object.freeze({
    profile: PROFILE,
    type: PROPOSAL_TYPE,
    principal,
    verificationMethod,
    publicKey,
  });
}

export {
  PROFILE,
  PROPOSAL_TYPE,
  createMarketplaceWebAuthEd25519EnrollmentProposal,
};
