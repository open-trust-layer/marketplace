from __future__ import annotations

import unittest

from marketplace.application.agreement_assent import VerifiedAgreementAssent
from marketplace.application.agreement_assent_coordination import (
    AgreementAssentCoordinationCollisionError,
    AgreementAssentCoordinationError,
    MemoryAgreementAssentCoordinationStore,
    MarketplaceAgreementAssentCoordinationService,
    PreparedAgreementAssent,
)
from marketplace.runtime.contracts import StoreDisposition


AGREEMENT = "r1_grS0_HlLNS2A1VqdELEa_daC4IJl_SBGzxcAO6esM5A"
OTHER_AGREEMENT = "r1_AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
BUYER = "urn:marketplace:test:buyer"
SELLER = "urn:marketplace:test:seller"
METHOD = "urn:example:olp:test-key-1"


class Clock:
    def __init__(self, value: int = 100) -> None:
        self.value = value

    def __call__(self) -> int:
        return self.value


def prepared(
    *,
    agreement: str = AGREEMENT,
    principal: str = BUYER,
    method: str = METHOD,
    identity_byte: int = 1,
    proof: bytes = b"proof",
) -> PreparedAgreementAssent:
    return PreparedAgreementAssent(
        agreement_record_id=agreement,
        principal=principal,
        verification_method=method,
        proof_identity=bytes([identity_byte]) * 32,
        proof_bytes=proof,
    )


def verified(
    *,
    agreement: str = AGREEMENT,
    principal: str = BUYER,
    method: str = METHOD,
) -> VerifiedAgreementAssent:
    return VerifiedAgreementAssent(
        agreement_record_id=agreement,
        principal=principal,
        verification_method=method,
        proof=object(),
    )


