from __future__ import annotations

import asyncio
import unittest
from unittest.mock import patch

from marketplace.application.auth_enrollment_asgi_composition import (
    MarketplaceAuthenticationEnrollmentAsgiCompositionError,
    PROFILE_NAME,
    compose_marketplace_authentication_enrollment_asgi,
)
from marketplace.application.auth_enrollment_http import (
    AUTH_ENROLLMENT_EVIDENCE_ROUTE,
    AUTH_ENROLLMENT_HTTP_REQUEST_MAX_BYTES,
    AUTH_ENROLLMENT_NONCE_ROUTE,
    MarketplaceAuthenticationEnrollmentHttpAdapter,
)
from marketplace.application.auth_enrollment_http_composition import (
    compose_marketplace_authentication_enrollment_http,
)
from marketplace.application.auth_enrollment_nonce import (
    MarketplaceAuthenticationEnrollmentNonceAuthority,
)
from marketplace.application.auth_http import (
    MarketplaceAuthenticatedApplicationHttpAdapter,
)
from marketplace.application.auth_http_composition import (
    compose_marketplace_authenticated_http,
)
from marketplace.application.auth_runtime_inputs import (
    compose_marketplace_authentication_runtime_inputs,
)
from marketplace.application.auth_session_http import (
    MarketplaceAuthenticationSessionHttpAdapter,
)
from marketplace.application.http import ApplicationHttpResponse
from marketplace.application.site_host import MarketplaceSiteHostAdapter
from tests.test_m17_5d_session_establishment_hardening import (
    invoke,
    json_headers,
    scope,
)
from tests.test_m17_5p_auth_http_composition import (
    _application,
    _authentication,
    _decode_json,
)
from tests.test_m17_6i_auth_enrollment_http import (
    AUTHORITY,
    LEASE_SECONDS,
    NONCE,
    RecordingAttestor,
    RecordingPolicy,
    SequenceMaterialSource,
)


def _graph():
    application, _store = _application()
    authentication = _authentication()
    runtime_inputs = compose_marketplace_authentication_runtime_inputs()
    http = compose_marketplace_authenticated_http(
        application=application,
        authentication=authentication,
        material_source=runtime_inputs.material_source,
        decode_record_json=_decode_json,
        record_principal=lambda record: record["issuer"],
    )
    nonce_source = SequenceMaterialSource([NONCE])
    nonce_authority = MarketplaceAuthenticationEnrollmentNonceAuthority(
        material_source=nonce_source
    )
    policy = RecordingPolicy()
    attestor = RecordingAttestor()
    enrollment = compose_marketplace_authentication_enrollment_http(
        http=http,
        nonce_authority=nonce_authority,
        policy=policy,
        attestor=attestor,
        authority=AUTHORITY,
        evidence_lease_seconds=LEASE_SECONDS,
    )
    return (
        enrollment,
        runtime_inputs,
        nonce_source,
        policy,
        attestor,
    )


def _response(status: int = 204) -> ApplicationHttpResponse:
    return ApplicationHttpResponse(
        status,
        "Synthetic",
        (("Content-Length", "0"),),
        b"",
    )


