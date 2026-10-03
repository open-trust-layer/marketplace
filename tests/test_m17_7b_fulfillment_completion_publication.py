from __future__ import annotations

import unittest
from unittest.mock import Mock, patch

from olp import RecordV1
from olp.encoding.deterministic_cbor import encode as olp_encode
from olp.encoding.record_identity import record_identity_text

from marketplace.application.fulfillment_completion_publication import (
    CLAIMED_COMPLETE_PERFORMANCE,
    COMMITMENT_ACCEPTANCE,
    COMMITMENT_COMPLETION,
    PROFILE_NAME,
    FulfillmentCompletionPublicationError,
    MarketplaceFulfillmentCompletionPublicationService,
)
from marketplace.application.state import MarketplaceApplicationStateService
from marketplace.reference.application_record_v1 import (
    decode_marketplace_application_record,
    prepare_marketplace_application_record,
)
from marketplace.reference.fulfillment_completion_evidence_v1 import (
    build_claimed_complete_performance_event,
    build_commitment_acceptance_event,
    build_commitment_completion_event,
    fulfillment_event_target,
)
from marketplace.reference.memory_application_v1 import MemoryApplicationStateStore
from marketplace.reference.record_v1 import (
    BASE,
    CORE_PROFILE,
    TYPE_AGREEMENT,
    validate_market_record,
)


SELLER = "did:example:seller"
BUYER = "did:example:buyer"
COMMITMENT_ID = "seller-delivery"
ACTION_SELL = f"{BASE}/action/sell"
SUBJECT = {"uri": "urn:example:item:moon-widget"}


def _canonical(values):
    return tuple(sorted(values, key=olp_encode))


def _agreement() -> RecordV1:
    seller = {"principal": SELLER}
    buyer = {"principal": BUYER}
    record = RecordV1.from_mapping(
        {
            "envelope_version": 1,
            "type": TYPE_AGREEMENT,
            "content": {
                "version": 1,
                "parties": list(_canonical((seller, buyer))),
                "subjects": [SUBJECT],
                "actions": [{"id": ACTION_SELL}],
                "terms": {},
                "commitments": [
                    {
                        "id": COMMITMENT_ID,
                        "party": seller,
                        "action": {"id": ACTION_SELL},
                        "subjects": [SUBJECT],
                    }
                ],
            },
            "profiles": [CORE_PROFILE],
        }
    )
    validate_market_record(record)
    return record


def _state_with_agreement():
    state = MarketplaceApplicationStateService(
        store=MemoryApplicationStateStore(),
        prepare_record=prepare_marketplace_application_record,
        decode_record=decode_marketplace_application_record,
    )
    state.initialize()
    agreement = _agreement()
    agreement_id = record_identity_text(agreement)
    state.publish(agreement)
    return state, agreement, agreement_id


def _service(
    state: MarketplaceApplicationStateService,
    *,
    performance=build_claimed_complete_performance_event,
    acceptance=build_commitment_acceptance_event,
    completion=build_commitment_completion_event,
    target=fulfillment_event_target,
    identity=record_identity_text,
):
    return MarketplaceFulfillmentCompletionPublicationService(
        state=state,
        build_claimed_complete_performance=performance,
        build_commitment_acceptance=acceptance,
        build_commitment_completion=completion,
        event_target=target,
        record_identity=identity,
    )


