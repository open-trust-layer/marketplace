"use strict";

const API_INTENTS = "/api/intents";
const API_PRODUCT_LISTINGS = "/api/product-listings";
const API_SYNC = "/api/sync";
const API_MVP_FLIGHT = "/api/mvp-flight";
const RESPONSES_SUFFIX = "/responses";
const PROPOSALS_SUFFIX = "/proposals";
const PAGE_LIMIT = 64;
const SYNC_LIMIT = 64;
const MAX_SYNC_PAGES = 4;
const MAX_LIST_PAGES = 4;
const MAX_RECORD_JSON_BYTES = 256 * 1024;
const MAX_PROPOSAL_URI_BYTES = 2048;
const MAX_RESPONSE_JSON_BYTES = 300 * 1024;
const MAP_WIDTH = 720;
const MAP_HEIGHT = 360;
const PRODUCT_LISTING_STRING_FIELDS = [
  "seller_principal", "subject_uri", "title", "description", "currency_code", "unit_uri",
];
const PRODUCT_LISTING_INTEGER_FIELDS = [
  "consideration_coefficient", "consideration_scale", "quantity_coefficient",
  "quantity_scale", "latitude_e6", "longitude_e6",
];
const PROPOSAL_FIELDS = ["buyer_principal", "subject_uri", "action_uri"];

const state = {
  records: new Map(),
  selectedId: null,
  selectedRecord: null,
  syncCursor: null,
  truncated: false,
};

const byId = (id) => document.getElementById(id);
const intentList = byId("intent-list");
const marketMap = byId("market-map");
const filterInput = byId("intent-filter");
const syncStatus = byId("sync-status");
const viewCount = byId("view-count");
const selectedRecordId = byId("selected-record-id");
const selectedRecordJson = byId("selected-record-json");
const responseList = byId("response-list");
const responseButton = byId("submit-response");
const mvpFlightButton = byId("run-mvp-flight");
const mvpFlightLifecycle = byId("mvp-flight-lifecycle");
const mvpFlightAudit = byId("mvp-flight-audit");
function stableClientError(code) {
  const error = new Error("Marketplace request failed");
  error.code = code;
  return error;
}

function reviewedApiPath(path) {
  if (typeof path !== "string" || !path.startsWith("/api/") || path.startsWith("//")) {
    throw stableClientError("CLIENT_PATH_INVALID");
  }
  return path;
}

async function apiFetch(path, { method = "GET", body = null } = {}) {
  const headers = { Accept: "application/json" };
  const init = {
    method,
    headers,
    credentials: "omit",
    cache: "no-store",
    redirect: "error",
    referrerPolicy: "no-referrer",
  };
  if (body !== null) {
    Object.assign(headers, {"Content-Type": "application/json"});
    init.body = body;
  }
  const response = await fetch(reviewedApiPath(path), init);
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
    throw stableClientError(typeof code === "string" ? code : `HTTP_${response.status}`);
  }
  return documentValue;
}

function requireRecordId(value) {
  if (typeof value !== "string" || value.length === 0 || value.length > 512) {
    throw stableClientError("RECORD_ID_INVALID");
  }
  return value;
}

function requireCursor(value) {
  if (!Number.isSafeInteger(value) || value < 0) {
    throw stableClientError("SYNC_CURSOR_INVALID");
  }
  return value;
}

function setStatus(message, kind = "") {
  syncStatus.textContent = message;
  syncStatus.className = kind;
}
function recordTerms(record) {
  const terms = record?.content?.terms;
  if (terms === null || typeof terms !== "object" || Array.isArray(terms)) {
    return [];
  }
  return Object.entries(terms);
}

function displayText(record, suffix, fallback) {
  for (const [key, value] of recordTerms(record)) {
    if (typeof key === "string" && key.endsWith(suffix) && typeof value === "string" && value.length > 0) {
      return value;
    }
  }
  return fallback;
}

