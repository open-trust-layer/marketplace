"""Framework-neutral HTTP application binding for the Marketplace product API.

The adapter consumes an already-framed request value and returns a bounded response
value. It owns no socket, server lifecycle, database connection, browser, or client
runtime. Marketplace semantics remain delegated to ``MarketplaceApplicationApiService``.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Callable

from .api import ApplicationApiError, IntentIndexPage, MarketplaceApplicationApiService
from .postgres_state import ApplicationStatePutResult, StoreDisposition, SyncChange, SyncPage

MAX_APPLICATION_HTTP_BODY_BYTES = 256 * 1024
MAX_APPLICATION_HTTP_RESPONSE_BYTES = 300 * 1024
MAX_APPLICATION_HTTP_PATH_CHARS = 1024
MAX_APPLICATION_HTTP_QUERY_ITEMS = 4
MAX_APPLICATION_HTTP_QUERY_VALUE_CHARS = 512
_JSON_CONTENT_TYPE = "application/json"
_JSON_RESPONSE_CONTENT_TYPE = "application/json; charset=utf-8"
_CSP = "default-src 'none'; frame-ancestors 'none'; base-uri 'none'"

RecordJsonDecoder = Callable[[bytes], Any]
RecordJsonEncoder = Callable[[Any], bytes]


class ApplicationHttpError(RuntimeError):
    """Stable adapter invariant failure without caller payload reflection."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True, slots=True)
class ApplicationHttpRequest:
    """Already-framed HTTP semantics supplied by a later host/framework adapter."""

    method: str
    path: str
    query: tuple[tuple[str, str], ...]
    content_type: str | None
    body: bytes


@dataclass(frozen=True, slots=True)
class ApplicationHttpResponse:
    """Bounded HTTP response semantics; transmission is deliberately out of scope."""

    status_code: int
    reason: str
    headers: tuple[tuple[str, str], ...]
    body: bytes


def _strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON member")
        result[key] = value
    return result


def _validate_json_object_bytes(body: bytes) -> None:
    if type(body) is not bytes or not body or len(body) > MAX_APPLICATION_HTTP_BODY_BYTES:
        raise ValueError("invalid JSON body bytes")
    if body.startswith(b"\xef\xbb\xbf"):
        raise ValueError("UTF-8 BOM is forbidden")
    try:
        text = body.decode("utf-8", "strict")
        document = json.loads(
            text,
            object_pairs_hook=_strict_object,
            parse_constant=lambda value: (_ for _ in ()).throw(ValueError("non-finite JSON number")),
        )
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError, ValueError):
        raise ValueError("invalid JSON object") from None
    if type(document) is not dict:
        raise ValueError("JSON top level must be an object")


def _control_json(document: object) -> bytes:
    try:
        body = json.dumps(
            document,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError, RecursionError, UnicodeEncodeError) as exc:
        raise ApplicationHttpError(
            "RESPONSE_ENCODING_FAILED",
            "application HTTP response could not be encoded safely",
        ) from exc
    if len(body) > MAX_APPLICATION_HTTP_RESPONSE_BYTES:
        raise ApplicationHttpError(
            "RESPONSE_TOO_LARGE",
            "application HTTP response exceeded the reviewed byte bound",
        )
    return body


def _response(
    status_code: int,
    reason: str,
    body: bytes,
    *,
    allow: str | None = None,
) -> ApplicationHttpResponse:
    if type(body) is not bytes:
        raise ApplicationHttpError("RESPONSE_INVALID", "application HTTP body must be exact bytes")
    if len(body) > MAX_APPLICATION_HTTP_RESPONSE_BYTES:
        raise ApplicationHttpError("RESPONSE_TOO_LARGE", "application HTTP response exceeded the reviewed byte bound")
    headers: tuple[tuple[str, str], ...] = (
        ("Content-Type", _JSON_RESPONSE_CONTENT_TYPE),
        ("Content-Length", str(len(body))),
        ("Cache-Control", "no-store"),
        ("X-Content-Type-Options", "nosniff"),
        ("Referrer-Policy", "no-referrer"),
        ("Content-Security-Policy", _CSP),
    )
    if allow is not None:
        headers += (("Allow", allow),)
    return ApplicationHttpResponse(status_code, reason, headers, body)


