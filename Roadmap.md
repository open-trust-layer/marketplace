# Hello, World! Marketplace — Roadmap

**Snapshot date:** 2026-10-10  
**Reviewed baseline:** main merge commit fd12304319938ac0b5a6130ec85feea1bc217c44 (M17.8E / PR #523).  
**Audience:** product, engineering, security, and Moon Commerce integration.  
**Status semantics:** COMPLETE means the stated *scope* has evidence; it does not imply production readiness.

> Marketplace is a universal economic-coordination layer on Open Layer Protocol (OLP). Evidence of intent, negotiation, and fulfillment is not proof of ownership, legality, payment, universal truth, or trust.

## Executive checkpoint

| Workstream | Current evidence | Status |
| --- | --- | --- |
| Core semantic foundations M1–M16 | README records completed definitions and conformance of foundations through remedy/workflow profiles | COMPLETE — specification/conformance scope |
| Database-free two-user Web MVP | [MARKETPLACE_MVP_ACCEPTANCE.md](MARKETPLACE_MVP_ACCEPTANCE.md) records CREATED → PUBLISHED → DISCOVERED → ACCEPTED → COMPLETED with repeatability and audit evidence | COMPLETE — local demonstrator scope |
| Authenticated Web/Agreement fulfillment | Source and conformance cover explicit Agreement publication and seller-attributed completion; M17.7O/P corrected live findings | SOURCE/CI ACCEPTED; LIVE ACCEPTANCE PENDING |
| M17.8E Web authentication URI guard | [PR #523](https://github.com/open-trust-layer/marketplace/pull/523) merged at fd123043; the exact reviewed PR head passed Marketplace conformance | MERGED — source-only |
| PostgreSQL-backed authenticated localhost browser flight | Fresh *post-M17.7P* two-party Agreement publish + seller-delivery completion still requires operator-authorized execution and non-secret evidence | PENDING |
| Android | Source/contract/toolchain wiring exists; no evidenced compiled, installed, signed, or distributed Android build | NOT RUNTIME ACCEPTED |
| Production Marketplace, payments and settlement | No production hosting, public-network activation, persistent production PostgreSQL, payment/settlement, or Android distribution | NOT ACTIVATED |
| Moon Commerce integration | Root moon.manifest.yaml is discovery metadata only, not running health or authority | METADATA ONLY |

Source of truth: [README.md](README.md), [MARKETPLACE_MVP_ACCEPTANCE.md](MARKETPLACE_MVP_ACCEPTANCE.md), applicable specifications and conformance tests. This document is a planning summary and must not overrule those controls.

## Immediate execution order

### P0 — Verify merged M17.8E and preserve exact security boundary

- [x] Merge narrow fail-closed Web auth Unicode-scalar validation after exact-head review and green PR conformance ([#523](https://github.com/open-trust-layer/marketplace/pull/523)).
- [x] Preserve original URI byte-size limits, signature behavior, routes, and stable errors in the reviewed patch.
- [ ] Independently capture *post-merge main/push* acceptance result and merged commit provenance. A successful PR-head run alone is not a claim about a later push-triggered run.
- [ ] Record any additional server-side, enrollment, or Agreement URI validation concerns as separately reviewed scopes; M17.8E does not claim to fix them.

**Exit:** exact merged main accepted and any new finding tracked; no accidental runtime activation.

### P1 — Complete the authenticated PostgreSQL-backed localhost product flight

Prerequisites: approved evaluator host, reviewed dependencies and pinned OLP checkout, locally provisioned auth evidence, a local PostgreSQL evaluator DSN, and **separate authorization for runtime execution**. Do not copy DSNs, keys, session values, or provisioning contents into GitHub.

- [ ] Run the existing *inert* fulfillment-completion preflight and confirm no server or PostgreSQL connection was started.
- [ ] With separate runtime authorization, run the reviewed loopback-only foreground mode from [MARKETPLACE_MVP_ACCEPTANCE.md](MARKETPLACE_MVP_ACCEPTANCE.md).
- [ ] Authenticate both parties; publish explicit Agreement; complete the seller-attributed seller-delivery claim.
- [ ] Capture only non-secret observable record identities, disposition/change-sequence evidence, and loopback boundary claims.
- [ ] Validate the captured JSON with the existing offline marketplace_authenticated_local_flight_evidence.py tool.
- [ ] Repeat the flow, including failure/recovery behavior; capture any real finding as a narrowly scoped bug fix + regression test.

**Exit:** validated MARKETPLACE_AUTHENTICATED_LOCAL_FLIGHT_EVIDENCE_V1 containing the required Agreement publication and CLAIMED_COMPLETE_PERFORMANCE for seller-delivery. Completion remains attributed evidence, not payment or universal truth.

### P2 — Product readiness before any public pilot

- [ ] Check buyer/seller error recovery and clear status presentation for auth, Agreement publication, and completion.
- [ ] Verify no accidental private-key/token/DSN disclosure in UI, logs, error bodies, or test artifacts.
- [ ] Exercise full two-user journey, restart/recovery, repeatability, and bounded data retention in the approved local evaluation environment.
- [ ] Resolve any regression without weakening exact-head conformance/security controls.
- [ ] Keep Russian/English-facing customer experience on the product checklist; do not claim full localization without browser evidence.

**Exit:** reproducible local user acceptance, a closed blocker list, and no unresolved material auth/data-security issue.

### P3 — Android acceptance lane

- [ ] Validate reviewed Android toolchain versions and reproducible dependency availability.
- [ ] Execute a separately approved compiled/emulator/device acceptance lane, preserving exact Web/API contract parity.
- [ ] Record evidence of build, install, functional authentication, and rollback only when actually observed.

**Exit:** traceable Android build/runtime evidence; source-only Gradle wiring is insufficient.

### P4 — Controlled preview planning (not deployment authority)

- [ ] Freeze threat model, authority/identity enrollment and custody boundaries, retention/deletion, backups, telemetry, rollback, abuse response and incident operations.
- [ ] Resolve hosting/postgres/security/keys/privacy obligations and provider readiness in a separate explicit launch plan.
- [ ] Gate any persistent runtime, public endpoint, production secrets, payment connector, settlement, external provider action, or app distribution behind independent authorization and verification.

**Exit:** approved, reviewed launch packet. This roadmap does **not** authorize a launch.

## Repository housekeeping

- [x] [PR #325](https://github.com/open-trust-layer/marketplace/pull/325) closed as superseded; newer M17.6D and M17.8 changes already exist on main. Do not resurrect the older identity contract without compatibility review.
- [ ] [PR #382](https://github.com/open-trust-layer/marketplace/pull/382): draft coding-agent policy v1.4/v1.7 adoption. Reconcile with later main and verified [branch-protection closeout #212](https://github.com/open-trust-layer/marketplace/issues/212); require fresh full CI and exact-head governance review if revived. Never silently replace current governance with stale text.
- [ ] [PR #142](https://github.com/open-trust-layer/marketplace/pull/142): draft M65 authority-lifecycle invariants. Assess whether the two additions still provide unique coverage, then rebase/requalify or close with written rationale.
- [ ] Recheck latest main, PR queue, and provider-visible acceptance status at each release checkpoint.

## Engineering effort — rough planning ranges, not measured work

The ranges below are **forward-looking engineering estimates only** from this 2026-10-10 snapshot. They are not supported by time tracking, and depend on available evaluator hosts, toolchains, credentials, defect count and review availability. They exclude external waiting, payment-provider onboarding and production infrastructure procurement.

| Next unit | Approximate engineering effort | Key dependency |
| --- | ---: | --- |
| P0 merged-main evidence and PR triage | 2–6 h | CI/provider access |
| P1 authenticated localhost flight and evidence | 6–16 h | Ready local PostgreSQL/auth evaluator + explicit runtime permission |
| P2 local product UX, negative paths and repeatability | 12–32 h | P1 findings |
| P3 Android compiled/runtime proof | 8–24 h | Android toolchain and test target |
| P4 preview security/operations readiness plan | 24–72 h | Threat model, environment and authorized launch scope |
| **Illustrative subtotal** | **52–150 h** | **Not a commitment or countdown to production** |

Material bugs or external prerequisites may expand these figures. A public product launch, payment activation, legal readiness or Android distribution must not be inferred from the subtotal.

## Product decision boundary

**Next decisive deliverable:** complete and validate the real PostgreSQL-backed, authenticated, **loopback-only** two-user Agreement + seller-delivery browser flight. Source merges do not substitute for this evidence. The database-free MVP may be demonstrated independently, but must not be represented as the persistent authenticated product.

## Краткий статус (RU)

Базовые спецификации и локальный MVP готовы в своих проверенных границах. Защита Web-аутентификации M17.8E объединена с main. Главная следующая задача — подтвердить в реальном браузере локальный сценарий с PostgreSQL: аутентификация двух участников, публикация Agreement и подтверждение выполнения обязательства seller-delivery. Для запуска локального сервера и работы с БД требуется отдельное разрешение. Продакшен, публичный доступ, платежи и выпуск Android не активированы.