function presentationLocation(record) {
  for (const [, value] of recordTerms(record)) {
    if (value === null || typeof value !== "object" || Array.isArray(value)) continue;
    if (typeof value.scheme !== "string" || !value.scheme.endsWith("/location/wgs84-e6")) continue;
    const latitude = value.value?.latitude_e6;
    const longitude = value.value?.longitude_e6;
    if (!Number.isInteger(latitude) || !Number.isInteger(longitude)) continue;
    if (latitude < -90000000 || latitude > 90000000) continue;
    if (longitude < -180000000 || longitude > 180000000) continue;
    return { latitude, longitude };
  }
  return null;
}
function projectLocation(location) {
  const x = Math.floor(((location.longitude + 180000000) * (MAP_WIDTH - 1)) / 360000000);
  const y = Math.floor(((90000000 - location.latitude) * (MAP_HEIGHT - 1)) / 180000000);
  return { x, y };
}

function svgElement(name, attributes = {}) {
  const node = document.createElementNS(marketMap.namespaceURI, name);
  for (const [key, value] of Object.entries(attributes)) {
    node.setAttribute(key, String(value));
  }
  return node;
}

function renderMap(records) {
  marketMap.replaceChildren();
  for (let step = 1; step < 6; step += 1) {
    const x = Math.floor(((MAP_WIDTH - 1) * step) / 6);
    const y = Math.floor(((MAP_HEIGHT - 1) * step) / 6);
    marketMap.append(svgElement("line", { x1: x, y1: 0, x2: x, y2: MAP_HEIGHT - 1, class: "map-grid" }));
    marketMap.append(svgElement("line", { x1: 0, y1: y, x2: MAP_WIDTH - 1, y2: y, class: "map-grid" }));
  }
  marketMap.append(svgElement("line", { x1: 0, y1: 179, x2: 719, y2: 179, class: "map-axis" }));
  marketMap.append(svgElement("line", { x1: 359, y1: 0, x2: 359, y2: 359, class: "map-axis" }));
  for (const [recordId, record] of records) {
    const location = presentationLocation(record);
    if (location === null) continue;
    const point = projectLocation(location);
    const marker = svgElement("circle", {
      cx: point.x,
      cy: point.y,
      r: state.selectedId === recordId ? 8 : 6,
      class: "map-marker",
      tabindex: 0,
      role: "button",
      "aria-label": `Select intent ${recordId}`,
    });
    marker.addEventListener("click", () => selectIntent(recordId));
    marker.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        selectIntent(recordId);
      }
    });
    marketMap.append(marker);
  }
}

function filteredRecords() {
  const query = filterInput.value.trim().toLocaleLowerCase();
  const records = Array.from(state.records.entries());
  if (!query) return records;
  return records.filter(([recordId, record]) => {
    const title = displayText(record, "/term/title", "");
    return recordId.toLocaleLowerCase().includes(query) || title.toLocaleLowerCase().includes(query);
  });
}
function renderList() {
  const records = filteredRecords();
  intentList.replaceChildren();
  if (records.length === 0) {
    const empty = document.createElement("p");
    empty.className = "empty-state";
    empty.textContent = "No intents in this bounded current view.";
    intentList.append(empty);
  }
  for (const [recordId, record] of records) {
    const card = document.createElement("button");
    card.type = "button";
    card.className = "intent-card";
    card.setAttribute("aria-current", state.selectedId === recordId ? "true" : "false");
    const title = document.createElement("span");
    title.className = "intent-title";
    title.textContent = displayText(record, "/term/title", "Marketplace intent");
    const identity = document.createElement("span");
    identity.className = "record-id muted small";
    identity.textContent = recordId;
    card.append(title, identity);
    card.addEventListener("click", () => selectIntent(recordId));
    intentList.append(card);
  }
  viewCount.textContent = `${records.length} intent${records.length === 1 ? "" : "s"}${state.truncated ? " · bounded view" : ""}`;
  renderMap(records);
}

