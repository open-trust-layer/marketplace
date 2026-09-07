"use strict";

const SESSION_TOKEN = /^mkt1_[A-Za-z0-9_-]{43}$/;
const PRINCIPAL_URI = /^[A-Za-z][A-Za-z0-9+.-]*:\S+$/;
const MAX_RESPONSE_JSON_BYTES = 300 * 1024;

function stableClientError(code) {
  const error = new Error("Marketplace client session operation failed");
  error.code = code;
  return error;
}

function reviewedApiPath(path) {
  if (typeof path !== "string" || !path.startsWith("/api/") || path.startsWith("//")) {
    throw stableClientError("CLIENT_PATH_INVALID");
  }
  return path;
}

function reviewedAuthenticatedRoute(method, path) {
  if (method === "GET") return path === "/api/auth/session";
  if (method !== "POST") return false;
  if (path === "/api/auth/logout") return true;
  if (path === "/api/product-listings") return true;
  if (path === "/api/intents") return true;
  if (!path.startsWith("/api/intents/")) return false;
  const parts = path.slice("/api/intents/".length).split("/");
  if (parts.length !== 2 || parts[0].length === 0) return false;
  if (parts[0].includes("?") || parts[0].includes("#")) return false;
  const tail = parts[1];
  return tail === "responses" || tail === "proposals";
}

class MarketplaceMemorySession {
  #bearerToken = null;
  #principal = null;

  get isActive() {
    return this.#bearerToken !== null;
  }

  adoptEstablishedSession(principal, sessionToken) {
    if (typeof principal !== "string" || !PRINCIPAL_URI.test(principal)) {
      throw stableClientError("AUTH_SESSION_INVALID");
    }
    if (typeof sessionToken !== "string" || !SESSION_TOKEN.test(sessionToken)) {
      throw stableClientError("AUTH_SESSION_INVALID");
    }
    this.#principal = principal;
    this.#bearerToken = sessionToken;
  }

  requirePrincipal() {
    if (this.#bearerToken === null || this.#principal === null) {
      throw stableClientError("AUTH_REQUIRED");
    }
    return this.#principal;
  }
  authorizationFor(method, path) {
    if (!reviewedAuthenticatedRoute(method, path)) return null;
    const token = this.#bearerToken;
    if (token === null) throw stableClientError("AUTH_REQUIRED");
    return `Bearer ${token}`;
  }

  detachAuthorizationForLogout() {
    const token = this.#bearerToken;
    if (token === null) throw stableClientError("AUTH_REQUIRED");
    const authorization = `Bearer ${token}`;
    this.clear();
    return authorization;
  }

  invalidateForServerCode(code) {
    if (code === "AUTH_SESSION_INVALID") this.clear();
  }

  clear() {
    this.#bearerToken = null;
    this.#principal = null;
  }

  toString() {
    return `MarketplaceMemorySession(active=${this.isActive})`;
  }
}

function productListingForSession(session, fields) {
  if (fields === null || typeof fields !== "object" || Array.isArray(fields)) {
    throw stableClientError("AUTH_PRINCIPAL_MISMATCH");
  }
  if (Object.hasOwn(fields, "seller_principal")) {
    throw stableClientError("AUTH_PRINCIPAL_MISMATCH");
  }
  return { ...fields, seller_principal: session.requirePrincipal() };
}

function proposalForSession(session, fields) {
  if (fields === null || typeof fields !== "object" || Array.isArray(fields)) {
    throw stableClientError("AUTH_PRINCIPAL_MISMATCH");
  }
  if (Object.hasOwn(fields, "buyer_principal")) {
    throw stableClientError("AUTH_PRINCIPAL_MISMATCH");
  }
  return { ...fields, buyer_principal: session.requirePrincipal() };
}