def _json_response(status_code: int, reason: str, document: object, *, allow: str | None = None) -> ApplicationHttpResponse:
    return _response(status_code, reason, _control_json(document), allow=allow)


def _error_response(status_code: int, reason: str, code: str, message: str, *, allow: str | None = None) -> ApplicationHttpResponse:
    return _json_response(
        status_code,
        reason,
        {"error": {"code": code, "message": message}},
        allow=allow,
    )


def _bad_request(code: str = "REQUEST_INVALID") -> ApplicationHttpResponse:
    return _error_response(400, "Bad Request", code, "request is invalid")


def _validate_request(request: ApplicationHttpRequest) -> None:
    if type(request) is not ApplicationHttpRequest:
        raise ApplicationHttpError("REQUEST_INVALID", "request must use the exact application HTTP request type")
    if type(request.method) is not str or type(request.path) is not str or type(request.body) is not bytes:
        raise ApplicationHttpError("REQUEST_INVALID", "request fields have invalid types")
    if type(request.query) is not tuple:
        raise ApplicationHttpError("REQUEST_INVALID", "query must be an exact tuple")
    if request.content_type is not None and type(request.content_type) is not str:
        raise ApplicationHttpError("REQUEST_INVALID", "content type has invalid type")
    if not request.method or len(request.method) > 8 or not request.path or len(request.path) > MAX_APPLICATION_HTTP_PATH_CHARS:
        raise ApplicationHttpError("REQUEST_INVALID", "request metadata exceeded reviewed bounds")
    if any(ord(char) < 32 or ord(char) == 127 for char in request.method + request.path):
        raise ApplicationHttpError("REQUEST_INVALID", "request metadata contains control characters")
    if request.content_type is not None and len(request.content_type) > 128:
        raise ApplicationHttpError("REQUEST_INVALID", "content type exceeded reviewed bounds")


def _query_map(query: tuple[tuple[str, str], ...], *, allowed: tuple[str, ...]) -> dict[str, str]:
    if len(query) > MAX_APPLICATION_HTTP_QUERY_ITEMS:
        raise ValueError("too many query items")
    result: dict[str, str] = {}
    for item in query:
        if type(item) is not tuple or len(item) != 2:
            raise ValueError("invalid query item")
        name, value = item
        if type(name) is not str or type(value) is not str:
            raise ValueError("invalid query item type")
        if name not in allowed or name in result:
            raise ValueError("unknown or duplicate query name")
        if not value or len(value) > MAX_APPLICATION_HTTP_QUERY_VALUE_CHARS:
            raise ValueError("invalid query value")
        if any(ord(char) < 32 or ord(char) == 127 for char in name + value):
            raise ValueError("query contains control character")
        result[name] = value
    return result


def _positive_int(value: str, *, maximum: int) -> int:
    if not value.isascii() or not value.isdigit():
        raise ValueError("integer query value is invalid")
    parsed = int(value)
    if parsed < 1 or parsed > maximum or str(parsed) != value:
        raise ValueError("integer query value is out of range")
    return parsed


def _nonnegative_int(value: str) -> int:
    if not value.isascii() or not value.isdigit():
        raise ValueError("cursor query value is invalid")
    parsed = int(value)
    if parsed < 0 or parsed > 9_223_372_036_854_775_807 or str(parsed) != value:
        raise ValueError("cursor query value is out of range")
    return parsed


def _record_id_from_path(path: str, *, responses: bool) -> str | None:
    parts = path.split("/")
    if responses:
        if len(parts) != 6 or parts[:3] != ["", "api", "intents"] or parts[5] != "responses":
            return None
        record_id = parts[3]
        if parts[4] != "":
            return None
    else:
        if len(parts) != 4 or parts[:3] != ["", "api", "intents"]:
            return None
        record_id = parts[3]
    if not record_id or len(record_id) > 512:
        return None
    if any(ord(char) < 33 or ord(char) > 126 or char in "/?#" for char in record_id):
        return None
    return record_id