function renderDetail() {
  const record = state.selectedRecord;
  selectedRecordId.textContent = state.selectedId ?? "No intent selected.";
  selectedRecordJson.textContent = record === undefined || record === null
    ? "Select an intent to inspect its reviewed record JSON."
    : JSON.stringify(record, null, 2);
  responseButton.disabled = record === undefined || record === null;
}
async function renderResponses(recordId) {
  responseList.replaceChildren();
  try {
    const documentValue = await apiFetch(`${API_INTENTS}/${encodeURIComponent(recordId)}${RESPONSES_SUFFIX}?limit=${PAGE_LIMIT}`);
    const ids = documentValue.record_ids;
    if (!Array.isArray(ids) || ids.length > PAGE_LIMIT) throw stableClientError("RESPONSE_LIST_INVALID");
    for (const value of ids) requireRecordId(value);
    if (ids.length === 0) {
      const empty = document.createElement("p");
      empty.className = "muted";
      empty.textContent = "No responses in this bounded local application view.";
      responseList.append(empty);
      return;
    }
    for (const id of ids) {
      const item = document.createElement("button");
      item.type = "button";
      item.className = "response-card record-id";
      item.textContent = id;
      item.addEventListener("click", () => void inspectIntent(id));
      responseList.append(item);
    }
  } catch (error) {
    const message = document.createElement("p");
    message.className = "error";
    message.textContent = `Responses unavailable: ${error.code ?? "CLIENT_FAILURE"}`;
    responseList.append(message);
  }
}

function selectIntent(recordId) {
  const reviewed = requireRecordId(recordId);
  const record = state.records.get(reviewed);
  state.selectedId = record === undefined ? null : reviewed;
  state.selectedRecord = record ?? null;
  renderList();
  renderDetail();
  if (state.selectedId !== null) void renderResponses(state.selectedId);
}

async function inspectIntent(recordId) {
  const reviewed = requireRecordId(recordId);
  try {
    const record = await apiFetch(`${API_INTENTS}/${encodeURIComponent(reviewed)}`);
    state.selectedId = reviewed;
    state.selectedRecord = record;
    renderList();
    renderDetail();
    await renderResponses(reviewed);
  } catch (error) {
    state.selectedId = null;
    state.selectedRecord = null;
    responseList.replaceChildren();
    renderList();
    renderDetail();
    setStatus(`Detail failed: ${error.code ?? "CLIENT_FAILURE"}`, "error");
  }
}
async function captureSyncWatermark() {
  const documentValue = await apiFetch(`${API_SYNC}?limit=${SYNC_LIMIT}`);
  if (!Array.isArray(documentValue.changes) || documentValue.changes.length !== 0) {
    throw stableClientError("SYNC_WATERMARK_INVALID");
  }
  if (documentValue.has_more !== false) throw stableClientError("SYNC_WATERMARK_INVALID");
  return requireCursor(documentValue.next_cursor);
}

async function hydrateCurrentIntents() {
  const next = new Map();
  const seenCursors = new Set();
  let cursor = null;
  for (let pageNumber = 0; pageNumber < MAX_LIST_PAGES; pageNumber += 1) {
    const suffix = cursor === null
      ? `?limit=${PAGE_LIMIT}`
      : `?cursor=${encodeURIComponent(cursor)}&limit=${PAGE_LIMIT}`;
    const page = await apiFetch(`${API_INTENTS}${suffix}`);
    if (!Array.isArray(page.record_ids) || page.record_ids.length > PAGE_LIMIT) {
      throw stableClientError("INTENT_LIST_INVALID");
    }
    for (const rawId of page.record_ids) {
      const recordId = requireRecordId(rawId);
      if (next.has(recordId)) throw stableClientError("INTENT_LIST_INVALID");
      const record = await apiFetch(`${API_INTENTS}/${encodeURIComponent(recordId)}`);
      next.set(recordId, record);
    }
    if (page.next_cursor === null) {
      state.records = next;
      state.truncated = false;
      if (state.selectedId !== null) {
        const selected = state.records.get(state.selectedId);
        state.selectedId = selected === undefined ? null : state.selectedId;
        state.selectedRecord = selected ?? null;
        if (state.selectedId === null) responseList.replaceChildren();
      }
      return;
    }
    if (typeof page.next_cursor !== "string" || page.next_cursor.length === 0 || page.next_cursor.length > 512) {
      throw stableClientError("INTENT_LIST_INVALID");
    }
    if (seenCursors.has(page.next_cursor)) throw stableClientError("INTENT_LIST_INVALID");
    seenCursors.add(page.next_cursor);
    cursor = page.next_cursor;
  }
  throw stableClientError("INTENT_LIST_TRUNCATED");
}

