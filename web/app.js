"use strict";

window.MarketplaceI18n = (() => {
  const SUPPORTED_LANGUAGES = new Set(["en", "ru"]);
  const messages = Object.freeze({
    "document.title": ["Open Layer Marketplace", "Open Layer Marketplace"],
    "shell.marketplace": ["Marketplace", "Маркетплейс"],
    "sync.notSynchronized": ["Not synchronized", "Не синхронизировано"],
    "sync.now": ["Sync now", "Синхронизировать"],
    "toolbar.filter": ["Filter current bounded view", "Фильтр текущего ограниченного представления"],
    "toolbar.placeholder": ["Record id or visible text", "ID записи или видимый текст"],
    "browse.zero": ["0 intents", "0 записей"],
    "map.projection": ["Presentation-only projection", "Проекция только для отображения"],
    "map.title": ["Map", "Карта"],
    "map.grid": ["WGS84 · offline grid", "WGS84 · офлайн-сетка"],
    "map.disclaimer": ["Locations are issuer-attributed presentation data, not verified position or protocol truth.", "Координаты — это данные отображения, заявленные издателем, а не подтверждённое местоположение или истина протокола."],
    "browse.boundary": ["Bounded current view", "Ограниченное текущее представление"],
    "browse.title": ["Intents", "Записи"],
    "detail.selected": ["Selected record", "Выбранная запись"],
    "detail.title": ["Intent detail", "Детали записи"],
    "detail.back": ["Back to parent listing", "К родительскому объявлению"],
    "detail.clear": ["Clear", "Очистить"],
    "detail.none": ["No intent selected.", "Запись не выбрана."],
    "detail.inspect": ["Select an intent to inspect its reviewed record JSON.", "Выберите запись, чтобы просмотреть проверенный JSON записи."],
    "responses.title": ["Responses", "Ответы"],
    "mvp.eyebrow": ["Local synthetic product acceptance", "Локальная синтетическая приёмка продукта"],
    "mvp.title": ["Complete MVP journey", "Полный сценарий MVP"],
    "mvp.notRun": ["Not run", "Не запускался"],
    "mvp.runIntro": ["Run the reviewed two-user local flight: identity → listing → publish → discover → verify → accept → agreement → completed.", "Запустите проверенный локальный сценарий двух пользователей: идентификатор → объявление → публикация → обнаружение → проверка → принятие → соглашение → завершено."],
    "mvp.run": ["Run complete local MVP journey", "Запустить полный локальный сценарий MVP"],
    "mvp.localOnly": ["Local synthetic test identities only. No payment, settlement, deployment, or universal-truth claim.", "Только локальные синтетические тестовые идентификаторы. Без платежей, расчётов, развёртывания и заявлений об универсальной истине."],
    "mvp.participants": ["Participants", "Участники"],
    "mvp.sellerEmpty": ["Seller: —", "Продавец: —"],
    "mvp.buyerEmpty": ["Buyer: —", "Покупатель: —"],
    "mvp.verification": ["Verification", "Проверка"],
    "mvp.notEvaluated": ["Not evaluated.", "Не оценено."],
    "mvp.completedEmpty": ["Completion timestamp: —", "Время завершения: —"],
    "mvp.auditTitle": ["Audit record identities", "Идентификаторы записей аудита"],
    "mvp.auditEmpty": ["Run the local MVP journey to produce the bounded audit trail.", "Запустите локальный сценарий MVP, чтобы сформировать ограниченный журнал аудита."],
    "author.shared": ["Shared structured authoring", "Общее структурированное создание"],
    "author.createListing": ["Create product listing", "Создать объявление"],
    "author.listingHelp": ["Enter transport fields only. M17.1Q/M72 remains authoritative for Marketplace semantics.", "Введите только транспортные поля. M17.1Q/M72 остаётся авторитетным источником семантики Marketplace."],
    "author.fillExample": ["Fill synthetic example", "Заполнить синтетический пример"],
    "field.sellerPrincipal": ["Seller principal URI", "URI принципала продавца"],
    "field.subjectUri": ["Subject URI", "URI предмета"],
    "field.title": ["Title", "Название"],
    "field.description": ["Description", "Описание"],
    "field.priceCoefficient": ["Price coefficient (integer)", "Коэффициент цены (целое число)"],
    "field.priceScale": ["Price scale (integer)", "Масштаб цены (целое число)"],
    "field.currency": ["Currency code", "Код валюты"],
    "field.quantityCoefficient": ["Quantity coefficient (integer)", "Коэффициент количества (целое число)"],
    "field.quantityScale": ["Quantity scale (integer)", "Масштаб количества (целое число)"],
    "field.unitUri": ["Unit URI", "URI единицы"],
    "field.latitude": ["Latitude E6 (integer)", "Широта E6 (целое число)"],
    "field.longitude": ["Longitude E6 (integer)", "Долгота E6 (целое число)"],
    "author.parent": ["Exact selected parent", "Точно выбранная родительская запись"],
    "author.createProposal": ["Create Proposal", "Создать предложение"],
    "author.proposalHelp": ["Enter buyer/request fields only. The selected parent is supplied by the route.", "Введите только поля покупателя/запроса. Выбранная родительская запись задаётся маршрутом."],
    "author.parentNone": ["Selected parent: none.", "Родительская запись: не выбрана."],
    "field.buyerPrincipal": ["Buyer principal URI", "URI принципала покупателя"],
    "field.actionUri": ["Action URI", "URI действия"],
    "browse.empty": ["No intents in this bounded current view.", "В текущем ограниченном представлении записей нет."],
    "browse.fallback": ["Marketplace intent", "Запись Marketplace"],
    "browse.boundedSuffix": ["bounded view", "ограничено"],
    "browse.proposalMetadata": ["Buyer {buyer} · Subject {subject} · Action {action}", "Покупатель {buyer} · Предмет {subject} · Действие {action}"],
    "browse.listingMetadata": ["Seller {seller} · Price {price} · Quantity {quantity}", "Продавец {seller} · Цена {price} · Количество {quantity}"],
    "map.select": ["Select intent {recordId}", "Выбрать запись {recordId}"],
    "proposal.parentMissing": ["Selected parent: {recordId} · product-listing subject unavailable for guided example.", "Родительская запись: {recordId} · предмет объявления недоступен для пошагового примера."],
    "proposal.parentSubject": ["Selected parent: {recordId} · subject {subjectUri}", "Родительская запись: {recordId} · предмет {subjectUri}"],
    "responses.empty": ["No responses in this bounded local application view.", "В текущем ограниченном локальном представлении ответов нет."],
    "responses.loading": ["Loading responses\u2026", "\u0417\u0430\u0433\u0440\u0443\u0436\u0430\u0435\u043c \u043e\u0442\u0432\u0435\u0442\u044b\u2026"],
    "responses.newProposal": ["New Proposal", "\u041d\u043e\u0432\u043e\u0435 \u043f\u0440\u0435\u0434\u043b\u043e\u0436\u0435\u043d\u0438\u0435"],
    "responses.proposal": ["Buyer Proposal", "Предложение покупателя"],
    "responses.metadata": ["Buyer {buyer} · Subject {subject} · Action {action} · Record {recordId}", "Покупатель {buyer} · Предмет {subject} · Действие {action} · Запись {recordId}"],
    "detail.responseParent": ["Response to parent record {recordId}", "\u041e\u0442\u0432\u0435\u0442 \u043d\u0430 \u0440\u043e\u0434\u0438\u0442\u0435\u043b\u044c\u0441\u043a\u0443\u044e \u0437\u0430\u043f\u0438\u0441\u044c {recordId}"],
    "responses.unavailable": ["Responses unavailable: {code}", "Ответы недоступны: {code}"],
    "detail.failed": ["Detail failed: {code}", "Не удалось загрузить детали: {code}"],
    "sync.capture": ["Capturing sync watermark…", "Фиксируем отметку синхронизации…"],
    "sync.done": ["Synchronized at local cursor {cursor}", "Синхронизировано на локальном курсоре {cursor}"],
    "sync.from": ["Syncing from local cursor {cursor}…", "Синхронизация с локального курсора {cursor}…"],
    "sync.paused": ["Sync paused at local cursor {cursor}; more changes remain", "Синхронизация приостановлена на локальном курсоре {cursor}; остались изменения"],
    "sync.failed": ["Sync failed: {code}", "Ошибка синхронизации: {code}"],
    "sync.initialFailed": ["Initial sync failed: {code}", "Ошибка начальной синхронизации: {code}"],
    "author.exampleLoaded": ["Synthetic example loaded. Review the fields, then submit manually.", "Синтетический пример загружен. Проверьте поля и отправьте вручную."],
    "proposal.exampleNeedsListing": ["Select a product listing with one valid subject before loading the example.", "Перед загрузкой примера выберите объявление с одним корректным предметом."],
    "proposal.exampleLoaded": ["Synthetic example loaded for the selected product listing. Review the fields, then submit manually.", "Синтетический пример загружен для выбранного объявления. Проверьте поля и отправьте вручную."],
    "listing.submitting": ["Submitting structured product listing…", "Отправляем структурированное объявление…"],
    "listing.refreshFailed": ["Product listing accepted, but local refresh failed: {code}", "Объявление принято, но локальное обновление не удалось: {code}"],
    "listing.acceptedSelected": ["Product listing accepted and selected for Proposal authoring.", "Объявление принято и выбрано для создания предложения."],
    "listing.accepted": ["Product listing accepted. Select it from the current view to continue.", "Объявление принято. Выберите его в текущем представлении, чтобы продолжить."],
    "listing.failed": ["Create failed: {code}", "Ошибка создания: {code}"],
    "proposal.selectParent": ["Select a parent intent first.", "Сначала выберите родительскую запись."],
    "proposal.selectListing": ["Select a product listing with one valid subject before creating a Proposal.", "Перед созданием предложения выберите объявление с одним корректным предметом."],
    "proposal.subjectMismatch": ["Proposal subject must exactly match the selected product listing subject {subjectUri}.", "Предмет предложения должен точно совпадать с предметом выбранного объявления {subjectUri}."],
    "proposal.submitting": ["Submitting structured Proposal…", "Отправляем структурированное предложение…"],
    "proposal.refreshFailed": ["Proposal accepted, but local refresh failed: {code}", "Предложение принято, но локальное обновление не удалось: {code}"],
    "proposal.acceptedRefreshed": ["Proposal accepted and parent responses refreshed.", "Предложение принято, ответы родительской записи обновлены."],
    "proposal.acceptedHighlighted": ["Proposal accepted; new Proposal {recordId} is marked in the response list.", "\u041f\u0440\u0435\u0434\u043b\u043e\u0436\u0435\u043d\u0438\u0435 \u043f\u0440\u0438\u043d\u044f\u0442\u043e; \u043d\u043e\u0432\u043e\u0435 \u043f\u0440\u0435\u0434\u043b\u043e\u0436\u0435\u043d\u0438\u0435 {recordId} \u043e\u0442\u043c\u0435\u0447\u0435\u043d\u043e \u0432 \u0441\u043f\u0438\u0441\u043a\u0435 \u043e\u0442\u0432\u0435\u0442\u043e\u0432."],
    "proposal.responsesUnavailable": ["Proposal accepted, but parent responses could not be refreshed: {code}", "Предложение принято, но не удалось обновить ответы родительской записи: {code}"],
    "proposal.responsesSuperseded": ["Proposal accepted, but parent response refresh was superseded by newer navigation.", "Предложение принято, но обновление ответов родительской записи было заменено более новым переходом."],
    "proposal.parentGone": ["Proposal accepted, but the parent is not present in the refreshed local view.", "Предложение принято, но родительская запись отсутствует в обновлённом локальном представлении."],
    "proposal.failed": ["Proposal failed: {code}", "Ошибка предложения: {code}"],
    "mvp.seller": ["Seller: {seller}", "Продавец: {seller}"],
    "mvp.buyer": ["Buyer: {buyer}", "Покупатель: {buyer}"],
    "mvp.completed": ["Completion timestamp: {timestamp}", "Время завершения: {timestamp}"],
    "mvp.verificationValue": ["Listing integrity={integrity}; agreement={agreement}; fulfillment={fulfillment}; universal truth={truth}; payment/settlement evaluated={payment}.", "Целостность объявления={integrity}; соглашение={agreement}; исполнение={fulfillment}; универсальная истина={truth}; платёж/расчёт оценён={payment}."],
    "mvp.running": ["Running bounded local two-user MVP journey…", "Запускаем ограниченный локальный сценарий MVP для двух пользователей…"],
    "mvp.completedStatus": ["MVP journey completed with visible verification and audit evidence.", "Сценарий MVP завершён с видимыми данными проверки и аудита."],
    "mvp.failed": ["MVP journey failed: {code}", "Сценарий MVP завершился ошибкой: {code}"],
    "aria.marketplaceControls": ["Marketplace controls", "Элементы управления Marketplace"],
    "aria.marketplaceBrowser": ["Marketplace browser", "Обзор Marketplace"],
    "aria.intentMap": ["Marketplace intent coordinate map", "Карта координат записей Marketplace"],
    "aria.mvpLifecycle": ["MVP lifecycle", "Жизненный цикл MVP"],
    "aria.authoring": ["Record authoring boundaries", "Границы создания записей"],
    "language.group": ["Language", "Язык"],
    "language.english": ["Switch to English", "Переключить на английский"],
    "language.russian": ["Switch to Russian", "Переключить на русский"],
  });

  const DYNAMIC_IDS = new Set([
    "sync-status", "view-count", "selected-record-id", "selected-record-summary", "selected-record-json", "proposal-parent",
    "mvp-flight-final", "mvp-flight-status", "mvp-flight-seller", "mvp-flight-buyer",
    "mvp-flight-verification", "mvp-flight-completed-at", "mvp-flight-audit", "create-status", "response-status",
  ]);
  let language = "en";
  const listeners = new Set();

  function messageEntry(key) {
    const entry = messages[key];
    if (!Array.isArray(entry) || entry.length !== 2) throw new Error("Marketplace translation key is invalid");
    return entry;
  }
  function t(key, variables = {}) {
    const template = messageEntry(key)[language === "ru" ? 1 : 0];
    return template.replace(/\{([A-Za-z0-9_]+)\}/g, (_match, name) => {
      if (!Object.prototype.hasOwnProperty.call(variables, name)) throw new Error("Marketplace translation variable is missing");
      return String(variables[name]);
    });
  }

  function keyForEnglishText(value) {
    for (const [key, entry] of Object.entries(messages)) {
      if (entry[0] === value) return key;
    }
    return null;
  }

  function markStaticSurface() {
    for (const element of document.querySelectorAll("body *")) {
      if (!DYNAMIC_IDS.has(element.id) && element.children.length === 0) {
        const text = element.textContent.trim();
        const key = keyForEnglishText(text);
        if (key !== null) element.dataset.i18n = key;
      }
      if (element instanceof HTMLInputElement && element.placeholder) {
        const placeholderKey = keyForEnglishText(element.placeholder);
        if (placeholderKey !== null) element.dataset.i18nPlaceholder = placeholderKey;
      }
      const ariaLabel = element.getAttribute("aria-label");
      if (ariaLabel) {
        const ariaKey = keyForEnglishText(ariaLabel);
        if (ariaKey !== null) element.dataset.i18nAriaLabel = ariaKey;
      }
    }
  }

  function applyStaticTranslations() {
    document.documentElement.lang = language;
    document.title = t("document.title");
    for (const element of document.querySelectorAll("[data-i18n]")) element.textContent = t(element.dataset.i18n);
    for (const element of document.querySelectorAll("[data-i18n-placeholder]")) element.placeholder = t(element.dataset.i18nPlaceholder);
    for (const element of document.querySelectorAll("[data-i18n-aria-label]")) element.setAttribute("aria-label", t(element.dataset.i18nAriaLabel));
    const english = document.getElementById("language-en");
    const russian = document.getElementById("language-ru");
    if (english !== null) {
      english.setAttribute("aria-pressed", language === "en" ? "true" : "false");
      english.setAttribute("aria-label", t("language.english"));
    }
    if (russian !== null) {
      russian.setAttribute("aria-pressed", language === "ru" ? "true" : "false");
      russian.setAttribute("aria-label", t("language.russian"));
    }
    const group = document.querySelector(".language-switch");
    if (group !== null) group.setAttribute("aria-label", t("language.group"));
  }

  function setLanguage(nextLanguage) {
    if (!SUPPORTED_LANGUAGES.has(nextLanguage)) throw new Error("Marketplace language is unsupported");
    if (language === nextLanguage) return;
    language = nextLanguage;
    applyStaticTranslations();
    for (const listener of listeners) listener(language);
  }

  function onChange(listener) {
    if (typeof listener !== "function") throw new TypeError("Marketplace language listener must be callable");
    listeners.add(listener);
    return () => listeners.delete(listener);
  }
  function mount() {
    const syncBox = document.querySelector(".sync-box");
    if (syncBox === null) throw new Error("Marketplace language mount point is unavailable");
    const switcher = document.createElement("div");
    switcher.className = "language-switch";
    switcher.setAttribute("role", "group");
    const english = document.createElement("button");
    english.id = "language-en";
    english.type = "button";
    english.className = "language-option";
    english.textContent = "EN";
    const russian = document.createElement("button");
    russian.id = "language-ru";
    russian.type = "button";
    russian.className = "language-option";
    russian.textContent = "RU";
    english.addEventListener("click", () => setLanguage("en"));
    russian.addEventListener("click", () => setLanguage("ru"));
    switcher.append(english, russian);
    syncBox.prepend(switcher);
    markStaticSurface();
    applyStaticTranslations();
  }

  return Object.freeze({ mount, onChange, setLanguage, t, get language() { return language; } });
})();

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
const i18n = window.MarketplaceI18n;
if (i18n === undefined) throw new Error("Marketplace localization is unavailable");
i18n.mount();
const SYNTHETIC_PRODUCT_LISTING_EXAMPLE = Object.freeze({
  seller_principal: "urn:open-layer-marketplace:demo:seller",
  subject_uri: "urn:open-layer-marketplace:demo:item:city-bicycle",
  title: "City bicycle",
  description: "Synthetic local evaluator listing.",
  consideration_coefficient: "12500",
  consideration_scale: "2",
  currency_code: "EUR",
  quantity_coefficient: "1",
  quantity_scale: "0",
  unit_uri: "urn:open-layer-marketplace:demo:unit:item",
  latitude_e6: "52090700",
  longitude_e6: "5121400",
});
const SYNTHETIC_PROPOSAL_EXAMPLE = Object.freeze({
  buyer_principal: "urn:open-layer-marketplace:demo:buyer",
  action_uri: "urn:open-layer-marketplace:demo:action:buy",
});