function requireRawIssuer(session, rawRecordJson, rawIssuerPrincipal) {
  const principal = session.requirePrincipal();
  let issuer;
  try {
    issuer = rawIssuerPrincipal(rawRecordJson);
  } catch {
    throw stableClientError("AUTH_PRINCIPAL_MISMATCH");
  }
  if (issuer !== principal) throw stableClientError("AUTH_PRINCIPAL_MISMATCH");
  return rawRecordJson;
}
async function decodeResponse(response, session) {
  const text = await response.text();
  if (new TextEncoder().encode(text).length > MAX_RESPONSE_JSON_BYTES) {
    throw stableClientError("APPLICATION_HTTP_RESPONSE_TOO_LARGE");
  }
  let documentValue = {};
  if (text) {
    try {
      documentValue = JSON.parse(text);
    } catch {
      throw stableClientError("RESPONSE_JSON_INVALID");
    }
  }
  if (!response.ok) {
    const code = documentValue?.error?.code;
    const stableCode = typeof code === "string" ? code : `HTTP_${response.status}`;
    session.invalidateForServerCode(stableCode);
    throw stableClientError(stableCode);
  }
  return documentValue;
}

function createMarketplaceSessionClient(fetchImpl, rawIssuerPrincipal) {
  if (typeof fetchImpl !== "function" || typeof rawIssuerPrincipal !== "function") {
    throw stableClientError("CLIENT_CONFIGURATION_INVALID");
  }
  const session = new MarketplaceMemorySession();

  async function request(path, { method = "GET", body = null } = {}) {
    const reviewedPath = reviewedApiPath(path);
    const headers = { Accept: "application/json" };
    const authorization = session.authorizationFor(method, reviewedPath);
    if (authorization !== null) headers.Authorization = authorization;
    const init = {
      method,
      headers,
      credentials: "omit",
      cache: "no-store",
      redirect: "error",
      referrerPolicy: "no-referrer",
    };
    if (body !== null) {
      headers["Content-Type"] = "application/json";
      init.body = body;
    }
    let response;
    try {
      response = await fetchImpl(reviewedPath, init);
    } catch {
      throw stableClientError("APPLICATION_HTTP_TRANSPORT_FAILED");
    }
    return decodeResponse(response, session);
  }

  async function createProductListing(fields) {
    const body = JSON.stringify(productListingForSession(session, fields));
    return request("/api/product-listings", { method: "POST", body });
  }

  async function createProposal(parentId, fields) {
    if (typeof parentId !== "string" || parentId.length === 0 || parentId.length > 512) {
      throw stableClientError("RECORD_ID_INVALID");
    }
    const body = JSON.stringify(proposalForSession(session, fields));
    const path = `/api/intents/${encodeURIComponent(parentId)}/proposals`;
    return request(path, { method: "POST", body });
  }

  async function createIntent(rawRecordJson) {
    const body = requireRawIssuer(session, rawRecordJson, rawIssuerPrincipal);
    return request("/api/intents", { method: "POST", body });
  }

  async function respondToIntent(parentId, rawRecordJson) {
    if (typeof parentId !== "string" || parentId.length === 0 || parentId.length > 512) {
      throw stableClientError("RECORD_ID_INVALID");
    }
    const body = requireRawIssuer(session, rawRecordJson, rawIssuerPrincipal);
    const path = `/api/intents/${encodeURIComponent(parentId)}/responses`;
    return request(path, { method: "POST", body });
  }

  async function inspectSession() {
    return request("/api/auth/session", { method: "GET" });
  }

  async function logout() {
    const authorization = session.detachAuthorizationForLogout();
    const headers = { Accept: "application/json", Authorization: authorization };
    let response;
    try {
      response = await fetchImpl("/api/auth/logout", {
        method: "POST",
        headers,
        credentials: "omit",
        cache: "no-store",
        redirect: "error",
        referrerPolicy: "no-referrer",
      });
    } catch {
      throw stableClientError("APPLICATION_HTTP_TRANSPORT_FAILED");
    }
    return decodeResponse(response, session);
  }

  return Object.freeze({
    session,
    request,
    createProductListing,
    createProposal,
    createIntent,
    respondToIntent,
    inspectSession,
    logout,
  });
}

export {
  MarketplaceMemorySession,
  createMarketplaceSessionClient,
  productListingForSession,
  proposalForSession,
  reviewedAuthenticatedRoute,
};