def _response_parent_path(path: str) -> str | None:
    parts = path.split("/")
    if len(parts) != 5 or parts[:3] != ["", "api", "intents"] or parts[4] != "responses":
        return None
    record_id = parts[3]
    if not record_id or len(record_id) > 512:
        return None
    if any(ord(char) < 33 or ord(char) > 126 or char in "/?#" for char in record_id):
        return None
    return record_id


def _require_empty_entity(request: ApplicationHttpRequest) -> bool:
    return request.body == b"" and request.content_type is None


def _put_document(result: object) -> dict[str, object]:
    if type(result) is not ApplicationStatePutResult:
        raise ApplicationHttpError("APPLICATION_API_RESULT_INVALID", "application API returned an invalid write result")
    if type(result.disposition) is not StoreDisposition:
        raise ApplicationHttpError("APPLICATION_API_RESULT_INVALID", "application API returned an invalid write disposition")
    if result.change_seq is not None and (type(result.change_seq) is not int or result.change_seq < 1):
        raise ApplicationHttpError("APPLICATION_API_RESULT_INVALID", "application API returned an invalid change sequence")
    return {"change_seq": result.change_seq, "disposition": result.disposition.value}


def _application_failure(exc: ApplicationApiError) -> ApplicationHttpResponse:
    mapping: dict[str, tuple[int, str, str]] = {
        "APPLICATION_API_NOT_INITIALIZED": (503, "Service Unavailable", "application API is not initialized"),
        "INTENT_RECORD_REQUIRED": (400, "Bad Request", "request does not contain a valid intent record"),
        "ROOT_INTENT_RESPONSE_FORBIDDEN": (400, "Bad Request", "root intent cannot be response-bound"),
        "RESPONSE_RECORD_NOT_INTENT": (400, "Bad Request", "response does not contain a valid intent record"),
        "RESPONSE_PARENT_MISMATCH": (400, "Bad Request", "response is not bound to the requested parent"),
        "PARENT_INTENT_NOT_FOUND": (404, "Not Found", "parent intent was not found"),
        "PARENT_RECORD_NOT_INTENT": (400, "Bad Request", "parent record is not an intent"),
        "SYNC_CURSOR_EXPIRED": (409, "Conflict", "sync cursor expired; full resynchronization is required"),
    }
    reviewed = mapping.get(exc.code)
    if reviewed is None:
        return _error_response(500, "Internal Server Error", "APPLICATION_API_FAILED", "application API could not complete safely")
    status, reason, message = reviewed
    return _error_response(status, reason, exc.code, message)