const state = {
  records: new Map(),
  selectedId: null,
  selectedRecord: null,
  syncCursor: null,
  truncated: false,
  responseParentId: null,
  responseIds: [],
  responseErrorCode: null,
  responseLoading: false,
  recentProposalId: null,
  recentProposalParentId: null,
  responseRequestSerial: 0,
  detailRequestSerial: 0,
  mvpFlightDocument: null,
  syncUi: { key: "sync.notSynchronized", variables: {}, kind: "" },
  formUi: new Map([["mvp-flight-status", { key: "mvp.localOnly", variables: {}, kind: "muted" }]]),
};

const byId = (id) => document.getElementById(id);
const intentList = byId("intent-list");
const marketMap = byId("market-map");
const filterInput = byId("intent-filter");
const syncStatus = byId("sync-status");
const viewCount = byId("view-count");
const selectedRecordId = byId("selected-record-id");
const selectedRecordSummary = byId("selected-record-summary");
const selectedRecordJson = byId("selected-record-json");
const responseList = byId("response-list");
const returnParentButton = byId("return-parent");
const responseButton = byId("submit-response");
const proposalExampleButton = byId("fill-example-proposal");
const proposalParent = byId("proposal-parent");
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

function renderSyncStatus() {
  syncStatus.textContent = i18n.t(state.syncUi.key, state.syncUi.variables);
  syncStatus.className = state.syncUi.kind;
}

