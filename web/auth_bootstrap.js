"use strict";

import { MarketplaceMemorySession } from "./client_session.js";
import {
  PROFILE as KEY_CREATION_PROFILE,
  createMarketplaceWebAuthEd25519KeyCreation,
} from "./auth_ed25519_key_creation.js";
import { createMarketplaceWebAuthEd25519ProofProvider } from "./auth_ed25519_proof_provider.js";
import { createMarketplaceWebAuthEstablishment } from "./auth_establishment.js";
import { createMarketplaceWebAgreementEd25519AssentProvider } from "./agreement_ed25519_assent_provider.js";
import { createMarketplaceWebAgreementAssentClient } from "./agreement_assent_client.js";

const BROWSER_PUBLIC_KEY_PREFIX = "mkpk1_";
const EVIDENCE_PUBLIC_KEY_PREFIX = "mkp1_";
const PUBLIC_KEY_PAYLOAD_CHARS = 43;
const BASE64URL = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_";
const URI = /^[A-Za-z][A-Za-z0-9+.-]*:\S+$/;
const MAX_URI_BYTES = 2048;

function stableBootstrapError(code) {
  const error = new Error("Marketplace browser authentication bootstrap failed");
  error.code = code;
  return error;
}

function utf8Bytes(value) {
  return new TextEncoder().encode(value).length;
}

function reviewedSubtle(value) {
  if (value === null || typeof value !== "object" ||
      typeof value.generateKey !== "function" ||
      typeof value.exportKey !== "function" || typeof value.sign !== "function") {
    throw stableBootstrapError("AUTH_BOOTSTRAP_CONFIGURATION_INVALID");
  }
  return value;
}

function reviewedFetch(value) {
  if (typeof value !== "function") {
    throw stableBootstrapError("AUTH_BOOTSTRAP_CONFIGURATION_INVALID");
  }
  return value;
}

function reviewedUri(value) {
  if (typeof value !== "string" || utf8Bytes(value) > MAX_URI_BYTES || !URI.test(value)) {
    throw stableBootstrapError("AUTH_REQUEST_INVALID");
  }
  return value;
}

function evidencePublicKeyFromBrowserCarrier(value) {
  if (typeof value !== "string" || !value.startsWith(BROWSER_PUBLIC_KEY_PREFIX)) {
    throw stableBootstrapError("AUTH_PUBLIC_KEY_INVALID");
  }
  const payload = value.slice(BROWSER_PUBLIC_KEY_PREFIX.length);
  if (payload.length !== PUBLIC_KEY_PAYLOAD_CHARS) {
    throw stableBootstrapError("AUTH_PUBLIC_KEY_INVALID");
  }
  for (const character of payload) {
    if (!BASE64URL.includes(character)) throw stableBootstrapError("AUTH_PUBLIC_KEY_INVALID");
  }
  const finalValue = BASE64URL.indexOf(payload[payload.length - 1]);
  if (finalValue < 0 || (finalValue & 0x03) !== 0) {
    throw stableBootstrapError("AUTH_PUBLIC_KEY_INVALID");
  }
  return EVIDENCE_PUBLIC_KEY_PREFIX + payload;
}

function createMarketplaceBrowserAuthBootstrap({ subtle, fetchImpl }) {
  const reviewedCrypto = reviewedSubtle(subtle);
  const reviewedTransport = reviewedFetch(fetchImpl);
  const session = new MarketplaceMemorySession();
  let keyResult = null;
  let activeVerificationMethod = null;

  async function createAuthenticationKey() {
    if (keyResult !== null || session.isActive) {
      throw stableBootstrapError("AUTH_KEY_ALREADY_CREATED");
    }
    const keyCreation = createMarketplaceWebAuthEd25519KeyCreation({ subtle: reviewedCrypto });
    const created = await keyCreation.createAuthenticationKey({ profile: KEY_CREATION_PROFILE });
    const evidencePublicKeyValue = evidencePublicKeyFromBrowserCarrier(created.publicKeyValue);
    keyResult = created;
    return Object.freeze({
      profile: created.profile,
      publicKeyValue: created.publicKeyValue,
      evidencePublicKeyValue,
    });
  }

  async function establishSession(principalValue, verificationMethodValue) {
    if (keyResult === null) throw stableBootstrapError("AUTH_KEY_REQUIRED");
    if (session.isActive) throw stableBootstrapError("AUTH_SESSION_ALREADY_ACTIVE");
    const principal = reviewedUri(principalValue);
    const verificationMethod = reviewedUri(verificationMethodValue);
    const proofProvider = createMarketplaceWebAuthEd25519ProofProvider({
      subtle: reviewedCrypto,
      privateKey: keyResult.privateKey,
      verificationMethod,
    });
    const establishment = createMarketplaceWebAuthEstablishment({
      fetchImpl: reviewedTransport,
      session,
      proofProvider,
    });
    const result = await establishment.establishSession(principal, verificationMethod);
    activeVerificationMethod = verificationMethod;
    return result;
  }

  function agreementAssentClient() {
    if (keyResult === null || !session.isActive || activeVerificationMethod === null) {
      throw stableBootstrapError("AGREEMENT_ASSENT_AUTH_REQUIRED");
    }
    const signer = createMarketplaceWebAgreementEd25519AssentProvider({
      subtle: reviewedCrypto,
      privateKey: keyResult.privateKey,
      verificationMethod: activeVerificationMethod,
    });
    return createMarketplaceWebAgreementAssentClient({
      fetchImpl: reviewedTransport,
      session,
      signer,
    });
  }

  function state() {
    const active = session.isActive;
    return Object.freeze({
      keyReady: keyResult !== null,
      active,
      principal: active ? session.requirePrincipal() : null,
      verificationMethod: active ? activeVerificationMethod : null,
    });
  }

  function reset() {
    session.clear();
    keyResult = null;
    activeVerificationMethod = null;
  }

  return Object.freeze({
    createAuthenticationKey,
    establishSession,
    agreementAssentClient,
    state,
    reset,
  });
}

export {
  createMarketplaceBrowserAuthBootstrap,
  evidencePublicKeyFromBrowserCarrier,
};