class M177BFulfillmentCompletionPublicationTests(unittest.TestCase):
    def test_profile_is_exact(self) -> None:
        self.assertEqual(
            PROFILE_NAME,
            "MARKETPLACE_APPLICATION_FULFILLMENT_COMPLETION_PUBLICATION_V1",
        )

    def test_each_operation_publishes_one_exact_rebound_event(self) -> None:
        cases = (
            (
                "publish_claimed_complete_performance",
                SELLER,
                CLAIMED_COMPLETE_PERFORMANCE,
            ),
            (
                "publish_commitment_acceptance",
                BUYER,
                COMMITMENT_ACCEPTANCE,
            ),
            (
                "publish_commitment_completion",
                SELLER,
                COMMITMENT_COMPLETION,
            ),
        )
        for method_name, issuer, evidence_kind in cases:
            with self.subTest(evidence_kind=evidence_kind):
                state, _agreement_record, agreement_id = _state_with_agreement()
                service = _service(state)
                watermark_before = state.sync_watermark()

                result = getattr(service, method_name)(
                    agreement_record_id=agreement_id,
                    commitment_id=COMMITMENT_ID,
                    issuer=issuer,
                )

                self.assertEqual(result.agreement_record_id, agreement_id)
                self.assertEqual(result.commitment_id, COMMITMENT_ID)
                self.assertEqual(result.evidence_kind, evidence_kind)
                self.assertGreater(state.sync_watermark(), watermark_before)
                stored = state.peek(result.record_id)
                self.assertIs(type(stored), RecordV1)
                self.assertEqual(
                    fulfillment_event_target(stored),
                    (agreement_id, COMMITMENT_ID),
                )
                self.assertEqual(record_identity_text(stored), result.record_id)

    def test_invalid_request_fails_before_state_read_or_builder(self) -> None:
        state, _agreement_record, agreement_id = _state_with_agreement()
        builder = Mock()
        service = _service(state, performance=builder)
        with patch.object(state, "peek", wraps=state.peek) as peek:
            with self.assertRaises(
                FulfillmentCompletionPublicationError
            ) as caught:
                service.publish_claimed_complete_performance(
                    agreement_record_id=agreement_id + "/bad",
                    commitment_id=COMMITMENT_ID,
                    issuer=SELLER,
                )
        self.assertEqual(
            caught.exception.code,
            "FULFILLMENT_PUBLICATION_REQUEST_INVALID",
        )
        peek.assert_not_called()
        builder.assert_not_called()

    def test_missing_agreement_fails_before_builder_and_write(self) -> None:
        state, _agreement_record, _agreement_id = _state_with_agreement()
        builder = Mock()
        service = _service(state, performance=builder)
        watermark_before = state.sync_watermark()

        with self.assertRaises(FulfillmentCompletionPublicationError) as caught:
            service.publish_claimed_complete_performance(
                agreement_record_id="r1_missing",
                commitment_id=COMMITMENT_ID,
                issuer=SELLER,
            )

        self.assertEqual(
            caught.exception.code,
            "FULFILLMENT_PUBLICATION_AGREEMENT_NOT_FOUND",
        )
        builder.assert_not_called()
        self.assertEqual(state.sync_watermark(), watermark_before)

    def test_builder_failure_never_publishes(self) -> None:
        state, _agreement_record, agreement_id = _state_with_agreement()
        service = _service(state)
        watermark_before = state.sync_watermark()

        with self.assertRaises(FulfillmentCompletionPublicationError) as caught:
            service.publish_claimed_complete_performance(
                agreement_record_id=agreement_id,
                commitment_id=COMMITMENT_ID,
                issuer=BUYER,
            )

        self.assertEqual(
            caught.exception.code,
            "FULFILLMENT_PUBLICATION_BUILD_FAILED",
        )
        self.assertEqual(state.sync_watermark(), watermark_before)

    def test_target_mismatch_blocks_before_identity_and_publish(self) -> None:
        state, _agreement_record, agreement_id = _state_with_agreement()
        identity = Mock(side_effect=AssertionError("identity must not run"))
        service = _service(
            state,
            target=lambda _event: ("r1_other", COMMITMENT_ID),
            identity=identity,
        )
        watermark_before = state.sync_watermark()

        with self.assertRaises(FulfillmentCompletionPublicationError) as caught:
            service.publish_commitment_acceptance(
                agreement_record_id=agreement_id,
                commitment_id=COMMITMENT_ID,
                issuer=BUYER,
            )

        self.assertEqual(
            caught.exception.code,
            "FULFILLMENT_PUBLICATION_BINDING_MISMATCH",
        )
        identity.assert_not_called()
        self.assertEqual(state.sync_watermark(), watermark_before)

    def test_identity_failure_blocks_before_publish(self) -> None:
        state, _agreement_record, agreement_id = _state_with_agreement()
        service = _service(
            state,
            identity=Mock(side_effect=RuntimeError("sensitive identity detail")),
        )
        watermark_before = state.sync_watermark()

        with self.assertRaises(FulfillmentCompletionPublicationError) as caught:
            service.publish_commitment_completion(
                agreement_record_id=agreement_id,
                commitment_id=COMMITMENT_ID,
                issuer=SELLER,
            )

        self.assertEqual(
            caught.exception.code,
            "FULFILLMENT_PUBLICATION_IDENTITY_FAILED",
        )
        self.assertNotIn("sensitive identity detail", str(caught.exception))
        self.assertEqual(state.sync_watermark(), watermark_before)

    def test_invalid_state_write_result_fails_closed(self) -> None:
        state, _agreement_record, agreement_id = _state_with_agreement()
        service = _service(state)
        with patch.object(state, "publish", return_value=object()) as publish:
            with self.assertRaises(
                FulfillmentCompletionPublicationError
            ) as caught:
                service.publish_commitment_acceptance(
                    agreement_record_id=agreement_id,
                    commitment_id=COMMITMENT_ID,
                    issuer=BUYER,
                )

        self.assertEqual(
            caught.exception.code,
            "FULFILLMENT_PUBLICATION_WRITE_FAILED",
        )
        publish.assert_called_once()


if __name__ == "__main__":
    unittest.main()
