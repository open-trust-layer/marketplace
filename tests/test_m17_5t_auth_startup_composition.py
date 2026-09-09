from __future__ import annotations

from dataclasses import FrozenInstanceError
import unittest
from unittest.mock import Mock, patch

from marketplace.application.auth_asgi_composition import (
    compose_marketplace_authenticated_asgi as _compose_r,
)
from marketplace.application.auth_http_composition import (
    compose_marketplace_authenticated_http as _compose_p,
)
from marketplace.application.auth_runtime_inputs import (
    MarketplaceAuthenticationRuntimeInputs,
    compose_marketplace_authentication_runtime_inputs,
)
from marketplace.application.auth_startup_composition import (
    PROFILE_NAME,
    MarketplaceAuthenticatedStartupComposition,
    MarketplaceAuthenticatedStartupCompositionError,
    compose_marketplace_authenticated_startup,
)
from marketplace.application.auth_startup_provisioning import (
    MarketplaceAuthenticationStartupProvisioning,
)
from marketplace.application.auth_static_composition import (
    compose_marketplace_static_authentication as _compose_o,
)
from tests.test_m17_5o_auth_static_composition import AT_TIME, _inputs
from tests.test_m17_5p_auth_http_composition import _application, _decode_json


ERROR_MESSAGE = "authenticated Marketplace startup composition failed"
MODULE = "marketplace.application.auth_startup_composition"


def _provisioning() -> MarketplaceAuthenticationStartupProvisioning:
    manifest, envelope = _inputs()
    return MarketplaceAuthenticationStartupProvisioning(
        trust_anchor_manifest=manifest,
        verification_method_evidence=envelope,
    )


def _runtime_inputs() -> MarketplaceAuthenticationRuntimeInputs:
    return compose_marketplace_authentication_runtime_inputs()


def _record_principal(record: object) -> str:
    if type(record) is not dict:
        raise TypeError("record must be object")
    return record["issuer"]  # type: ignore[return-value]


def _compose():
    application, _store = _application()
    provisioning = _provisioning()
    runtime_inputs = _runtime_inputs()
    with patch(
        "marketplace.application.auth_runtime_inputs._time_ns",
        return_value=AT_TIME * 1_000_000_000,
    ):
        result = compose_marketplace_authenticated_startup(
            application=application,
            provisioning=provisioning,
            runtime_inputs=runtime_inputs,
            decode_record_json=_decode_json,
            record_principal=_record_principal,
        )
    return result, application, provisioning, runtime_inputs


