from __future__ import annotations

import json
import unittest

from marketplace.application.api import IntentIndexPage
from marketplace.application.auth_http_composition import (
    PROFILE_NAME,
    MarketplaceAuthenticatedHttpCompositionError,
    compose_marketplace_authenticated_http,
)
from marketplace.application.auth_static_composition import (
    compose_marketplace_static_authentication,
)
from marketplace.application.composition import compose_marketplace_application
from marketplace.application.http import ApplicationHttpRequest
from marketplace.application.postgres_state import (
    ApplicationStatePutResult,
    ExpiryResult,
    PreparedApplicationRecord,
    StoreDisposition,
    SyncPage,
)
from tests.test_m17_5o_auth_static_composition import (
    ALT_AUTH_PRIVATE_BYTES,
    AT_TIME,
    AUTH_PRIVATE_BYTES,
    CHALLENGE,
    METHOD,
    OTHER_PRINCIPAL,
    PRINCIPAL,
    SESSION_TOKEN,
    _inputs,
    _private,
    _proof_document,
)


class MemoryStore:
    def __init__(self) -> None:
        self.puts: list[PreparedApplicationRecord] = []

    def initialize(self) -> ExpiryResult:
        return ExpiryResult((), ())

    def put(self, prepared: PreparedApplicationRecord) -> ApplicationStatePutResult:
        self.puts.append(prepared)
        return ApplicationStatePutResult(StoreDisposition.STORED, len(self.puts))

    def get(self, record_id: str) -> PreparedApplicationRecord | None:
        return None

    def peek(self, record_id: str) -> PreparedApplicationRecord | None:
        return None

    def list_response_ids(
        self,
        parent_record_id: str,
        *,
        limit: int,
    ) -> tuple[str, ...]:
        return ()

    def sync_since(self, cursor_value: int, *, limit: int) -> SyncPage:
        return SyncPage((), cursor_value, False)

    def sync_watermark(self) -> int:
        return len(self.puts)


class StaticIntentQuery:
    def list_intent_ids(
        self,
        *,
        cursor: str | None,
        limit: int,
    ) -> IntentIndexPage:
        return IntentIndexPage((), None)


class DeterministicMaterialSource:
    def __init__(self) -> None:
        self.challenge_calls = 0
        self.session_calls = 0

    def challenge_bytes(self) -> bytes:
        self.challenge_calls += 1
        return CHALLENGE

    def session_token_bytes(self) -> bytes:
        self.session_calls += 1
        return SESSION_TOKEN


class FailingMaterialSource(DeterministicMaterialSource):
    def challenge_bytes(self) -> bytes:
        self.challenge_calls += 1
        raise RuntimeError("synthetic material failure")


def _decode_json(body: bytes):
    return json.loads(body.decode("utf-8"))


