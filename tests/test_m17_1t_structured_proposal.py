from __future__ import annotations

import unittest

from marketplace.application.proposal import (
    MAX_PROPOSAL_PARENT_RECORD_ID_CHARS,
    BuyerRequestProposalDraft,
)


class M17StructuredProposalDraftTests(unittest.TestCase):
    def draft(self, **changes):
        values = {
            "buyer_principal": "did:example:buyer",
            "subject_uri": "urn:sku:moon-widget",
            "action_uri": "https://example.test/actions/buy",
            "parent_record_id": "r1_" + "A" * 43,
        }
        values.update(changes)
        return BuyerRequestProposalDraft(**values)

    def test_accepts_bounded_core_buyer_request_fields(self):
        draft = self.draft()
        self.assertEqual(draft.buyer_principal, "did:example:buyer")
        self.assertEqual(draft.subject_uri, "urn:sku:moon-widget")
        self.assertEqual(draft.action_uri, "https://example.test/actions/buy")
        self.assertEqual(draft.parent_record_id, "r1_" + "A" * 43)

    def test_rejects_non_absolute_or_unbounded_uri_fields(self):
        for field in ("buyer_principal", "subject_uri", "action_uri"):
            with self.subTest(field=field):
                with self.assertRaises(ValueError):
                    self.draft(**{field: "not an absolute uri"})
        with self.assertRaises(ValueError):
            self.draft(action_uri="https://example.test/" + "x" * 2048)

    def test_rejects_invalid_parent_application_shape(self):
        with self.assertRaises(ValueError):
            self.draft(parent_record_id="")
        with self.assertRaises(ValueError):
            self.draft(parent_record_id="r" * (MAX_PROPOSAL_PARENT_RECORD_ID_CHARS + 1))
        with self.assertRaises(ValueError):
            self.draft(parent_record_id="\ud800")

    def test_rejects_type_subclasses_and_non_text(self):
        class Text(str):
            pass

        for field in ("buyer_principal", "subject_uri", "action_uri", "parent_record_id"):
            with self.subTest(field=field):
                with self.assertRaises(ValueError):
                    self.draft(**{field: Text("did:example:value")})


if __name__ == "__main__":
    unittest.main()