function setStatus(key, variables = {}, kind = "") {
  state.syncUi = { key, variables, kind };
  renderSyncStatus();
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
      "aria-label": i18n.t("map.select", { recordId }),
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
    const summary = proposalResponseSummary(record);
    const listingSummary = summary === null ? productListingSummary(record) : null;
    const title = summary === null
      ? displayText(record, "/term/title", "")
      : i18n.t("responses.proposal");
    const metadata = summary === null
      ? listingSummary === null
        ? ""
        : i18n.t("browse.listingMetadata", { seller: listingSummary.sellerPrincipal, price: listingSummary.price, quantity: listingSummary.quantity })
      : i18n.t("browse.proposalMetadata", { buyer: summary.buyerPrincipal, subject: summary.subjectUri, action: summary.actionUri });
    return [recordId, title, metadata].some((value) => value.toLocaleLowerCase().includes(query));
  });
}
function localizedIntentCount(count) {
  if (i18n.language !== "ru") return `${count} intent${count === 1 ? "" : "s"}`;
  const mod10 = count % 10;
  const mod100 = count % 100;
  const noun = mod10 === 1 && mod100 !== 11 ? "запись" : mod10 >= 2 && mod10 <= 4 && (mod100 < 12 || mod100 > 14) ? "записи" : "записей";
  return `${count} ${noun}`;
}