def _encode_json(record: object) -> bytes:
    return json.dumps(
        record,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _prepare_record(record: object) -> PreparedApplicationRecord:
    if type(record) is not dict:
        raise TypeError("test record must be object")
    record_id = record.get("id")
    if type(record_id) is not str or not record_id:
        raise ValueError("test record id required")
    response_to = record.get("response_to", ())
    if type(response_to) is list:
        response_to = tuple(response_to)
    return PreparedApplicationRecord(
        record_id=record_id,
        canonical_record=_encode_json(record),
        response_to=response_to,
    )


def _application():
    store = MemoryStore()
    application = compose_marketplace_application(
        store=store,
        intent_query=StaticIntentQuery(),
        prepare_record=_prepare_record,
        decode_record=_decode_json,
        response_parent_ids=lambda record: tuple(record.get("response_to", ())),
        is_intent_record=lambda record: type(record) is dict,
        decode_record_json=_decode_json,
        encode_record_json=_encode_json,
        build_product_listing_record=lambda draft: {
            "id": "r-listing",
            "issuer": draft.seller_principal,
        },
        build_proposal_record=lambda draft: {
            "id": "r-proposal",
            "issuer": draft.buyer_principal,
            "response_to": [draft.parent_record_id],
        },
        index_html=b"<html>Marketplace</html>",
        app_js=b"console.log('marketplace');",
        styles_css=b"body{}",
    )
    application.initialize()
    return application, store


def _authentication():
    manifest, envelope = _inputs()
    return compose_marketplace_static_authentication(
        trust_anchor_manifest=manifest,
        verification_method_evidence=envelope,
        at_time=AT_TIME,
    )


def _compose(material_source=None):
    application, store = _application()
    authentication = _authentication()
    source = material_source or DeterministicMaterialSource()
    composition = compose_marketplace_authenticated_http(
        application=application,
        authentication=authentication,
        material_source=source,
        decode_record_json=_decode_json,
        record_principal=lambda record: record["issuer"],
    )
    return composition, application, authentication, source, store


def _challenge_request() -> ApplicationHttpRequest:
    body = _encode_json(
        {
            "principal": PRINCIPAL,
            "verification_method": METHOD,
        }
    )
    return ApplicationHttpRequest(
        "POST",
        "/api/auth/challenges",
        (),
        "application/json",
        body,
    )


def _session_request(proof_document: dict[str, object]) -> ApplicationHttpRequest:
    challenge = _encode_challenge(CHALLENGE)
    body = _encode_json(
        {
            "challenge": challenge,
            "proof": proof_document,
        }
    )
    return ApplicationHttpRequest(
        "POST",
        "/api/auth/sessions",
        (),
        "application/json",
        body,
    )


def _encode_challenge(challenge: bytes) -> str:
    from marketplace.application.auth_challenge import (
        encode_marketplace_auth_challenge,
    )

    return encode_marketplace_auth_challenge(challenge)


def _establish_session(composition) -> None:
    challenge_response = composition.session_http.handle(
        _challenge_request(),
        session_token=None,
        session_invalid=False,
        now=AT_TIME,
    )
    if challenge_response.status_code != 201:
        raise AssertionError(challenge_response.body)
    session_response = composition.session_http.handle(
        _session_request(_proof_document(_private(AUTH_PRIVATE_BYTES))),
        session_token=None,
        session_invalid=False,
        now=AT_TIME,
    )
    if session_response.status_code != 201:
        raise AssertionError(session_response.body)


class MarketplaceAuthenticatedHttpCompositionTests(unittest.TestCase):
    def test_profile_exact_types_and_stable_failure(self) -> None:
        self.assertEqual(
            PROFILE_NAME,
            "MARKETPLACE_APPLICATION_AUTH_HTTP_COMPOSITION_V1",
        )
        application, _ = _application()
        authentication = _authentication()
        source = DeterministicMaterialSource()

        with self.assertRaises(
            MarketplaceAuthenticatedHttpCompositionError
        ) as caught:
            compose_marketplace_authenticated_http(
                application=object(),  # type: ignore[arg-type]
                authentication=authentication,
                material_source=source,
                decode_record_json=_decode_json,
                record_principal=lambda record: record["issuer"],
            )
        self.assertEqual(
            str(caught.exception),
            "authenticated Marketplace HTTP composition failed",
        )

        with self.assertRaises(MarketplaceAuthenticatedHttpCompositionError):
            compose_marketplace_authenticated_http(
                application=application,
                authentication=object(),  # type: ignore[arg-type]
                material_source=source,
                decode_record_json=_decode_json,
                record_principal=lambda record: record["issuer"],
            )

    def test_exact_instances_are_shared_and_material_is_not_called(self) -> None:
        composition, application, authentication, source, _store = _compose()

        self.assertIs(composition.application, application)
        self.assertIs(composition.authentication, authentication)
        self.assertIs(composition.application_http._base, application.http)
        self.assertIs(
            composition.application_http._auth,
            authentication.auth_service,
        )
        self.assertIs(
            composition.session_http._auth,
            authentication.auth_service,
        )
        self.assertIs(
            composition.product_listing_authoring._auth,
            authentication.auth_service,
        )
        self.assertIs(
            composition.proposal_authoring._auth,
            authentication.auth_service,
        )
        self.assertIs(
            composition.session_http._verify_proof.__self__,
            authentication.proof_verifier,
        )
        self.assertIs(
            composition.application_http._create_intent.__self__,
            application.api,
        )
        self.assertIs(
            composition.application_http._respond_to_intent.__self__,
            application.api,
        )
        self.assertEqual(source.challenge_calls, 0)
        self.assertEqual(source.session_calls, 0)

    def test_valid_session_authorizes_matching_raw_intent_write(self) -> None:
        composition, _application_value, _authentication_value, source, store = (
            _compose()
        )
        _establish_session(composition)
        self.assertEqual(source.challenge_calls, 1)
        self.assertEqual(source.session_calls, 1)

        body = _encode_json({"id": "r-auth-write", "issuer": PRINCIPAL})
        response = composition.application_http.handle(
            ApplicationHttpRequest(
                "POST",
                "/api/intents",
                (),
                "application/json",
                body,
            ),
            session_token=SESSION_TOKEN,
            session_invalid=False,
            now=AT_TIME,
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(len(store.puts), 1)
        self.assertEqual(store.puts[0].record_id, "r-auth-write")

    def test_different_principal_is_rejected_before_downstream_write(self) -> None:
        composition, _application_value, _authentication_value, _source, store = (
            _compose()
        )
        _establish_session(composition)

        body = _encode_json({"id": "r-denied", "issuer": OTHER_PRINCIPAL})
        response = composition.application_http.handle(
            ApplicationHttpRequest(
                "POST",
                "/api/intents",
                (),
                "application/json",
                body,
            ),
            session_token=SESSION_TOKEN,
            session_invalid=False,
            now=AT_TIME,
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(len(store.puts), 0)

    def test_invalid_proof_and_material_failure_remain_fail_closed(self) -> None:
        composition, *_ = _compose()
        self.assertEqual(
            composition.session_http.handle(
                _challenge_request(),
                session_token=None,
                session_invalid=False,
                now=AT_TIME,
            ).status_code,
            201,
        )
        bad_session = composition.session_http.handle(
            _session_request(_proof_document(_private(ALT_AUTH_PRIVATE_BYTES))),
            session_token=None,
            session_invalid=False,
            now=AT_TIME,
        )
        self.assertEqual(bad_session.status_code, 401)

        failing, *_ = _compose(FailingMaterialSource())
        material_failure = failing.session_http.handle(
            _challenge_request(),
            session_token=None,
            session_invalid=False,
            now=AT_TIME,
        )
        self.assertEqual(material_failure.status_code, 503)

    def test_reviewed_reads_delegate_to_existing_base_http(self) -> None:
        composition, application, _authentication_value, _source, _store = (
            _compose()
        )
        request = ApplicationHttpRequest(
            "GET",
            "/api/intents",
            (),
            None,
            b"",
        )
        expected = application.http.handle(request)
        actual = composition.application_http.handle(
            request,
            session_token=None,
            session_invalid=False,
            now=AT_TIME,
        )
        self.assertEqual(actual, expected)


if __name__ == "__main__":
    unittest.main()