class M176KAuthenticationEnrollmentAsgiCompositionTests(unittest.TestCase):
    def test_profile_exact_types_identity_and_zero_composition_consumption(self) -> None:
        enrollment, runtime_inputs, nonce_source, policy, attestor = _graph()
        with (
            patch(
                "marketplace.application.auth_material._token_bytes",
                side_effect=AssertionError("credential material consumed"),
            ) as token_bytes,
            patch(
                "marketplace.application.auth_runtime_inputs._time_ns",
                side_effect=AssertionError("clock consumed"),
            ) as clock,
        ):
            result = compose_marketplace_authentication_enrollment_asgi(
                enrollment=enrollment,
                runtime_inputs=runtime_inputs,
            )

        self.assertEqual(
            PROFILE_NAME,
            "MARKETPLACE_APPLICATION_AUTH_ENROLLMENT_ASGI_COMPOSITION_V1",
        )
        self.assertIs(result.enrollment, enrollment)
        self.assertIs(result.runtime_inputs, runtime_inputs)
        self.assertIs(result.asgi._site, enrollment.http.application.site)
        self.assertIs(result.asgi._marketplace_http, enrollment.http.application_http)
        self.assertIs(result.asgi._auth_http, enrollment.http.session_http)
        self.assertIs(result.asgi._enrollment_http, enrollment.enrollment_http)
        self.assertIs(result.asgi._now.__self__, runtime_inputs.clock)
        token_bytes.assert_not_called()
        clock.assert_not_called()
        self.assertEqual(nonce_source.calls, 0)
        self.assertEqual(policy.calls, 0)
        self.assertEqual(attestor.calls, 0)

    def test_mismatched_runtime_material_fails_before_asgi_construction(self) -> None:
        enrollment, _runtime_inputs, nonce_source, policy, attestor = _graph()
        other = compose_marketplace_authentication_runtime_inputs()
        with patch(
            "marketplace.application.auth_enrollment_asgi_composition."
            "MarketplaceSessionEstablishmentAsgiHttpAdapter"
        ) as constructor:
            with self.assertRaises(
                MarketplaceAuthenticationEnrollmentAsgiCompositionError
            ):
                compose_marketplace_authentication_enrollment_asgi(
                    enrollment=enrollment,
                    runtime_inputs=other,
                )
        constructor.assert_not_called()
        self.assertEqual(nonce_source.calls, 0)
        self.assertEqual(policy.calls, 0)
        self.assertEqual(attestor.calls, 0)

    def test_exact_enrollment_routes_select_only_enrollment_http_and_clock_once(self) -> None:
        enrollment, runtime_inputs, *_ = _graph()
        result = compose_marketplace_authentication_enrollment_asgi(
            enrollment=enrollment,
            runtime_inputs=runtime_inputs,
        )
        for route in (AUTH_ENROLLMENT_NONCE_ROUTE, AUTH_ENROLLMENT_EVIDENCE_ROUTE):
            body = b"{}"
            with (
                patch.object(
                    MarketplaceAuthenticationEnrollmentHttpAdapter,
                    "handle",
                    return_value=_response(),
                ) as enrollment_handle,
                patch.object(
                    MarketplaceAuthenticatedApplicationHttpAdapter,
                    "handle",
                    side_effect=AssertionError("ordinary Marketplace HTTP selected"),
                ),
                patch.object(
                    MarketplaceAuthenticationSessionHttpAdapter,
                    "handle",
                    side_effect=AssertionError("session HTTP selected"),
                ),
                patch(
                    "marketplace.application.auth_runtime_inputs._time_ns",
                    return_value=123_000_000_000,
                ) as clock,
            ):
                sent = asyncio.run(
                    invoke(
                        result.asgi,
                        scope(
                            method="POST",
                            path=route,
                            headers=json_headers(body),
                        ),
                        body,
                    )
                )
            self.assertEqual(sent[0]["status"], 204)
            enrollment_handle.assert_called_once()
            clock.assert_called_once()

    def test_future_enrollment_like_route_falls_through_to_existing_marketplace_http(self) -> None:
        enrollment, runtime_inputs, *_ = _graph()
        result = compose_marketplace_authentication_enrollment_asgi(
            enrollment=enrollment,
            runtime_inputs=runtime_inputs,
        )
        with (
            patch.object(
                MarketplaceAuthenticationEnrollmentHttpAdapter,
                "handle",
                side_effect=AssertionError("future route selected as enrollment"),
            ),
            patch.object(
                MarketplaceAuthenticatedApplicationHttpAdapter,
                "handle",
                return_value=_response(202),
            ) as marketplace_handle,
            patch(
                "marketplace.application.auth_runtime_inputs._time_ns",
                return_value=124_000_000_000,
            ),
        ):
            sent = asyncio.run(
                invoke(
                    result.asgi,
                    scope(
                        method="POST",
                        path="/api/authentication-enrollment/future",
                        headers=json_headers(b"{}"),
                    ),
                    b"{}",
                )
            )
        self.assertEqual(sent[0]["status"], 202)
        marketplace_handle.assert_called_once()

    def test_existing_auth_api_and_site_routes_keep_existing_owners(self) -> None:
        enrollment, runtime_inputs, *_ = _graph()
        result = compose_marketplace_authentication_enrollment_asgi(
            enrollment=enrollment,
            runtime_inputs=runtime_inputs,
        )

        with (
            patch.object(
                MarketplaceAuthenticationSessionHttpAdapter,
                "handle",
                return_value=_response(201),
            ) as auth_handle,
            patch.object(
                MarketplaceAuthenticationEnrollmentHttpAdapter,
                "handle",
                side_effect=AssertionError("enrollment selected for auth route"),
            ),
            patch(
                "marketplace.application.auth_runtime_inputs._time_ns",
                return_value=125_000_000_000,
            ),
        ):
            auth_sent = asyncio.run(
                invoke(
                    result.asgi,
                    scope(
                        method="POST",
                        path="/api/auth/challenges",
                        headers=json_headers(b"{}"),
                    ),
                    b"{}",
                )
            )
        self.assertEqual(auth_sent[0]["status"], 201)
        auth_handle.assert_called_once()

        with (
            patch.object(
                MarketplaceAuthenticatedApplicationHttpAdapter,
                "handle",
                return_value=_response(202),
            ) as marketplace_handle,
            patch.object(
                MarketplaceAuthenticationEnrollmentHttpAdapter,
                "handle",
                side_effect=AssertionError("enrollment selected for ordinary API"),
            ),
            patch(
                "marketplace.application.auth_runtime_inputs._time_ns",
                return_value=126_000_000_000,
            ),
        ):
            api_sent = asyncio.run(invoke(result.asgi, scope(path="/api/intents")))
        self.assertEqual(api_sent[0]["status"], 202)
        marketplace_handle.assert_called_once()

        with (
            patch.object(
                MarketplaceSiteHostAdapter,
                "handle",
                return_value=_response(200),
            ) as site_handle,
            patch(
                "marketplace.application.auth_runtime_inputs._time_ns",
                side_effect=AssertionError("site route read auth clock"),
            ),
        ):
            site_sent = asyncio.run(invoke(result.asgi, scope(path="/")))
        self.assertEqual(site_sent[0]["status"], 200)
        site_handle.assert_called_once()

    def test_enrollment_body_limit_fails_before_receive_or_handler(self) -> None:
        enrollment, runtime_inputs, *_ = _graph()
        result = compose_marketplace_authentication_enrollment_asgi(
            enrollment=enrollment,
            runtime_inputs=runtime_inputs,
        )
        oversized = AUTH_ENROLLMENT_HTTP_REQUEST_MAX_BYTES + 1
        request_scope = scope(
            method="POST",
            path=AUTH_ENROLLMENT_NONCE_ROUTE,
            headers=(
                (b"content-type", b"application/json"),
                (b"content-length", str(oversized).encode("ascii")),
            ),
        )
        sent = []
        receive_calls = 0

        async def receive():
            nonlocal receive_calls
            receive_calls += 1
            raise AssertionError("oversized enrollment body reached receive")

        async def send(message):
            sent.append(message)

        with patch.object(
            MarketplaceAuthenticationEnrollmentHttpAdapter,
            "handle",
            side_effect=AssertionError("oversized enrollment body reached handler"),
        ):
            asyncio.run(result.asgi(request_scope, receive, send))

        self.assertEqual(receive_calls, 0)
        self.assertEqual(sent[0]["status"], 400)
        self.assertIn(b"AUTH_ENROLLMENT_REQUEST_INVALID", sent[1]["body"])


if __name__ == "__main__":
    unittest.main()
