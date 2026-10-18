# BM0 — Commercial validation plan (planning only)

**Status (2026-10-19): PROPOSED / NOT TESTED / NOT LAUNCHED.**
**Decision source:** [Marketplace monetization roadmap PR #604](https://github.com/open-trust-layer/marketplace/pull/604). This document is an independently reviewable BM0 work product; it does **not** claim that #604 is merged. If it has not merged, its strategy is owner-approved but the repository roadmap merge remains pending.
**Risk/capabilities:** LOW, repository documentation only; READ_PROJECT and WRITE_PROJECT.
**Authority:** Strategy, discovery design and offline financial modelling only. No customers contacted, customer data collected, host activated, courier dispatched, charge initiated, checkout configured, token accepted, or payment processor selected by this file.

## Non-negotiable boundaries

Marketplace and OLP remain Apache-2.0/open, interoperable, independently implementable and operator-neutral. Competing operators, couriers, hosting providers and self-hosting remain possible. An optional Moon Company operated service can charge transparently for its own value added; protocol access, semantic validity, OLP evidence and federation are never paywalled. MOON is neither required nor currently accepted, and no price support, buyback or peg is promised.

Keep separate: goods seller/consideration; delivery provider/service; platform operator service; payment processor and settlement; OLP fulfillment/acceptance evidence. A record of delivery does not prove buyer acceptance, legal title, payment, settlement, compliance or truth. Never treat GMV or pass-through payments as Moon Company revenue. Never disguise sponsorship as neutral search ranking.

## BM0 deliverable and evidence ledger

BM0 is **completed** only when a reproducible package contains: written hypotheses; sourced comparable-price research; privacy-safe, consent-based discovery summaries; a reviewed cost model with units and assumptions; a prioritized Seller Pro backlog; jurisdiction-by-jurisdiction readiness decisions; pilot criteria with denominators; and a signed go/no-go recommendation. This document supplies the **framework**, not the uncollected evidence.

| Work item | Current state | Evidence required to finish |
| --- | --- | --- |
| Business streams and non-activation constraints | OWNER DECIDED | Strategy in #604; confirm merge separately |
| Hypothesis/pricing research design | DOCUMENTED, UNEXECUTED | Dated provider comparisons with links, product/fee definitions and jurisdictions |
| Merchant/buyer/courier/enterprise discovery | PLANNED, NO CLAIMED INTERVIEWS | Consented interview notes, coded findings and contradictions |
| Cost model | FORMULAS ONLY | Source-tagged and dated cost observations with currency/tax treatment |
| Seller Pro priority | PROVISIONAL | Interview-based scoring and technical feasibility review |
| Regulatory, privacy, payment and tax | OPEN CHECKLIST | Named professional/operational owner and written decisions for each pilot territory |
| Pilot thresholds/launch approval | PROPOSED | Decision on thresholds and distinct deployment/payment authorization |

No sales, customer demand, adoption, transaction or market statistic is asserted in BM0.

## 1. Falsifiable commercial hypotheses

Each hypothesis is *unvalidated*. Acceptance requires independent research and documented counterevidence.

| Stream | Hypothesis | Evidence to seek | Falsification / alternative |
| --- | --- | --- | --- |
| Official operated Marketplace | Some sellers and buyers will prefer convenient discovery, support and dispute coordination to self-hosting | Separate willingness-to-use / willingness-to-pay interviews; competing operator fee schedules; support workload | Users reject explicit fee, or service costs exceed defensible net fees; offer fixed-fee support or no operator fee |
| Marketplace Pro | A seller segment values bulk listing, inventory synchronization, analytics and automation | Task-frequency ranking, existing tooling cost, mocked plan preference, churn risks | Features are rarely used, or must be open baseline conformance; defer subscription |
| Logistics | Sellers value optional carrier comparison/dispatch; couriers value distinct, opt-in transport work | Seller shipping workflows, carrier/courier eligibility, insurance claims, quote-to-acceptance economics | Low geographic density, unsafe provider controls or no viable insurance; retain seller-managed mode only |
| Managed Marketplace | Some organizations prefer hosting, migration, integrations, operations and SLAs rather than self-managing | Enterprise interviews, integration scope, deployment/security procurement, support cost | No paying segment or bespoke support overwhelms margin; offer scoped professional services first |

## 2. Research and pricing protocol

1. **Market definition before prices.** Select a lawful jurisdiction, category, B2C/B2B model, seller-of-record and operator-of-record. Avoid a synthetic global “marketplace fee.”
2. **Comparable service capture.** For each comparator, record URL, capture date, location, service bundle, fixed/variable fees, payment processing inclusions, VAT/tax treatment, refund/chargeback rules, minimum monthly commitments and ranking/sponsorship rules. Verify official pricing/terms rather than reproducing unsupported hearsay.
3. **Pricing experiments without checkout.** Prepare transparent side-by-side *mock* fee disclosure variants: no operator service / flat optional service / percentage-capped optional service, and subscription tiers with clear baseline functionality. Present as research concepts, not offers. No live collection or pre-authorization.
4. **Conjoint/trade-off interviews.** Ask for current pain, actual recent workflow, substitute products, observed current spend, blockers and reaction to explicitly labelled hypothetical prices. Separate preference from purchase intent and actual willingness to pay.
5. **Triangulate.** Capture negative responses and segment differences. Do not scale interview intent into adoption forecasts. Record range/source/uncertainty for each model input; missing evidence stays UNKNOWN.

**Proposed recruiting targets (planning assumptions, not achieved sample sizes):** 12–15 independent sellers, 12–15 buyers, 8–12 couriers/carrier representatives, and 5–8 managed-service prospects. Purposively sample different size, geography, platform use and fulfillment methods; record recruitment bias. These interviews are directional discovery, not statistically representative population estimates. No contact or personal-data collection is authorized by this plan.

**Interview outline:** latest actual task; current alternatives; required documents and handling of disputes/refunds; what fails; which steps merit an optional paid service; preferred price basis; dealbreakers; data portability; open-source and self-hosting expectations; choice of seller-managed vs distinct courier vs external carrier. Do not solicit real payment credentials, precise addresses or shipment/customer histories.

**Research data controls:** obtain explicit consent where needed; publish only aggregated, de-identified findings; define access, data minimization, lawful basis and deletion/retention schedule before interviews; do not commit identities, transcripts, real orders, payment details or confidential quotes to this repository. Operate within Marketplace retention/isolation policy and any jurisdiction-specific requirements. Any actual outreach, data-processing agreement or service account setup requires its own operational authority.

## 3. Provisional Seller Pro prioritization

Preserve an adequate and interoperable open-source core. A subscription purchases optional hosted convenience, service levels or additional tools, never protocol validity, portable evidence, basic import/export, self-hostability or mandatory discoverability.

| Candidate | Draft priority | Rationale / unknown |
| --- | --- | --- |
| Bulk listing + portable import/export | P1 research | High potential task repetition; ensure non-Pro interoperability and open formats |
| Inventory synchronization and conflict preview | P1 research | High operational value, but risky external connector permissions |
| Seller activity analytics with privacy-safe aggregation | P1 research | Value unproven; enforce minimization and authorization |
| Order workflow automation with dry-run/audit | P2 research | Valuable if repeatable; requires risk, consent and rollback design |
| Professional storefront customization | P2 research | Visual benefit uncertain; baseline store remains usable |
| Optional hosted priority support/SLA | P2 research | Cost must be modelled; no preferential evidence/rank |
| Paid visibility / rankings | EXCLUDED FROM BM0 | Risk of deceptive ranking; any future sponsored result must be explicitly identified and separately approved |

Scoring method for BM0 completion: record interview frequency, severity, alternative cost, implementation/security burden, service cost and accessibility impact. Use a transparent score with UNKNOWN rather than invented numeric ratings. Product/security reviewers may veto ideas that undermine portability or authorization.

## 4. Readiness checklist (not legal advice)

Create a separate checklist row **per pilot jurisdiction and business stream** with owner, applicability rationale, counsel/accountant/provider source, evidence link, resolution date and status (UNKNOWN / PASS / BLOCKED / NOT_APPLICABLE). Do not assume the rules of one country apply worldwide.

- [ ] Operator identity, consumer-facing terms, identity of contracting merchant, disclosures, cancellation/right-of-withdrawal, returns/refunds, disputes, complaints and product safety allocation.
- [ ] Marketplace/intermediary obligations, consumer and trader verification where applicable, prohibited-goods policy, anti-fraud/abuse escalation and transparency in discovery/ranking/sponsorship.
- [ ] Privacy roles (controller/processor), lawful basis, purpose limitation, data minimization, information notices, subject rights, cross-border transfers, retention and breach response.
- [ ] Merchant onboarding, KYB/KYC if applicable, sanctions/AML responsibility, fraud prevention, PSP responsibilities, payment authorization, refunds/chargebacks, segregation of funds and payout/settlement controls.
- [ ] Tax treatment of goods, separately supplied delivery, operator fee, subscriptions and managed services; VAT/GST/sales tax, invoicing, taxable event, reporting and cross-border treatment.
- [ ] Courier eligibility, licensing, insurance, liability for loss/damage, worker classification, occupational safety, delivery address access and incident handling.
- [ ] Managed-hosting SLAs, uptime/security responsibility, tenant isolation, backup/restore, portability, processor agreements, migration and termination.
- [ ] Accessibility, localization, customer-support channels, accessibility of fee breakdown, audit and evidence portability.
- [ ] Payments and MOON: no token checkout; any eventual token rail demands separate verified identity, legal, volatility, refund, custody and consumer disclosure approvals.

**Initial research jurisdictions:** decide explicitly; the owner's project geography does not establish a lawful target market. EU/EEA, UK, Russia and other regimes must each be evaluated independently if proposed; consult appropriately qualified advisers rather than assuming coverage.

## 5. Accounting and fulfillment separation

Display to a buyer *before* committing any future order: goods price and tax, separately identified delivery quote and tax, optional operator service fee and tax, total payable, identity of each provider, and cancellation/refund allocation. Seller Pro subscription and managed-service invoices are separate contractual revenue streams. Evidence about receipt/delivery/buyer acceptance stays distinct from PSP settlement and money owed to sellers/couriers.

Reference formulas and sensitivity controls are in [BM0 unit economics](bm0-unit-economics.md).

## 6. Proposed pilot metrics and decision framework

**The following are *candidate design thresholds*, not achievements, forecasts or authorized launch goals.** The BM0 owner must approve each numeric threshold and time window before a pilot. Record unique order ID, denominator, currency, observation horizon, source provenance and missing-data rate for every measure.

| Measure | Definition | Proposed decision rule (not yet approved) |
| --- | --- | --- |
| Fee disclosure completeness | Eligible simulated pilot order views showing itemized goods/delivery/optional operator fee/tax **before** consent / all eligible views | 100% of reviewed cases before any paid pilot |
| Reconciliation integrity | Reviewed sample line items reconciling seller amount, courier amount, operator fee, PSP cost and refunds / reviewed sample | 100% in synthetic acceptance; real pilot requires independently approved control |
| Eligible order outcome | Independently confirmed fulfilled eligible orders / eligible orders, with cancelled/disputed denominators reported separately | Set minimum only after baseline data and an approved sample design |
| Contribution margin per eligible order | Net recognized operator revenue minus attributable variable cost, with reversals | Non-negative under a feasible, evidenced scenario; report downside sensitivity |
| Merchant utility | Interview participants showing a recent repeatable pain and selecting a proposed tool over alternatives / eligible interviews | Report raw numerator/denominator; no extrapolation from small samples |
| Pro feature demand | Qualified seller workflow demonstrations requesting a particular tool / qualified seller demonstrations | Rank P1/P2 after qualitative coding, not invented adoption estimates |
| Logistics quote-to-acceptance | Accepted eligible quotes / eligible quotes, with no-quote and cancellation denominators | Set threshold only after provider/coverage feasibility |
| Disputes and safety | Disputed orders / fulfilled orders; policy/privacy/security incidents with severity and response evidence | Zero unresolved **material** legal/privacy/security incidents at go/no-go |
| Support burden | Support minutes and cost per eligible order, plus time-to-first-response | Compare with researched cost assumption and approved service target |
| Managed-service viability | Qualified, compliant deployment requirements / prospects and priced scope cost | Explicit written scope and positive post-support contribution scenario |

**BM0 exit / no-go:** no commercial launch is implied by positive discovery. If evidence is missing, model results are negative/indeterminate, data collection is impermissible, or any material readiness blocker is open, outcome is **NO-GO / MORE RESEARCH**, not an automatic pilot.

## 7. Separate commercial launch prerequisites (BM1+ only)

1. [Issue #525](https://github.com/open-trust-layer/marketplace/issues/525): genuine fresh authenticated two-party browser/Agreement/fulfillment acceptance with valid bounded evidence; no expired test provisioning reuse.
2. [Issue #528](https://github.com/open-trust-layer/marketplace/issues/528): authoritative host, lifecycle and production-readiness determination; no inference from localhost HTML or green source CI.
3. P2–P4 product, security, privacy, accessible UI, conformance, incident-response, backup/restore, operations, authentication and rollback acceptance for the exact target deployment.
4. Jurisdiction-specific counsel/accountant/PSP, seller/courier agreements, privacy and tax checklist decisions. Fee breakdown/terms and consumer cancellation/refund flows independently validated.
5. Evidence of viable, non-misleading pricing and service economics with downside cases and provider contracts.
6. Explicit separate owner authorization for any production activation, external outreach/data processing, live carrier dispatch, payment collection, refunds or settlements, MOON asset operations, paid subscriptions or merchant onboarding.
7. A documented opt-out/exit/data export/self-host path; competing operators and replaceable delivery/payment providers continue to work.

No requirement above can be waived by merging this documentation, by a successful CI run, or by the business owner's strategy approval.

## BM0 proposed task order

1. **BM0-A** — Sourced pricing/comparator matrix + revised hypotheses (research only).
2. **BM0-B** — Cost-driver inventory, tax-exclusive unit economics, pass-through checks, pessimistic cases (offline only).
3. **BM0-C** — Consent/retention-reviewed interviews and blinded evidence ledger (requires separate outreach/data authority).
4. **BM0-D** — Seller Pro priority workshop and interoperable-feature boundary review.
5. **BM0-E** — Jurisdictional legal/privacy/payment/tax owner map and go/no-go memo.

**Rollback:** revert this planning document; no runtime state, private data or payments are changed. **Stop:** on semantic conflation of OLP evidence/payment, mandatory platform/token access, fabricated data, privacy retention drift, or any unauthorized operational action.
