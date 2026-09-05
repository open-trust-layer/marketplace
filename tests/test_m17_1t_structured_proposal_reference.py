from __future__ import annotations

import unittest

from olp.model.evidence import EvidenceKind, EvidenceRefV1
from olp.transport import encode_identity_text

from marketplace.application.proposal import BuyerRequestProposalDraft
from marketplace.reference.proposal_v1 import (
    ProposalProfileError,
    build_buyer_request_proposal_record,
)
from marketplace.reference.record_v1 import (
    CORE_PROFILE,
    PROPOSAL_PROFILE,
    TYPE_INTENT,
    validate_market_record,
)


class M17StructuredProposalReferenceTests(unittest.TestCase):
    def draft(self, **changes):
        values = {
            "buyer_principal": "did:example:buyer",
            "subject_uri": "urn:sku:moon-widget",
            "action_uri": "https://example.test/actions/buy",
            "parent_record_id": encode_identity_text("record", b"\x11" * 32),
        }
        values.update(changes)
        return BuyerRequestProposalDraft(**values)

    def test_builds_one_valid_core_proposal_bound_to_exact_parent(self):
        parent = encode_identity_text("record", b"\x11" * 32)
        record = build_buyer_request_proposal_record(self.draft(parent_record_id=parent))
        validate_market_record(record)

        self.assertEqual(record.type, TYPE_INTENT)
        self.assertEqual(set(record.profiles), {CORE_PROFILE, PROPOSAL_PROFILE})
        self.assertEqual(len(record.profiles), 2)
        self.assertEqual(record.content["issuer"], {"principal": "did:example:buyer"})
        self.assertEqual(record.content["subjects"], ({"uri": "urn:sku:moon-widget"},))
        self.assertEqual(record.content["action"], {"id": "https://example.test/actions/buy"})
        self.assertEqual(record.content["terms"], {})
        self.assertEqual(len(record.content["response_to"]), 1)
        parent_ref = EvidenceRefV1.from_value(record.content["response_to"][0])
        self.assertEqual(parent_ref.kind, EvidenceKind.RECORD)
        self.assertEqual(parent_ref.identity_digest, b"\x11" * 32)

    def test_malformed_or_wrong_kind_parent_fails_non_reflectively(self):
        for parent in ("r1_not-valid", encode_identity_text("proof", b"\x22" * 32)):
            with self.subTest(parent=parent[:3]):
                with self.assertRaises(ProposalProfileError) as caught:
                    build_buyer_request_proposal_record(self.draft(parent_record_id=parent))
                self.assertEqual(caught.exception.code, "PROPOSAL_PARENT_ID_INVALID")
                self.assertNotIn(parent, str(caught.exception))
                self.assertIsNone(caught.exception.__cause__)

    def test_tampered_frozen_draft_is_revalidated_before_olp_construction(self):
        draft = self.draft()
        object.__setattr__(draft, "action_uri", object())
        with self.assertRaises(ProposalProfileError) as caught:
            build_buyer_request_proposal_record(draft)
        self.assertEqual(caught.exception.code, "PROPOSAL_DRAFT_INVALID")
        self.assertIsNone(caught.exception.__cause__)

    def test_requires_exact_draft_type(self):
        with self.assertRaises(TypeError):
            build_buyer_request_proposal_record(object())  # type: ignore[arg-type]


if __name__ == "__main__":
    unittest.main()
