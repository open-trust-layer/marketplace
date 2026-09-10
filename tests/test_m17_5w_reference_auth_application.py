from __future__ import annotations

import unittest
from unittest.mock import Mock, patch

from marketplace.application.asgi import MarketplaceAsgiHttpAdapter
from marketplace.application.auth_launch import (
    MarketplaceAuthenticatedLoopbackLaunchPlan,
)
from marketplace.application.auth_runtime_inputs import (
    MarketplaceAuthenticationRuntimeInputs,
)
from marketplace.application.auth_startup_provisioning import (
    MarketplaceAuthenticationStartupProvisioning,
)
from marketplace.application.composition import MarketplaceApplicationComposition
from marketplace.application.launch import (
    LOOPBACK_LAUNCH_HOST,
    MAX_LAUNCH_PORT,
    MIN_LAUNCH_PORT,
    MarketplaceApplicationLaunchPlan,
)
from marketplace.reference.application_record_json_v1 import (
    decode_marketplace_application_record_json,
)
from marketplace.reference.application_record_v1 import (
    marketplace_record_issuer_principal,
)
from marketplace.reference.auth_application_v1 import (
    PROFILE_NAME,
    MarketplaceReferenceAuthenticatedLaunchError,
    build_reference_authenticated_marketplace_launch_plan,
)
from tests.test_m17_5o_auth_static_composition import AT_TIME
from tests.test_m17_5p_auth_http_composition import _application
from tests.test_m17_5t_auth_startup_composition import _provisioning, _runtime_inputs

ERROR_MESSAGE = "reference authenticated Marketplace launch composition failed"
MODULE = "marketplace.reference.auth_application_v1"

class _StringSubclass(str):
    pass


class _IntegerSubclass(int):
    pass


def _plan(port: int = 8443) -> MarketplaceApplicationLaunchPlan:
    application, _store = _application()
    return MarketplaceApplicationLaunchPlan(
        host=LOOPBACK_LAUNCH_HOST,
        port=port,
        composition=application,
        asgi=MarketplaceAsgiHttpAdapter(site=application.site),
    )


def _inputs():
    return _plan(), _provisioning(), _runtime_inputs()


def _forge_plan(plan: MarketplaceApplicationLaunchPlan, **changes):
    forged = object.__new__(MarketplaceApplicationLaunchPlan)
    for name in ("host", "port", "composition", "asgi"):
        object.__setattr__(forged, name, changes.get(name, getattr(plan, name)))
    return forged


def _forge_asgi_with_wrong_site() -> MarketplaceAsgiHttpAdapter:
    forged = object.__new__(MarketplaceAsgiHttpAdapter)
    object.__setattr__(forged, "_site", object())
    return forged