class MarketplaceApplicationHttpAdapter:
    """Bind exact application routes without owning HTTP runtime or transport I/O."""

    def __init__(
        self,
        *,
        api: MarketplaceApplicationApiService,
        decode_record_json: RecordJsonDecoder,
        encode_record_json: RecordJsonEncoder,
    ) -> None:
        if not callable(decode_record_json) or not callable(encode_record_json):
            raise TypeError("record JSON codecs MUST be callable")
        self._api = api
        self._decode_record_json = decode_record_json
        self._encode_record_json = encode_record_json

    def _decode_record(self, body: bytes) -> Any:
        _validate_json_object_bytes(body)
        try:
            return self._decode_record_json(body)
        except Exception:
            raise ValueError("record JSON decoder rejected request") from None

    def _encode_record(self, record: Any) -> bytes:
        try:
            body = self._encode_record_json(record)
        except Exception as exc:
            raise ApplicationHttpError("RECORD_ENCODING_FAILED", "record could not be encoded safely") from exc
        if type(body) is not bytes or not body or len(body) > MAX_APPLICATION_HTTP_BODY_BYTES:
            raise ApplicationHttpError("RECORD_ENCODING_FAILED", "record encoder returned invalid bytes")
        try:
            _validate_json_object_bytes(body)
        except ValueError as exc:
            raise ApplicationHttpError("RECORD_ENCODING_FAILED", "record encoder returned invalid JSON") from exc
        return body

    def handle(self, request: ApplicationHttpRequest) -> ApplicationHttpResponse:
        try:
            _validate_request(request)
        except ApplicationHttpError:
            return _bad_request()
        if len(request.body) > MAX_APPLICATION_HTTP_BODY_BYTES:
            return _error_response(413, "Payload Too Large", "PAYLOAD_TOO_LARGE", "request body exceeded the reviewed bound")

        if request.path == "/api/intents":
            return self._intents(request)
        if request.path == "/api/sync":
            return self._sync(request)
        parent_id = _response_parent_path(request.path)
        if parent_id is not None:
            return self._responses(request, parent_id)
        record_id = _record_id_from_path(request.path, responses=False)
        if record_id is not None:
            return self._intent(request, record_id)
        return _error_response(404, "Not Found", "ROUTE_NOT_FOUND", "route does not exist")

    def _intents(self, request: ApplicationHttpRequest) -> ApplicationHttpResponse:
        if request.method == "GET":
            if not _require_empty_entity(request):
                return _bad_request()
            try:
                query = _query_map(request.query, allowed=("cursor", "limit"))
                limit = 64 if "limit" not in query else _positive_int(query["limit"], maximum=256)
                cursor = query.get("cursor")
                page = self._api.list_intents(cursor=cursor, limit=limit)
                if type(page) is not IntentIndexPage:
                    raise ApplicationHttpError("APPLICATION_API_RESULT_INVALID", "intent list result is invalid")
                return _json_response(200, "OK", {"next_cursor": page.next_cursor, "record_ids": list(page.record_ids)})
            except ValueError:
                return _bad_request("QUERY_INVALID")
            except ApplicationApiError as exc:
                return _application_failure(exc)
            except ApplicationHttpError:
                return _error_response(500, "Internal Server Error", "APPLICATION_API_RESULT_INVALID", "application API returned an invalid result")
            except Exception:
                return _error_response(500, "Internal Server Error", "APPLICATION_API_FAILED", "application API could not complete safely")

        if request.method == "POST":
            if request.query:
                return _bad_request("QUERY_INVALID")
            if request.content_type != _JSON_CONTENT_TYPE:
                return _error_response(415, "Unsupported Media Type", "UNSUPPORTED_MEDIA_TYPE", "application/json is required")
            try:
                record = self._decode_record(request.body)
            except ValueError:
                return _bad_request("INVALID_JSON_BODY")
            try:
                return _json_response(201, "Created", _put_document(self._api.create_intent(record)))
            except ApplicationApiError as exc:
                return _application_failure(exc)
            except ApplicationHttpError:
                return _error_response(500, "Internal Server Error", "APPLICATION_API_RESULT_INVALID", "application API returned an invalid result")
            except Exception:
                return _error_response(500, "Internal Server Error", "APPLICATION_API_FAILED", "application API could not complete safely")

        return _error_response(405, "Method Not Allowed", "METHOD_NOT_ALLOWED", "route does not accept this method", allow="GET, POST")

    def _intent(self, request: ApplicationHttpRequest, record_id: str) -> ApplicationHttpResponse:
        if request.method != "GET":
            return _error_response(405, "Method Not Allowed", "METHOD_NOT_ALLOWED", "route does not accept this method", allow="GET")
        if request.query or not _require_empty_entity(request):
            return _bad_request()
        try:
            record = self._api.get_intent(record_id)
            if record is None:
                return _error_response(404, "Not Found", "INTENT_NOT_FOUND", "intent was not found")
            return _response(200, "OK", self._encode_record(record))
        except ApplicationApiError as exc:
            return _application_failure(exc)
        except ApplicationHttpError:
            return _error_response(500, "Internal Server Error", "RECORD_ENCODING_FAILED", "record could not be encoded safely")
        except Exception:
            return _error_response(500, "Internal Server Error", "APPLICATION_API_FAILED", "application API could not complete safely")

    def _responses(self, request: ApplicationHttpRequest, parent_id: str) -> ApplicationHttpResponse:
        if request.method == "GET":
            if not _require_empty_entity(request):
                return _bad_request()
            try:
                query = _query_map(request.query, allowed=("limit",))
                limit = 64 if "limit" not in query else _positive_int(query["limit"], maximum=256)
                values = self._api.list_responses(parent_id, limit=limit)
                if type(values) is not tuple or any(type(value) is not str or not value for value in values):
                    raise ApplicationHttpError("APPLICATION_API_RESULT_INVALID", "response list result is invalid")
                if len(values) > limit:
                    raise ApplicationHttpError("APPLICATION_API_RESULT_INVALID", "response list exceeded limit")
                return _json_response(200, "OK", {"record_ids": list(values)})
            except ValueError:
                return _bad_request("QUERY_INVALID")
            except ApplicationApiError as exc:
                return _application_failure(exc)
            except ApplicationHttpError:
                return _error_response(500, "Internal Server Error", "APPLICATION_API_RESULT_INVALID", "application API returned an invalid result")
            except Exception:
                return _error_response(500, "Internal Server Error", "APPLICATION_API_FAILED", "application API could not complete safely")

        if request.method == "POST":
            if request.query:
                return _bad_request("QUERY_INVALID")
            if request.content_type != _JSON_CONTENT_TYPE:
                return _error_response(415, "Unsupported Media Type", "UNSUPPORTED_MEDIA_TYPE", "application/json is required")
            try:
                record = self._decode_record(request.body)
            except ValueError:
                return _bad_request("INVALID_JSON_BODY")
            try:
                return _json_response(201, "Created", _put_document(self._api.respond_to_intent(parent_id, record)))
            except ApplicationApiError as exc:
                return _application_failure(exc)
            except ApplicationHttpError:
                return _error_response(500, "Internal Server Error", "APPLICATION_API_RESULT_INVALID", "application API returned an invalid result")
            except Exception:
                return _error_response(500, "Internal Server Error", "APPLICATION_API_FAILED", "application API could not complete safely")

        return _error_response(405, "Method Not Allowed", "METHOD_NOT_ALLOWED", "route does not accept this method", allow="GET, POST")

    def _sync(self, request: ApplicationHttpRequest) -> ApplicationHttpResponse:
        if request.method != "GET":
            return _error_response(405, "Method Not Allowed", "METHOD_NOT_ALLOWED", "route does not accept this method", allow="GET")
        if not _require_empty_entity(request):
            return _bad_request()
        try:
            query = _query_map(request.query, allowed=("cursor", "limit"))
            cursor = 0 if "cursor" not in query else _nonnegative_int(query["cursor"])
            limit = 128 if "limit" not in query else _positive_int(query["limit"], maximum=256)
            page = self._api.sync(cursor=cursor, limit=limit)
            if type(page) is not SyncPage or type(page.changes) is not tuple:
                raise ApplicationHttpError("APPLICATION_API_RESULT_INVALID", "sync result is invalid")
            changes: list[dict[str, object]] = []
            for change in page.changes:
                if type(change) is not SyncChange:
                    raise ApplicationHttpError("APPLICATION_API_RESULT_INVALID", "sync change is invalid")
                changes.append({"change_kind": change.change_kind, "record_id": change.record_id, "seq": change.seq})
            return _json_response(
                200,
                "OK",
                {"changes": changes, "has_more": page.has_more, "next_cursor": page.next_cursor},
            )
        except ValueError:
            return _bad_request("QUERY_INVALID")
        except ApplicationApiError as exc:
            return _application_failure(exc)
        except ApplicationHttpError:
            return _error_response(500, "Internal Server Error", "APPLICATION_API_RESULT_INVALID", "application API returned an invalid result")
        except Exception:
            return _error_response(500, "Internal Server Error", "APPLICATION_API_FAILED", "application API could not complete safely")


__all__ = [
    "ApplicationHttpError",
    "ApplicationHttpRequest",
    "ApplicationHttpResponse",
    "MAX_APPLICATION_HTTP_BODY_BYTES",
    "MAX_APPLICATION_HTTP_RESPONSE_BYTES",
    "MarketplaceApplicationHttpAdapter",
    "RecordJsonDecoder",
    "RecordJsonEncoder",
]