async function fullResync() {
  setStatus("Capturing sync watermark…");
  const watermark = await captureSyncWatermark();
  await hydrateCurrentIntents();
  state.syncCursor = watermark;
  renderList();
  renderDetail();
  setStatus(`Synchronized at local cursor ${watermark}`, "success");
}
async function applySyncPage(documentValue) {
  if (!Array.isArray(documentValue.changes) || documentValue.changes.length > SYNC_LIMIT) {
    throw stableClientError("SYNC_PAGE_INVALID");
  }
  for (const change of documentValue.changes) {
    if (change === null || typeof change !== "object") throw stableClientError("SYNC_PAGE_INVALID");
    const recordId = requireRecordId(change.record_id);
    if (!Number.isSafeInteger(change.seq) || change.seq <= state.syncCursor) throw stableClientError("SYNC_PAGE_INVALID");
    if (change.change_kind !== "DELETE" && change.change_kind !== "UPSERT") {
      throw stableClientError("SYNC_PAGE_INVALID");
    }
    state.syncCursor = change.seq;
  }
  const nextCursor = requireCursor(documentValue.next_cursor);
  if (nextCursor < state.syncCursor) throw stableClientError("SYNC_PAGE_INVALID");
  state.syncCursor = nextCursor;
  if (typeof documentValue.has_more !== "boolean") throw stableClientError("SYNC_PAGE_INVALID");
  return documentValue.has_more;
}

async function incrementalSync() {
  if (state.syncCursor === null) return fullResync();
  setStatus(`Syncing from local cursor ${state.syncCursor}…`);
  try {
    let browseDirty = false;
    let hasMore = false;
    for (let pageNumber = 0; pageNumber < MAX_SYNC_PAGES; pageNumber += 1) {
      const documentValue = await apiFetch(`${API_SYNC}?cursor=${state.syncCursor}&limit=${SYNC_LIMIT}`);
      hasMore = await applySyncPage(documentValue);
      if (documentValue.changes.length > 0) browseDirty = true;
      if (!hasMore) break;
    }
    if (browseDirty) await hydrateCurrentIntents();
    renderList();
    renderDetail();
    if (hasMore) {
      setStatus(`Sync paused at local cursor ${state.syncCursor}; more changes remain`, "warning");
      return;
    }
    setStatus(`Synchronized at local cursor ${state.syncCursor}`, "success");
  } catch (error) {
    if (error.code === "SYNC_CURSOR_EXPIRED") return fullResync();
    throw error;
  }
}
function canonicalIntegerJsonToken(value) {
  if (typeof value !== "string" || !/^(0|-?[1-9][0-9]*)$/.test(value)) {
    throw stableClientError("PRODUCT_LISTING_INTEGER_INVALID");
  }
  return value;
}

function productListingJsonBody() {
  const parts = [];
  for (const name of PRODUCT_LISTING_STRING_FIELDS) {
    const value = byId(`create-${name.replaceAll("_", "-")}`).value;
    parts.push(`${JSON.stringify(name)}:${JSON.stringify(value)}`);
  }
  for (const name of PRODUCT_LISTING_INTEGER_FIELDS) {
    const value = byId(`create-${name.replaceAll("_", "-")}`).value;
    parts.push(`${JSON.stringify(name)}:${canonicalIntegerJsonToken(value)}`);
  }
  const body = `{${parts.join(",")}}`;
  if (new TextEncoder().encode(body).length > MAX_RECORD_JSON_BYTES) {
    throw stableClientError("PRODUCT_LISTING_JSON_TOO_LARGE");
  }
  return body;
}

function reviewedProposalUri(value) {
  if (typeof value !== "string" || value.length === 0) throw stableClientError("PROPOSAL_FIELD_INVALID");
  if (new TextEncoder().encode(value).length > MAX_PROPOSAL_URI_BYTES) throw stableClientError("PROPOSAL_FIELD_INVALID");
  if (!/^[A-Za-z][A-Za-z0-9+.-]*:\S+$/.test(value)) throw stableClientError("PROPOSAL_FIELD_INVALID");
  return value;
}

