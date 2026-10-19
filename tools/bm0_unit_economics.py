"""Synthetic-only, offline BM0 unit-economics arithmetic.

No network, disk I/O, customer records, payments, price approval or OLP settlement
inference. Caller supplies explicit Decimal amounts and role classifications.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal, ROUND_CEILING
import re

ZERO = Decimal("0")
STREAMS = frozenset({"marketplace", "pro", "logistics", "managed", "fixed"})
_ID = re.compile(r"^[a-zA-Z][a-zA-Z0-9_-]{0,63}$")
_CCY = re.compile(r"^[A-Z]{3}$")


class BM0ModelError(ValueError):
    """Content-free error code, never interpolating user-supplied data."""
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def _money(value: object) -> Decimal:
    if type(value) is not Decimal or not value.is_finite():
        raise BM0ModelError("AMOUNT_INVALID")
    if value < ZERO:
        raise BM0ModelError("AMOUNT_NEGATIVE")
    # Bounded synthetic inputs: up to 18 whole digits and 6 decimal places.
    # With <=1000 cost lines this also keeps sums exact in the default
    # 28-digit Decimal arithmetic context; no implicit rounding/overflow.
    if value.adjusted() > 17 or value.as_tuple().exponent < -6:
        raise BM0ModelError("AMOUNT_OUT_OF_BOUNDS")
    return value


@dataclass(frozen=True)
class OperatorCost:
    cost_id: str
    stream: str
    amount: Decimal

    def __post_init__(self) -> None:
        if type(self.cost_id) is not str or _ID.fullmatch(self.cost_id) is None:
            raise BM0ModelError("COST_ID_INVALID")
        if type(self.stream) is not str or self.stream not in STREAMS:
            raise BM0ModelError("COST_STREAM_INVALID")
        _money(self.amount)


@dataclass(frozen=True)
class OfflineScenario:
    scenario_id: str
    currency: str
    tax_basis: str
    completed_orders: int
    eligible_orders: int
    goods_gmv: Decimal
    operator_fee_gross: Decimal
    operator_fee_reversals: Decimal = ZERO
    pro_gross: Decimal = ZERO
    pro_reversals: Decimal = ZERO
    brokerage_gross: Decimal = ZERO
    brokerage_reversals: Decimal = ZERO
    managed_gross: Decimal = ZERO
    managed_reversals: Decimal = ZERO
    seller_pass_through: Decimal = ZERO
    courier_pass_through: Decimal = ZERO
    tax_pass_through: Decimal = ZERO
    costs: tuple[OperatorCost, ...] = field(default_factory=tuple)
    source_status: str = "SYNTHETIC_ONLY"
    operator_role: str = "AGENT"

    def __post_init__(self) -> None:
        if type(self.scenario_id) is not str or _ID.fullmatch(self.scenario_id) is None:
            raise BM0ModelError("SCENARIO_ID_INVALID")
        if type(self.currency) is not str or _CCY.fullmatch(self.currency) is None:
            raise BM0ModelError("CURRENCY_INVALID")
        if self.tax_basis != "EXCLUSIVE":
            raise BM0ModelError("TAX_BASIS_UNSUPPORTED")
        if self.source_status != "SYNTHETIC_ONLY":
            raise BM0ModelError("SYNTHETIC_DATA_REQUIRED")
        if self.operator_role != "AGENT":
            raise BM0ModelError("OPERATOR_ROLE_UNSUPPORTED")
        if (type(self.completed_orders) is not int or type(self.eligible_orders) is not int
            or self.completed_orders < 0 or self.eligible_orders < 0
            or self.eligible_orders > self.completed_orders):
            raise BM0ModelError("ORDER_COUNTS_INVALID")
        money_fields = (
            "goods_gmv", "operator_fee_gross", "operator_fee_reversals",
            "pro_gross", "pro_reversals", "brokerage_gross", "brokerage_reversals",
            "managed_gross", "managed_reversals", "seller_pass_through",
            "courier_pass_through", "tax_pass_through",
        )
        for name in money_fields:
            _money(getattr(self, name))
        if self.eligible_orders == 0 and self.operator_fee_gross != ZERO:
            raise BM0ModelError("INELIGIBLE_OPERATOR_FEE")
        for gross, reversal in (
            (self.operator_fee_gross, self.operator_fee_reversals),
            (self.pro_gross, self.pro_reversals),
            (self.brokerage_gross, self.brokerage_reversals),
            (self.managed_gross, self.managed_reversals),
        ):
            if reversal > gross:
                raise BM0ModelError("REVERSAL_EXCEEDS_GROSS")
        if type(self.costs) is not tuple or len(self.costs) > 1000:
            raise BM0ModelError("COST_LEDGER_INVALID")
        ids: set[str] = set()
        for line in self.costs:
            if type(line) is not OperatorCost:
                raise BM0ModelError("COST_LEDGER_INVALID")
            if line.cost_id in ids:
                raise BM0ModelError("COST_ID_DUPLICATE")
            ids.add(line.cost_id)


@dataclass(frozen=True)
class OfflineResult:
    scenario_id: str
    currency: str
    marketplace_revenue: Decimal
    pro_revenue: Decimal
    brokerage_revenue: Decimal
    managed_revenue: Decimal
    total_operator_revenue: Decimal
    variable_cost: Decimal
    fixed_cost: Decimal
    contribution: Decimal
    operating_result: Decimal
    goods_gmv_outside_revenue: Decimal
    seller_pass_through_outside_revenue: Decimal
    courier_pass_through_outside_revenue: Decimal
    tax_pass_through_outside_revenue: Decimal
    evidence_status: str = "SYNTHETIC_ONLY"
    launch_status: str = "NOT_AUTHORIZED"


def evaluate_synthetic(scenario: OfflineScenario) -> OfflineResult:
    """Pure Decimal arithmetic, independent from shipment and OLP claim evidence."""
    if type(scenario) is not OfflineScenario:
        raise BM0ModelError("SCENARIO_INVALID")
    mp = scenario.operator_fee_gross - scenario.operator_fee_reversals
    pro = scenario.pro_gross - scenario.pro_reversals
    broker = scenario.brokerage_gross - scenario.brokerage_reversals
    managed = scenario.managed_gross - scenario.managed_reversals
    revenue = mp + pro + broker + managed
    fixed = sum((c.amount for c in scenario.costs if c.stream == "fixed"), ZERO)
    variable = sum((c.amount for c in scenario.costs if c.stream != "fixed"), ZERO)
    contribution = revenue - variable
    return OfflineResult(
        scenario_id=scenario.scenario_id, currency=scenario.currency,
        marketplace_revenue=mp, pro_revenue=pro, brokerage_revenue=broker,
        managed_revenue=managed, total_operator_revenue=revenue,
        variable_cost=variable, fixed_cost=fixed, contribution=contribution,
        operating_result=contribution - fixed,
        goods_gmv_outside_revenue=scenario.goods_gmv,
        seller_pass_through_outside_revenue=scenario.seller_pass_through,
        courier_pass_through_outside_revenue=scenario.courier_pass_through,
        tax_pass_through_outside_revenue=scenario.tax_pass_through,
    )


def break_even_eligible_orders(fixed_uncovered: Decimal, per_order_margin: Decimal) -> int | None:
    """None means volume alone cannot break even, not a feasible zero threshold."""
    fixed = _money(fixed_uncovered)
    if type(per_order_margin) is not Decimal or not per_order_margin.is_finite():
        raise BM0ModelError("MARGIN_INVALID")
    if per_order_margin <= ZERO:
        return None
    return int((fixed / per_order_margin).to_integral_value(rounding=ROUND_CEILING))
