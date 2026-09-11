"use strict";

const PROFILE = "MARKETPLACE_WEB_AUTH_ED25519_PROOF_PROVIDER_V1";
const ESTABLISHMENT_PROFILE = "MARKETPLACE_WEB_AUTH_SESSION_ESTABLISHMENT_V1";
const AUTH_DOMAIN = "https://open-trust-layer.github.io/marketplace/application-auth/v1";
const AUTH_PURPOSE = "assertion";
const PROOF_TYPE = "MarketplaceAuthenticationProof";
const PROOF_VERSION = 1;
const PROOF_CRYPTOSUITE = "https://open-trust-layer.github.io/marketplace/application-auth/eddsa-ed25519-v1";
const TRANSCRIPT_DOMAIN = "MARKETPLACE-AUTH";
const CHALLENGE_PREFIX = "mkc1_";
const SIGNATURE_PREFIX = "mks1_";
const BASE64URL = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_";
const CHALLENGE_PAYLOAD_CHARS = 43;
const SIGNATURE_PAYLOAD_CHARS = 86;
const MAX_URI_BYTES = 2048;

function stableProofError() {
  const error = new Error("Marketplace Web authentication proof operation failed");
  error.code = "AUTH_PROOF_UNAVAILABLE";
  return error;
}

function utf8(value) {
  return new TextEncoder().encode(value);
}

function reviewedUri(value) {
  if (typeof value !== "string" || value.length === 0 || utf8(value).length > MAX_URI_BYTES ||
      !/^[A-Za-z][A-Za-z0-9+.-]*:\S+$/.test(value)) {
    throw stableProofError();
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
  if (value < 0) throw stableProofError();
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
  if (bits > 0 && buffer !== 0) throw stableProofError();
  const bytes = Uint8Array.from(output);
  if (bytes.length !== expectedBytes || encodeBase64Url(bytes) !== payload) throw stableProofError();
  return bytes;
}

function decodeChallenge(value) {
  if (typeof value !== "string" || !value.startsWith(CHALLENGE_PREFIX)) throw stableProofError();
  const payload = value.slice(CHALLENGE_PREFIX.length);
  if (payload.length !== CHALLENGE_PAYLOAD_CHARS) throw stableProofError();
  return decodeBase64Url(payload, 32);
}

function lengthPrefixed(value) {
  const bytes = utf8(value);
  if (bytes.length > 0xffff) throw stableProofError();
  const output = new Uint8Array(2 + bytes.length);
  output[0] = (bytes.length >> 8) & 0xff;
  output[1] = bytes.length & 0xff;
  output.set(bytes, 2);
  return output;
}

function concatenate(parts) {
  const size = parts.reduce((total, part) => total + part.length, 0);
  const output = new Uint8Array(size);
  let offset = 0;
  for (const part of parts) {
    output.set(part, offset);
    offset += part.length;
  }
  return output;
}

function buildTranscript(verificationMethod, challengeBytes) {
  return concatenate([
    utf8(TRANSCRIPT_DOMAIN),
    Uint8Array.of(0x00, PROOF_VERSION),
    lengthPrefixed(PROOF_CRYPTOSUITE),
    lengthPrefixed(AUTH_PURPOSE),
    lengthPrefixed(verificationMethod),
    lengthPrefixed(AUTH_DOMAIN),
    challengeBytes,
  ]);
}

function reviewedPrivateKey(privateKey) {
  if (privateKey === null || typeof privateKey !== "object" ||
      privateKey.type !== "private" || privateKey.extractable !== false ||
      privateKey.algorithm === null || typeof privateKey.algorithm !== "object" ||
      privateKey.algorithm.name !== "Ed25519" || !Array.isArray(privateKey.usages) ||
      privateKey.usages.length !== 1 || privateKey.usages[0] !== "sign") {
    throw stableProofError();
  }
  return privateKey;
}

function reviewedSubtle(subtle) {
  if (subtle === null || typeof subtle !== "object" || typeof subtle.sign !== "function") {
    throw stableProofError();
  }
  return subtle;
}

function reviewedRequest(request, verificationMethod) {
  if (!exactKeys(request, ["profile", "principal", "verificationMethod", "challenge", "domain", "proofPurpose"])) {
    throw stableProofError();
  }
  if (request.profile !== ESTABLISHMENT_PROFILE ||
      request.verificationMethod !== verificationMethod ||
      request.domain !== AUTH_DOMAIN || request.proofPurpose !== AUTH_PURPOSE) {
    throw stableProofError();
  }
  reviewedUri(request.principal);
  reviewedUri(request.verificationMethod);
  return request;
}

function encodeSignature(bytes) {
  if (!(bytes instanceof Uint8Array) || bytes.length !== 64) throw stableProofError();
  const payload = encodeBase64Url(bytes);
  if (payload.length !== SIGNATURE_PAYLOAD_CHARS) throw stableProofError();
  return SIGNATURE_PREFIX + payload;
}

function createMarketplaceWebAuthEd25519ProofProvider({ subtle, privateKey, verificationMethod }) {
  const reviewedSigner = reviewedSubtle(subtle);
  reviewedPrivateKey(privateKey);
  const pinnedVerificationMethod = reviewedUri(verificationMethod);

  async function createAuthenticationProof(requestValue) {
    const request = reviewedRequest(requestValue, pinnedVerificationMethod);
    const challengeBytes = decodeChallenge(request.challenge);
    reviewedPrivateKey(privateKey);
    const transcript = buildTranscript(pinnedVerificationMethod, challengeBytes);
    let signatureResult;
    try {
      signatureResult = await reviewedSigner.sign(
        { name: "Ed25519" },
        privateKey,
        transcript,
      );
    } catch {
      throw stableProofError();
    }
    if (!(signatureResult instanceof ArrayBuffer)) throw stableProofError();
    const proofValue = encodeSignature(new Uint8Array(signatureResult));
    return Object.freeze({
      type: PROOF_TYPE,
      version: PROOF_VERSION,
      cryptosuite: PROOF_CRYPTOSUITE,
      proofPurpose: AUTH_PURPOSE,
      verificationMethod: pinnedVerificationMethod,
      domain: AUTH_DOMAIN,
      challenge: request.challenge,
      proofValue,
    });
  }

  return Object.freeze({ createAuthenticationProof });
}

export {
  PROFILE,
  createMarketplaceWebAuthEd25519ProofProvider,
};
