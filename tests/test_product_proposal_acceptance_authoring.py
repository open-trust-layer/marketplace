from __future__ import annotations

import unittest

from marketplace.application.listing import ExactDecimal, ProductListingDraft, UNIT_ITEM
from marketplace.application.postgres_state import (
    ApplicationStatePutResult,
    ExpiryResult,
    PreparedApplicationRecord,
    StoreDisposition,
    SyncPage,
)
from marketplace.application.proposal_acceptance import (
    MarketplaceProposalAcceptanceAuthoringService,
    ProposalAcceptanceAuthoringError,
)
from marketplace.application.state import MarketplaceApplicationStateService


SELLER = "did:example:seller"
OTHER = "did:example:other"
PROPOSAL_ID = "r-proposal"
LISTING_ID = "r-listing"
ACCEPTANCE_ID = "r-acceptance"


class FakeStore:
    def __init__(self, objects: dict[str, object]) -> None:
        self.objects = dict(objects)
        self.prepared = {
            record_id: PreparedApplicationRecord(record_id, record_id.encode("ascii"))
            for record_id in objects
        }
        self.put_calls: list[PreparedApplicationRecord] = []

    def initialize(self):
        return ExpiryResult((), ())

    def put(self, prepared):
        self.put_calls.append(prepared)
        return ApplicationStatePutResult(StoreDisposition.STORED, 7)

    def get(self, record_id):
        return self.prepared.get(record_id)

    def peek(self, record_id):
        return self.prepared.get(record_id)

    def list_response_ids(self, parent_record_id, *, limit):
        return ()

    def sync_since(self, cursor_value, *, limit):
        return SyncPage((), cursor_value, False)

    def sync_watermark(self):
        return 0


def listing(seller=SELLER):
    return ProductListingDraft(
        seller_principal=seller,
        subject_uri="urn:sku:moon-widget",
        title="Moon widget",
        description="Reviewed listing.",
        consideration=ExactDecimal(1, 0),
        currency_code="EUR",
        quantity=ExactDecimal(1, 0),
        unit_uri=UNIT_ITEM,
        latitude_e6=1,
        longitude_e6=1,
    )


def make_service(*, objects=None, builder=None, relation=None, predicate=None, extractor=None):
    source = objects or {
        PROPOSAL_ID: {"kind": "proposal"},
        LISTING_ID: {"kind": "listing"},
    }
    store = FakeStore(source)

    def prepare(record):
        return PreparedApplicationRecord(ACCEPTANCE_ID, b"acceptance")

    def decode(data):
        record_id = data.decode("ascii")
        return source[record_id]

    state = MarketplaceApplicationStateService(
        store=store,
        prepare_record=prepare,
        decode_record=decode,
    )
    state.initialize()
    built: list[tuple[str, str]] = []

    def default_builder(seller, proposal_id):
        built.append((seller, proposal_id))
        return {"kind": "acceptance", "proposal": proposal_id}

    service = MarketplaceProposalAcceptanceAuthoringService(
        state=state,
        is_proposal_record=predicate or (lambda record: record.get("kind") == "proposal"),
        proposal_parent_ids=lambda record: (LISTING_ID,),
        extract_product_listing=extractor or (lambda record: listing()),
        build_record=builder or default_builder,
        acceptance_proposal_id=relation or (lambda record: record["proposal"]),
        record_identity=lambda record: ACCEPTANCE_ID,
    )
    return service, store, built


class ProposalAcceptanceAuthoringTests(unittest.TestCase):
    def test_success_derives_listing_owner_and_publishes_once(self) -> None:
        service, store, built = make_service()
        result = service.accept_proposal(
            seller_principal=SELLER,
            proposal_record_id=PROPOSAL_ID,
        )
        self.assertEqual(result.to_document(), {
            "change_seq": 7,
            "disposition": "STORED",
            "record_id": ACCEPTANCE_ID,
        })
        self.assertEqual(built, [(SELLER, PROPOSAL_ID)])
        self.assertEqual(len(store.put_calls), 1)
        self.assertEqual(store.put_calls[0].record_id, ACCEPTANCE_ID)

    def test_seller_mismatch_blocks_before_build_or_publish(self) -> None:
        service, store, built = make_service()
        with self.assertRaises(ProposalAcceptanceAuthoringError) as caught:
            service.accept_proposal(
                seller_principal=OTHER,
                proposal_record_id=PROPOSAL_ID,
            )
        self.assertEqual(caught.exception.code, "PROPOSAL_ACCEPTANCE_SELLER_MISMATCH")
        self.assertEqual(built, [])
        self.assertEqual(store.put_calls, [])

    def test_missing_or_invalid_proposal_fails_closed(self) -> None:
        cases = (
            ("r-missing", {LISTING_ID: {"kind": "listing"}}, None, "PROPOSAL_ACCEPTANCE_PROPOSAL_NOT_FOUND"),
            (PROPOSAL_ID, None, lambda record: False, "PROPOSAL_ACCEPTANCE_PROPOSAL_INVALID"),
        )
        for proposal_id, objects, predicate, code in cases:
            with self.subTest(code=code):
                service, store, _ = make_service(objects=objects, predicate=predicate)
                with self.assertRaises(ProposalAcceptanceAuthoringError) as caught:
                    service.accept_proposal(seller_principal=SELLER, proposal_record_id=proposal_id)
                self.assertEqual(caught.exception.code, code)
                self.assertEqual(store.put_calls, [])

    def test_relation_mismatch_blocks_before_publish(self) -> None:
        service, store, built = make_service(relation=lambda record: "r-other")
        with self.assertRaises(ProposalAcceptanceAuthoringError) as caught:
            service.accept_proposal(
                seller_principal=SELLER,
                proposal_record_id=PROPOSAL_ID,
            )
        self.assertEqual(caught.exception.code, "PROPOSAL_ACCEPTANCE_BINDING_MISMATCH")
        self.assertEqual(built, [(SELLER, PROPOSAL_ID)])
        self.assertEqual(store.put_calls, [])


if __name__ == "__main__":
    unittest.main()
