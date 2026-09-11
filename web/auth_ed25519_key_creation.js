"use strict";

const PROFILE = "MARKETPLACE_WEB_AUTH_ED25519_KEY_CREATION_V1";
const PUBLIC_KEY_PREFIX = "mkpk1_";
const PUBLIC_KEY_BYTES = 32;
const PUBLIC_KEY_PAYLOAD_CHARS = 43;
const BASE64URL = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_";

function stableKeyCreationError() {
  const error = new Error("Marketplace Web authentication key creation failed");
  error.code = "AUTH_KEY_CREATION_UNAVAILABLE";
  return error;
}

function exactKeys(value, expected) {
  if (value === null || typeof value !== "object" || Array.isArray(value)) return false;
  const keys = Object.keys(value).sort();
  const wanted = [...expected].sort();
  return keys.length === wanted.length && keys.every((key, index) => key === wanted[index]);
}

function reviewedSubtle(subtle) {
  if (subtle === null || typeof subtle !== "object" ||
      typeof subtle.generateKey !== "function" || typeof subtle.exportKey !== "function") {
    throw stableKeyCreationError();
  }
  return subtle;
}

function reviewedRequest(request) {
  if (!exactKeys(request, ["profile"]) || request.profile !== PROFILE) {
    throw stableKeyCreationError();
  }
  return request;
}

function reviewedPrivateKey(privateKey) {
  if (privateKey === null || typeof privateKey !== "object" ||
      privateKey.type !== "private" || privateKey.extractable !== false ||
      privateKey.algorithm === null || typeof privateKey.algorithm !== "object" ||
      privateKey.algorithm.name !== "Ed25519" || !Array.isArray(privateKey.usages) ||
      privateKey.usages.length !== 1 || privateKey.usages[0] !== "sign") {
    throw stableKeyCreationError();
  }
  return privateKey;
}

function reviewedPublicKey(publicKey) {
  if (publicKey === null || typeof publicKey !== "object" ||
      publicKey.type !== "public" || publicKey.extractable !== true ||
      publicKey.algorithm === null || typeof publicKey.algorithm !== "object" ||
      publicKey.algorithm.name !== "Ed25519" || !Array.isArray(publicKey.usages) ||
      publicKey.usages.length !== 1 || publicKey.usages[0] !== "verify") {
    throw stableKeyCreationError();
  }
  return publicKey;
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

function encodePublicKey(rawPublicKey) {
  if (!(rawPublicKey instanceof ArrayBuffer) || rawPublicKey.byteLength !== PUBLIC_KEY_BYTES) {
    throw stableKeyCreationError();
  }
  const payload = encodeBase64Url(new Uint8Array(rawPublicKey));
  if (payload.length !== PUBLIC_KEY_PAYLOAD_CHARS) throw stableKeyCreationError();
  return PUBLIC_KEY_PREFIX + payload;
}

function createMarketplaceWebAuthEd25519KeyCreation({ subtle }) {
  const reviewedCrypto = reviewedSubtle(subtle);

  async function createAuthenticationKey(requestValue) {
    reviewedRequest(requestValue);

    let keyPair;
    try {
      keyPair = await reviewedCrypto.generateKey(
        { name: "Ed25519" },
        false,
        ["sign", "verify"],
      );
    } catch {
      throw stableKeyCreationError();
    }

    if (!exactKeys(keyPair, ["privateKey", "publicKey"])) throw stableKeyCreationError();
    const privateKey = reviewedPrivateKey(keyPair.privateKey);
    const publicKey = reviewedPublicKey(keyPair.publicKey);

    let rawPublicKey;
    try {
      rawPublicKey = await reviewedCrypto.exportKey("raw", publicKey);
    } catch {
      throw stableKeyCreationError();
    }
    const publicKeyValue = encodePublicKey(rawPublicKey);

    return Object.freeze({
      profile: PROFILE,
      privateKey,
      publicKeyValue,
    });
  }

  return Object.freeze({ createAuthenticationKey });
}

export {
  PROFILE,
  createMarketplaceWebAuthEd25519KeyCreation,
};