function proposalJsonBody() {
  const parts = [];
  for (const name of PROPOSAL_FIELDS) {
    const value = reviewedProposalUri(byId(`proposal-${name.replaceAll("_", "-")}`).value);
    parts.push(`${JSON.stringify(name)}:${JSON.stringify(value)}`);
  }
  const body = `{${parts.join(",")}}`;
  if (new TextEncoder().encode(body).length > MAX_RECORD_JSON_BYTES) {
    throw stableClientError("PROPOSAL_JSON_TOO_LARGE");
  }
  return body;
}

function setFormStatus(id, message, kind = "") {
  const target = byId(id);
  target.textContent = message;
  target.className = kind || "muted";
}

async function createProductListing(event) {
  event.preventDefault();
  try {
    const body = productListingJsonBody();
    setFormStatus("create-status", "Submitting structured product listing…");
    await apiFetch(API_PRODUCT_LISTINGS, { method: "POST", body });
    setFormStatus("create-status", "Product listing accepted by the shared application API.", "success");
    await fullResync();
  } catch (error) {
    setFormStatus("create-status", `Create failed: ${error.code ?? "CLIENT_FAILURE"}`, "error");
  }
}
async function createProposal(event) {
  event.preventDefault();
  if (state.selectedId === null) {
    setFormStatus("response-status", "Select a parent intent first.", "error");
    return;
  }
  try {
    const body = proposalJsonBody();
    const parentId = requireRecordId(state.selectedId);
    setFormStatus("response-status", "Submitting structured Proposal…");
    await apiFetch(`${API_INTENTS}/${encodeURIComponent(parentId)}${PROPOSALS_SUFFIX}`, {
      method: "POST",
      body,
    });
    setFormStatus("response-status", "Proposal accepted by the shared application API.", "success");
    await fullResync();
    if (state.records.has(parentId)) selectIntent(parentId);
  } catch (error) {
    setFormStatus("response-status", `Proposal failed: ${error.code ?? "CLIENT_FAILURE"}`, "error");
  }
}

function reviewedMvpText(value, maximum = 4096) {
  if (typeof value !== "string" || value.length === 0 || value.length > maximum) {
    throw stableClientError("MVP_FLIGHT_DOCUMENT_INVALID");
  }
  return value;
}

function reviewedMvpFlightDocument(value) {
  if (value === null || typeof value !== "object" || Array.isArray(value)) {
    throw stableClientError("MVP_FLIGHT_DOCUMENT_INVALID");
  }
  if (value.profile !== "MARKETPLACE_MVP_FLIGHT_ACCEPTANCE_V1") {
    throw stableClientError("MVP_FLIGHT_DOCUMENT_INVALID");
  }
  const participants = value.participants;
  const verification = value.verification;
  const records = value.records;
  if (participants === null || typeof participants !== "object" || Array.isArray(participants)) {
    throw stableClientError("MVP_FLIGHT_DOCUMENT_INVALID");
  }
  if (verification === null || typeof verification !== "object" || Array.isArray(verification)) {
    throw stableClientError("MVP_FLIGHT_DOCUMENT_INVALID");
  }
  if (records === null || typeof records !== "object" || Array.isArray(records)) {
    throw stableClientError("MVP_FLIGHT_DOCUMENT_INVALID");
  }
  const states = value.states;
  const audit = value.audit_record_ids;
  if (!Array.isArray(states) || states.length === 0 || states.length > 16) {
    throw stableClientError("MVP_FLIGHT_DOCUMENT_INVALID");
  }
  if (!Array.isArray(audit) || audit.length === 0 || audit.length > 32) {
    throw stableClientError("MVP_FLIGHT_DOCUMENT_INVALID");
  }
  for (const stateValue of states) reviewedMvpText(stateValue, 64);
  for (const recordId of audit) requireRecordId(recordId);
  if (new Set(audit).size !== audit.length) throw stableClientError("MVP_FLIGHT_DOCUMENT_INVALID");
  const finalState = reviewedMvpText(value.final_state, 64);
  if (finalState !== states[states.length - 1]) throw stableClientError("MVP_FLIGHT_DOCUMENT_INVALID");
  if (typeof verification.listing_integrity_verified !== "boolean") throw stableClientError("MVP_FLIGHT_DOCUMENT_INVALID");
  if (typeof verification.universal_truth !== "boolean") throw stableClientError("MVP_FLIGHT_DOCUMENT_INVALID");
  if (typeof verification.payment_or_settlement_evaluated !== "boolean") throw stableClientError("MVP_FLIGHT_DOCUMENT_INVALID");
  return {
    seller: reviewedMvpText(participants.seller),
    buyer: reviewedMvpText(participants.buyer),
    states,
    finalState,
    completedAt: reviewedMvpText(value.completed_at, 128),
    listingId: requireRecordId(records.listing),
    agreementId: requireRecordId(records.agreement),
    agreementFormation: reviewedMvpText(verification.agreement_formation, 128),
    fulfillmentConclusion: reviewedMvpText(verification.fulfillment_conclusion, 128),
    listingIntegrityVerified: verification.listing_integrity_verified,
    universalTruth: verification.universal_truth,
    paymentOrSettlementEvaluated: verification.payment_or_settlement_evaluated,
    audit,
  };
}

