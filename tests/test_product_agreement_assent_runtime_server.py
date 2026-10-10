from __future__ import annotations

import unittest
from unittest.mock import patch

from marketplace.application.agreement_assent_launch import (
    build_marketplace_agreement_assent_loopback_launch_plan,
)
from marketplace.application.agreement_assent_runtime_server import (
    EXECUTE_ONE_AGREEMENT_ASSENT_MARKETPLACE_LOOPBACK_SERVER,
    PROFILE_NAME,
    MarketplaceAgreementAssentLocalRuntimeError,
    run_marketplace_agreement_assent_foreground,
)
from marketplace.application.auth_session_asgi import (
    MarketplaceSessionEstablishmentAsgiHttpAdapter,
)
from marketplace.application.launch import LOOPBACK_LAUNCH_HOST
from tests.test_product_agreement_assent_startup_composition import _compose


class _ProviderProbe:
    def __init__(self, *, fail: bool = False, expose_callable: bool = True) -> None:
        self.inspections = 0
        self.calls: list[tuple[object, str, int]] = []
        self.fail = fail
        self.expose_callable = expose_callable

    @property
    def run(self):
        self.inspections += 1
        if not self.expose_callable:
            return None

        def invoke(*, application: object, host: str, port: int) -> None:
            self.calls.append((application, host, port))
            if self.fail:
                raise ValueError("provider detail")

        return invoke


def _plan(port: int = 8443):
    startup, _authenticated_startup, _runtime_inputs = _compose()
    return build_marketplace_agreement_assent_loopback_launch_plan(
        host=LOOPBACK_LAUNCH_HOST,
        port=port,
        startup=startup,
    )


class ProductAgreementAssentRuntimeServerTests(unittest.TestCase):
    def test_profile_token_and_single_provider_delegation(self) -> None:
        plan = _plan()
        provider = _ProviderProbe()
        result = run_marketplace_agreement_assent_foreground(
            plan=plan,
            provider=provider,
            execute_token=EXECUTE_ONE_AGREEMENT_ASSENT_MARKETPLACE_LOOPBACK_SERVER,
        )

        self.assertIsNone(result)
        self.assertEqual(
            PROFILE_NAME,
            "MARKETPLACE_AGREEMENT_ASSENT_FOREGROUND_RUNTIME_V1",
        )
        self.assertEqual(provider.inspections, 1)
        self.assertEqual(provider.calls, [(plan.asgi, plan.host, plan.port)])

    def test_wrong_token_fails_before_provider_inspection(self) -> None:
        plan = _plan()
        for token in ("", "EXECUTE_ONE_MARKETPLACE_LOOPBACK_SERVER", object()):
            provider = _ProviderProbe()
            with self.subTest(token=type(token).__name__):
                with self.assertRaises(MarketplaceAgreementAssentLocalRuntimeError):
                    run_marketplace_agreement_assent_foreground(
                        plan=plan,
                        provider=provider,
                        execute_token=token,  # type: ignore[arg-type]
                    )
                self.assertEqual(provider.inspections, 0)
                self.assertEqual(provider.calls, [])

    def test_invalid_plan_fails_before_provider_inspection(self) -> None:
        provider = _ProviderProbe()
        with self.assertRaises(MarketplaceAgreementAssentLocalRuntimeError):
            run_marketplace_agreement_assent_foreground(
                plan=object(),  # type: ignore[arg-type]
                provider=provider,
                execute_token=EXECUTE_ONE_AGREEMENT_ASSENT_MARKETPLACE_LOOPBACK_SERVER,
            )
        self.assertEqual(provider.inspections, 0)

    def test_provider_shape_and_failure_are_stable_and_not_retried(self) -> None:
        plan = _plan()

        missing = _ProviderProbe(expose_callable=False)
        with self.assertRaises(MarketplaceAgreementAssentLocalRuntimeError):
            run_marketplace_agreement_assent_foreground(
                plan=plan,
                provider=missing,
                execute_token=EXECUTE_ONE_AGREEMENT_ASSENT_MARKETPLACE_LOOPBACK_SERVER,
            )
        self.assertEqual(missing.inspections, 1)
        self.assertEqual(missing.calls, [])

        failing = _ProviderProbe(fail=True)
        with self.assertRaises(MarketplaceAgreementAssentLocalRuntimeError) as caught:
            run_marketplace_agreement_assent_foreground(
                plan=plan,
                provider=failing,
                execute_token=EXECUTE_ONE_AGREEMENT_ASSENT_MARKETPLACE_LOOPBACK_SERVER,
            )
        self.assertEqual(str(caught.exception), "Agreement assent loopback runtime failed")
        self.assertNotIn("provider detail", str(caught.exception))
        self.assertEqual(failing.inspections, 1)
        self.assertEqual(len(failing.calls), 1)

    def test_runtime_seam_consumes_no_other_authority_before_provider_call(self) -> None:
        plan = _plan()
        provider = _ProviderProbe()
        with (
            patch(
                "marketplace.application.auth_runtime_inputs._time_ns",
                side_effect=AssertionError("clock consumed"),
            ) as clock,
            patch(
                "marketplace.application.auth_material._token_bytes",
                side_effect=AssertionError("material consumed"),
            ) as material,
            patch.object(
                MarketplaceSessionEstablishmentAsgiHttpAdapter,
                "__call__",
                side_effect=AssertionError("request handled"),
            ) as request,
            patch("socket.socket", side_effect=AssertionError("socket used")) as socket,
        ):
            run_marketplace_agreement_assent_foreground(
                plan=plan,
                provider=provider,
                execute_token=EXECUTE_ONE_AGREEMENT_ASSENT_MARKETPLACE_LOOPBACK_SERVER,
            )

        self.assertEqual(len(provider.calls), 1)
        clock.assert_not_called()
        material.assert_not_called()
        request.assert_not_called()
        socket.assert_not_called()


if __name__ == "__main__":
    unittest.main()