function renderList() {
  const records = filteredRecords();
  intentList.replaceChildren();
  if (records.length === 0) {
    const empty = document.createElement("p");
    empty.className = "empty-state";
    empty.textContent = i18n.t("browse.empty");
    intentList.append(empty);
  }
  for (const [recordId, record] of records) {
    const card = document.createElement("button");
    card.type = "button";
    card.className = "intent-card";
    card.setAttribute("aria-current", state.selectedId === recordId ? "true" : "false");
    const summary = proposalResponseSummary(record);
    const listingSummary = summary === null ? productListingSummary(record) : null;
    const title = document.createElement("span");
    title.className = "intent-title";
    title.textContent = summary === null
      ? displayText(record, "/term/title", i18n.t("browse.fallback"))
      : i18n.t("responses.proposal");
    const identity = document.createElement("span");
    identity.className = "record-id muted small";
    identity.textContent = recordId;
    if (summary === null) {
      if (listingSummary === null) {
        card.append(title, identity);
      } else {
        const metadata = document.createElement("span");
        metadata.className = "record-id muted small";
        metadata.textContent = i18n.t("browse.listingMetadata", { seller: listingSummary.sellerPrincipal, price: listingSummary.price, quantity: listingSummary.quantity });
        card.append(title, metadata, identity);
      }
    } else {
      const metadata = document.createElement("span");
      metadata.className = "record-id muted small";
      metadata.textContent = i18n.t("browse.proposalMetadata", { buyer: summary.buyerPrincipal, subject: summary.subjectUri, action: summary.actionUri });
      card.append(title, metadata, identity);
    }
    card.addEventListener("click", () => selectIntent(recordId));
    intentList.append(card);
  }
  const countLabel = localizedIntentCount(records.length);
  viewCount.textContent = state.truncated ? `${countLabel} · ${i18n.t("browse.boundedSuffix")}` : countLabel;
  renderMap(records);
}

