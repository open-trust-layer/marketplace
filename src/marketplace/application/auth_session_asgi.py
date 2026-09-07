"""Explicit M17.5D ASGI seam; defining it does not activate runtime auth."""
from __future__ import annotations

from typing import Any, Callable

from .asgi import (
    AsgiHttpAdapterError,
    AsgiReceive,
    AsgiSend,
    _fail,
    _read_request_body,
    _response_headers,
    _review_scope,
)
from .auth_http import MarketplaceAuthenticatedApplicationHttpAdapter
from .auth_session_http import AUTH_REQUEST_MAX_BYTES, MarketplaceAuthenticationSessionHttpAdapter
from .bearer import MarketplaceBearerTransportError, parse_marketplace_bearer_authorization
from .http import (
    ApplicationHttpRequest,
    ApplicationHttpResponse,
    MAX_APPLICATION_HTTP_RESPONSE_BYTES,
    _error_response,
)
from .site_host import MarketplaceSiteHostAdapter


class MarketplaceSessionEstablishmentAsgiHttpAdapter:
    """Route exact auth endpoints plus existing M17.5C protected writes."""

    __slots__ = ("_site", "_marketplace_http", "_auth_http", "_now")
    def __init__(
        self,
        *,
        site: MarketplaceSiteHostAdapter,
        marketplace_http: MarketplaceAuthenticatedApplicationHttpAdapter,
        auth_http: MarketplaceAuthenticationSessionHttpAdapter,
        now: Callable[[], int],
    ) -> None:
        if type(site) is not MarketplaceSiteHostAdapter:
            raise TypeError("site MUST be exact MarketplaceSiteHostAdapter")
        if type(marketplace_http) is not MarketplaceAuthenticatedApplicationHttpAdapter:
            raise TypeError("marketplace_http MUST be exact authenticated HTTP adapter")
        if type(auth_http) is not MarketplaceAuthenticationSessionHttpAdapter:
            raise TypeError("auth_http MUST be exact authentication-session HTTP adapter")
        if not callable(now):
            raise TypeError("now MUST be callable")
        self._site = site
        self._marketplace_http = marketplace_http
        self._auth_http = auth_http
        self._now = now

    async def __call__(
        self,
        scope: dict[str, Any],
        receive: AsgiReceive,
        send: AsgiSend,
    ) -> None:
        if not callable(receive) or not callable(send):
            raise TypeError("ASGI receive and send MUST be callable")
        method, path, query, content_type, content_length, authorization = _review_scope(
            scope,
            allow_authorization=True,
        )
        auth_route = path.startswith("/api/auth/")
        try:
            body = await _read_request_body(
                receive,
                expected_length=content_length,
                max_body_bytes=AUTH_REQUEST_MAX_BYTES if auth_route else 256 * 1024,
            )
        except AsgiHttpAdapterError as exc:
            if not auth_route or exc.code != "ASGI_REQUEST_TOO_LARGE":
                raise
            response = _error_response(
                400, "Bad Request", "AUTH_REQUEST_INVALID", "authentication request is invalid"
            )
            headers = _response_headers(response)
            await send({"type": "http.response.start", "status": response.status_code, "headers": headers})
            await send({"type": "http.response.body", "body": response.body, "more_body": False})
            return
        request = ApplicationHttpRequest(method, path, query, content_type, body)

        session_token: bytes | None = None
        session_invalid = False
        if authorization is not None:
            try:
                session_token = parse_marketplace_bearer_authorization(authorization)
            except MarketplaceBearerTransportError:
                session_invalid = True

        try:
            if auth_route or path.startswith("/api/") or authorization is not None:
                now = self._now()
                if type(now) is not int or now < 0:
                    _fail("ASGI_AUTH_TIME_INVALID", "application auth clock is invalid")
            if auth_route:
                response = self._auth_http.handle(
                    request,
                    session_token=session_token,
                    session_invalid=session_invalid,
                    now=now,
                )
            elif path.startswith("/api/") or authorization is not None:
                response = self._marketplace_http.handle(
                    request,
                    session_token=session_token,
                    session_invalid=session_invalid,
                    now=now,
                )
            else:
                response = self._site.handle(request)
        except AsgiHttpAdapterError:
            raise
        except Exception:
            _fail("ASGI_SITE_FAILURE", "Marketplace auth site host could not complete safely")

        if (
            type(response) is not ApplicationHttpResponse
            or type(response.status_code) is not int
            or not 100 <= response.status_code <= 599
            or type(response.reason) is not str
            or type(response.body) is not bytes
            or len(response.body) > MAX_APPLICATION_HTTP_RESPONSE_BYTES
        ):
            _fail("ASGI_RESPONSE_INVALID", "Marketplace auth site host returned an invalid response")
        headers = _response_headers(response)
        await send({"type": "http.response.start", "status": response.status_code, "headers": headers})
        await send({"type": "http.response.body", "body": response.body, "more_body": False})


__all__ = ["MarketplaceSessionEstablishmentAsgiHttpAdapter"]