class MarketplaceReferenceAuthenticatedLaunchTests(unittest.TestCase):
    def test_profile_success_identity_and_single_clock_sample(self) -> None:
        plan, provisioning, runtime_inputs = _inputs()
        clock = Mock(return_value=AT_TIME * 1_000_000_000)
        with (
            patch("marketplace.application.auth_runtime_inputs._time_ns", clock),
            patch(
                "marketplace.application.auth_material._token_bytes",
                side_effect=AssertionError("credential material consumed"),
            ) as material,
        ):
            result = build_reference_authenticated_marketplace_launch_plan(
                application_plan=plan,
                provisioning=provisioning,
                runtime_inputs=runtime_inputs,
            )
        self.assertEqual(PROFILE_NAME, "MARKETPLACE_REFERENCE_AUTHENTICATED_LAUNCH_V1")
        self.assertIs(type(result), MarketplaceAuthenticatedLoopbackLaunchPlan)
        self.assertEqual(result.host, plan.host)
        self.assertEqual(result.port, plan.port)
        self.assertIs(result.startup.http.application, plan.composition)
        self.assertIs(result.asgi, result.startup.asgi.asgi)
        self.assertIs(result.startup.asgi.runtime_inputs, runtime_inputs)
        clock.assert_called_once_with()
        material.assert_not_called()

    def test_exact_reference_callables_and_single_t_u_calls(self) -> None:
        plan, provisioning, runtime_inputs = _inputs()
        from marketplace.application.auth_launch import (
            build_marketplace_authenticated_loopback_launch_plan as real_u,
        )
        from marketplace.application.auth_startup_composition import (
            compose_marketplace_authenticated_startup as real_t,
        )
        clock = Mock(return_value=AT_TIME * 1_000_000_000)
        with (
            patch("marketplace.application.auth_runtime_inputs._time_ns", clock),
            patch(
                f"{MODULE}.compose_marketplace_authenticated_startup",
                wraps=real_t,
            ) as t,
            patch(
                f"{MODULE}.build_marketplace_authenticated_loopback_launch_plan",
                wraps=real_u,
            ) as u,
        ):
            result = build_reference_authenticated_marketplace_launch_plan(
                application_plan=plan,
                provisioning=provisioning,
                runtime_inputs=runtime_inputs,
            )
        t.assert_called_once_with(
            application=plan.composition,
            provisioning=provisioning,
            runtime_inputs=runtime_inputs,
            decode_record_json=decode_marketplace_application_record_json,
            record_principal=marketplace_record_issuer_principal,
        )
        startup = t.return_value
        u.assert_called_once()
        kwargs = u.call_args.kwargs
        self.assertEqual(kwargs["host"], plan.host)
        self.assertEqual(kwargs["port"], plan.port)
        self.assertIs(result.startup.http.application, plan.composition)
        self.assertIs(kwargs["startup"], result.startup)
        clock.assert_called_once_with()

    def test_invalid_application_plan_fails_before_clock(self) -> None:
        plan, provisioning, runtime_inputs = _inputs()
        cases = (
            object(),
            _forge_plan(plan, host="0.0.0.0"),
            _forge_plan(plan, host=_StringSubclass(LOOPBACK_LAUNCH_HOST)),
            _forge_plan(plan, port=0),
            _forge_plan(plan, port=MAX_LAUNCH_PORT + 1),
            _forge_plan(plan, port=True),
            _forge_plan(plan, port=_IntegerSubclass(8443)),
            _forge_plan(plan, composition=object()),
            _forge_plan(plan, asgi=object()),
            _forge_plan(plan, asgi=_forge_asgi_with_wrong_site()),
        )
        for candidate in cases:
            with self.subTest(candidate=type(candidate).__name__):
                clock = Mock(side_effect=AssertionError("clock consumed"))
                with patch(
                    "marketplace.application.auth_runtime_inputs._time_ns", clock
                ):
                    with self.assertRaises(
                        MarketplaceReferenceAuthenticatedLaunchError
                    ) as caught:
                        build_reference_authenticated_marketplace_launch_plan(
                            application_plan=candidate,  # type: ignore[arg-type]
                            provisioning=provisioning,
                            runtime_inputs=runtime_inputs,
                        )
                self.assertEqual(str(caught.exception), ERROR_MESSAGE)
                clock.assert_not_called()

    def test_invalid_s_or_q_fails_before_clock(self) -> None:
        plan, provisioning, runtime_inputs = _inputs()
        cases = (
            (object(), runtime_inputs),
            (provisioning, object()),
        )
        for candidate_s, candidate_q in cases:
            with self.subTest(
                s=type(candidate_s).__name__, q=type(candidate_q).__name__
            ):
                clock = Mock(side_effect=AssertionError("clock consumed"))
                with patch(
                    "marketplace.application.auth_runtime_inputs._time_ns", clock
                ):
                    with self.assertRaises(
                        MarketplaceReferenceAuthenticatedLaunchError
                    ) as caught:
                        build_reference_authenticated_marketplace_launch_plan(
                            application_plan=plan,
                            provisioning=candidate_s,  # type: ignore[arg-type]
                            runtime_inputs=candidate_q,  # type: ignore[arg-type]
                        )
                self.assertEqual(str(caught.exception), ERROR_MESSAGE)
                clock.assert_not_called()

    def test_t_and_u_failures_are_stable_non_reflective(self) -> None:
        plan, provisioning, runtime_inputs = _inputs()
        for target in (
            "compose_marketplace_authenticated_startup",
            "build_marketplace_authenticated_loopback_launch_plan",
        ):
            with self.subTest(target=target):
                with patch(
                    f"{MODULE}.{target}", side_effect=ValueError("secret detail")
                ):
                    with self.assertRaises(
                        MarketplaceReferenceAuthenticatedLaunchError
                    ) as caught:
                        build_reference_authenticated_marketplace_launch_plan(
                            application_plan=plan,
                            provisioning=provisioning,
                            runtime_inputs=runtime_inputs,
                        )
                self.assertEqual(str(caught.exception), ERROR_MESSAGE)
                self.assertNotIn("secret detail", str(caught.exception))

    def test_output_validation_rejects_forged_u_result(self) -> None:
        plan, provisioning, runtime_inputs = _inputs()
        with (
            patch(
                "marketplace.application.auth_runtime_inputs._time_ns",
                return_value=AT_TIME * 1_000_000_000,
            ),
            patch(
                f"{MODULE}.build_marketplace_authenticated_loopback_launch_plan",
                return_value=object(),
            ),
        ):
            with self.assertRaises(
                MarketplaceReferenceAuthenticatedLaunchError
            ) as caught:
                build_reference_authenticated_marketplace_launch_plan(
                    application_plan=plan,
                    provisioning=provisioning,
                    runtime_inputs=runtime_inputs,
                )
        self.assertEqual(str(caught.exception), ERROR_MESSAGE)

    def test_exact_port_bounds_flow_unchanged(self) -> None:
        for port in (MIN_LAUNCH_PORT, MAX_LAUNCH_PORT):
            with self.subTest(port=port):
                plan = _plan(port)
                provisioning = _provisioning()
                runtime_inputs = _runtime_inputs()
                with patch(
                    "marketplace.application.auth_runtime_inputs._time_ns",
                    return_value=AT_TIME * 1_000_000_000,
                ):
                    result = build_reference_authenticated_marketplace_launch_plan(
                        application_plan=plan,
                        provisioning=provisioning,
                        runtime_inputs=runtime_inputs,
                    )
                self.assertEqual(result.port, port)
                self.assertEqual(result.host, LOOPBACK_LAUNCH_HOST)

    def test_no_runtime_or_external_io_surface_is_touched(self) -> None:
        plan, provisioning, runtime_inputs = _inputs()
        with (
            patch(
                "marketplace.application.auth_runtime_inputs._time_ns",
                return_value=AT_TIME * 1_000_000_000,
            ),
            patch(
                "marketplace.application.auth_material._token_bytes",
                side_effect=AssertionError("material consumed"),
            ) as material,
            patch.object(
                MarketplaceApplicationComposition,
                "initialize",
                side_effect=AssertionError("initialized"),
            ) as initialize,
        ):
            result = build_reference_authenticated_marketplace_launch_plan(
                application_plan=plan,
                provisioning=provisioning,
                runtime_inputs=runtime_inputs,
            )
        self.assertIs(result.startup.http.application, plan.composition)
        material.assert_not_called()
        initialize.assert_not_called()


if __name__ == "__main__":
    unittest.main()
