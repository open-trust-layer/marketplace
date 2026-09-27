"""Authenticated HTTP seam for publishing one already-formed Agreement."""
from __future__ import annotations

from typing import Any

from .agreement_assent_candidate import (
    AgreementAssentCandidateResolutionError,
    MarketplaceAgreementAssentCandidateResolutionService,
)
from .agreement_assent_http import MarketplaceAuthenticatedAgreementAssentHttpAdapter
from .agreement_assent_workflow import (
    AgreementAssentWorkflowError,
    MarketplaceAgreementAssentWorkflowService,
)
from .agreement_publication import (
    AgreementPublicationPreflightError,
    AgreementPublicationPreflightResult,
    MarketplaceAgreementPublicationPreflightService,
)
from .agreement_publication_write import (
    AgreementPublicationResult,
    AgreementPublicationWriteError,
    MarketplaceAgreementPublicationService,
)
from .auth import ApplicationAuthError, MarketplaceApplicationAuthService
from .auth_http import _auth_error, _auth_invalid, _auth_required
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


_PUBLICATION_FIELDS = frozenset({"acceptance_record_id"})


def _record_id(value: object) -> str:
    if type(value) is not str or not value or len(value) > 512:
        raise ValueError("record identity is invalid")
    if any(ord(char) < 33 or ord(char) > 126 or char in "/?#" for char in value):
        raise ValueError("record identity is invalid")
    return value


def _publication_route(path: str) -> str | None:
    parts = path.split("/")
    if len(parts) != 4 or parts[:3] != ["", "api", "agreements"]:
        return None
    try:
        return _record_id(parts[3])
    except ValueError:
        return None


def _candidate_failure(
    exc: AgreementAssentCandidateResolutionError,
) -> ApplicationHttpResponse:
    if exc.code == "AGREEMENT_ASSENT_CANDIDATE_PROPOSAL_NOT_FOUND":
        return _error_response(
            404,
            "Not Found",
            exc.code,
            "required Proposal was not found",
        )
    if exc.code == "AGREEMENT_ASSENT_CANDIDATE_PROPOSAL_UNAVAILABLE":
        return _error_response(
            503,
            "Service Unavailable",
            exc.code,
            "required Marketplace state is unavailable",
        )
    return _error_response(
        409,
        "Conflict",
        exc.code,
        "Agreement publication source preconditions are not satisfied",
    )


def _preflight_negative(
    result: AgreementPublicationPreflightResult,
) -> ApplicationHttpResponse:
    if result.reason == "ACTOR_NOT_AGREEMENT_PARTY":
        return _error_response(
            403,
            "Forbidden",
            "AGREEMENT_PUBLICATION_PARTY_REQUIRED",
            "authenticated principal is not an Agreement party",
        )
    if result.reason == "ACTOR_ASSENT_NOT_COVERED":
        return _error_response(
            409,
            "Conflict",
            "AGREEMENT_PUBLICATION_ASSENT_REQUIRED",
            "authenticated principal assent is not covered",
        )
    if result.reason == "FORMATION_EVIDENCE_INCOMPLETE":
        return _error_response(
            409,
            "Conflict",
            "AGREEMENT_PUBLICATION_FORMATION_INCOMPLETE",
            "Agreement formation evidence is incomplete",
        )
    return _error_response(
        409,
        "Conflict",
        "AGREEMENT_PUBLICATION_PREFLIGHT_NOT_SATISFIED",
        "Agreement publication preconditions are not satisfied",
    )