class MarketplaceAuthenticatedStartupCompositionTests(unittest.TestCase):
    def test_profile_exact_types_identity_and_frozen_result(self) -> None:
        result, application, _provisioning_bundle, runtime_inputs = _compose()
        self.assertEqual(
            PROFILE_NAME,
            "MARKETPLACE_APPLICATION_AUTH_STARTUP_COMPOSITION_V1",
        )
        self.assertIs(type(result), MarketplaceAuthenticatedStartupComposition)
        self.assertIs(result.http.application, application)
        self.assertIs(result.http.authentication, result.authentication)
        self.assertIs(result.asgi.http, result.http)
        self.assertIs(result.asgi.runtime_inputs, runtime_inputs)
        self.assertIs(
            result.http.session_http._challenge_bytes.__self__,
            runtime_inputs.material_source,
        )
        self.assertIs(result.asgi.asgi._now.__self__, runtime_inputs.clock)
        with self.assertRaises(FrozenInstanceError):
            result.http = object()  # type: ignore[misc,assignment]

    def test_exact_sampled_time_and_s_q_objects_flow_to_o_p_r(self) -> None:
        application, _store = _application()
        provisioning = _provisioning()
        runtime_inputs = _runtime_inputs()
        with (
            patch(
                "marketplace.application.auth_runtime_inputs._time_ns",
                return_value=AT_TIME * 1_000_000_000,
            ) as clock,
            patch(
                f"{MODULE}.compose_marketplace_static_authentication",
                wraps=_compose_o,
            ) as o,
            patch(
                f"{MODULE}.compose_marketplace_authenticated_http",
                wraps=_compose_p,
            ) as p,
            patch(
                f"{MODULE}.compose_marketplace_authenticated_asgi",
                wraps=_compose_r,
            ) as r,
        ):
            result = compose_marketplace_authenticated_startup(
                application=application,
                provisioning=provisioning,
                runtime_inputs=runtime_inputs,
                decode_record_json=_decode_json,
                record_principal=_record_principal,
            )
        self.assertEqual(clock.call_count, 1)
        self.assertEqual(o.call_count, 1)
        self.assertIs(
            o.call_args.kwargs["trust_anchor_manifest"],
            provisioning.trust_anchor_manifest,
        )
        self.assertIs(
            o.call_args.kwargs["verification_method_evidence"],
            provisioning.verification_method_evidence,
        )
        self.assertEqual(o.call_args.kwargs["at_time"], AT_TIME)
        self.assertIs(p.call_args.kwargs["application"], application)
        self.assertIs(p.call_args.kwargs["authentication"], result.authentication)
        self.assertIs(
            p.call_args.kwargs["material_source"],
            runtime_inputs.material_source,
        )
        self.assertIs(r.call_args.kwargs["http"], result.http)
        self.assertIs(r.call_args.kwargs["runtime_inputs"], runtime_inputs)

    def test_composition_consumes_only_one_clock_sample(self) -> None:
        application, _store = _application()
        provisioning = _provisioning()
        runtime_inputs = _runtime_inputs()
        decode = Mock(side_effect=AssertionError("decode called"))
        principal = Mock(side_effect=AssertionError("principal called"))
        with (
            patch(
                "marketplace.application.auth_runtime_inputs._time_ns",
                return_value=AT_TIME * 1_000_000_000,
            ) as clock,
            patch("marketplace.application.auth_material._token_bytes") as material,
            patch(
                "marketplace.application.composition."
                "MarketplaceApplicationComposition.initialize"
            ) as initialize,
            patch(
                "marketplace.application.auth_startup_provisioning."
                "load_marketplace_authentication_startup_provisioning"
            ) as load_provisioning,
            patch(
                "marketplace.application.auth_runtime_inputs."
                "compose_marketplace_authentication_runtime_inputs"
            ) as compose_runtime,
        ):
            result = compose_marketplace_authenticated_startup(
                application=application,
                provisioning=provisioning,
                runtime_inputs=runtime_inputs,
                decode_record_json=decode,
                record_principal=principal,
            )
        self.assertIs(result.asgi.runtime_inputs, runtime_inputs)
        self.assertEqual(clock.call_count, 1)
        material.assert_not_called()
        decode.assert_not_called()
        principal.assert_not_called()
        initialize.assert_not_called()
        load_provisioning.assert_not_called()
        compose_runtime.assert_not_called()

    def test_invalid_inputs_fail_before_clock_consumption(self) -> None:
        application, _store = _application()
        provisioning = _provisioning()
        runtime_inputs = _runtime_inputs()
        cases = (
            {"application": object()},
            {"provisioning": object()},
            {"runtime_inputs": object()},
            {"decode_record_json": None},
            {"record_principal": None},
        )
        for changes in cases:
            kwargs = {
                "application": application,
                "provisioning": provisioning,
                "runtime_inputs": runtime_inputs,
                "decode_record_json": _decode_json,
                "record_principal": _record_principal,
            }
            kwargs.update(changes)
            with self.subTest(changes=tuple(changes)):
                with patch(
                    "marketplace.application.auth_runtime_inputs._time_ns",
                    side_effect=AssertionError("clock consumed"),
                ) as clock:
                    with self.assertRaises(
                        MarketplaceAuthenticatedStartupCompositionError
                    ):
                        compose_marketplace_authenticated_startup(
                            **kwargs  # type: ignore[arg-type]
                        )
                clock.assert_not_called()

    def test_clock_and_stage_failures_are_ordered_and_non_reflective(self) -> None:
        application, _store = _application()
        provisioning = _provisioning()
        runtime_inputs = _runtime_inputs()

        with (
            patch(
                "marketplace.application.auth_runtime_inputs._time_ns",
                side_effect=RuntimeError("sensitive clock detail"),
            ) as clock,
            patch(f"{MODULE}.compose_marketplace_static_authentication") as o,
            patch(f"{MODULE}.compose_marketplace_authenticated_http") as p,
            patch(f"{MODULE}.compose_marketplace_authenticated_asgi") as r,
        ):
            with self.assertRaises(
                MarketplaceAuthenticatedStartupCompositionError
            ) as caught:
                compose_marketplace_authenticated_startup(
                    application=application,
                    provisioning=provisioning,
                    runtime_inputs=runtime_inputs,
                    decode_record_json=_decode_json,
                    record_principal=_record_principal,
                )
        self.assertEqual(clock.call_count, 1)
        o.assert_not_called()
        p.assert_not_called()
        r.assert_not_called()
        self.assertEqual(str(caught.exception), ERROR_MESSAGE)
        self.assertNotIn("sensitive", str(caught.exception))

        for failing_stage in ("o", "p", "r"):
            with self.subTest(failing_stage=failing_stage):
                patches = {
                    "o": patch(
                        f"{MODULE}.compose_marketplace_static_authentication",
                        side_effect=RuntimeError("sensitive O detail"),
                    ) if failing_stage == "o" else patch(
                        f"{MODULE}.compose_marketplace_static_authentication",
                        wraps=_compose_o,
                    ),
                    "p": patch(
                        f"{MODULE}.compose_marketplace_authenticated_http",
                        side_effect=RuntimeError("sensitive P detail"),
                    ) if failing_stage == "p" else patch(
                        f"{MODULE}.compose_marketplace_authenticated_http",
                        wraps=_compose_p,
                    ),
                    "r": patch(
                        f"{MODULE}.compose_marketplace_authenticated_asgi",
                        side_effect=RuntimeError("sensitive R detail"),
                    ) if failing_stage == "r" else patch(
                        f"{MODULE}.compose_marketplace_authenticated_asgi",
                        wraps=_compose_r,
                    ),
                }
                with (
                    patch(
                        "marketplace.application.auth_runtime_inputs._time_ns",
                        return_value=AT_TIME * 1_000_000_000,
                    ) as sampled_clock,
                    patches["o"] as o_stage,
                    patches["p"] as p_stage,
                    patches["r"] as r_stage,
                ):
                    with self.assertRaises(
                        MarketplaceAuthenticatedStartupCompositionError
                    ) as stage_error:
                        compose_marketplace_authenticated_startup(
                            application=application,
                            provisioning=provisioning,
                            runtime_inputs=runtime_inputs,
                            decode_record_json=_decode_json,
                            record_principal=_record_principal,
                        )
                self.assertEqual(sampled_clock.call_count, 1)
                self.assertEqual(str(stage_error.exception), ERROR_MESSAGE)
                self.assertNotIn("sensitive", str(stage_error.exception))
                if failing_stage == "o":
                    self.assertEqual(o_stage.call_count, 1)
                    p_stage.assert_not_called()
                    r_stage.assert_not_called()
                elif failing_stage == "p":
                    self.assertEqual(o_stage.call_count, 1)
                    self.assertEqual(p_stage.call_count, 1)
                    r_stage.assert_not_called()
                else:
                    self.assertEqual(o_stage.call_count, 1)
                    self.assertEqual(p_stage.call_count, 1)
                    self.assertEqual(r_stage.call_count, 1)

    def test_direct_construction_cannot_mix_graphs(self) -> None:
        first, _application_one, _provisioning_one, _runtime_one = _compose()
        second, _application_two, _provisioning_two, _runtime_two = _compose()
        with self.assertRaises(MarketplaceAuthenticatedStartupCompositionError):
            MarketplaceAuthenticatedStartupComposition(
                authentication=first.authentication,
                http=second.http,
                asgi=second.asgi,
            )
        with self.assertRaises(MarketplaceAuthenticatedStartupCompositionError):
            MarketplaceAuthenticatedStartupComposition(
                authentication=first.authentication,
                http=first.http,
                asgi=second.asgi,
            )


if __name__ == "__main__":
    unittest.main()