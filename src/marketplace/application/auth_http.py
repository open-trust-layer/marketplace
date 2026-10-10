"""Authenticated HTTP routing for reviewed Marketplace reads and writes."""
from __future__ import annotations

from typing import Any, Callable

from .api import ApplicationApiError
from .auth import (
    ApplicationAuthError,
    AuthenticatedProductListingAuthoringService,
    AuthenticatedProposalAcceptanceAuthoringService,
    AuthenticatedProposalAuthoringService,
    MarketplaceApplicationAuthService,
)
from .authoring import ProductListingAuthoringError
from .http import (
    ApplicationHttpRequest,
    ApplicationHttpResponse,
    MarketplaceApplicationHttpAdapter,
    _application_failure,
    _bad_request,
    _decode_json_object_bytes,
    _error_response,
    _json_response,
    _product_listing_fields,
    _proposal_draft,
    _proposal_parent_path,
    _put_document,
    _response_parent_path,
)
from .proposal_acceptance import (
    ProposalAcceptanceAuthoringError,
    ProposalAcceptancePublicationResult,
)
from .proposal_authoring import ProposalAuthoringError
from .proposal_acceptance_resolution import (
    MarketplaceProposalAcceptanceResolutionService,
    ProposalAcceptanceResolutionError,
    ProposalAcceptanceResolutionResult,
)


RecordPrincipalExtractor = Callable[[Any], str]
RecordJsonDecoder = Callable[[bytes], Any]
RawIntentCreator = Callable[[Any], Any]
RawResponseCreator = Callable[[str, Any], Any]


def _auth_error(exc: ApplicationAuthError) -> ApplicationHttpResponse:
    if exc.code == "AUTH_PRINCIPAL_MISMATCH":
        return _error_response(
            403,
            "Forbidden",
            "AUTH_PRINCIPAL_MISMATCH",
            "authenticated session principal does not match the write issuer",
        )
    return _error_response(
        401,
        "Unauthorized",
        "AUTH_SESSION_INVALID",
        "application session is invalid",
    )


def _auth_required() -> ApplicationHttpResponse:
    return _error_response(
        401,
        "Unauthorized",
        "AUTH_REQUIRED",
        "application authentication is required",
    )


def _auth_invalid() -> ApplicationHttpResponse:
    return _error_response(
        401,
        "Unauthorized",
        "AUTH_SESSION_INVALID",
        "application session is invalid",
    )


def _acceptance_proposal_path(path: str) -> str | None:
    parts = path.split("/")
    if len(parts) != 5 or parts[:3] != ["", "api", "intents"] or parts[4] != "acceptance":
        return None
    record_id = parts[3]
    if not record_id or len(record_id) > 512:
        return None
    if any(ord(char) < 33 or ord(char) > 126 or char in "/?#" for char in record_id):
        return None
    return record_id

def _protected_read(request: ApplicationHttpRequest) -> tuple[str, str | None] | None:
    if request.method != "GET":
        return None
    acceptance_proposal = _acceptance_proposal_path(request.path)
    if acceptance_proposal is not None:
        return ("acceptance_resolution", acceptance_proposal)
    return None


def _protected_write(request: ApplicationHttpRequest) -> tuple[str, str | None] | None:
    if request.method != "POST":
        return None
    if request.path == "/api/intents":
        return ("intent", None)
    if request.path == "/api/product-listings":
        return ("listing", None)
    acceptance_proposal = _acceptance_proposal_path(request.path)
    if acceptance_proposal is not None:
        return ("acceptance", acceptance_proposal)
    proposal_parent = _proposal_parent_path(request.path)
    if proposal_parent is not None:
        return ("proposal", proposal_parent)
    response_parent = _response_parent_path(request.path)
    if response_parent is not None:
        return ("response", response_parent)
    return None


