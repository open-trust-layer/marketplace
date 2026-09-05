import unittest

from olp import RecordV1
from olp.encoding.record_identity import record_identity_text
from olp.model.evidence import EvidenceRefV1
from olp.transport import encode_identity_text

from marketplace.application.api import IntentIndexPage
from marketplace.application.authoring import ProductListingAuthoringFields
from marketplace.application.listing import PRODUCT_LISTING_PROFILE, UNIT_ITEM
from marketplace.application.postgres_state import (
    ApplicationStatePutResult,
    ExpiryResult,
    PreparedApplicationRecord,
    SyncPage,
)
from marketplace.application.proposal import BuyerRequestProposalDraft
from marketplace.reference.application_v1 import build_reference_marketplace_application_launch_plan
from marketplace.reference.application_record_v1 import decode_marketplace_application_record
from marketplace.reference.product_listing_v1 import build_product_listing_record
from marketplace.reference.proposal_v1 import build_buyer_request_proposal_record
from marketplace.reference.record_v1 import PROPOSAL_PROFILE, TYPE_INTENT
from marketplace.runtime.contracts import StoreDisposition


class MemoryStateStore:
    def __init__(self) -> None:
        self.records: dict[str, PreparedApplicationRecord] = {}
        self.decoded: dict[bytes, RecordV1] = {}
        self.captured: list[RecordV1] = []
        self.change_seq = 0

    def initialize(self) -> ExpiryResult:
        return ExpiryResult((), ())

    def prepare(self, record: object) -> PreparedApplicationRecord:
        if type(record) is not RecordV1:
            raise TypeError("test preparer requires exact RecordV1")
        record_id = record_identity_text(record)
        canonical = record_id.encode("ascii")
        parents: tuple[str, ...] = ()
        if PROPOSAL_PROFILE in record.profiles:
            refs = tuple(record.content["response_to"])
            parents = tuple(
                encode_identity_text("record", EvidenceRefV1.from_value(value).identity_digest)
                for value in refs
            )
        self.decoded[canonical] = record
        self.captured.append(record)
        return PreparedApplicationRecord(record_id, canonical, parents)

    def decode(self, canonical: bytes) -> RecordV1:
        return self.decoded[canonical]

    def put(self, prepared: PreparedApplicationRecord) -> ApplicationStatePutResult:
        self.change_seq += 1
        self.records[prepared.record_id] = prepared
        self.captured.append(decode_marketplace_application_record(prepared.canonical_record))
        return ApplicationStatePutResult(StoreDisposition.STORED, self.change_seq)

    def get(self, record_id: str) -> PreparedApplicationRecord | None:
        return self.records.get(record_id)

    def peek(self, record_id: str) -> PreparedApplicationRecord | None:
        return self.records.get(record_id)

    def list_response_ids(self, parent_record_id: str, *, limit: int) -> tuple[str, ...]:
        values = tuple(
            record_id
            for record_id, prepared in sorted(self.records.items())
            if parent_record_id in prepared.response_to
        )
        return values[:limit]

    def sync_since(self, cursor_value: int, *, limit: int) -> SyncPage:
        return SyncPage((), cursor_value, False)

    def sync_watermark(self) -> int:
        return self.change_seq


class EmptyIntentQuery:
    def list_intent_ids(self, *, cursor: str | None, limit: int) -> IntentIndexPage:
        return IntentIndexPage(())


def response_parent_ids(record: object) -> tuple[str, ...]:
    if type(record) is not RecordV1 or PROPOSAL_PROFILE not in record.profiles:
        return ()
    return tuple(
        encode_identity_text("record", EvidenceRefV1.from_value(value).identity_digest)
        for value in record.content["response_to"]
    )


def is_intent_record(record: object) -> bool:
    return type(record) is RecordV1 and record.type == TYPE_INTENT


def unused_decode_json(body: bytes) -> object:
    raise AssertionError("raw JSON decoder must remain unused by structured authoring integration")


def unused_encode_json(record: object) -> bytes:
    raise AssertionError("raw JSON encoder must remain unused by structured authoring integration")


class M17ReferenceStructuredAuthoringTests(unittest.TestCase):
    def plan(self):
        store = MemoryStateStore()
        plan = build_reference_marketplace_application_launch_plan(
            host="127.0.0.1",
            port=48732,
            store=store,
            intent_query=EmptyIntentQuery(),
            decode_record_json=unused_decode_json,
            encode_record_json=unused_encode_json,
            index_html=b"<!doctype html>",
            app_js=b"'use strict';",
            styles_css=b"body{}",
        )
        return plan, store

    def test_factory_binds_exact_reviewed_reference_builders(self):
        plan, _ = self.plan()
        self.assertIs(plan.composition.authoring._build_record, build_product_listing_record)
        self.assertIs(
            plan.composition.proposal_authoring._build_record,
            build_buyer_request_proposal_record,
        )

    def test_structured_listing_then_proposal_materialize_genuine_records(self):
        plan, store = self.plan()
        plan.composition.initialize()

        listing_result = plan.composition.authoring.create_product_listing(
            ProductListingAuthoringFields(
                seller_principal="did:example:seller",
                subject_uri="urn:example:item:bicycle",
                title="Berlin bicycle",
                description="Reviewed structured listing",
                consideration_coefficient=125,
                consideration_scale=2,
                currency_code="EUR",
                quantity_coefficient=1,
                quantity_scale=0,
                unit_uri=UNIT_ITEM,
                latitude_e6=52_520_000,
                longitude_e6=13_405_000,
            )
        )
        self.assertEqual(listing_result.disposition, StoreDisposition.STORED)
        listing = store.captured[-1]
        self.assertIs(type(listing), RecordV1)
        self.assertIn(PRODUCT_LISTING_PROFILE, listing.profiles)
        parent_record_id = record_identity_text(listing)

        proposal_result = plan.composition.proposal_authoring.create_buyer_request_proposal(
            BuyerRequestProposalDraft(
                buyer_principal="did:example:buyer",
                subject_uri="urn:example:item:bicycle",
                action_uri="https://example.test/actions/buy",
                parent_record_id=parent_record_id,
            )
        )
        self.assertEqual(proposal_result.disposition, StoreDisposition.STORED)
        proposal = store.captured[-1]
        self.assertIs(type(proposal), RecordV1)
        self.assertIn(PROPOSAL_PROFILE, proposal.profiles)
        self.assertEqual(response_parent_ids(proposal), (parent_record_id,))
        proposal_record_id = record_identity_text(proposal)
        self.assertEqual(store.records[proposal_record_id].response_to, (parent_record_id,))
        self.assertIn(proposal_record_id, store.list_response_ids(parent_record_id, limit=64))


if __name__ == "__main__":
    unittest.main()