function selectedProductListingSubjectUri(record) {
  if (record === null || typeof record !== "object" || Array.isArray(record)) return null;
  if (!Array.isArray(record.profiles) || !record.profiles.some((profile) => typeof profile === "string" && profile.endsWith("/profile/product-listing-v1"))) return null;
  const subjects = record.content?.subjects;
  if (!Array.isArray(subjects) || subjects.length !== 1) return null;
  const subject = subjects[0];
  if (subject === null || typeof subject !== "object" || Array.isArray(subject)) return null;
  try {
    return reviewedProposalUri(subject.uri);
  } catch {
    return null;
  }
}

function exactDecimalPresentation(value) {
  if (value === null || typeof value !== "object" || Array.isArray(value)) return null;
  const coefficient = value.coefficient;
  const scale = value.scale;
  if (!Number.isSafeInteger(coefficient) || !Number.isSafeInteger(scale) || scale < 0 || scale > 18) return null;
  const negative = coefficient < 0;
  let digits = String(Math.abs(coefficient));
  if (scale > 0) {
    digits = digits.padStart(scale + 1, "0");
    digits = `${digits.slice(0, -scale)}.${digits.slice(-scale)}`;
  }
  return negative ? `-${digits}` : digits;
}

function productListingSummary(record) {
  if (record === null || typeof record !== "object" || Array.isArray(record)) return null;
  if (!Array.isArray(record.profiles) || !record.profiles.some((profile) => typeof profile === "string" && profile.endsWith("/profile/product-listing-v1"))) return null;
  const issuer = record.content?.issuer;
  const action = record.content?.action;
  if (issuer === null || typeof issuer !== "object" || Array.isArray(issuer)) return null;
  if (action === null || typeof action !== "object" || Array.isArray(action)) return null;
  const subjectUri = selectedProductListingSubjectUri(record);
  let consideration = null;
  let quantity = null;
  for (const [key, value] of recordTerms(record)) {
    if (typeof key !== "string") continue;
    if (key.endsWith("/term/consideration")) consideration = value;
    if (key.endsWith("/term/quantity")) quantity = value;
  }
  if (subjectUri === null || consideration === null || quantity === null) return null;
  if (typeof consideration !== "object" || Array.isArray(consideration) || consideration.kind !== "monetary") return null;
  if (typeof quantity !== "object" || Array.isArray(quantity)) return null;
  const amount = exactDecimalPresentation(consideration.amount);
  const quantityValue = exactDecimalPresentation(quantity.value);
  if (amount === null || quantityValue === null || typeof consideration.currency_code !== "string" || !/^[A-Z]{3}$/.test(consideration.currency_code)) return null;
  if (consideration.amount.coefficient < 0 || quantity.value.coefficient <= 0) return null;
  try {
    const actionUri = reviewedProposalUri(action.id);
    if (!actionUri.endsWith("/action/sell")) return null;
    return { sellerPrincipal: reviewedProposalUri(issuer.principal), subjectUri, price: `${amount} ${consideration.currency_code}`, quantity: `${quantityValue} ${reviewedProposalUri(quantity.unit)}` };
  } catch {
    return null;
  }
}

function proposalResponseSummary(record) {
  if (record === null || typeof record !== "object" || Array.isArray(record)) return null;
  if (!Array.isArray(record.profiles) || !record.profiles.some((profile) => typeof profile === "string" && profile.endsWith("/profile/proposal-v1"))) return null;
  const issuer = record.content?.issuer;
  const subjects = record.content?.subjects;
  const action = record.content?.action;
  if (issuer === null || typeof issuer !== "object" || Array.isArray(issuer)) return null;
  if (!Array.isArray(subjects) || subjects.length !== 1) return null;
  const subject = subjects[0];
  if (subject === null || typeof subject !== "object" || Array.isArray(subject)) return null;
  if (action === null || typeof action !== "object" || Array.isArray(action)) return null;
  try {
    return {
      buyerPrincipal: reviewedProposalUri(issuer.principal),
      subjectUri: reviewedProposalUri(subject.uri),
      actionUri: reviewedProposalUri(action.id),
    };
  } catch {
    return null;
  }
}

function newlyCreatedProductListingId(previousIds, expectedSubjectUri, previousViewWasCurrent) {
  if (!(previousIds instanceof Set) || typeof previousViewWasCurrent !== "boolean") {
    throw stableClientError("POST_CREATE_SELECTION_INVALID");
  }
  if (!previousViewWasCurrent || state.truncated) return null;
  const candidates = [];
  for (const [recordId, record] of state.records.entries()) {
    if (previousIds.has(recordId)) continue;
    if (selectedProductListingSubjectUri(record) === expectedSubjectUri) candidates.push(recordId);
  }
  return candidates.length === 1 ? candidates[0] : null;
}

function newlyCreatedProposalId(parentId, previousResponseIds, expectedSummary, previousResponsesWereCurrent) {
  const reviewedParent = requireRecordId(parentId);
  if (!(previousResponseIds instanceof Set) || expectedSummary === null || typeof expectedSummary !== "object" || Array.isArray(expectedSummary) || typeof previousResponsesWereCurrent !== "boolean") throw stableClientError("POST_PROPOSAL_SELECTION_INVALID");
  const expectedBuyer = reviewedProposalUri(expectedSummary.buyerPrincipal);
  const expectedSubject = reviewedProposalUri(expectedSummary.subjectUri);
  const expectedAction = reviewedProposalUri(expectedSummary.actionUri);
  if (!previousResponsesWereCurrent || state.selectedId !== reviewedParent || state.responseLoading || state.responseErrorCode !== null) return null;
  const candidates = state.responseIds.filter((recordId) => {
    if (previousResponseIds.has(recordId)) return false;
    const summary = proposalResponseSummary(state.records.get(recordId));
    return summary !== null && summary.buyerPrincipal === expectedBuyer && summary.subjectUri === expectedSubject && summary.actionUri === expectedAction;
  });
  return candidates.length === 1 ? candidates[0] : null;
}

