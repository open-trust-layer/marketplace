import asyncio
import json
import unittest
from unittest.mock import patch

from marketplace.application.asgi import AsgiHttpAdapterError
from marketplace.application.auth_asgi_composition import (
    PROFILE_NAME,
    MarketplaceAuthenticatedAsgiComposition,
    MarketplaceAuthenticatedAsgiCompositionError,
    compose_marketplace_authenticated_asgi,
)
from marketplace.application.auth_http_composition import (
    compose_marketplace_authenticated_http,
)
from marketplace.application.auth_runtime_inputs import (
    MarketplaceAuthenticationRuntimeInputs,
    MarketplaceAuthenticationUnixClock,
    compose_marketplace_authentication_runtime_inputs,
)
from marketplace.application.auth_session_asgi import (
    MarketplaceSessionEstablishmentAsgiHttpAdapter,
)
from tests.test_m17_5o_auth_static_composition import AT_TIME, METHOD, PRINCIPAL
from tests.test_m17_5p_auth_http_composition import (
    _application,
    _authentication,
    _decode_json,
)


def _compose():
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
    composition = compose_marketplace_authenticated_asgi(
        http=http,
        runtime_inputs=runtime_inputs,
    )
    return composition, http, runtime_inputs


def _scope(
    path: str,
    *,
    method: str = "GET",
    body: bytes = b"",
) -> dict[str, object]:
    headers: list[tuple[bytes, bytes]] = []
    if body:
        headers = [
            (b"content-type", b"application/json"),
            (b"content-length", str(len(body)).encode("ascii")),
        ]
    return {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": method,
        "path": path,
        "raw_path": path.encode("ascii"),
        "root_path": "",
        "query_string": b"",
        "headers": headers,
    }


async def _invoke(
    asgi: MarketplaceSessionEstablishmentAsgiHttpAdapter,
    scope: dict[str, object],
    body: bytes = b"",
) -> list[dict[str, object]]:
    receive_events = [
        {"type": "http.request", "body": body, "more_body": False}
    ]
    sent: list[dict[str, object]] = []

    async def receive() -> dict[str, object]:
        return receive_events.pop(0)

    async def send(event: dict[str, object]) -> None:
        sent.append(event)

    await asgi(scope, receive, send)
    return sent


