# BM0 — Offline unit-economics specification

**Status:** HYPOTHESES / VARIABLES ONLY (2026-10-19). All inputs are **UNKNOWN** until independently sourced. No customer, market, cost, price or revenue figures are asserted. Companion: [BM0 validation plan](bm0-commercial-validation.md). No money movement or system integration is authorized.

## Accounting contract

Use one stated reporting currency and one reporting period. Record whether each currency value is tax-inclusive or tax-exclusive; normalize before calculation and state exchange-rate provenance/timestamp if translation is needed. Use a tax-exclusive operator P&L wherever applicable; tax collected for third parties is not operator income. Clearly identify whether the operator is principal or agent under applicable law/accounting guidance before recognizing sales.

- **GMV**: total eligible goods consideration transacted between buyers and sellers, reported separately from operator revenue. Do not count orders or payment authorizations as transacted without the defined measurement event.
- **Goods proceeds (G)**: consideration due to goods seller; **delivery proceeds (D)**: consideration due to the contracted delivery provider; **platform fee (F)**: separately disclosed consideration due to the optional Marketplace operator.
- **Payment/settlement costs (P)**: PSP/acquirer charges, network fees, FX and chargeback processing, allocated to the party actually bearing them. Tracking an authorization does not mean money settled.
- **Refunds/chargebacks/reversals (R)**: reduction to revenue recognized by operator plus separately attributable unrecovered costs.
- **Subscription revenue (S)** and **managed-services revenue (M)**: recognized in their respective service periods, not automatically per transaction; exclude refundable deposits and unearned deferred revenue.
- **Courier compensation**: pass-through when operator acts as an agent; if operator acts as transport principal under reviewed contracts, calculate separate transport gross revenue, carrier cost and liability without silently mixing into a goods order margin.
- **Fulfillment**: attributable OLP claims and buyer review are not invoices, PSP payments, settlement records, accepted service quality or legal proofs. Preserve separate references and adjudication.

## Source-tagged model input ledger (fill before projecting)

| Input | Unit | Source/evidence and as-of date | Uncertainty |
| --- | --- | --- | --- |
| Eligible completed transactions (N) | orders/period | UNKNOWN | UNKNOWN |
| Average goods value (G_bar) | currency/order, excl. tax | UNKNOWN | UNKNOWN |
| Optional operator fee charged (F_bar) | currency/eligible order, excl. tax | UNKNOWN; **no rate approved** | UNKNOWN |
| Fee-eligible share (q) | fraction, 0..1 | UNKNOWN | UNKNOWN |
| Operator fee reversals (r_fee) | fraction or directly observed currency | UNKNOWN | UNKNOWN |
| Operator-borne PSP/chargeback cost (P_bar) | currency/order | UNKNOWN | UNKNOWN |
| Support minutes per eligible order (t_support) | minutes/order | UNKNOWN | UNKNOWN |
| Fully loaded support expense (w_support) | currency/minute | UNKNOWN | UNKNOWN |
| Variable hosting, fraud, notification, analytics (V_bar) | currency/order | UNKNOWN | UNKNOWN |
| Logistics broker net fee (B_bar) | currency/transport arrangement | UNKNOWN; **no carrier monopoly** | UNKNOWN |
| Transport coordination cost (C_log) | currency/arrangement | UNKNOWN | UNKNOWN |
| Pro active billed sellers (U) | seller-periods/period | UNKNOWN | UNKNOWN |
| Net Pro subscription price (S_bar) | currency/seller-period | UNKNOWN; **no price approved** | UNKNOWN |
| Pro seller-specific variable cost (C_pro) | currency/seller-period | UNKNOWN | UNKNOWN |
| Managed-services recognized net fees (M_total) | currency/period | UNKNOWN | UNKNOWN |
| Managed-service direct delivery cost (C_managed) | currency/period | UNKNOWN | UNKNOWN |
| Allocable fixed operating expense (K) | currency/period | UNKNOWN | UNKNOWN |

For every replacement of UNKNOWN with a numeric input, record source, acquisition date, owner, exact scope, currency, applicable tax treatment, and an explicit observed / quoted / **assumed** classification. An assumption cannot be promoted into market fact by repeated use.

## Per-order and per-period model

Define **E = N * q** as operator-fee-eligible transactions and use exact observed count when possible. Let **F_net = F_bar * (1 - r_fee)** only when r_fee is a valid homogeneous reversal fraction; otherwise use sum of recognized fee lines minus actual reversals. Do not apply a fee to ineligible or cancelled orders.

**Official operated Marketplace** contribution per eligible fee-bearing order, conditional on a valid homogeneous model:

    CM_marketplace_order = F_net - P_bar - (t_support * w_support) - V_bar

**Whole Marketplace service** contribution, including support costs for ineligible/free orders:

    CM_marketplace_total = recognized_operator_fees
                         - operator_borne_payment_costs
                         - operator_borne_support_costs
                         - operator_borne_variable_infra_and_risk_costs
                         - operator_borne_refund_and_chargeback_losses