function renderSelectedRecordSummary(record) {
  selectedRecordSummary.replaceChildren();
  selectedRecordSummary.hidden = true;
  if (record === undefined || record === null) return;
  const proposalSummary = proposalResponseSummary(record);
  const listingSummary = proposalSummary === null ? productListingSummary(record) : null;
  if (proposalSummary === null && listingSummary === null) return;
  const title = document.createElement("span");
  title.className = "intent-title";
  const metadata = document.createElement("span");
  metadata.className = "record-id muted small";
  if (proposalSummary !== null) {
    title.textContent = i18n.t("responses.proposal");
    metadata.textContent = i18n.t("browse.proposalMetadata", { buyer: proposalSummary.buyerPrincipal, subject: proposalSummary.subjectUri, action: proposalSummary.actionUri });
  } else {
    title.textContent = displayText(record, "/term/title", i18n.t("browse.fallback"));
    metadata.textContent = i18n.t("browse.listingMetadata", { seller: listingSummary.sellerPrincipal, price: listingSummary.price, quantity: listingSummary.quantity });
  }
  selectedRecordSummary.append(title, metadata);
  if (state.responseParentId !== null && state.selectedId !== state.responseParentId) {
    const parent = document.createElement("span");
    parent.className = "record-id muted small";
    parent.textContent = i18n.t("detail.responseParent", { recordId: state.responseParentId });
    selectedRecordSummary.append(parent);
  }
  selectedRecordSummary.hidden = false;
}

function renderProposalParentGuidance(record) {
  const subjectUri = selectedProductListingSubjectUri(record);
  proposalExampleButton.disabled = subjectUri === null;
  if (state.selectedId === null) {
    proposalParent.textContent = i18n.t("author.parentNone");
    return;
  }
  proposalParent.textContent = subjectUri === null
    ? i18n.t("proposal.parentMissing", { recordId: state.selectedId })
    : i18n.t("proposal.parentSubject", { recordId: state.selectedId, subjectUri });
}

function renderDetail() {
  const record = state.selectedRecord;
  const canReturnToParent = state.responseParentId !== null
    && state.selectedId !== null
    && state.selectedId !== state.responseParentId;
  returnParentButton.hidden = !canReturnToParent;
  returnParentButton.disabled = !canReturnToParent;
  selectedRecordId.textContent = state.selectedId ?? i18n.t("detail.none");
  renderSelectedRecordSummary(record);
  selectedRecordJson.textContent = record === undefined || record === null
    ? i18n.t("detail.inspect")
    : JSON.stringify(record, null, 2);
  responseButton.disabled = selectedProductListingSubjectUri(record) === null;
  renderProposalParentGuidance(record);
}
function renderResponseLoading() {
  responseList.replaceChildren();
  const loading = document.createElement("p");
  loading.className = "muted";
  loading.textContent = i18n.t("responses.loading");
  responseList.append(loading);
}

function renderResponseItems(recordId, ids) {
  responseList.replaceChildren();
  if (ids.length === 0) {
    const empty = document.createElement("p");
    empty.className = "muted";
    empty.textContent = i18n.t("responses.empty");
    responseList.append(empty);
    return;
  }
  for (const id of ids) {
    const item = document.createElement("button");
    item.type = "button";
    item.className = "response-card record-id";
    const summary = proposalResponseSummary(state.records.get(id));
    if (summary === null) {
      item.textContent = id;
    } else {
      const title = document.createElement("span");
      title.className = "intent-title";
      const isRecentProposal = state.recentProposalParentId === recordId && state.recentProposalId === id;
      title.textContent = i18n.t(isRecentProposal ? "responses.newProposal" : "responses.proposal");
      const metadata = document.createElement("span");
      metadata.className = "record-id muted small";
      metadata.textContent = i18n.t("responses.metadata", { buyer: summary.buyerPrincipal, subject: summary.subjectUri, action: summary.actionUri, recordId: id });
      item.append(title, metadata);
    }
    item.addEventListener("click", () => {
      state.responseParentId = recordId;
    });
    item.addEventListener("click", () => void inspectIntent(id));
    responseList.append(item);
  }
}

async function renderResponses(recordId) {
  const requestSerial = state.responseRequestSerial + 1;
  state.responseRequestSerial = requestSerial;
  state.responseLoading = true;
  renderResponseLoading();
  try {
    const documentValue = await apiFetch(`${API_INTENTS}/${encodeURIComponent(recordId)}${RESPONSES_SUFFIX}?limit=${PAGE_LIMIT}`);
    if (state.selectedId !== recordId || state.responseRequestSerial !== requestSerial) return false;
    const ids = documentValue.record_ids;
    if (!Array.isArray(ids) || ids.length > PAGE_LIMIT) throw stableClientError("RESPONSE_LIST_INVALID");
    for (const value of ids) requireRecordId(value);
    state.responseLoading = false;
    state.responseIds = ids;
    state.responseErrorCode = null;
    renderResponseItems(recordId, ids);
    return true;
  } catch (error) {
    if (state.selectedId !== recordId || state.responseRequestSerial !== requestSerial) return false;
    state.responseLoading = false;
    state.responseIds = [];
    state.responseErrorCode = error.code ?? "CLIENT_FAILURE";
    const message = document.createElement("p");
    message.className = "error";
    message.textContent = i18n.t("responses.unavailable", { code: state.responseErrorCode });
    responseList.append(message);
    return true;
  }
}

