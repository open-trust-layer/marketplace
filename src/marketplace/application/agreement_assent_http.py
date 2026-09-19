"""Authenticated HTTP seam for Agreement assent preparation and signature intake."""
from __future__ import annotations

from typing import Any, Callable

from .agreement_assent_candidate import (
    AgreementAssentCandidateResolutionError,
    MarketplaceAgreementAssentCandidateResolutionService,
)
from .agreement_assent_workflow import (
    AgreementAssentWorkflowError,
    MarketplaceAgreementAssentWorkflowService,
)
from .auth import ApplicationAuthError, MarketplaceApplicationAuthService
from .auth_http import (
    MarketplaceAuthenticatedApplicationHttpAdapter,
    _auth_error,
    _auth_invalid,
    _auth_required,
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


SigningInputCarrierEncoder = Callable[[bytes], Any]
SignatureCarrierDecoder = Callable[[Any], bytes]

_PREPARATION_FIELDS = frozenset({"acceptance_record_id"})
_SUBMISSION_FIELDS = frozenset({"acceptance_record_id", "signature"})


def _record_id(value: object) -> str:
    if type(value) is not str or not value or len(value) > 512:
        raise ValueError("record identity is invalid")
    if any(ord(char) < 33 or ord(char) > 126 or char in "/?#" for char in value):
        raise ValueError("record identity is invalid")
    return value


def _assent_route(path: str) -> tuple[str, str] | None:
    parts = path.split("/")
    if (
        len(parts) == 6
        and parts[:3] == ["", "api", "agreements"]
        and parts[4:] == ["assent", "preparation"]
    ):
        try:
            return ("preparation", _record_id(parts[3]))
        except ValueError:
            return None
    if (
        len(parts) == 5
        and parts[:3] == ["", "api", "agreements"]
        and parts[4] == "assent"
    ):
        try:
            return ("submission", _record_id(parts[3]))
        except ValueError:
            return None
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
        "Agreement assent candidate preconditions are not satisfied",
    )


def _workflow_failure(
    exc: AgreementAssentWorkflowError,
    *,
    submission: bool,
) -> ApplicationHttpResponse:
    if submission and exc.code == "AGREEMENT_ASSENT_WORKFLOW_VERIFICATION_FAILED":
        return _error_response(
            400,
            "Bad Request",
            "AGREEMENT_ASSENT_SIGNATURE_REJECTED",
            "Agreement assent signature was rejected",
        )
    if submission and exc.code == "AGREEMENT_ASSENT_WORKFLOW_STORE_FAILED":
        return _error_response(
            503,
            "Service Unavailable",
            "AGREEMENT_ASSENT_COORDINATION_UNAVAILABLE",
            "Agreement assent coordination is unavailable",
        )
    return _error_response(
        409,
        "Conflict",
        exc.code,
        "Agreement assent preconditions are not satisfied",
    )


