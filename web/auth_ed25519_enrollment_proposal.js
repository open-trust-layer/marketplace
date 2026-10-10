"use strict";

const PROFILE = "MARKETPLACE_WEB_AUTH_ED25519_ENROLLMENT_PROPOSAL_V1";
const TYPE = "MarketplaceAuthenticationEnrollmentProposal";
const ENROLLMENT_PUBLIC_KEY_PREFIX = "mkpk1_";
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

// TextEncoder silently replaces unpaired UTF-16 surrogates with U+FFFD.
// Authentication identifiers must preserve their exact scalar sequence:
// silently repairing a malformed string would change its identity bytes.
function validUnicodeScalarSequence(value) {
  for (let index = 0; index < value.length; index += 1) {
    const unit = value.charCodeAt(index);
    if (unit >= 0xd800 && unit <= 0xdbff) {
      const next = value.charCodeAt(index + 1);
      if (!(next >= 0xdc00 && next <= 0xdfff)) return false;
      index += 1;
    } else if (unit >= 0xdc00 && unit <= 0xdfff) {
      return false;
    }
  }
  return true;
}

function reviewedUri(value) {
  if (typeof value !== "string" || value.length === 0 ||
      !validUnicodeScalarSequence(value) || utf8(value).length > MAX_URI_BYTES ||
      !/^[A-Za-z][A-Za-z0-9+.-]*:\S+$/.test(value)) {
    throw stableEnrollmentProposalError();
  }
  return value;
}

function exactKeys(value, expected) {
  if (value === null || typeof value !== "object" || Array.isArray(value)) return false;
  const keys = Object.keys(value).sort();
  const wanted = [...expected].sort();
  return keys.length === wanted.length && keys.every((key, index) => key === wanted[index]);
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

function reviewedPublicKey(value) {
  if (typeof value !== "string" || !value.startsWith(ENROLLMENT_PUBLIC_KEY_PREFIX)) {
    throw stableEnrollmentProposalError();
  }
  const payload = value.slice(ENROLLMENT_PUBLIC_KEY_PREFIX.length);
  if (payload.length !== PUBLIC_KEY_PAYLOAD_CHARS) throw stableEnrollmentProposalError();
  const bytes = decodeBase64Url(payload, PUBLIC_KEY_BYTES);
  if (ENROLLMENT_PUBLIC_KEY_PREFIX + encodeBase64Url(bytes) !== value) {
    throw stableEnrollmentProposalError();
  }
  return bytes;
}

function reviewedRequest(request) {
  if (!exactKeys(request, ["profile", "principal", "verificationMethod", "publicKeyValue"]) ||
      request.profile !== PROFILE) {
    throw stableEnrollmentProposalError();
  }
  return Object.freeze({
    principal: reviewedUri(request.principal),
    verificationMethod: reviewedUri(request.verificationMethod),
    publicKeyBytes: reviewedPublicKey(request.publicKeyValue),
  });
}

function createMarketplaceWebAuthEd25519EnrollmentProposal(requestValue) {
  const request = reviewedRequest(requestValue);
  const payload = encodeBase64Url(request.publicKeyBytes);
  if (payload.length !== PUBLIC_KEY_PAYLOAD_CHARS) throw stableEnrollmentProposalError();

  return Object.freeze({
    profile: PROFILE,
    type: TYPE,
    principal: request.principal,
    verificationMethod: request.verificationMethod,
    publicKey: EVIDENCE_PUBLIC_KEY_PREFIX + payload,
  });
}

export {
  PROFILE,
  createMarketplaceWebAuthEd25519EnrollmentProposal,
};