function selectIntent(recordId) {
  const reviewed = requireRecordId(recordId);
  state.detailRequestSerial += 1;
  const record = state.records.get(reviewed);
  state.responseParentId = null;
  state.responseIds = [];
  state.responseErrorCode = null;
  state.responseLoading = false;
  state.selectedId = record === undefined ? null : reviewed;
  state.selectedRecord = record ?? null;
  renderList();
  renderDetail();
  if (state.selectedId !== null) return renderResponses(state.selectedId);
  return Promise.resolve();
}

async function inspectIntent(recordId) {
  const reviewed = requireRecordId(recordId);
  const requestSerial = state.detailRequestSerial + 1;
  state.detailRequestSerial = requestSerial;
  try {
    const record = await apiFetch(`${API_INTENTS}/${encodeURIComponent(reviewed)}`);
    if (state.detailRequestSerial !== requestSerial) return false;
    state.selectedId = reviewed;
    state.selectedRecord = record;
    state.responseIds = [];
    state.responseErrorCode = null;
    state.responseLoading = false;
    renderList();
    renderDetail();
    await renderResponses(reviewed);
    return true;
  } catch (error) {
    if (state.detailRequestSerial !== requestSerial) return false;
    state.selectedId = null;
    state.selectedRecord = null;
    state.responseLoading = false;
    responseList.replaceChildren();
    renderList();
    renderDetail();
    setStatus("detail.failed", { code: error.code ?? "CLIENT_FAILURE" }, "error");
    return true;
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
  setStatus("sync.capture");
  const watermark = await captureSyncWatermark();
  await hydrateCurrentIntents();
  state.syncCursor = watermark;
  renderList();
  renderDetail();
  setStatus("sync.done", { cursor: watermark }, "success");
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
  setStatus("sync.from", { cursor: state.syncCursor });
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
      setStatus("sync.paused", { cursor: state.syncCursor }, "warning");
      return;
    }
    setStatus("sync.done", { cursor: state.syncCursor }, "success");
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

function renderFormStatus(id) {
  const target = byId(id);
  const ui = state.formUi.get(id);
  if (target === null || ui === undefined) return;
  target.textContent = i18n.t(ui.key, ui.variables);
  target.className = ui.kind || "muted";
}

function renderFormStatuses() {
  for (const id of state.formUi.keys()) renderFormStatus(id);
}

function setFormStatus(id, key, variables = {}, kind = "") {
  state.formUi.set(id, { key, variables, kind });
  renderFormStatus(id);
}

function fillSyntheticExample(prefix, values) {
  for (const [name, value] of Object.entries(values)) {
    byId(`${prefix}-${name.replaceAll("_", "-")}`).value = value;
  }
}

function fillSyntheticListingExample() {
  fillSyntheticExample("create", SYNTHETIC_PRODUCT_LISTING_EXAMPLE);
  setFormStatus("create-status", "author.exampleLoaded");
}

function fillSyntheticProposalExample() {
  const subjectUri = selectedProductListingSubjectUri(state.selectedRecord);
  if (subjectUri === null) {
    setFormStatus("response-status", "proposal.exampleNeedsListing", {}, "error");
    return;
  }
  fillSyntheticExample("proposal", { ...SYNTHETIC_PROPOSAL_EXAMPLE, subject_uri: subjectUri });
  setFormStatus("response-status", "proposal.exampleLoaded");
}

async function createProductListing(event) {
  event.preventDefault();
  try {
    const body = productListingJsonBody();
    const submittedSubjectUri = byId("create-subject-uri").value;
    const previousIds = new Set(state.records.keys());
    const previousViewWasCurrent = state.syncCursor !== null && state.truncated === false;
    setFormStatus("create-status", "listing.submitting");
    await apiFetch(API_PRODUCT_LISTINGS, { method: "POST", body });
    try {
      await fullResync();
    } catch (error) {
      setFormStatus("create-status", "listing.refreshFailed", { code: error.code ?? "CLIENT_FAILURE" }, "warning");
      return;
    }
    const createdId = newlyCreatedProductListingId(previousIds, submittedSubjectUri, previousViewWasCurrent);
    if (createdId !== null) {
      selectIntent(createdId);
      setFormStatus("create-status", "listing.acceptedSelected", {}, "success");
      return;
    }
    setFormStatus("create-status", "listing.accepted", {}, "success");
  } catch (error) {
    setFormStatus("create-status", "listing.failed", { code: error.code ?? "CLIENT_FAILURE" }, "error");
  }
}
async function createProposal(event) {
  event.preventDefault();
  if (state.selectedId === null) {
    setFormStatus("response-status", "proposal.selectParent", {}, "error");
    return;
  }
  const parentSubjectUri = selectedProductListingSubjectUri(state.selectedRecord);
  if (parentSubjectUri === null) {
    setFormStatus("response-status", "proposal.selectListing", {}, "error");
    return;
  }
  try {
    const submittedSubjectUri = reviewedProposalUri(byId("proposal-subject-uri").value);
    if (submittedSubjectUri !== parentSubjectUri) {
      setFormStatus("response-status", "proposal.subjectMismatch", { subjectUri: parentSubjectUri }, "error");
      return;
    }
    const body = proposalJsonBody();
    const parentId = requireRecordId(state.selectedId);
    const previousResponseIds = new Set(state.responseIds);
    const previousResponsesWereCurrent = !state.responseLoading && state.responseErrorCode === null;
    const expectedSummary = {
      buyerPrincipal: reviewedProposalUri(byId("proposal-buyer-principal").value),
      subjectUri: submittedSubjectUri,
      actionUri: reviewedProposalUri(byId("proposal-action-uri").value),
    };
    state.recentProposalId = null;
    state.recentProposalParentId = null;
    setFormStatus("response-status", "proposal.submitting");
    await apiFetch(`${API_INTENTS}/${encodeURIComponent(parentId)}${PROPOSALS_SUFFIX}`, {
      method: "POST",
      body,
    });
    try {
      await fullResync();
    } catch (error) {
      setFormStatus("response-status", "proposal.refreshFailed", { code: error.code ?? "CLIENT_FAILURE" }, "warning");
      return;
    }
    if (state.records.has(parentId)) {
      const responsesCurrent = await selectIntent(parentId);
      if (responsesCurrent !== true) {
        setFormStatus("response-status", "proposal.responsesSuperseded", {}, "warning");
        return;
      }
      if (state.responseErrorCode !== null) {
        setFormStatus("response-status", "proposal.responsesUnavailable", { code: state.responseErrorCode }, "warning");
        return;
      }
      const createdId = newlyCreatedProposalId(parentId, previousResponseIds, expectedSummary, previousResponsesWereCurrent);
      if (createdId !== null) {
        state.recentProposalId = createdId;
        state.recentProposalParentId = parentId;
        renderResponseItems(parentId, state.responseIds);
        setFormStatus("response-status", "proposal.acceptedHighlighted", { recordId: createdId }, "success");
        return;
      }
      setFormStatus("response-status", "proposal.acceptedRefreshed", {}, "success");
      return;
    }
    setFormStatus("response-status", "proposal.parentGone", {}, "warning");
  } catch (error) {
    setFormStatus("response-status", "proposal.failed", { code: error.code ?? "CLIENT_FAILURE" }, "error");
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

function renderMvpFlightState() {
  if (state.mvpFlightDocument === null) {
    byId("mvp-flight-final").textContent = i18n.t("mvp.notRun");
    byId("mvp-flight-seller").textContent = i18n.t("mvp.sellerEmpty");
    byId("mvp-flight-buyer").textContent = i18n.t("mvp.buyerEmpty");
    byId("mvp-flight-verification").textContent = i18n.t("mvp.notEvaluated");
    byId("mvp-flight-completed-at").textContent = i18n.t("mvp.completedEmpty");
    mvpFlightLifecycle.replaceChildren();
    mvpFlightAudit.textContent = i18n.t("mvp.auditEmpty");
    return;
  }
  const flight = reviewedMvpFlightDocument(state.mvpFlightDocument);
  byId("mvp-flight-final").textContent = flight.finalState;
  byId("mvp-flight-seller").textContent = i18n.t("mvp.seller", { seller: flight.seller });
  byId("mvp-flight-buyer").textContent = i18n.t("mvp.buyer", { buyer: flight.buyer });
  byId("mvp-flight-completed-at").textContent = i18n.t("mvp.completed", { timestamp: flight.completedAt });
  byId("mvp-flight-verification").textContent = i18n.t("mvp.verificationValue", {
    integrity: flight.listingIntegrityVerified, agreement: flight.agreementFormation,
    fulfillment: flight.fulfillmentConclusion, truth: flight.universalTruth, payment: flight.paymentOrSettlementEvaluated,
  });
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

function renderMvpFlight(documentValue) {
  state.mvpFlightDocument = documentValue;
  renderMvpFlightState();
}

async function runMvpFlight() {
  mvpFlightButton.disabled = true;
  setFormStatus("mvp-flight-status", "mvp.running");
  try {
    const documentValue = await apiFetch(API_MVP_FLIGHT, { method: "POST" });
    renderMvpFlight(documentValue);
    setFormStatus("mvp-flight-status", "mvp.completedStatus", {}, "success");
  } catch (error) {
    setFormStatus("mvp-flight-status", "mvp.failed", { code: error.code ?? "CLIENT_FAILURE" }, "error");
  } finally {
    mvpFlightButton.disabled = false;
  }
}

async function runSyncAction() {
  try {
    await incrementalSync();
  } catch (error) {
    setStatus("sync.failed", { code: error.code ?? "CLIENT_FAILURE" }, "error");
  }
}

filterInput.addEventListener("input", renderList);
byId("sync-now").addEventListener("click", () => void runSyncAction());
returnParentButton.addEventListener("click", () => {
  const parentId = state.responseParentId;
  if (parentId === null) return;
  state.responseParentId = null;
  if (state.records.has(parentId)) {
    selectIntent(parentId);
  } else {
    void inspectIntent(parentId);
  }
});
byId("clear-selection").addEventListener("click", () => {
  state.detailRequestSerial += 1;
  state.responseParentId = null;
  state.responseIds = [];
  state.responseErrorCode = null;
  state.responseLoading = false;
  state.selectedId = null;
  state.selectedRecord = null;
  responseList.replaceChildren();
  renderList();
  renderDetail();
});
byId("fill-example-listing").addEventListener("click", fillSyntheticListingExample);
byId("fill-example-proposal").addEventListener("click", fillSyntheticProposalExample);
byId("create-form").addEventListener("submit", (event) => void createProductListing(event));
byId("response-form").addEventListener("submit", (event) => void createProposal(event));
mvpFlightButton.addEventListener("click", () => void runMvpFlight());

i18n.onChange(() => {
  renderSyncStatus();
  renderFormStatuses();
  renderList();
  renderDetail();
  if (state.selectedId !== null) {
    if (state.responseLoading) {
      renderResponseLoading();
    } else if (state.responseErrorCode === null) {
      renderResponseItems(state.selectedId, state.responseIds);
    } else {
      responseList.replaceChildren();
      const message = document.createElement("p");
      message.className = "error";
      message.textContent = i18n.t("responses.unavailable", { code: state.responseErrorCode });
      responseList.append(message);
    }
  }
  renderMvpFlightState();
});

renderSyncStatus();
renderFormStatuses();
renderList();
renderDetail();
renderMvpFlightState();
void fullResync().catch((error) => {
  setStatus("sync.initialFailed", { code: error.code ?? "CLIENT_FAILURE" }, "error");
});