class MarketplaceAuthenticatedAgreementPublicationHttpAdapter:
    """Publish one exact formed Agreement through reviewed application services."""

    def __init__(
        self,
        *,
        base: MarketplaceAuthenticatedAgreementAssentHttpAdapter,
        auth: MarketplaceApplicationAuthService,
        candidate_resolution: MarketplaceAgreementAssentCandidateResolutionService,
        workflow: MarketplaceAgreementAssentWorkflowService,
        preflight: MarketplaceAgreementPublicationPreflightService,
        publication: MarketplaceAgreementPublicationService,
    ) -> None:
        if type(base) is not MarketplaceAuthenticatedAgreementAssentHttpAdapter:
            raise TypeError(
                "base MUST be exact MarketplaceAuthenticatedAgreementAssentHttpAdapter"
            )
        if type(auth) is not MarketplaceApplicationAuthService:
            raise TypeError("auth MUST be exact MarketplaceApplicationAuthService")
        if (
            type(candidate_resolution)
            is not MarketplaceAgreementAssentCandidateResolutionService
        ):
            raise TypeError(
                "candidate_resolution MUST be exact Agreement assent candidate resolver"
            )
        if type(workflow) is not MarketplaceAgreementAssentWorkflowService:
            raise TypeError(
                "workflow MUST be exact MarketplaceAgreementAssentWorkflowService"
            )
        if type(preflight) is not MarketplaceAgreementPublicationPreflightService:
            raise TypeError(
                "preflight MUST be exact MarketplaceAgreementPublicationPreflightService"
            )
        if type(publication) is not MarketplaceAgreementPublicationService:
            raise TypeError(
                "publication MUST be exact MarketplaceAgreementPublicationService"
            )
        self._base = base
        self._auth = auth
        self._candidate_resolution = candidate_resolution
        self._workflow = workflow
        self._preflight = preflight
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

        proposal_id = _publication_route(request.path)
        if proposal_id is None:
            return self._base.handle(
                request,
                session_token=session_token,
                session_invalid=session_invalid,
                now=now,
            )

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
            return _bad_request("AGREEMENT_PUBLICATION_REQUEST_INVALID")
        if frozenset(document) != _PUBLICATION_FIELDS:
            return _bad_request("AGREEMENT_PUBLICATION_REQUEST_INVALID")
        try:
            acceptance_id = _record_id(document["acceptance_record_id"])
        except (KeyError, ValueError):
            return _bad_request("AGREEMENT_PUBLICATION_REQUEST_INVALID")

        try:
            session = self._auth.validate_session(
                session_token=session_token,
                now=now,
            )
        except ApplicationAuthError as exc:
            return _auth_error(exc)

        try:
            candidate = self._candidate_resolution.resolve(
                proposal_record_id=proposal_id,
                acceptance_record_id=acceptance_id,
            )
        except AgreementAssentCandidateResolutionError as exc:
            return _candidate_failure(exc)

        try:
            formation = self._workflow.formation_status(
                candidate=candidate,
                at_time=now,
            )
        except AgreementAssentWorkflowError as exc:
            return _error_response(
                409,
                "Conflict",
                exc.code,
                "Agreement formation could not be established safely",
            )
        except Exception:
            return _error_response(
                500,
                "Internal Server Error",
                "AGREEMENT_PUBLICATION_FORMATION_FAILED",
                "Agreement formation could not be established safely",
            )

        try:
            preflight = self._preflight.review(
                candidate=candidate,
                formation=formation,
                actor_principal=session.principal,
            )
        except AgreementPublicationPreflightError as exc:
            return _error_response(
                409,
                "Conflict",
                exc.code,
                "Agreement publication preflight failed",
            )
        except Exception:
            return _error_response(
                500,
                "Internal Server Error",
                "AGREEMENT_PUBLICATION_PREFLIGHT_FAILED",
                "Agreement publication preflight failed safely",
            )

        if (
            type(preflight) is not AgreementPublicationPreflightResult
            or preflight.agreement_record_id != candidate.record_id
        ):
            return _error_response(
                500,
                "Internal Server Error",
                "AGREEMENT_PUBLICATION_PREFLIGHT_INVALID",
                "Agreement publication preflight returned an invalid result",
            )
        if not preflight.preconditions_satisfied:
            return _preflight_negative(preflight)
        if (
            preflight.reason != "PRECONDITIONS_SATISFIED"
            or preflight.formation_evidence != "EVIDENCE_SUFFICIENT_FOR_PROFILE"
            or preflight.actor_principal != session.principal
        ):
            return _error_response(
                409,
                "Conflict",
                "AGREEMENT_PUBLICATION_PREFLIGHT_NOT_SATISFIED",
                "Agreement publication preconditions are not satisfied",
            )

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
            result = self._publication.publish(
                candidate=candidate,
                preflight=preflight,
            )
        except AgreementPublicationWriteError as exc:
            return _error_response(
                503,
                "Service Unavailable",
                exc.code,
                "Agreement publication did not complete safely",
            )
        except Exception:
            return _error_response(
                500,
                "Internal Server Error",
                "AGREEMENT_PUBLICATION_FAILED",
                "Agreement publication did not complete safely",
            )

        if (
            type(result) is not AgreementPublicationResult
            or result.record_id != candidate.record_id
        ):
            return _error_response(
                500,
                "Internal Server Error",
                "AGREEMENT_PUBLICATION_RESULT_INVALID",
                "Agreement publication returned an invalid result",
            )

        status = 201 if result.disposition is StoreDisposition.STORED else 200
        reason = "Created" if status == 201 else "OK"
        return _json_response(
            status,
            reason,
            {
                "agreement_record_id": result.record_id,
                "disposition": result.disposition.value,
                "change_seq": result.change_seq,
            },
        )


__all__ = [
    "MarketplaceAuthenticatedAgreementPublicationHttpAdapter",
]
