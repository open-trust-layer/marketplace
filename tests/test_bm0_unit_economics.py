"""Synthetic-only contract tests: no customer data, remote calls or financial actions."""
from __future__ import annotations

from dataclasses import FrozenInstanceError
from decimal import Decimal
import unittest

from tools.bm0_unit_economics import (
    BM0ModelError, OfflineScenario, OperatorCost,
    break_even_eligible_orders, evaluate_synthetic,
)


def D(amount: str) -> Decimal:
    return Decimal(amount)


def case(**changes: object) -> OfflineScenario:
    values = dict(
        scenario_id="fixture", currency="USD", tax_basis="EXCLUSIVE",
        completed_orders=0, eligible_orders=0,
        goods_gmv=D("0"), operator_fee_gross=D("0"),
    )
    values.update(changes)
    return OfflineScenario(**values)


def cost(cid: str, stream: str, amount: str) -> OperatorCost:
    return OperatorCost(cid, stream, D(amount))


class BM0OfflineUnitEconomicsTests(unittest.TestCase):
    def fails(self, code: str, **fields: object) -> None:
        with self.assertRaises(BM0ModelError) as raised:
            case(**fields)
        self.assertEqual(raised.exception.code, code)
        self.assertEqual(str(raised.exception), code)

    def test_f01_operator_fee_support_psp_fixed_and_refunds(self):
        result = evaluate_synthetic(case(
            completed_orders=10, eligible_orders=5, goods_gmv=D("1000"),
            operator_fee_gross=D("20.00"), operator_fee_reversals=D("2.00"),
            costs=(cost("psp", "marketplace", "1.00"),
                   cost("support", "marketplace", "1.50"),
                   cost("hosting", "marketplace", "0.50"),
                   cost("fixed", "fixed", "20.00")),
        ))
        self.assertEqual(result.marketplace_revenue, D("18.00"))
        self.assertEqual(result.variable_cost, D("3.00"))
        self.assertEqual(result.contribution, D("15.00"))
        self.assertEqual(result.operating_result, D("-5.00"))
        self.assertEqual(result.total_operator_revenue, D("18.00"))
        self.assertEqual(result.goods_gmv_outside_revenue, D("1000"))
        self.assertEqual(result.launch_status, "NOT_AUTHORIZED")

    def test_f02_no_optional_fee_even_when_gmv_positive(self):
        result = evaluate_synthetic(case(
            completed_orders=10, eligible_orders=0, goods_gmv=D("1000"),
            seller_pass_through=D("1000"), costs=(cost("rent", "fixed", "5"),),
        ))
        self.assertEqual(result.total_operator_revenue, D("0"))
        self.assertEqual(result.operating_result, D("-5"))
        self.assertEqual(result.seller_pass_through_outside_revenue, D("1000"))

    def test_f03_seller_managed_shipping_is_not_brokerage(self):
        result = evaluate_synthetic(case(
            completed_orders=1, goods_gmv=D("100"),
            courier_pass_through=D("12"),
        ))
        self.assertEqual(result.brokerage_revenue, D("0"))
        self.assertEqual(result.courier_pass_through_outside_revenue, D("12"))
        self.assertEqual(result.total_operator_revenue, D("0"))

    def test_f04_complete_fee_refund_preserves_losses(self):
        result = evaluate_synthetic(case(
            completed_orders=1, eligible_orders=1, goods_gmv=D("100"),
            operator_fee_gross=D("4"), operator_fee_reversals=D("4"),
            costs=(cost("unrecovered", "marketplace", "0.40"),),
        ))
        self.assertEqual(result.marketplace_revenue, D("0"))
        self.assertEqual(result.operating_result, D("-0.40"))

    def test_f05_break_even_and_nonpositive_margin(self):
        self.assertEqual(break_even_eligible_orders(D("20"), D("3")), 7)
        self.assertEqual(break_even_eligible_orders(D("0"), D("3")), 0)
        self.assertIsNone(break_even_eligible_orders(D("20"), D("0")))
        self.assertIsNone(break_even_eligible_orders(D("20"), D("-2")))

    def test_f06_pro_period_not_counted_as_marketplace_fees(self):
        result = evaluate_synthetic(case(
            pro_gross=D("30"), costs=(cost("seller_pro_work", "pro", "6"),),
        ))
        self.assertEqual(result.pro_revenue, D("30"))
        self.assertEqual(result.marketplace_revenue, D("0"))
        self.assertEqual(result.total_operator_revenue, D("30"))
        self.assertEqual(result.contribution, D("24"))

    def test_no_orders_means_zero_transaction_fee_not_zero_fixed_cost(self):
        result = evaluate_synthetic(case(costs=(cost("fixed", "fixed", "9"),)))
        self.assertEqual(result.marketplace_revenue, D("0"))
        self.assertEqual(result.operating_result, D("-9"))

    def test_higher_cost_or_fee_reversal_cannot_increase_margin(self):
        baseline = evaluate_synthetic(case(
            completed_orders=1, eligible_orders=1, operator_fee_gross=D("5"),
        ))
        increased_cost = evaluate_synthetic(case(
            completed_orders=1, eligible_orders=1, operator_fee_gross=D("5"),
            costs=(cost("extra", "marketplace", "1"),),
        ))
        increased_refund = evaluate_synthetic(case(
            completed_orders=1, eligible_orders=1, operator_fee_gross=D("5"),
            operator_fee_reversals=D("1"),
        ))
        self.assertLess(increased_cost.contribution, baseline.contribution)
        self.assertLess(increased_refund.contribution, baseline.contribution)

    def test_pass_through_and_tax_are_never_operator_revenue(self):
        result = evaluate_synthetic(case(
            completed_orders=1, goods_gmv=D("120"),
            seller_pass_through=D("120"), courier_pass_through=D("15"),
            tax_pass_through=D("19"),
        ))
        self.assertEqual(result.total_operator_revenue, D("0"))
        self.assertEqual(result.tax_pass_through_outside_revenue, D("19"))
        self.assertEqual(result.seller_pass_through_outside_revenue, D("120"))
        self.assertEqual(result.courier_pass_through_outside_revenue, D("15"))

    def test_genuine_brokerage_is_separate_and_reversible(self):
        result = evaluate_synthetic(case(
            brokerage_gross=D("4.00"), brokerage_reversals=D("1.00"),
            courier_pass_through=D("75.00"),
            costs=(cost("courier_coordination", "logistics", "0.50"),),
        ))
        self.assertEqual(result.brokerage_revenue, D("3"))
        self.assertEqual(result.contribution, D("2.50"))
        self.assertEqual(result.total_operator_revenue, D("3"))

    def test_managed_service_is_separate_stream(self):
        result = evaluate_synthetic(case(
            managed_gross=D("100"), managed_reversals=D("10"),
            pro_gross=D("20"),
            costs=(cost("hosting", "managed", "40"),),
        ))
        self.assertEqual(result.managed_revenue, D("90"))
        self.assertEqual(result.pro_revenue, D("20"))
        self.assertEqual(result.total_operator_revenue, D("110"))
        self.assertEqual(result.operating_result, D("70"))

    def test_exact_decimal_and_period_reconciliation(self):
        s = case(
            completed_orders=2, eligible_orders=2,
            operator_fee_gross=D("0.1") + D("0.2"),
            pro_gross=D("0.3"), brokerage_gross=D("0.4"),
            managed_gross=D("0.5"),
        )
        r = evaluate_synthetic(s)
        self.assertEqual(r.marketplace_revenue, D("0.3"))
        self.assertEqual(
            r.total_operator_revenue,
            r.marketplace_revenue + r.pro_revenue
            + r.brokerage_revenue + r.managed_revenue,
        )
        self.assertEqual(r.total_operator_revenue, D("1.5"))

    def test_reject_ineligible_operator_fees(self):
        self.fails("INELIGIBLE_OPERATOR_FEE", operator_fee_gross=D("1"))

    def test_reject_order_count_type_bounds(self):
        for invalid in (-1, True, 1.25, "1"):
            with self.subTest(value=repr(invalid)):
                self.fails("ORDER_COUNTS_INVALID", completed_orders=invalid)
        self.fails("ORDER_COUNTS_INVALID", completed_orders=1, eligible_orders=2)

    def test_reject_invalid_money_inputs(self):
        for invalid in (None, 1, 1.0, "1.0", D("NaN"), D("Infinity")):
            with self.subTest(value=repr(invalid)):
                self.fails("AMOUNT_INVALID", pro_gross=invalid)
        self.fails("AMOUNT_NEGATIVE", goods_gmv=D("-1"))

    def test_reject_reversal_greater_than_gross(self):
        self.fails("REVERSAL_EXCEEDS_GROSS", pro_gross=D("1"), pro_reversals=D("2"))

    def test_reject_mixed_currency_unreviewed_tax_and_non_agent_role(self):
        self.fails("CURRENCY_INVALID", currency="usd")
        self.fails("TAX_BASIS_UNSUPPORTED", tax_basis="INCLUSIVE")
        self.fails("OPERATOR_ROLE_UNSUPPORTED", operator_role="PRINCIPAL")
        self.fails("SYNTHETIC_DATA_REQUIRED", source_status="OBSERVED")

    def test_duplicate_cost_ids_are_not_double_counted(self):
        self.fails("COST_ID_DUPLICATE", costs=(
            cost("same", "pro", "2"), cost("same", "fixed", "2"),
        ))

    def test_cost_ids_streams_and_line_shapes_fail_closed(self):
        with self.assertRaises(BM0ModelError):
            OperatorCost("client/secret", "fixed", D("1"))
        with self.assertRaises(BM0ModelError):
            OperatorCost("valid", "protocol_fee", D("1"))
        self.fails("COST_LEDGER_INVALID", costs=[cost("x", "fixed", "1")])

    def test_input_is_immutable_and_no_external_action_authorized(self):
        item = case()
        with self.assertRaises(FrozenInstanceError):
            item.currency = "EUR"
        r = evaluate_synthetic(item)
        self.assertEqual(r.evidence_status, "SYNTHETIC_ONLY")
        self.assertEqual(r.launch_status, "NOT_AUTHORIZED")

    def test_break_even_fails_closed_on_ambiguous_amounts(self):
        with self.assertRaises(BM0ModelError):
            break_even_eligible_orders(D("10"), D("NaN"))
        with self.assertRaises(BM0ModelError):
            break_even_eligible_orders(D("-1"), D("3"))
        with self.assertRaises(BM0ModelError):
            break_even_eligible_orders(None, D("3"))


if __name__ == "__main__":
    unittest.main()
