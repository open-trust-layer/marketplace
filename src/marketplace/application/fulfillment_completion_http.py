"""M17.7C authenticated HTTP seam for reviewed fulfillment completion evidence."""
from __future__ import annotations

import re
from typing import Final

from .agreement_publication_http import (
    MarketplaceAuthenticatedAgreementPublicationHttpAdapter,
)
from .auth import ApplicationAuthError, MarketplaceApplicationAuthService
from .auth_http import _auth_error, _auth_invalid, _auth_required
from .fulfillment_completion_publication import (
    CLAIMED_COMPLETE_PERFORMANCE,
    COMMITMENT_ACCEPTANCE,
    COMMITMENT_COMPLETION,
    FulfillmentCompletionPublicationError,
    FulfillmentEvidencePublicationResult,
    MarketplaceFulfillmentCompletionPublicationService,
)
from .http import (
    ApplicationHttpError,
    ApplicationHttpRequest,
    ApplicationHttpResponse,
    _bad_request,
    _decode_json_object_bytes,
    _error_response,
    _json_response,
    _validate_request,
)
from .postgres_state import StoreDisposition


PROFILE_NAME: Final = "MARKETPLACE_AUTHENTICATED_FULFILLMENT_COMPLETION_HTTP_V1"

_REQUEST_FIELDS = frozenset({"evidence_kind"})
_EVIDENCE_KINDS = frozenset(
    {
        CLAIMED_COMPLETE_PERFORMANCE,
        COMMITMENT_ACCEPTANCE,
        COMMITMENT_COMPLETION,
    }
)
_MAX_RECORD_ID_CHARS: Final = 512
_LOCAL_ID_RE = re.compile(r"^[A-Za-z][A-Za-z0-9._-]{0,63}$")


def _record_id(value: object) -> str:
    if type(value) is not str or not value or len(value) > _MAX_RECORD_ID_CHARS:
        raise ValueError("record identity is invalid")
    if any(ord(char) < 33 or ord(char) > 126 or char in "/?#" for char in value):
        raise ValueError("record identity is invalid")
    return value


def _commitment_id(value: object) -> str:
    if type(value) is not str or _LOCAL_ID_RE.fullmatch(value) is None:
        raise ValueError("commitment id is invalid")
    return value


def _completion_route(path: str) -> tuple[str, str] | None:
    parts = path.split("/")
    if (
        len(parts) != 7
        or parts[:3] != ["", "api", "agreements"]
        or parts[4] != "commitments"
        or parts[6] != "completion-evidence"
    ):
        return None
    try:
        return _record_id(parts[3]), _commitment_id(parts[5])
    except ValueError:
        return None


def _publication_failure(
    exc: FulfillmentCompletionPublicationError,
) -> ApplicationHttpResponse:
    if exc.code == "FULFILLMENT_PUBLICATION_REQUEST_INVALID":
        return _bad_request(exc.code)
    if exc.code == "FULFILLMENT_PUBLICATION_AGREEMENT_NOT_FOUND":
        return _error_response(
            404,
            "Not Found",
            exc.code,
            "required Agreement was not found",
        )
    if exc.code in {
        "FULFILLMENT_PUBLICATION_AGREEMENT_UNAVAILABLE",
        "FULFILLMENT_PUBLICATION_WRITE_FAILED",
    }:
        return _error_response(
            503,
            "Service Unavailable",
            exc.code,
            "fulfillment completion publication did not complete safely",
        )
    if exc.code == "FULFILLMENT_PUBLICATION_BUILD_FAILED":
        return _error_response(
            409,
            "Conflict",
            exc.code,
            "fulfillment completion evidence could not be authored safely",
        )
    return _error_response(
        500,
        "Internal Server Error",
        exc.code,
        "fulfillment completion publication failed safely",
    )


