from __future__ import annotations

import unittest
from unittest.mock import patch

from marketplace.application.agreement_assent_coordination import (
    MemoryAgreementAssentCoordinationStore,
)
from marketplace.application.auth_launch import (
    build_marketplace_authenticated_loopback_launch_plan,
)
from marketplace.application.launch import LOOPBACK_LAUNCH_HOST
from marketplace.reference.agreement_assent_http_v1 import (
    decode_agreement_assent_signature,
    encode_agreement_assent_signing_input,
)
from marketplace.reference.agreement_assent_launch_v1 import (
    PROFILE_NAME,
    MarketplaceReferenceAgreementAssentLaunch,
    MarketplaceReferenceAgreementAssentLaunchError,
    build_reference_agreement_assent_launch,
)
from tests.test_m17_5t_auth_startup_composition import _compose


PORT = 18443


def _authenticated_plan():
    startup, _application, _provisioning, _runtime_inputs = _compose()
    return build_marketplace_authenticated_loopback_launch_plan(
        host=LOOPBACK_LAUNCH_HOST,
        port=PORT,
        startup=startup,
    )


def _store():
    return MemoryAgreementAssentCoordinationStore(clock=lambda: 321)


class ProductReferenceAgreementAssentLaunchTests(unittest.TestCase):
    def test_profile_and_exact_graph_selection(self) -> None:
        authenticated = _authenticated_plan()
        store = _store()
        result = build_reference_agreement_assent_launch(
            authenticated_plan=authenticated,
            coordination_store=store,
        )

        self.assertEqual(
            PROFILE_NAME,
            "MARKETPLACE_REFERENCE_AGREEMENT_ASSENT_LAUNCH_V1",
        )
        self.assertIs(type(result), MarketplaceReferenceAgreementAssentLaunch)
        self.assertIs(result.authenticated_plan, authenticated)
        self.assertIs(result.services.authenticated_startup, authenticated.startup)
        self.assertIs(result.startup.authenticated_startup, authenticated.startup)
        self.assertIs(
            result.startup.agreement_http.candidate_resolution,
            result.services.candidate_resolution,
        )
        self.assertIs(
            result.startup.agreement_http.workflow,
            result.services.workflow,
        )
        self.assertIs(result.plan.startup, result.startup)
        self.assertEqual(result.plan.host, authenticated.host)
        self.assertEqual(result.plan.port, authenticated.port)
        self.assertIs(result.plan.asgi, result.startup.agreement_asgi.asgi)
        self.assertIs(result.services.coordination._store, store)
        self.assertFalse(result.services.coordination._initialized)

    def test_exact_reference_http_carriers_are_selected(self) -> None:
        result = build_reference_agreement_assent_launch(
            authenticated_plan=_authenticated_plan(),
            coordination_store=_store(),
        )
        self.assertIs(
            result.startup.agreement_http.assent_http._encode_signing_input,
            encode_agreement_assent_signing_input,
        )
        self.assertIs(
            result.startup.agreement_http.assent_http._decode_signature,
            decode_agreement_assent_signature,
        )

    def test_selection_does_not_initialize_store_or_execute_runtime(self) -> None:
        authenticated = _authenticated_plan()
        store = _store()
        with (
            patch.object(
                MemoryAgreementAssentCoordinationStore,
                "initialize",
                side_effect=AssertionError("store initialized"),
            ) as initialize,
            patch.object(
                MemoryAgreementAssentCoordinationStore,
                "_now",
                side_effect=AssertionError("coordination clock consumed"),
            ) as now,
            patch(
                "marketplace.application.agreement_assent_runtime_server."
                "run_marketplace_agreement_assent_foreground",
                side_effect=AssertionError("runtime executed"),
            ) as run,
            patch("socket.socket", side_effect=AssertionError("socket used")) as socket,
        ):
            result = build_reference_agreement_assent_launch(
                authenticated_plan=authenticated,
                coordination_store=store,
            )

        self.assertIs(result.plan.asgi, result.startup.agreement_asgi.asgi)
        initialize.assert_not_called()
        now.assert_not_called()
        run.assert_not_called()
        socket.assert_not_called()

    def test_invalid_authenticated_plan_fails_closed(self) -> None:
        with self.assertRaises(MarketplaceReferenceAgreementAssentLaunchError):
            build_reference_agreement_assent_launch(
                authenticated_plan=object(),  # type: ignore[arg-type]
                coordination_store=_store(),
            )


if __name__ == "__main__":
    unittest.main()
