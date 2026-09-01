"""Bounded transport-free HTTP application adapter for the local M76 visual contract."""
from __future__ import annotations

from dataclasses import dataclass

from .local_visual_v1 import (
    LocalVisualInteractionError,
    LocalVisualSubmission,
    render_local_buy_sell_form,
    submit_local_buy_sell_form,
)


MAX_LOCAL_UI_HTTP_BODY_BYTES = 49_152
_MAX_LOCAL_UI_HTTP_RESPONSE_BYTES = 65_536
_FORM_CONTENT_TYPE = "application/x-www-form-urlencoded"
_FORM_FIELDS = (
    "seller_principal",
    "subject_uri",
    "title",
    "description",
    "consideration",
    "currency_code",
    "quantity",
    "unit_uri",
    "latitude",
    "longitude",
    "buyer_principal",
    "buyer_action_uri",
)
_FORM_FIELD_BYTES = tuple(name.encode("ascii") for name in _FORM_FIELDS)
_CSP = (
    "default-src 'none'; style-src 'unsafe-inline'; form-action 'self'; "
    "base-uri 'none'; frame-ancestors 'none'"
)


class LocalUiHttpError(RuntimeError):
    """Stable adapter misuse/invariant failure that never reflects caller content."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True, slots=True)
class LocalUiHttpRequest:
    """Exact already-framed local HTTP request consumed by the M77 adapter."""

    method: str
    target: str
    content_type: str | None
    body: bytes


@dataclass(frozen=True, slots=True)
class LocalUiHttpResponse:
    """Exact bounded HTTP application response; transport transmission is out of scope."""

    status_code: int
    reason: str
    headers: tuple[tuple[str, str], ...]
    body: bytes


def _error_html(title: str, message: str) -> str:
    return (
        "<!doctype html>"
        '<html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        f"<title>{title}</title></head><body><main>"
        f"<h1>{title}</h1><p>{message}</p>"
        "</main></body></html>"
    )


def _response(status_code: int, reason: str, html: str, *, allow: str | None = None) -> LocalUiHttpResponse:
    if type(html) is not str:
        raise LocalUiHttpError("RESPONSE_INVALID", "local UI HTTP response body must be text")
    try:
        body = html.encode("utf-8")
    except UnicodeEncodeError as exc:
        raise LocalUiHttpError("RESPONSE_INVALID", "local UI HTTP response body is not UTF-8 encodable") from exc
    if len(body) > _MAX_LOCAL_UI_HTTP_RESPONSE_BYTES:
        raise LocalUiHttpError("RESPONSE_TOO_LARGE", "local UI HTTP response exceeded the reviewed bound")

    headers: tuple[tuple[str, str], ...] = (
        ("Content-Type", "text/html; charset=utf-8"),
        ("Content-Length", str(len(body))),
        ("Cache-Control", "no-store"),
        ("X-Content-Type-Options", "nosniff"),
        ("Referrer-Policy", "no-referrer"),
        ("Content-Security-Policy", _CSP),
    )
    if allow is not None:
        headers += (("Allow", allow),)
    return LocalUiHttpResponse(
        status_code=status_code,
        reason=reason,
        headers=headers,
        body=body,
    )


def _bad_request() -> LocalUiHttpResponse:
    return _response(400, "Bad Request", _error_html("Bad Request", "The local request was invalid."))


def _hex_nibble(value: int) -> int:
    if 48 <= value <= 57:
        return value - 48
    if 65 <= value <= 70:
        return value - 55
    if 97 <= value <= 102:
        return value - 87
    return -1


def _decode_form_value(raw: bytes) -> str:
    output = bytearray()
    index = 0
    while index < len(raw):
        value = raw[index]
        if value == 43:  # application/x-www-form-urlencoded '+' -> SP
            output.append(32)
            index += 1
            continue
        if value == 37:  # percent escape
            if index + 2 >= len(raw):
                raise ValueError("malformed percent escape")
            high = _hex_nibble(raw[index + 1])
            low = _hex_nibble(raw[index + 2])
            if high < 0 or low < 0:
                raise ValueError("malformed percent escape")
            output.append((high << 4) | low)
            index += 3
            continue
        output.append(value)
        index += 1
    return bytes(output).decode("utf-8", errors="strict")


def _parse_form(body: bytes) -> dict[str, str]:
    if not body or body.count(b"&") != len(_FORM_FIELDS) - 1:
        raise ValueError("unexpected form field count")

    parsed: dict[str, str] = {}
    for pair in body.split(b"&"):
        if pair.count(b"=") != 1:
            raise ValueError("noncanonical form pair")
        raw_name, raw_value = pair.split(b"=", 1)
        if raw_name not in _FORM_FIELD_BYTES:
            raise ValueError("unknown form field")
        name = raw_name.decode("ascii")
        if name in parsed:
            raise ValueError("duplicate form field")
        parsed[name] = _decode_form_value(raw_value)

    if tuple(sorted(parsed)) != tuple(sorted(_FORM_FIELDS)):
        raise ValueError("missing form field")
    return parsed


def _validate_request(request: LocalUiHttpRequest) -> None:
    if type(request) is not LocalUiHttpRequest:
        raise LocalUiHttpError("REQUEST_INVALID", "local UI HTTP request must be the exact request type")
    if type(request.method) is not str or type(request.target) is not str or type(request.body) is not bytes:
        raise LocalUiHttpError("REQUEST_INVALID", "local UI HTTP request fields have invalid types")
    if request.content_type is not None and type(request.content_type) is not str:
        raise LocalUiHttpError("REQUEST_INVALID", "local UI HTTP content type has invalid type")
    if len(request.method) > 8 or len(request.target) > 64:
        raise LocalUiHttpError("REQUEST_INVALID", "local UI HTTP request metadata exceeded reviewed bounds")
    if request.content_type is not None and len(request.content_type) > 128:
        raise LocalUiHttpError("REQUEST_INVALID", "local UI HTTP content type exceeded reviewed bounds")


def handle_local_ui_http_request(request: LocalUiHttpRequest) -> LocalUiHttpResponse:
    """Handle one already-framed local UI request without owning or exercising transport authority."""
    _validate_request(request)

    if request.target == "/":
        if request.method != "GET":
            return _response(
                405,
                "Method Not Allowed",
                _error_html("Method Not Allowed", "This local route accepts GET only."),
                allow="GET",
            )
        if request.body != b"" or request.content_type is not None:
            return _bad_request()
        return _response(200, "OK", render_local_buy_sell_form())

    if request.target == "/local-buy-sell":
        if request.method != "POST":
            return _response(
                405,
                "Method Not Allowed",
                _error_html("Method Not Allowed", "This local route accepts POST only."),
                allow="POST",
            )
        if len(request.body) > MAX_LOCAL_UI_HTTP_BODY_BYTES:
            return _response(
                413,
                "Payload Too Large",
                _error_html("Payload Too Large", "The local form submission exceeded the reviewed bound."),
            )
        if request.content_type != _FORM_CONTENT_TYPE:
            return _response(
                415,
                "Unsupported Media Type",
                _error_html("Unsupported Media Type", "The local form media type is not supported."),
            )
        try:
            values = _parse_form(request.body)
            submission = LocalVisualSubmission(**values)
            page = submit_local_buy_sell_form(submission)
        except (UnicodeDecodeError, ValueError):
            return _bad_request()
        except LocalVisualInteractionError as exc:
            if exc.code == "SUBMISSION_INVALID":
                return _bad_request()
            return _response(
                500,
                "Internal Server Error",
                _error_html("Internal Server Error", "The reviewed local visual path could not complete."),
            )
        return _response(200, "OK", page)

    return _response(
        404,
        "Not Found",
        _error_html("Not Found", "The requested local route does not exist."),
    )


__all__ = [
    "MAX_LOCAL_UI_HTTP_BODY_BYTES",
    "LocalUiHttpError",
    "LocalUiHttpRequest",
    "LocalUiHttpResponse",
    "handle_local_ui_http_request",
]
