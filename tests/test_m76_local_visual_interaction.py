from __future__ import annotations

from dataclasses import FrozenInstanceError
import unittest

from marketplace.reference.local_visual_v1 import (
    LocalVisualInteractionError,
    LocalVisualSubmission,
    render_local_buy_sell_form,
    submit_local_buy_sell_form,
)


def valid_submission() -> LocalVisualSubmission:
    return LocalVisualSubmission(
        seller_principal="did:example:seller",
        subject_uri="urn:example:product:bicycle-1",
        title="City bicycle",
        description="One carefully maintained bicycle.",
        consideration="125.00",
        currency_code="EUR",
        quantity="1",
        unit_uri="https://open-trust-layer.github.io/marketplace/semantics/v1/profile/product-listing-v1/unit/item",
        latitude="52.520000",
        longitude="13.405000",
        buyer_principal="did:example:buyer",
        buyer_action_uri="https://example.test/actions/buy",
    )


class M76LocalVisualInteractionTests(unittest.TestCase):
    def test_form_is_deterministic_self_contained_and_inert(self):
        first = render_local_buy_sell_form()
        second = render_local_buy_sell_form()

        self.assertEqual(first, second)
        self.assertIn('<form method="post" action="/local-buy-sell">', first)
        for field in (
            "seller_principal",
            "subject_uri",
            "title",
            "description",
            "consideration",
            "currency_code",
            "quantity",
            "unit_uri",
            "latitude",
            "longitude",
            "buyer_principal",
            "buyer_action_uri",
        ):
            self.assertIn(f'name="{field}"', first)
        lowered = first.lower()
        self.assertNotIn("<script", lowered)
        self.assertNotIn("<iframe", lowered)
        self.assertNotIn("src=", lowered)
        self.assertNotIn("http://", lowered)
        self.assertNotIn("https://", lowered)
        self.assertIn("no agreement", lowered)
        self.assertIn("no payment", lowered)

    def test_exact_submission_completes_reviewed_m75_path_and_returns_bounded_html(self):
        submission = valid_submission()

        page = submit_local_buy_sell_form(submission)

        self.assertIn("COMPATIBLE_UNDER_METHOD", page)
        self.assertIn("seller_record_id=r1_", page)
        self.assertIn("buyer_record_id=r1_", page)
        self.assertIn("protocol_truth=false", page)
        self.assertIn("creates_agreement=false", page)
        self.assertNotIn(submission.description, page)
        self.assertNotIn(submission.buyer_principal, page)
        self.assertNotIn(submission.buyer_action_uri, page)
        lowered = page.lower()
        self.assertNotIn("<script", lowered)
        self.assertNotIn("<iframe", lowered)
        self.assertNotIn("http://", lowered)
        self.assertNotIn("https://", lowered)

    def test_submission_is_frozen_and_exact_type_is_required(self):
        submission = valid_submission()
        with self.assertRaises(FrozenInstanceError):
            submission.title = "changed"  # type: ignore[misc]

        class DerivedSubmission(LocalVisualSubmission):
            pass

        derived = DerivedSubmission(**{
            field: getattr(submission, field)
            for field in submission.__dataclass_fields__
        })
        with self.assertRaises(LocalVisualInteractionError) as raised:
            submit_local_buy_sell_form(derived)
        self.assertEqual(raised.exception.code, "SUBMISSION_INVALID")

    def test_hostile_invalid_value_fails_without_reflection(self):
        submission = valid_submission()
        hostile = "12.3.4-HOSTILE"
        invalid = LocalVisualSubmission(
            seller_principal=submission.seller_principal,
            subject_uri=submission.subject_uri,
            title=submission.title,
            description=submission.description,
            consideration=hostile,
            currency_code=submission.currency_code,
            quantity=submission.quantity,
            unit_uri=submission.unit_uri,
            latitude=submission.latitude,
            longitude=submission.longitude,
            buyer_principal=submission.buyer_principal,
            buyer_action_uri=submission.buyer_action_uri,
        )

        with self.assertRaises(LocalVisualInteractionError) as raised:
            submit_local_buy_sell_form(invalid)

        self.assertEqual(raised.exception.code, "SUBMISSION_INVALID")
        self.assertNotIn(hostile, str(raised.exception))

    def test_non_text_field_fails_closed_through_reviewed_m75_validation(self):
        submission = valid_submission()
        invalid = LocalVisualSubmission(
            seller_principal=b"did:example:seller",  # type: ignore[arg-type]
            subject_uri=submission.subject_uri,
            title=submission.title,
            description=submission.description,
            consideration=submission.consideration,
            currency_code=submission.currency_code,
            quantity=submission.quantity,
            unit_uri=submission.unit_uri,
            latitude=submission.latitude,
            longitude=submission.longitude,
            buyer_principal=submission.buyer_principal,
            buyer_action_uri=submission.buyer_action_uri,
        )

        with self.assertRaises(LocalVisualInteractionError) as raised:
            submit_local_buy_sell_form(invalid)

        self.assertEqual(raised.exception.code, "SUBMISSION_INVALID")


if __name__ == "__main__":
    unittest.main()
