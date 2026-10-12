
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

function reviewedAgreementAssentRoute(path) {
  if (!path.startsWith("/api/agreements/")) return false;
  const parts = path.slice("/api/agreements/".length).split("/");
  if (parts.length < 2 || parts.length > 3 || parts[0].length === 0 || parts[0].length > 1536) {
    return false;
  }
  if (parts[0].includes("?") || parts[0].includes("#")) return false;
  if (parts[1] !== "assent") return false;
  if (parts.length === 2) return true;
  return parts[2] === "preparation" || parts[2] === "status";
}

function reviewedAgreementPublicationRoute(path) {
  if (!path.startsWith("/api/agreements/")) return false;
  const parts = path.slice("/api/agreements/".length).split("/");
  if (parts.length !== 1 || parts[0].length === 0 || parts[0].length > 1536) {
    return false;
  }
  return !parts[0].includes("?") && !parts[0].includes("#");
}

function reviewedFulfillmentCompletionRoute(path) {
  if (!path.startsWith("/api/agreements/")) return false;
  const parts = path.slice("/api/agreements/".length).split("/");
  if (
    parts.length !== 4 ||
    parts[0].length === 0 ||
    parts[0].length > 1536 ||
    parts[1] !== "commitments" ||
    parts[2].length === 0 ||
    parts[2].length > 64 ||
    parts[3] !== "completion-evidence"
  ) {
    return false;
  }
  if (parts[0].includes("?") || parts[0].includes("#")) return false;
  if (parts[2].includes("?") || parts[2].includes("#")) return false;
  return /^[A-Za-z][A-Za-z0-9._-]{0,63}$/.test(parts[2]);
}

function reviewedAuthenticatedRoute(method, path) {
  if (method === "GET") {
    if (path === "/api/auth/session") return true;
    if (!path.startsWith("/api/intents/")) return false;
    const parts = path.slice("/api/intents/".length).split("/");
    if (parts.length !== 2 || parts[0].length === 0) return false;
    if (parts[0].includes("?") || parts[0].includes("#")) return false;
    return parts[1] === "acceptance";
  }
  if (method !== "POST") return false;
  if (path === "/api/auth/logout") return true;
  if (path === "/api/authentication-enrollment/nonces") return true;
  if (path === "/api/authentication-enrollment/evidence") return true;
  if (path === "/api/product-listings") return true;
  if (path === "/api/intents") return true;
  if (reviewedAgreementAssentRoute(path)) return true;
  if (reviewedAgreementPublicationRoute(path)) return true;
  if (reviewedFulfillmentCompletionRoute(path)) return true;
  if (!path.startsWith("/api/intents/")) return false;
  const parts = path.slice("/api/intents/".length).split("/");
  if (parts.length !== 2 || parts[0].length === 0) return false;
  if (parts[0].includes("?") || parts[0].includes("#")) return false;
  const tail = parts[1];
  return tail === "responses" || tail === "proposals" || tail === "acceptance";
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
function rejectOversizedDeclaredResponse(response) {
  // Reject an explicitly oversized representation before buffering its body.
  // Missing or malformed length still uses the existing post-read byte bound.
  const length = response.headers?.get?.("content-length");
  if (typeof length === "string" && /^[0-9]+$/.test(length) &&
      Number(length) > MAX_RESPONSE_JSON_BYTES) {
    throw stableClientError("APPLICATION_HTTP_RESPONSE_TOO_LARGE");
  }
}

async function readBoundedResponseText(response) {
  // Prefer bounded, incremental decoding when Fetch exposes a body stream.
  // Retain the existing text() bound for synthetic/legacy responses without one.
  if (response.body === null || typeof response.body?.getReader !== "function") {
    const text = await response.text();
    if (new TextEncoder().encode(text).length > MAX_RESPONSE_JSON_BYTES) {
      throw stableClientError("APPLICATION_HTTP_RESPONSE_TOO_LARGE");
    }
    return text;
  }
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  const fragments = [];
  let receivedBytes = 0;
  try {
    for (;;) {
      const chunk = await reader.read();
      if (chunk.done) break;
      if (!(chunk.value instanceof Uint8Array)) {
        throw stableClientError("RESPONSE_BODY_READ_FAILED");
      }
      if (chunk.value.byteLength > MAX_RESPONSE_JSON_BYTES - receivedBytes) {
        throw stableClientError("APPLICATION_HTTP_RESPONSE_TOO_LARGE");
      }
      receivedBytes += chunk.value.byteLength;
      fragments.push(decoder.decode(chunk.value, { stream: true }));
    }
    fragments.push(decoder.decode());
    return fragments.join("");
  } catch (error) {
    // Release the body on oversize/failure, without reflecting provider errors.
    try {
      const cancellation = reader.cancel();
      if (cancellation && typeof cancellation.catch === "function") {
        cancellation.catch(() => {});
      }
    } catch {}
    if (error?.code === "APPLICATION_HTTP_RESPONSE_TOO_LARGE") throw error;
    throw stableClientError("RESPONSE_BODY_READ_FAILED");
  } finally {
    reader.releaseLock();
  }
}

function reviewedServerErrorCode(code, status) {
  // Server JSON is untrusted, even when it came from an application route.
  // Keep bounded protocol-like error codes; never surface arbitrary response text.
  if (typeof code === "string" && /^[A-Z][A-Z0-9_]{1,79}$/.test(code)) return code;
  if (Number.isInteger(status) && status >= 100 && status <= 599) return `HTTP_${status}`;
  return "APPLICATION_HTTP_FAILED";
}

async function decodeResponse(response, session) {
  rejectOversizedDeclaredResponse(response);
  const text = await readBoundedResponseText(response);
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
    const stableCode = reviewedServerErrorCode(code, response.status);
    session.invalidateForServerCode(stableCode);
    throw stableClientError(stableCode);
  }
  return documentValue;
}

function createMarketplaceSessionClient(
  fetchImpl,
  rawIssuerPrincipal,
  session = new MarketplaceMemorySession(),
) {
  if (
    typeof fetchImpl !== "function" ||
    typeof rawIssuerPrincipal !== "function" ||
    !(session instanceof MarketplaceMemorySession)
  ) {
    throw stableClientError("CLIENT_CONFIGURATION_INVALID");
  }

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
  reviewedAgreementPublicationRoute,
  reviewedFulfillmentCompletionRoute,
  reviewedAuthenticatedRoute,
};