class MarketplaceAuthenticatedAgreementAssentHttpAdapter:
    """Add only reviewed Agreement-assent routes over an existing auth HTTP adapter."""

    def __init__(
        self,
        *,
        base: MarketplaceAuthenticatedApplicationHttpAdapter,
        auth: MarketplaceApplicationAuthService,
        candidate_resolution: MarketplaceAgreementAssentCandidateResolutionService,
        workflow: MarketplaceAgreementAssentWorkflowService,
        encode_signing_input: SigningInputCarrierEncoder,
        decode_signature: SignatureCarrierDecoder,
    ) -> None:
        if type(base) is not MarketplaceAuthenticatedApplicationHttpAdapter:
            raise TypeError(
                "base MUST be exact MarketplaceAuthenticatedApplicationHttpAdapter"
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
        if not callable(encode_signing_input):
            raise TypeError("encode_signing_input MUST be callable")
        if not callable(decode_signature):
            raise TypeError("decode_signature MUST be callable")
        self._base = base
        self._auth = auth
        self._candidate_resolution = candidate_resolution
        self._workflow = workflow
        self._encode_signing_input = encode_signing_input
        self._decode_signature = decode_signature

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
        route = _assent_route(request.path)
        if route is None:
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

        kind, proposal_id = route
        try:
            document = _decode_json_object_bytes(request.body)
        except (TypeError, ValueError):
            return _bad_request("AGREEMENT_ASSENT_REQUEST_INVALID")

        if kind == "preparation":
            return self._prepare(
                document,
                proposal_id=proposal_id,
                session_token=session_token,
                now=now,
            )
        return self._submit(
            document,
            proposal_id=proposal_id,
            session_token=session_token,
            now=now,
        )

    def _session(
        self,
        *,
        session_token: bytes,
        now: int,
        touch: bool,
    ):
        try:
            if touch:
                return self._auth.authenticate_session(
                    session_token=session_token,
                    now=now,
                )
            return self._auth.validate_session(
                session_token=session_token,
                now=now,
            )
        except ApplicationAuthError as exc:
            return _auth_error(exc)

    def _candidate(
        self,
        *,
        proposal_id: str,
        acceptance_id: str,
    ):
        try:
            return self._candidate_resolution.resolve(
                proposal_record_id=proposal_id,
                acceptance_record_id=acceptance_id,
            )
        except AgreementAssentCandidateResolutionError as exc:
            return _candidate_failure(exc)

    def _prepare(
        self,
        document: dict[str, Any],
        *,
        proposal_id: str,
        session_token: bytes,
        now: int,
    ) -> ApplicationHttpResponse:
        if frozenset(document) != _PREPARATION_FIELDS:
            return _bad_request("AGREEMENT_ASSENT_REQUEST_INVALID")
        try:
            acceptance_id = _record_id(document["acceptance_record_id"])
        except (KeyError, ValueError):
            return _bad_request("AGREEMENT_ASSENT_REQUEST_INVALID")

        session = self._session(
            session_token=session_token,
            now=now,
            touch=False,
        )
        if type(session) is ApplicationHttpResponse:
            return session
        candidate = self._candidate(
            proposal_id=proposal_id,
            acceptance_id=acceptance_id,
        )
        if type(candidate) is ApplicationHttpResponse:
            return candidate

        try:
            preparation = self._workflow.prepare(
                candidate=candidate,
                principal=session.principal,
                verification_method=session.verification_method,
                at_time=now,
            )
            carrier = self._encode_signing_input(preparation.signing_input)
            return _json_response(
                200,
                "OK",
                {
                    "agreement_record_id": preparation.agreement_record_id,
                    "proof_input": carrier,
                    "verification_method": preparation.verification_method,
                },
            )
        except AgreementAssentWorkflowError as exc:
            return _workflow_failure(exc, submission=False)
        except Exception:
            return _error_response(
                500,
                "Internal Server Error",
                "AGREEMENT_ASSENT_PREPARATION_FAILED",
                "Agreement assent preparation could not be encoded safely",
            )

    def _submit(
        self,
        document: dict[str, Any],
        *,
        proposal_id: str,
        session_token: bytes,
        now: int,
    ) -> ApplicationHttpResponse:
        if frozenset(document) != _SUBMISSION_FIELDS:
            return _bad_request("AGREEMENT_ASSENT_REQUEST_INVALID")
        try:
            acceptance_id = _record_id(document["acceptance_record_id"])
            signature = self._decode_signature(document["signature"])
        except Exception:
            return _bad_request("AGREEMENT_ASSENT_REQUEST_INVALID")
        if type(signature) is not bytes or len(signature) != 64:
            return _bad_request("AGREEMENT_ASSENT_REQUEST_INVALID")

        session = self._session(
            session_token=session_token,
            now=now,
            touch=True,
        )
        if type(session) is ApplicationHttpResponse:
            return session
        candidate = self._candidate(
            proposal_id=proposal_id,
            acceptance_id=acceptance_id,
        )
        if type(candidate) is ApplicationHttpResponse:
            return candidate

        try:
            preparation = self._workflow.prepare(
                candidate=candidate,
                principal=session.principal,
                verification_method=session.verification_method,
                at_time=now,
            )
            result = self._workflow.submit(
                candidate=candidate,
                preparation=preparation,
                signature=signature,
                at_time=now,
            )
        except AgreementAssentWorkflowError as exc:
            return _workflow_failure(exc, submission=True)
        except Exception:
            return _error_response(
                500,
                "Internal Server Error",
                "AGREEMENT_ASSENT_SUBMISSION_FAILED",
                "Agreement assent submission could not complete safely",
            )

        status = (
            201
            if result.disposition is StoreDisposition.STORED
            else 200
        )
        reason = "Created" if status == 201 else "OK"
        return _json_response(
            status,
            reason,
            {
                "accepted_at": result.accepted_at,
                "agreement_record_id": result.agreement_record_id,
                "authorizes_side_effects": False,
                "disposition": result.disposition.value,
                "expires_at": result.expires_at,
                "publishes_agreement": False,
            },
        )


__all__ = [
    "MarketplaceAuthenticatedAgreementAssentHttpAdapter",
    "SignatureCarrierDecoder",
    "SigningInputCarrierEncoder",
]