function renderMvpFlight(documentValue) {
  const flight = reviewedMvpFlightDocument(documentValue);
  byId("mvp-flight-final").textContent = flight.finalState;
  byId("mvp-flight-seller").textContent = `Seller: ${flight.seller}`;
  byId("mvp-flight-buyer").textContent = `Buyer: ${flight.buyer}`;
  byId("mvp-flight-completed-at").textContent = `Completion timestamp: ${flight.completedAt}`;
  byId("mvp-flight-verification").textContent =
    `Listing integrity=${flight.listingIntegrityVerified}; agreement=${flight.agreementFormation}; ` +
    `fulfillment=${flight.fulfillmentConclusion}; universal truth=${flight.universalTruth}; ` +
    `payment/settlement evaluated=${flight.paymentOrSettlementEvaluated}.`;
  mvpFlightLifecycle.replaceChildren();
  for (const stateValue of flight.states) {
    const item = document.createElement("li");
    item.textContent = stateValue;
    mvpFlightLifecycle.append(item);
  }
  mvpFlightAudit.textContent = [
    `listing=${flight.listingId}`,
    `agreement=${flight.agreementId}`,
    ...flight.audit.map((recordId, index) => `audit[${index}]=${recordId}`),
  ].join("\n");
}

async function runMvpFlight() {
  mvpFlightButton.disabled = true;
  setFormStatus("mvp-flight-status", "Running bounded local two-user MVP journey?");
  try {
    const documentValue = await apiFetch(API_MVP_FLIGHT, { method: "POST" });
    renderMvpFlight(documentValue);
    setFormStatus("mvp-flight-status", "MVP journey completed with visible verification and audit evidence.", "success");
  } catch (error) {
    setFormStatus("mvp-flight-status", `MVP journey failed: ${error.code ?? "CLIENT_FAILURE"}`, "error");
  } finally {
    mvpFlightButton.disabled = false;
  }
}

async function runSyncAction() {
  try {
    await incrementalSync();
  } catch (error) {
    setStatus(`Sync failed: ${error.code ?? "CLIENT_FAILURE"}`, "error");
  }
}

filterInput.addEventListener("input", renderList);
byId("sync-now").addEventListener("click", () => void runSyncAction());
byId("clear-selection").addEventListener("click", () => {
  state.selectedId = null;
  state.selectedRecord = null;
  responseList.replaceChildren();
  renderList();
  renderDetail();
});
byId("create-form").addEventListener("submit", (event) => void createProductListing(event));
byId("response-form").addEventListener("submit", (event) => void createProposal(event));
mvpFlightButton.addEventListener("click", () => void runMvpFlight());

renderList();
renderDetail();
void fullResync().catch((error) => {
  setStatus(`Initial sync failed: ${error.code ?? "CLIENT_FAILURE"}`, "error");
});
