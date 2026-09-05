from __future__ import annotations

import unittest

from marketplace.application.api import (
    ApplicationApiError,
    IntentIndexPage,
    MarketplaceApplicationApiService,
)
from marketplace.application.postgres_state import (
    ApplicationStatePutResult,
    ExpiryResult,
    StoreDisposition,
)
from marketplace.application.proposal import BuyerRequestProposalDraft
from marketplace.application.proposal_authoring import (
    MarketplaceProposalAuthoringService,
    ProposalAuthoringError,
)


class FakeStateService:
    def __init__(self, parent_record_id: str, parent_record: object) -> None:
        self.parent_record_id = parent_record_id
        self.parent_record = parent_record
        self.publish_calls: list[object] = []
        self.peek_calls: list[str] = []
        self.get_calls: list[str] = []

    def initialize(self):
        return ExpiryResult((), ())

    def publish(self, record):
        self.publish_calls.append(record)
        return ApplicationStatePutResult(StoreDisposition.STORED, 11)

    def peek(self, record_id):
        self.peek_calls.append(record_id)
        if record_id == self.parent_record_id:
            return self.parent_record
        return None

    def get(self, record_id):
        self.get_calls.append(record_id)
        if record_id == self.parent_record_id:
            return self.parent_record
        return None

    def response_ids(self, record_id, *, limit=64):
        return ()

    def sync_since(self, cursor, *, limit=128):
        raise AssertionError("sync is outside M17.1U")

    def sync_watermark(self):
        return 0


class FakeIntentQuery:
    def list_intent_ids(self, *, cursor, limit):
        return IntentIndexPage((), None)


class M17StructuredProposalAuthoringTests(unittest.TestCase):
    PARENT_ID = "r-parent"

    def make_api(self):
        parent_record = object()
        state = FakeStateService(self.PARENT_ID, parent_record)
        parents: dict[int, tuple[str, ...]] = {}
        api = MarketplaceApplicationApiService(
            state=state,
            intent_query=FakeIntentQuery(),
            response_parent_ids=lambda record: tuple(parents.get(id(record), ())),
            is_intent_record=lambda record: True,
        )
        return api, state, parents

    def draft(self, **changes):
        values = {
            "buyer_principal": "did:example:buyer",
            "subject_uri": "urn:sku:moon-widget",
            "action_uri": "https://open-trust-layer.github.io/marketplace/semantics/v1/action/request",
            "parent_record_id": self.PARENT_ID,
        }
        values.update(changes)
        return BuyerRequestProposalDraft(**values)

    def test_reviewed_draft_builds_once_and_responds_through_existing_api(self):
        api, state, parents = self.make_api()
        api.initialize()
        built: list[BuyerRequestProposalDraft] = []
        response_record = object()
        parents[id(response_record)] = (self.PARENT_ID,)

        def build(draft: BuyerRequestProposalDraft):
            built.append(draft)
            return response_record

        service = MarketplaceProposalAuthoringService(api=api, build_record=build)
        original = self.draft()
        result = service.create_buyer_request_proposal(original)

        self.assertEqual(result.change_seq, 11)
        self.assertEqual(state.publish_calls, [response_record])
        self.assertEqual(state.peek_calls, [self.PARENT_ID])
        self.assertEqual(state.get_calls, [self.PARENT_ID])
        self.assertEqual(len(built), 1)
        self.assertIsNot(built[0], original)
        self.assertEqual(built[0], original)

    def test_tampered_draft_fails_before_builder_or_api_state_access(self):
        api, state, _ = self.make_api()
        api.initialize()
        build_calls: list[object] = []
        service = MarketplaceProposalAuthoringService(
            api=api,
            build_record=lambda draft: build_calls.append(draft),
        )
        draft = self.draft()
        object.__setattr__(draft, "subject_uri", "not-an-absolute-uri")

        with self.assertRaises(ProposalAuthoringError) as caught:
            service.create_buyer_request_proposal(draft)

        self.assertEqual(caught.exception.code, "PROPOSAL_DRAFT_INVALID")
        self.assertIsNone(caught.exception.__cause__)
        self.assertEqual(build_calls, [])
        self.assertEqual(state.peek_calls, [])
        self.assertEqual(state.get_calls, [])
        self.assertEqual(state.publish_calls, [])

    def test_builder_failure_is_stable_and_non_reflective(self):
        api, state, _ = self.make_api()
        api.initialize()

        def fail_builder(draft):
            raise RuntimeError("secret builder detail")

        service = MarketplaceProposalAuthoringService(api=api, build_record=fail_builder)
        with self.assertRaises(ProposalAuthoringError) as caught:
            service.create_buyer_request_proposal(self.draft())

        self.assertEqual(caught.exception.code, "PROPOSAL_BUILD_FAILED")
        self.assertNotIn("secret", str(caught.exception).lower())
        self.assertIsNone(caught.exception.__cause__)
        self.assertEqual(state.publish_calls, [])

    def test_response_parent_mismatch_is_rejected_by_existing_api(self):
        api, state, parents = self.make_api()
        api.initialize()
        response_record = object()
        parents[id(response_record)] = ("r-other",)
        service = MarketplaceProposalAuthoringService(
            api=api,
            build_record=lambda draft: response_record,
        )

        with self.assertRaises(ApplicationApiError) as caught:
            service.create_buyer_request_proposal(self.draft())

        self.assertEqual(caught.exception.code, "RESPONSE_PARENT_MISMATCH")
        self.assertEqual(state.peek_calls, [])
        self.assertEqual(state.get_calls, [])
        self.assertEqual(state.publish_calls, [])

    def test_missing_parent_is_rejected_by_existing_api(self):
        api, state, parents = self.make_api()
        api.initialize()
        response_record = object()
        parents[id(response_record)] = (self.PARENT_ID,)
        state.parent_record_id = "r-different"
        service = MarketplaceProposalAuthoringService(
            api=api,
            build_record=lambda draft: response_record,
        )

        with self.assertRaises(ApplicationApiError) as caught:
            service.create_buyer_request_proposal(self.draft())

        self.assertEqual(caught.exception.code, "PARENT_INTENT_NOT_FOUND")
        self.assertEqual(state.peek_calls, [self.PARENT_ID])
        self.assertEqual(state.get_calls, [])
        self.assertEqual(state.publish_calls, [])

    def test_uninitialized_application_api_remains_authoritative(self):
        api, state, parents = self.make_api()
        response_record = object()
        parents[id(response_record)] = (self.PARENT_ID,)
        service = MarketplaceProposalAuthoringService(
            api=api,
            build_record=lambda draft: response_record,
        )

        with self.assertRaises(ApplicationApiError) as caught:
            service.create_buyer_request_proposal(self.draft())

        self.assertEqual(caught.exception.code, "APPLICATION_API_NOT_INITIALIZED")
        self.assertEqual(state.peek_calls, [])
        self.assertEqual(state.publish_calls, [])

    def test_requires_exact_draft_value(self):
        api, _, _ = self.make_api()
        service = MarketplaceProposalAuthoringService(
            api=api,
            build_record=lambda draft: object(),
        )
        with self.assertRaises(TypeError):
            service.create_buyer_request_proposal(object())  # type: ignore[arg-type]


if __name__ == "__main__":
    unittest.main()