class AgreementAssentCoordinationTests(unittest.TestCase):
    def test_first_insert_and_duplicate_do_not_extend_absolute_expiry(self) -> None:
        clock = Clock()
        store = MemoryAgreementAssentCoordinationStore(
            clock=clock,
            retention_seconds=10,
        )
        item = prepared()
        first = store.put(item)
        self.assertEqual(first.disposition, StoreDisposition.STORED)
        self.assertEqual((first.accepted_at, first.expires_at), (100, 110))

        clock.value = 105
        duplicate = store.put(item)
        self.assertEqual(duplicate.disposition, StoreDisposition.DUPLICATE)
        self.assertEqual((duplicate.accepted_at, duplicate.expires_at), (100, 110))

    def test_conflicting_evidence_for_same_agreement_principal_fails_closed(self) -> None:
        store = MemoryAgreementAssentCoordinationStore(clock=Clock())
        store.put(prepared())
        with self.assertRaises(AgreementAssentCoordinationCollisionError):
            store.put(prepared(identity_byte=2, proof=b"different"))

    def test_different_principals_are_distinct_and_sorted(self) -> None:
        store = MemoryAgreementAssentCoordinationStore(clock=Clock())
        store.put(prepared(principal=SELLER, method="urn:example:olp:seller-key"))
        store.put(prepared(principal=BUYER))
        values = store.list_for_agreement(AGREEMENT)
        self.assertEqual(tuple(value.principal for value in values), (BUYER, SELLER))

    def test_read_neither_refreshes_nor_deletes_expired_evidence(self) -> None:
        clock = Clock()
        store = MemoryAgreementAssentCoordinationStore(
            clock=clock,
            retention_seconds=10,
        )
        item = prepared()
        store.put(item)
        clock.value = 109
        self.assertEqual(store.peek(AGREEMENT, BUYER), item)
        clock.value = 110
        self.assertIsNone(store.peek(AGREEMENT, BUYER))
        expired = store.expire_due()
        self.assertEqual(expired.expired_keys, ((AGREEMENT, BUYER),))

    def test_put_performs_bounded_expiry_and_can_reuse_capacity(self) -> None:
        clock = Clock()
        store = MemoryAgreementAssentCoordinationStore(
            clock=clock,
            retention_seconds=5,
            max_entries=1,
        )
        store.put(prepared())
        clock.value = 105
        result = store.put(
            prepared(
                agreement=OTHER_AGREEMENT,
                principal=SELLER,
                method="urn:example:olp:seller-key",
                identity_byte=3,
            )
        )
        self.assertEqual(result.disposition, StoreDisposition.STORED)

    def test_capacity_fails_closed_before_unbounded_growth(self) -> None:
        store = MemoryAgreementAssentCoordinationStore(
            clock=Clock(),
            max_entries=1,
        )
        store.put(prepared())
        with self.assertRaises(AgreementAssentCoordinationError) as caught:
            store.put(
                prepared(
                    agreement=OTHER_AGREEMENT,
                    principal=SELLER,
                    method="urn:example:olp:seller-key",
                    identity_byte=3,
                )
            )
        self.assertEqual(
            caught.exception.code,
            "AGREEMENT_ASSENT_COORDINATION_CAPACITY_EXCEEDED",
        )

    def test_initialize_expires_due_entries(self) -> None:
        clock = Clock()
        store = MemoryAgreementAssentCoordinationStore(
            clock=clock,
            retention_seconds=5,
        )
        store.put(prepared())
        clock.value = 105
        result = store.initialize()
        self.assertEqual(result.expired_keys, ((AGREEMENT, BUYER),))
        self.assertEqual(store.list_for_agreement(AGREEMENT), ())

    def test_service_requires_initialization_and_exact_verified_binding(self) -> None:
        clock = Clock()
        store = MemoryAgreementAssentCoordinationStore(clock=clock)
        service = MarketplaceAgreementAssentCoordinationService(
            store=store,
            prepare_verified_assent=lambda value: prepared(
                agreement=value.agreement_record_id,
                principal=value.principal,
                method=value.verification_method,
            ),
        )
        with self.assertRaises(AgreementAssentCoordinationError) as caught:
            service.accept(verified())
        self.assertEqual(
            caught.exception.code,
            "AGREEMENT_ASSENT_COORDINATION_NOT_INITIALIZED",
        )
        service.initialize()
        result = service.accept(verified())
        self.assertEqual(result.disposition, StoreDisposition.STORED)
        self.assertEqual(service.peek(AGREEMENT, BUYER), prepared())

    def test_service_rejects_preparer_binding_drift(self) -> None:
        service = MarketplaceAgreementAssentCoordinationService(
            store=MemoryAgreementAssentCoordinationStore(clock=Clock()),
            prepare_verified_assent=lambda _value: prepared(principal=SELLER),
        )
        service.initialize()
        with self.assertRaises(AgreementAssentCoordinationError) as caught:
            service.accept(verified())
        self.assertEqual(
            caught.exception.code,
            "AGREEMENT_ASSENT_PREPARATION_MISMATCH",
        )

    def test_retention_is_bounded_to_thirty_days_and_exact_integer(self) -> None:
        with self.assertRaises(ValueError):
            MemoryAgreementAssentCoordinationStore(
                clock=Clock(),
                retention_seconds=30 * 24 * 60 * 60 + 1,
            )
        with self.assertRaises(ValueError):
            MemoryAgreementAssentCoordinationStore(
                clock=Clock(),
                retention_seconds=True,
            )

    def test_prepared_evidence_is_public_bounded_material_only(self) -> None:
        item = prepared()
        self.assertEqual(len(item.proof_identity), 32)
        self.assertEqual(item.proof_bytes, b"proof")
        with self.assertRaises(ValueError):
            PreparedAgreementAssent(
                AGREEMENT,
                BUYER,
                METHOD,
                b"x" * 31,
                b"proof",
            )
        with self.assertRaises(ValueError):
            PreparedAgreementAssent(
                AGREEMENT,
                BUYER,
                METHOD,
                b"x" * 32,
                b"",
            )


if __name__ == "__main__":
    unittest.main()