**Seller Pro**, independently:

    CM_pro = (U * S_bar - subscription_reversals) - (U * C_pro) - other_attributable_Pro_costs

**Logistics coordination**, only for actual independent optional brokerage arrangements:

    CM_logistics = recognized_broker_service_fees - logistics_coordination_costs
                   - broker_borne_reversals_or_loss

If transport is provided directly as principal, model recognized gross delivery consideration and actual carrier payout, insurance, claims, service cost and taxes separately. Never count provider pass-through as brokerage revenue.

**Managed Marketplace**:

    CM_managed = M_total - C_managed - managed_service_variable_costs - reversals

**Combined operator contribution**, for a period with no double-counting:

    CM_total = CM_marketplace_total + CM_pro + CM_logistics + CM_managed
    Operating_result_before_tax = CM_total - K

Separate common-cost allocations (e.g., support or infrastructure) using a single documented allocation key; each actual cost appears exactly once. Present both allocated and unallocated views and prevent counting merchant proceeds, gross merchandise value, tax remittance or carrier pass-through as revenue.

**Fee effective take rate (disclosed analytical metric)** = recognized net operator transaction service fees / eligible settled goods GMV when denominator is positive. This is not a protocol commission and must never imply that the operator charges every interoperable Marketplace instance.

**Break-even** (only if marginal contribution is positive and other streams/fixed costs are consistently accounted): necessary incremental eligible fee-bearing orders = ceil(remaining uncovered fixed costs / per-order incremental contribution). If marginal contribution <= 0, break-even by volume alone is **NOT FEASIBLE**. If inputs unknown, report **INSUFFICIENT EVIDENCE**, not zero or a made-up order count.

## Sensitivity and downside plan

Run, at minimum, separate no-operator-fee/self-host, optional operator-fee, Pro-only, brokerage-only, managed-service-only and combined scenarios. For each, compare documented LOW / CENTRAL / HIGH **assumptions**, varying eligible share, refunds, support minutes, chargebacks, paid seller retention, courier claims, pricing, infrastructure and compliance costs. **These are scenario parameters, not probability distributions or forecasts.**

Maintain cash-flow timing separately from accrual earnings: collection, seller payable, courier payable, PSP settlement lag, VAT/tax remittance, reserves, disputed funds, refunds and chargeback exposures. Do not treat cash passing through the operator as free cash available to Moon Company.

## Deterministic spreadsheet/calculator acceptance tests

A future offline calculator (or independently checked workbook) must reject missing required inputs, negative monetary quantities that are not marked reversals, fractions outside [0,1], mismatched currencies, ambiguous tax treatment and double-counted cost IDs. Verify these invariants using wholly synthetic fixtures, not customer records:

1. If **N=0** and there is no Pro, logistics or managed-service revenue, recognized transaction revenue is zero. Fixed cost can still make operating result negative.
2. If **q=0**, optional transaction service-fee revenue is zero even with positive goods GMV.
3. Increasing operator-borne refunds or costs cannot improve operator margin, all else constant.
4. A seller-managed shipment with no brokerage service produces zero brokerage revenue, regardless of shipping amount.
5. A courier pass-through payment leaves agent-mode recognized brokerage revenue unchanged.
6. In a hypothetical fully refunded transaction with no earned operator fee, related operator fee net revenue is zero or lower after nonrefundable costs; OLP completion evidence must not override this accounting.
7. A non-positive marginal contribution does not produce an apparently finite positive break-even order count.
8. Tax collected for remittance, seller funds and carrier pass-through cannot inflate recognized operator net income.
9. Subscription or managed-service fees must not be counted twice in both order-level margin and period revenue.
10. Sum of order-level fee allocations equals period recognized operator fee totals, subject to explicit rounding rules and reconciliation references.

## Decision and audit output schema

For each scenario export a reviewable, synthetic or aggregate-only summary:

- scenario_id, report_period, jurisdiction, seller-of-record/operator-of-record role;
- currency, tax basis, input source version/date, assumption IDs, evidence quality;
- N, eligible N, GMV, **net recognized operator revenue by stream** (not GMV);
- seller and courier payable amounts **shown outside operator revenue**;
- payment/support/logistics/managed costs, risk/reversals and fixed expense;
- contribution by stream, total, operating result, sensitivity low/central/high;
- method for missing evidence, owner/date of review, launch status **NOT_AUTHORIZED**.

Never store real buyer/seller identities, live orders, detailed payment records, real location trails or credentials in publicly committed fixtures. Reuse existing Marketplace audit, retention and project isolation rules. A green offline model says nothing about readiness to accept money.

## Exit gate

BM0 economics can be marked **VALIDATED FOR DECISION** only after source-cited inputs, reconciliation checks and independently reviewed adverse cases; it does not mean the business is viable or launch-approved. Launch requires separate #525 authenticated acceptance, #528 host/lifecycle classification, P2–P4 product gates, jurisdictional tax/legal/PSP due diligence, reviewed fee disclosures, data controls and express operator/payment/production authorization.

**Rollback:** revert this document. There is no runtime or financial side effect.