class MarketplaceAuthenticatedAsgiCompositionTests(unittest.TestCase):
    def test_profile_exact_types_and_identity_coherence(self) -> None:
        composition, http, runtime_inputs = _compose()

        self.assertEqual(
            PROFILE_NAME,
            "MARKETPLACE_APPLICATION_AUTH_ASGI_COMPOSITION_V1",
        )
        self.assertIsInstance(
            composition,
            MarketplaceAuthenticatedAsgiComposition,
        )
        self.assertIs(composition.http, http)
        self.assertIs(composition.runtime_inputs, runtime_inputs)
        self.assertIs(composition.asgi._site, http.application.site)
        self.assertIs(
            composition.asgi._marketplace_http,
            http.application_http,
        )
        self.assertIs(composition.asgi._auth_http, http.session_http)
        self.assertIs(composition.asgi._now.__self__, runtime_inputs.clock)
        self.assertIs(
            http.session_http._challenge_bytes.__self__,
            runtime_inputs.material_source,
        )
        self.assertIs(
            http.session_http._session_token_bytes.__self__,
            runtime_inputs.material_source,
        )

    def test_mismatched_runtime_material_fails_before_asgi_construction(self) -> None:
        composition, http, _runtime_inputs = _compose()
        other = compose_marketplace_authentication_runtime_inputs()

        with patch(
            "marketplace.application.auth_asgi_composition."
            "MarketplaceSessionEstablishmentAsgiHttpAdapter",
        ) as constructor:
            with self.assertRaises(
                MarketplaceAuthenticatedAsgiCompositionError
            ) as caught:
                compose_marketplace_authenticated_asgi(
                    http=http,
                    runtime_inputs=other,
                )
        constructor.assert_not_called()
        self.assertEqual(
            str(caught.exception),
            "authenticated Marketplace ASGI composition failed",
        )
        self.assertIsNot(
            composition.runtime_inputs.material_source,
            other.material_source,
        )

    def test_direct_result_construction_cannot_bypass_material_coherence(self) -> None:
        _composition, http, _runtime_inputs = _compose()
        other = compose_marketplace_authentication_runtime_inputs()
        mismatched_asgi = MarketplaceSessionEstablishmentAsgiHttpAdapter(
            site=http.application.site,
            marketplace_http=http.application_http,
            auth_http=http.session_http,
            now=other.clock.now,
        )

        with self.assertRaises(MarketplaceAuthenticatedAsgiCompositionError):
            MarketplaceAuthenticatedAsgiComposition(
                http=http,
                runtime_inputs=other,
                asgi=mismatched_asgi,
            )

    def test_composition_consumes_no_inputs_or_request_surfaces(self) -> None:
        composition, http, runtime_inputs = _compose()

        with (
            patch(
                "marketplace.application.auth_material._token_bytes"
            ) as material,
            patch(
                "marketplace.application.auth_runtime_inputs._time_ns"
            ) as clock,
            patch(
                "marketplace.application.composition."
                "MarketplaceApplicationComposition.initialize"
            ) as initialize,
            patch(
                "marketplace.application.auth_http."
                "MarketplaceAuthenticatedApplicationHttpAdapter.handle"
            ) as application_handle,
            patch(
                "marketplace.application.auth_session_http."
                "MarketplaceAuthenticationSessionHttpAdapter.handle"
            ) as session_handle,
            patch(
                "marketplace.application.auth_session_asgi."
                "MarketplaceSessionEstablishmentAsgiHttpAdapter.__call__"
            ) as asgi_call,
        ):
            result = compose_marketplace_authenticated_asgi(
                http=http,
                runtime_inputs=runtime_inputs,
            )

        self.assertIs(result.http, composition.http)
        material.assert_not_called()
        clock.assert_not_called()
        initialize.assert_not_called()
        application_handle.assert_not_called()
        session_handle.assert_not_called()
        asgi_call.assert_not_called()

    def test_site_delivery_reads_no_clock_and_auth_request_reads_once(self) -> None:
        composition, _http, _runtime_inputs = _compose()

        with patch(
            "marketplace.application.auth_runtime_inputs._time_ns",
            return_value=AT_TIME * 1_000_000_000,
        ) as clock:
            site_events = asyncio.run(_invoke(composition.asgi, _scope("/")))
            self.assertEqual(site_events[0]["status"], 200)
            self.assertEqual(clock.call_count, 0)

            body = json.dumps(
                {
                    "principal": PRINCIPAL,
                    "verification_method": METHOD,
                },
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
            with patch(
                "marketplace.application.auth_material._token_bytes",
                return_value=b"r" * 32,
            ):
                auth_events = asyncio.run(
                    _invoke(
                        composition.asgi,
                        _scope(
                            "/api/auth/challenges",
                            method="POST",
                            body=body,
                        ),
                        body,
                    )
                )
            self.assertEqual(auth_events[0]["status"], 201)
            self.assertEqual(clock.call_count, 1)

    def test_clock_failure_remains_existing_asgi_fail_closed_error(self) -> None:
        composition, _http, _runtime_inputs = _compose()
        body = json.dumps(
            {
                "principal": PRINCIPAL,
                "verification_method": METHOD,
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")

        with patch(
            "marketplace.application.auth_runtime_inputs._time_ns",
            side_effect=RuntimeError("synthetic clock detail"),
        ):
            with self.assertRaises(AsgiHttpAdapterError) as caught:
                asyncio.run(
                    _invoke(
                        composition.asgi,
                        _scope(
                            "/api/auth/challenges",
                            method="POST",
                            body=body,
                        ),
                        body,
                    )
                )
        self.assertEqual(caught.exception.code, "ASGI_SITE_FAILURE")
        self.assertNotIn("synthetic clock detail", str(caught.exception))

    def test_invalid_exact_types_fail_closed(self) -> None:
        _composition, http, runtime_inputs = _compose()

        with self.assertRaises(MarketplaceAuthenticatedAsgiCompositionError):
            compose_marketplace_authenticated_asgi(
                http=object(),  # type: ignore[arg-type]
                runtime_inputs=runtime_inputs,
            )
        with self.assertRaises(MarketplaceAuthenticatedAsgiCompositionError):
            compose_marketplace_authenticated_asgi(
                http=http,
                runtime_inputs=object(),  # type: ignore[arg-type]
            )
        self.assertIs(
            type(runtime_inputs.clock),
            MarketplaceAuthenticationUnixClock,
        )
        self.assertIs(type(runtime_inputs), MarketplaceAuthenticationRuntimeInputs)


if __name__ == "__main__":
    unittest.main()