class MarketplaceAuthenticatedFulfillmentCompletionHttpAdapter:
    """Publish one reviewed fulfillment event for the authenticated principal."""

    def __init__(
        self,
        *,
        base: MarketplaceAuthenticatedAgreementPublicationHttpAdapter,
        auth: MarketplaceApplicationAuthService,
        publication: MarketplaceFulfillmentCompletionPublicationService,
    ) -> None:
        if type(base) is not MarketplaceAuthenticatedAgreementPublicationHttpAdapter:
            raise TypeError(
                "base MUST be exact MarketplaceAuthenticatedAgreementPublicationHttpAdapter"
            )
        if type(auth) is not MarketplaceApplicationAuthService:
            raise TypeError("auth MUST be exact MarketplaceApplicationAuthService")
        if type(publication) is not MarketplaceFulfillmentCompletionPublicationService:
            raise TypeError(
                "publication MUST be exact MarketplaceFulfillmentCompletionPublicationService"
            )
        self._base = base
        self._auth = auth
        self._publication = publication

    def handle(
        self,
        request: ApplicationHttpRequest,
        *,
        session_token: bytes | None,
        session_invalid: bool,
        now: int,
    ) -> ApplicationHttpResponse:
        try:
            _validate_request(request)
        except ApplicationHttpError:
            return _bad_request()

        target = _completion_route(request.path)
        if target is None:
            return self._base.handle(
                request,
                session_token=session_token,
                session_invalid=session_invalid,
                now=now,
            )
        agreement_record_id, commitment_id = target

        if type(session_invalid) is not bool:
            raise TypeError("session_invalid MUST be exact bool")
        if type(now) is not int or isinstance(now, bool) or now < 0:
            raise ValueError("now MUST be a non-negative exact integer")
        if request.method != "POST":
            return _error_response(
                405,
                "Method Not Allowed",
                "METHOD_NOT_ALLOWED",
                "route does not accept this method",
                allow="POST",
            )
        if request.query:
            return _bad_request("QUERY_INVALID")
        if request.content_type != "application/json":
            return _error_response(
                415,
                "Unsupported Media Type",
                "UNSUPPORTED_MEDIA_TYPE",
                "application/json is required",
            )
        if session_invalid:
            return _auth_invalid()
        if session_token is None:
            return _auth_required()
        if type(session_token) is not bytes or len(session_token) != 32:
            return _auth_invalid()

        try:
            document = _decode_json_object_bytes(request.body)
        except (TypeError, ValueError):
            return _bad_request("FULFILLMENT_PUBLICATION_REQUEST_INVALID")
        if frozenset(document) != _REQUEST_FIELDS:
            return _bad_request("FULFILLMENT_PUBLICATION_REQUEST_INVALID")
        evidence_kind = document.get("evidence_kind")
        if type(evidence_kind) is not str or evidence_kind not in _EVIDENCE_KINDS:
            return _bad_request("FULFILLMENT_PUBLICATION_REQUEST_INVALID")

        try:
            session = self._auth.validate_session(
                session_token=session_token,
                now=now,
            )
        except ApplicationAuthError as exc:
            return _auth_error(exc)

        try:
            touched = self._auth.authenticate_session(
                session_token=session_token,
                now=now,
            )
        except ApplicationAuthError as exc:
            return _auth_error(exc)
        if (
            touched.principal != session.principal
            or touched.verification_method != session.verification_method
        ):
            return _auth_invalid()

        try:
            if evidence_kind == CLAIMED_COMPLETE_PERFORMANCE:
                result = self._publication.publish_claimed_complete_performance(
                    agreement_record_id=agreement_record_id,
                    commitment_id=commitment_id,
                    issuer=session.principal,
                )
            elif evidence_kind == COMMITMENT_ACCEPTANCE:
                result = self._publication.publish_commitment_acceptance(
                    agreement_record_id=agreement_record_id,
                    commitment_id=commitment_id,
                    issuer=session.principal,
                )
            else:
                result = self._publication.publish_commitment_completion(
                    agreement_record_id=agreement_record_id,
                    commitment_id=commitment_id,
                    issuer=session.principal,
                )
        except FulfillmentCompletionPublicationError as exc:
            return _publication_failure(exc)
        except Exception:
            return _error_response(
                500,
                "Internal Server Error",
                "FULFILLMENT_PUBLICATION_FAILED",
                "fulfillment completion publication failed safely",
            )

        if (
            type(result) is not FulfillmentEvidencePublicationResult
            or result.agreement_record_id != agreement_record_id
            or result.commitment_id != commitment_id
            or result.evidence_kind != evidence_kind
        ):
            return _error_response(
                500,
                "Internal Server Error",
                "FULFILLMENT_PUBLICATION_RESULT_INVALID",
                "fulfillment completion publication returned an invalid result",
            )

        status = 201 if result.disposition is StoreDisposition.STORED else 200
        reason = "Created" if status == 201 else "OK"
        return _json_response(status, reason, result.to_document())


__all__ = [
    "MarketplaceAuthenticatedFulfillmentCompletionHttpAdapter",
    "PROFILE_NAME",
]