class MarketplaceAuthenticatedApplicationHttpAdapter:
    """Protect reviewed authenticated routes with one request-lifetime session token."""

    def __init__(
        self,
        *,
        base: MarketplaceApplicationHttpAdapter,
        auth: MarketplaceApplicationAuthService,
        product_listing_authoring: AuthenticatedProductListingAuthoringService,
        proposal_authoring: AuthenticatedProposalAuthoringService,
        proposal_acceptance_authoring: AuthenticatedProposalAcceptanceAuthoringService | None = None,
        proposal_acceptance_resolution: MarketplaceProposalAcceptanceResolutionService | None = None,
        decode_record_json: RecordJsonDecoder,
        create_intent: RawIntentCreator,
        respond_to_intent: RawResponseCreator,
        record_principal: RecordPrincipalExtractor,
    ) -> None:
        if type(base) is not MarketplaceApplicationHttpAdapter:
            raise TypeError("base MUST be exact MarketplaceApplicationHttpAdapter")
        if type(auth) is not MarketplaceApplicationAuthService:
            raise TypeError("auth MUST be exact MarketplaceApplicationAuthService")
        if type(product_listing_authoring) is not AuthenticatedProductListingAuthoringService:
            raise TypeError("product_listing_authoring MUST be exact authenticated authoring service")
        if type(proposal_authoring) is not AuthenticatedProposalAuthoringService:
            raise TypeError("proposal_authoring MUST be exact authenticated proposal service")
        if (
            proposal_acceptance_authoring is not None
            and type(proposal_acceptance_authoring) is not AuthenticatedProposalAcceptanceAuthoringService
        ):
            raise TypeError("proposal_acceptance_authoring MUST be exact authenticated acceptance service when supplied")
        if (
            proposal_acceptance_resolution is not None
            and type(proposal_acceptance_resolution) is not MarketplaceProposalAcceptanceResolutionService
        ):
            raise TypeError("proposal_acceptance_resolution MUST be exact acceptance resolution service when supplied")
        if not callable(decode_record_json):
            raise TypeError("decode_record_json MUST be callable")
        if not callable(create_intent):
            raise TypeError("create_intent MUST be callable")
        if not callable(respond_to_intent):
            raise TypeError("respond_to_intent MUST be callable")
        if not callable(record_principal):
            raise TypeError("record_principal MUST be callable")
        self._base = base
        self._auth = auth
        self._product_listing_authoring = product_listing_authoring
        self._proposal_authoring = proposal_authoring
        self._proposal_acceptance_authoring = proposal_acceptance_authoring
        self._proposal_acceptance_resolution = proposal_acceptance_resolution
        self._decode_record_json = decode_record_json
        self._create_intent = create_intent
        self._respond_to_intent = respond_to_intent
        self._record_principal = record_principal

    def handle(
        self,
        request: ApplicationHttpRequest,
        *,
        session_token: bytes | None,
        session_invalid: bool,
        now: int,
    ) -> ApplicationHttpResponse:
        if type(session_invalid) is not bool:
            raise TypeError("session_invalid MUST be exact bool")
        if type(now) is not int or now < 0:
            raise ValueError("now MUST be a non-negative exact integer")
        protected = _protected_write(request)
        if protected is None:
            protected = _protected_read(request)
        if protected is None:
            if session_invalid or session_token is not None:
                return _auth_invalid()
            return self._base.handle(request)
        if session_invalid:
            return _auth_invalid()
        if session_token is None:
            return _auth_required()
        if type(session_token) is not bytes or len(session_token) != 32:
            return _auth_invalid()
        try:
            session = self._auth.validate_session(session_token=session_token, now=now)
        except ApplicationAuthError as exc:
            return _auth_error(exc)
        kind, parent_id = protected
        if kind == "listing":
            return self._product_listing(request, session_token=session_token, now=now)
        if kind == "proposal":
            return self._proposal(
                request,
                parent_id=parent_id,
                session_token=session_token,
                now=now,
            )
        if kind == "acceptance":
            return self._proposal_acceptance(
                request,
                proposal_id=parent_id,
                session_token=session_token,
                now=now,
            )
        if kind == "acceptance_resolution":
            return self._proposal_acceptance_resolution_response(
                request,
                proposal_id=parent_id,
                principal=session.principal,
            )
        if kind == "intent":
            return self._raw_intent(request, session_token=session_token, now=now)
        if kind == "response":
            return self._raw_response(
                request,
                parent_id=parent_id,
                session_token=session_token,
                now=now,
            )
        return _auth_invalid()

    def _product_listing(
        self,
        request: ApplicationHttpRequest,
        *,
        session_token: bytes,
        now: int,
    ) -> ApplicationHttpResponse:
        if request.query:
            return _bad_request("QUERY_INVALID")
        if request.content_type != "application/json":
            return _error_response(
                415,
                "Unsupported Media Type",
                "UNSUPPORTED_MEDIA_TYPE",
                "application/json is required",
            )
        try:
            document = _decode_json_object_bytes(request.body)
            fields = _product_listing_fields(document)
        except (TypeError, ValueError):
            return _bad_request("PRODUCT_LISTING_REQUEST_INVALID")
        try:
            result = self._product_listing_authoring.create_product_listing(
                session_token=session_token,
                fields=fields,
                now=now,
            )
            return _json_response(201, "Created", _put_document(result))
        except ApplicationAuthError as exc:
            return _auth_error(exc)
        except ProductListingAuthoringError as exc:
            if exc.code == "PRODUCT_LISTING_FIELDS_INVALID":
                return _error_response(400, "Bad Request", exc.code, "structured product-listing fields are invalid")
            if exc.code == "PRODUCT_LISTING_BUILD_FAILED":
                return _error_response(500, "Internal Server Error", exc.code, "product listing record could not be built")
            return _error_response(500, "Internal Server Error", "PRODUCT_LISTING_AUTHORING_FAILED", "product listing could not be authored safely")
        except ApplicationApiError as exc:
            return _application_failure(exc)
        except Exception:
            return _error_response(500, "Internal Server Error", "PRODUCT_LISTING_AUTHORING_FAILED", "product listing could not be authored safely")

    def _proposal(
        self,
        request: ApplicationHttpRequest,
        *,
        parent_id: str | None,
        session_token: bytes,
        now: int,
    ) -> ApplicationHttpResponse:
        if type(parent_id) is not str or not parent_id:
            return _bad_request()
        if request.query:
            return _bad_request("QUERY_INVALID")
        if request.content_type != "application/json":
            return _error_response(415, "Unsupported Media Type", "UNSUPPORTED_MEDIA_TYPE", "application/json is required")
        try:
            document = _decode_json_object_bytes(request.body)
            draft = _proposal_draft(document, parent_id)
        except (TypeError, ValueError):
            return _bad_request("PROPOSAL_REQUEST_INVALID")
        try:
            result = self._proposal_authoring.create_buyer_request_proposal(
                session_token=session_token,
                draft=draft,
                now=now,
            )
            return _json_response(201, "Created", _put_document(result))
        except ApplicationAuthError as exc:
            return _auth_error(exc)
        except ProposalAuthoringError as exc:
            if exc.code == "PROPOSAL_DRAFT_INVALID":
                return _error_response(400, "Bad Request", exc.code, "structured Proposal draft is invalid")
            if exc.code == "PROPOSAL_BUILD_FAILED":
                return _error_response(
                    500,
                    "Internal Server Error",
                    exc.code,
                    "Proposal record could not be built",
                )
            return _error_response(
                500,
                "Internal Server Error",
                "PROPOSAL_AUTHORING_FAILED",
                "Proposal could not be authored safely",
            )
        except ApplicationApiError as exc:
            return _application_failure(exc)
        except Exception:
            return _error_response(
                500,
                "Internal Server Error",
                "PROPOSAL_AUTHORING_FAILED",
                "Proposal could not be authored safely",
            )

    def _proposal_acceptance(
        self,
        request: ApplicationHttpRequest,
        *,
        proposal_id: str | None,
        session_token: bytes,
        now: int,
    ) -> ApplicationHttpResponse:
        if type(proposal_id) is not str or not proposal_id:
            return _bad_request()
        if request.query or request.body != b"" or request.content_type is not None:
            return _bad_request("PROPOSAL_ACCEPTANCE_REQUEST_INVALID")
        if self._proposal_acceptance_authoring is None:
            return _error_response(
                503,
                "Service Unavailable",
                "PROPOSAL_ACCEPTANCE_UNAVAILABLE",
                "seller Proposal acceptance is not configured",
            )
        try:
            result = self._proposal_acceptance_authoring.accept_proposal(
                session_token=session_token,
                proposal_record_id=proposal_id,
                now=now,
            )
        except ApplicationAuthError as exc:
            return _auth_error(exc)
        except ProposalAcceptanceAuthoringError as exc:
            if exc.code == "PROPOSAL_ACCEPTANCE_SELLER_MISMATCH":
                return _error_response(
                    403,
                    "Forbidden",
                    exc.code,
                    "authenticated seller does not own the Proposal parent listing",
                )
            if exc.code in {
                "PROPOSAL_ACCEPTANCE_PROPOSAL_NOT_FOUND",
                "PROPOSAL_ACCEPTANCE_LISTING_NOT_FOUND",
            }:
                return _error_response(404, "Not Found", exc.code, "required Marketplace record was not found")
            if exc.code in {
                "PROPOSAL_ACCEPTANCE_PROPOSAL_UNAVAILABLE",
                "PROPOSAL_ACCEPTANCE_LISTING_UNAVAILABLE",
            }:
                return _error_response(503, "Service Unavailable", exc.code, "required Marketplace state is unavailable")
            if exc.code in {
                "PROPOSAL_ACCEPTANCE_REQUEST_INVALID",
                "PROPOSAL_ACCEPTANCE_PROPOSAL_INVALID",
                "PROPOSAL_ACCEPTANCE_PARENT_INVALID",
                "PROPOSAL_ACCEPTANCE_LISTING_INVALID",
            }:
                return _error_response(409, "Conflict", exc.code, "Proposal acceptance preconditions are not satisfied")
            return _error_response(
                500,
                "Internal Server Error",
                "PROPOSAL_ACCEPTANCE_FAILED",
                "seller Proposal acceptance could not be published safely",
            )
        if type(result) is not ProposalAcceptancePublicationResult:
            return _error_response(
                500,
                "Internal Server Error",
                "PROPOSAL_ACCEPTANCE_RESULT_INVALID",
                "seller Proposal acceptance returned an invalid result",
            )
        return _json_response(201, "Created", result.to_document())
    def _proposal_acceptance_resolution_response(
        self,
        request: ApplicationHttpRequest,
        *,
        proposal_id: str | None,
        principal: str,
    ) -> ApplicationHttpResponse:
        if type(proposal_id) is not str or not proposal_id:
            return _bad_request()
        if request.query or request.body != b"" or request.content_type is not None:
            return _bad_request("PROPOSAL_ACCEPTANCE_RESOLUTION_REQUEST_INVALID")
        if self._proposal_acceptance_resolution is None:
            return _error_response(
                503,
                "Service Unavailable",
                "PROPOSAL_ACCEPTANCE_RESOLUTION_UNAVAILABLE",
                "Proposal acceptance resolution is not configured",
            )
        try:
            result = self._proposal_acceptance_resolution.resolve(
                principal=principal,
                proposal_record_id=proposal_id,
            )
        except ProposalAcceptanceResolutionError as exc:
            if exc.code == "PROPOSAL_ACCEPTANCE_RESOLUTION_PARTY_REQUIRED":
                return _error_response(
                    403,
                    "Forbidden",
                    exc.code,
                    "authenticated principal is not a Proposal party",
                )
            if exc.code in {
                "PROPOSAL_ACCEPTANCE_RESOLUTION_PROPOSAL_NOT_FOUND",
                "PROPOSAL_ACCEPTANCE_RESOLUTION_LISTING_NOT_FOUND",
                "PROPOSAL_ACCEPTANCE_RESOLUTION_NOT_FOUND",
            }:
                return _error_response(
                    404,
                    "Not Found",
                    exc.code,
                    "required Proposal acceptance evidence was not found",
                )
            if exc.code == "PROPOSAL_ACCEPTANCE_RESOLUTION_STATE_UNAVAILABLE":
                return _error_response(
                    503,
                    "Service Unavailable",
                    exc.code,
                    "required Marketplace state is unavailable",
                )
            if exc.code in {
                "PROPOSAL_ACCEPTANCE_RESOLUTION_REQUEST_INVALID",
                "PROPOSAL_ACCEPTANCE_RESOLUTION_PROPOSAL_INVALID",
                "PROPOSAL_ACCEPTANCE_RESOLUTION_PARENT_INVALID",
                "PROPOSAL_ACCEPTANCE_RESOLUTION_LISTING_INVALID",
                "PROPOSAL_ACCEPTANCE_RESOLUTION_DERIVATION_FAILED",
                "PROPOSAL_ACCEPTANCE_RESOLUTION_ACCEPTANCE_INVALID",
            }:
                return _error_response(
                    409,
                    "Conflict",
                    exc.code,
                    "Proposal acceptance resolution preconditions are not satisfied",
                )
            return _error_response(
                500,
                "Internal Server Error",
                "PROPOSAL_ACCEPTANCE_RESOLUTION_FAILED",
                "Proposal acceptance could not be resolved safely",
            )
        if type(result) is not ProposalAcceptanceResolutionResult:
            return _error_response(
                500,
                "Internal Server Error",
                "PROPOSAL_ACCEPTANCE_RESOLUTION_RESULT_INVALID",
                "Proposal acceptance resolution returned an invalid result",
            )
        return _json_response(200, "OK", result.to_document())

    def _authorize_raw_record(
        self,
        record: Any,
        *,
        session_token: bytes,
        now: int,
    ) -> ApplicationHttpResponse | None:
        try:
            principal = self._record_principal(record)
        except Exception:
            return _error_response(
                403,
                "Forbidden",
                "AUTH_PRINCIPAL_MISMATCH",
                "authenticated session principal does not match the write issuer",
            )
        if type(principal) is not str or not principal:
            return _error_response(
                403,
                "Forbidden",
                "AUTH_PRINCIPAL_MISMATCH",
                "authenticated session principal does not match the write issuer",
            )
        try:
            self._auth.authorize_principal(
                session_token=session_token,
                claimed_principal=principal,
                now=now,
            )
        except ApplicationAuthError as exc:
            return _auth_error(exc)
        return None

    def _raw_intent(
        self,
        request: ApplicationHttpRequest,
        *,
        session_token: bytes,
        now: int,
    ) -> ApplicationHttpResponse:
        if request.query:
            return _bad_request("QUERY_INVALID")
        if request.content_type != "application/json":
            return _error_response(
                415,
                "Unsupported Media Type",
                "UNSUPPORTED_MEDIA_TYPE",
                "application/json is required",
            )
        try:
            _decode_json_object_bytes(request.body)
            record = self._decode_record_json(request.body)
        except Exception:
            return _bad_request("INVALID_JSON_BODY")
        denied = self._authorize_raw_record(
            record,
            session_token=session_token,
            now=now,
        )
        if denied is not None:
            return denied
        try:
            return _json_response(201, "Created", _put_document(self._create_intent(record)))
        except ApplicationApiError as exc:
            return _application_failure(exc)
        except Exception:
            return _error_response(500, "Internal Server Error", "APPLICATION_API_FAILED", "application API could not complete safely")

    def _raw_response(
        self,
        request: ApplicationHttpRequest,
        *,
        parent_id: str | None,
        session_token: bytes,
        now: int,
    ) -> ApplicationHttpResponse:
        if type(parent_id) is not str or not parent_id:
            return _bad_request()
        if request.query:
            return _bad_request("QUERY_INVALID")
        if request.content_type != "application/json":
            return _error_response(
                415,
                "Unsupported Media Type",
                "UNSUPPORTED_MEDIA_TYPE",
                "application/json is required",
            )
        try:
            _decode_json_object_bytes(request.body)
            record = self._decode_record_json(request.body)
        except Exception:
            return _bad_request("INVALID_JSON_BODY")
        denied = self._authorize_raw_record(
            record,
            session_token=session_token,
            now=now,
        )
        if denied is not None:
            return denied
        try:
            return _json_response(201, "Created", _put_document(self._respond_to_intent(parent_id, record)))
        except ApplicationApiError as exc:
            return _application_failure(exc)
        except Exception:
            return _error_response(500, "Internal Server Error", "APPLICATION_API_FAILED", "application API could not complete safely")


__all__ = [
    "MarketplaceAuthenticatedApplicationHttpAdapter",
    "RawIntentCreator",
    "RawResponseCreator",
    "RecordJsonDecoder",
    "RecordPrincipalExtractor",
]
