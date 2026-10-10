from __future__ import annotations

from datetime import datetime, timezone
import unittest
from unittest.mock import Mock, patch

from marketplace.application.auth_launch import (
    build_marketplace_authenticated_loopback_launch_plan,
)
from marketplace.application.launch import LOOPBACK_LAUNCH_HOST
from marketplace.application.postgres_agreement_assent import (
    PostgresAgreementAssentCoordinationStore,
)
from marketplace.reference.agreement_assent_postgres_v1 import (
    PROFILE_NAME,
    MarketplaceReferenceAgreementAssentPostgres,
    MarketplaceReferenceAgreementAssentPostgresError,
    build_reference_agreement_assent_postgres,
)
from tests.test_m17_5t_auth_startup_composition import _compose


PORT = 18444


def _authenticated_plan():
    startup, _application, _provisioning, _runtime_inputs = _compose()
    return build_marketplace_authenticated_loopback_launch_plan(
        host=LOOPBACK_LAUNCH_HOST,
        port=PORT,
        startup=startup,
    )


class ProductReferenceAgreementAssentPostgresTests(unittest.TestCase):
    def test_profile_exact_store_and_launch_binding(self) -> None:
        connection_factory = Mock(name="connection_factory")
        clock = Mock(
            name="clock",
            return_value=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )
        result = build_reference_agreement_assent_postgres(
            authenticated_plan=_authenticated_plan(),
            connection_factory=connection_factory,
            clock=clock,
        )

        self.assertEqual(
            PROFILE_NAME,
            "MARKETPLACE_REFERENCE_AGREEMENT_ASSENT_POSTGRES_V1",
        )
        self.assertIs(type(result), MarketplaceReferenceAgreementAssentPostgres)
        self.assertIs(type(result.store), PostgresAgreementAssentCoordinationStore)
        self.assertIs(result.store._connection_factory, connection_factory)
        self.assertIs(result.store._clock, clock)
        self.assertIs(result.launch.services.coordination._store, result.store)
        self.assertFalse(result.launch.services.coordination._initialized)
        connection_factory.assert_not_called()
        clock.assert_not_called()

    def test_composition_does_not_initialize_or_open_postgres(self) -> None:
        connection_factory = Mock(
            name="connection_factory",
            side_effect=AssertionError("database opened"),
        )
        clock = Mock(name="clock", side_effect=AssertionError("clock consumed"))
        with (
            patch.object(
                PostgresAgreementAssentCoordinationStore,
                "initialize",
                side_effect=AssertionError("store initialized"),
            ) as initialize,
            patch.object(
                PostgresAgreementAssentCoordinationStore,
                "apply_migrations",
                side_effect=AssertionError("migration applied"),
            ) as migrate,
        ):
            result = build_reference_agreement_assent_postgres(
                authenticated_plan=_authenticated_plan(),
                connection_factory=connection_factory,
                clock=clock,
            )

        self.assertFalse(result.launch.services.coordination._initialized)
        initialize.assert_not_called()
        migrate.assert_not_called()
        connection_factory.assert_not_called()
        clock.assert_not_called()

    def test_noncallable_provider_inputs_fail_before_store_construction(self) -> None:
        with patch(
            "marketplace.reference.agreement_assent_postgres_v1."
            "PostgresAgreementAssentCoordinationStore"
        ) as constructor:
            with self.assertRaises(MarketplaceReferenceAgreementAssentPostgresError):
                build_reference_agreement_assent_postgres(
                    authenticated_plan=_authenticated_plan(),
                    connection_factory=object(),  # type: ignore[arg-type]
                    clock=lambda: datetime.now(timezone.utc),
                )
        constructor.assert_not_called()


if __name__ == "__main__":
    unittest.main()
