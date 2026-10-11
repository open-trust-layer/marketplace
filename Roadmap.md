# Hello, World! Marketplace — Roadmap

**Checkpoint date:** 2026-10-11
**Reviewed baseline:** `main` merge commit `b753548137845694db88b9f2c1b5757a5d57ccdf` (UTF-8 Web placeholder fix / PR #539). Its exact-head [PR acceptance #38128359016](https://github.com/open-trust-layer/marketplace/actions/runs/38128359016) **completed successfully**; independent [main-push acceptance #38129774633](https://github.com/open-trust-layer/marketplace/actions/runs/38129774633) was **in progress at this checkpoint**, so merged-main acceptance remains unverified until that run completes successfully. Earlier PR #533's [merged-main acceptance #38113072116](https://github.com/open-trust-layer/marketplace/actions/runs/38113072116) succeeded.
**Original planning snapshot:** 2026-10-10. Forward estimates below remain rough engineering forecasts, not elapsed hours.
**Audience:** product, engineering, security, and Moon Commerce integration.
**Status semantics:** COMPLETE means the stated *scope* has evidence; it does not imply production readiness.

> Marketplace is a universal economic-coordination layer on Open Layer Protocol (OLP). Evidence of intent, negotiation, and fulfillment is not proof of ownership, legality, payment, universal truth, or trust.

## Executive checkpoint

| Workstream | Current evidence | Status |
| --- | --- | --- |
| Core semantic foundations M1–M16 | README records completed definitions and conformance of foundations through remedy/workflow profiles | COMPLETE — specification/conformance scope |
| Database-free two-user Web MVP | [MARKETPLACE_MVP_ACCEPTANCE.md](MARKETPLACE_MVP_ACCEPTANCE.md) records CREATED → PUBLISHED → DISCOVERED → ACCEPTED → COMPLETED with repeatability and audit evidence | COMPLETE — local demonstrator scope |
| Authenticated Web/Agreement fulfillment | Source and conformance cover explicit Agreement publication and seller-attributed completion; M17.7O/P corrected live findings | SOURCE/CI ACCEPTED; LIVE ACCEPTANCE PENDING |
| M17.8E Web authentication URI guard | [PR #523](https://github.com/open-trust-layer/marketplace/pull/523) merged at `fd123043`; [merged-main CI #38082717846](https://github.com/open-trust-layer/marketplace/actions/runs/38082717846) succeeded | MERGED / MAIN CI VERIFIED |
| Repository governance v1.7 | [PR #382](https://github.com/open-trust-layer/marketplace/pull/382) merged at `7616320`; [merged-main acceptance #38087998470](https://github.com/open-trust-layer/marketplace/actions/runs/38087998470) succeeded; strict `acceptance` protection verified | MERGED / MAIN CI VERIFIED |
| M17.7R offline evidence validation | [PR #526](https://github.com/open-trust-layer/marketplace/pull/526) bounded reads; [#529](https://github.com/open-trust-layer/marketplace/pull/529) matched browser safe-integer bounds; [#530](https://github.com/open-trust-layer/marketplace/pull/530) made nested JSON fail closed; respective merged-main CI [#38104714317](https://github.com/open-trust-layer/marketplace/actions/runs/38104714317), [#38108050763](https://github.com/open-trust-layer/marketplace/actions/runs/38108050763), [#38110494074](https://github.com/open-trust-layer/marketplace/actions/runs/38110494074) succeeded | MERGED / MAIN CI VERIFIED |
| M17.7V/W read-only localhost asset preflight | [PR #531](https://github.com/open-trust-layer/marketplace/pull/531) bounded local asset reads; [#532](https://github.com/open-trust-layer/marketplace/pull/532) normalized malformed/truncated HTTP errors; merged-main CI [#38111080300](https://github.com/open-trust-layer/marketplace/actions/runs/38111080300) and [#38112073801](https://github.com/open-trust-layer/marketplace/actions/runs/38112073801) succeeded; no live preflight invoked | MERGED / MAIN CI VERIFIED |
| M17.7U evaluator evidence preview UX | [PR #533](https://github.com/open-trust-layer/marketplace/pull/533) retains prepared status across language/detail re-renders; exact-head [acceptance #38112092330](https://github.com/open-trust-layer/marketplace/actions/runs/38112092330) succeeded; separate main-push [#38113072116](https://github.com/open-trust-layer/marketplace/actions/runs/38113072116) succeeded | MERGED / MAIN CI VERIFIED; BROWSER UX NOT VERIFIED |
| October 11 source-only hardening / housekeeping | [PR #534](https://github.com/open-trust-layer/marketplace/pull/534) roadmap, [#535](https://github.com/open-trust-layer/marketplace/pull/535) static-asset regular-file checks, [#536](https://github.com/open-trust-layer/marketplace/pull/536) Moon inspector parser guard, [#537](https://github.com/open-trust-layer/marketplace/pull/537) Moon metadata-token hygiene, [#538](https://github.com/open-trust-layer/marketplace/pull/538) evidence-file regular-file guard, [#539](https://github.com/open-trust-layer/marketplace/pull/539) readable Web auth placeholders | MERGED / SOURCE ONLY; #539 exact-head CI GREEN, MAIN-PUSH CI IN PROGRESS AT CHECKPOINT |
| PostgreSQL-backed authenticated localhost browser flight | [Issue #525](https://github.com/open-trust-layer/marketplace/issues/525) tracks fresh *post-M17.7P* two-party Agreement publication and seller-delivery completion; requires separately authorized loopback execution and non-secret evidence | LIVE ACCEPTANCE PENDING |
| Android | Source/contract/toolchain wiring exists; no evidenced compiled, installed, signed, or distributed Android build | NOT RUNTIME ACCEPTED |
| Production Marketplace, payments and settlement | No production hosting, public-network activation, persistent production PostgreSQL, payment/settlement, or Android distribution | NOT ACTIVATED |
| Moon Commerce integration | Root `moon.manifest.yaml` declares development `workspace` health; [Issue #528](https://github.com/open-trust-layer/marketplace/issues/528) tracks the Moon Core fallback heartbeat mismatch. Neither proves a running service | METADATA ONLY / CLASSIFICATION RECONCILIATION PENDING |

Source of truth: [README.md](README.md), [MARKETPLACE_MVP_ACCEPTANCE.md](MARKETPLACE_MVP_ACCEPTANCE.md), applicable specifications and conformance tests. This document is a planning summary and must not overrule those controls.

## Immediate execution order

### P0 — Close merged-main evidence and source-governance housekeeping

- [x] Merge narrow fail-closed Web auth Unicode-scalar validation after exact-head review and green PR conformance ([#523](https://github.com/open-trust-layer/marketplace/pull/523)).
- [x] Preserve original URI byte-size limits, signature behavior, routes, and stable errors in the reviewed patch.
- [x] Independently verified post-merge `main` push acceptance: GitHub Actions run [#38082717846](https://github.com/open-trust-layer/marketplace/actions/runs/38082717846) completed successfully for merge `fd12304319938ac0b5a6130ec85feea1bc217c44`.
- [x] Merged [PR #382](https://github.com/open-trust-layer/marketplace/pull/382) after reconciled policy review and exact-head FULL CI; separately verified [main push #38087998470](https://github.com/open-trust-layer/marketplace/actions/runs/38087998470) succeeded.
- [x] Merged [PR #526](https://github.com/open-trust-layer/marketplace/pull/526) to bound the offline browser-flight evidence file read to 64 KiB + one sentinel, with regression tests and successful exact-head CI.
- [x] Independently verified successful separate post-merge main push [#38104714317](https://github.com/open-trust-layer/marketplace/actions/runs/38104714317) on commit `11d4f1ac57111a8ae0d4044314d43adee3161741`.
- [x] Merged [PR #527](https://github.com/open-trust-layer/marketplace/pull/527) to reconcile the roadmap baseline and superseded-PR housekeeping; its separate [main push #38106288756](https://github.com/open-trust-layer/marketplace/actions/runs/38106288756) succeeded.
- [x] Merged source-only hardening [PRs #529](https://github.com/open-trust-layer/marketplace/pull/529), [#530](https://github.com/open-trust-layer/marketplace/pull/530), [#531](https://github.com/open-trust-layer/marketplace/pull/531), and [#532](https://github.com/open-trust-layer/marketplace/pull/532) after separate exact-head full acceptance; their individual merged-main CI runs passed.
- [x] Merged [PR #533](https://github.com/open-trust-layer/marketplace/pull/533) after exact-head full CI for P2 evidence-preview status; this is source-only, not browser/runtime acceptance.
- [x] Independently verified [PR #533 merged-main push #38113072116](https://github.com/open-trust-layer/marketplace/actions/runs/38113072116) passed on `44a50144d93f86ef7a3e17310b6e3f96040392df`.
- [x] Merged source-only PRs [#534](https://github.com/open-trust-layer/marketplace/pull/534) through [#538](https://github.com/open-trust-layer/marketplace/pull/538); no runtime authorization or activation follows from these merges.
- [x] Merged UTF-8 static Web-shell correction [PR #539](https://github.com/open-trust-layer/marketplace/pull/539) at `b753548137845694db88b9f2c1b5757a5d57ccdf` after exact-head [acceptance #38128359016](https://github.com/open-trust-layer/marketplace/actions/runs/38128359016) succeeded, two-file patch review, and zero unresolved review threads.
- [ ] Independently verify [#539 merged-main push acceptance #38129774633](https://github.com/open-trust-layer/marketplace/actions/runs/38129774633) reaches success; it was still in progress at this documentation checkpoint.
- [ ] Record any additional server-side, enrollment, or Agreement URI validation concerns as separately reviewed scopes; M17.8E does not claim to fix them.

**Exit:** independent merged-main CI verified for each merge; #533's main-push evidence is green, whereas the new #539 merged-main run still requires a terminal successful result. Further findings remain narrow scopes; no accidental runtime activation.

### P1 — Complete the authenticated PostgreSQL-backed localhost product flight

**Tracking:** [Issue #525](https://github.com/open-trust-layer/marketplace/issues/525). Offline validator input is bounded by merged PR #526; this does **not** establish live browser acceptance.

Prerequisites: approved evaluator host, reviewed dependencies and pinned OLP checkout, locally provisioned auth evidence, a local PostgreSQL evaluator DSN, and **separate authorization for runtime execution**. Do not copy DSNs, keys, session values, or provisioning contents into GitHub.

- [ ] Run the existing *inert* fulfillment-completion preflight and confirm no server or PostgreSQL connection was started.
- [ ] With separate runtime authorization, run the reviewed loopback-only foreground mode from [MARKETPLACE_MVP_ACCEPTANCE.md](MARKETPLACE_MVP_ACCEPTANCE.md).
- [ ] Authenticate both parties; publish explicit Agreement; complete the seller-attributed seller-delivery claim.
- [ ] Capture only non-secret observable record identities, disposition/change-sequence evidence, and loopback boundary claims.
- [ ] Validate the captured JSON with `tools/marketplace_authenticated_local_flight_evidence.py` (64 KiB maximum, bounded read) and retain only non-secret evidence.
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
- [x] [PR #382](https://github.com/open-trust-layer/marketplace/pull/382): v1.7 engineering governance merged after reconciling historical provider protection evidence, current `acceptance` rules, full CI, and independent CRITICAL-risk review boundaries.
- [x] [PR #142](https://github.com/open-trust-layer/marketplace/pull/142): closed without merge as superseded; current main covers M64–M70 lifecycle invariants, and the old draft's non-idempotent close expectation conflicted with the reviewed current behavior.
- [ ] Resolve [Issue #528](https://github.com/open-trust-layer/marketplace/issues/528) lifecycle classification with Moon Company without treating development workspace presence as a live service or fabricating a heartbeat.
- [ ] Recheck latest main, PR queue, and provider-visible acceptance status at each release checkpoint.

## Engineering effort — rough planning ranges, not measured work

The ranges below are **forward-looking engineering estimates only**, now updated for the 2026-10-11 checkpoint. They are not supported by time tracking, and depend on available evaluator hosts, toolchains, credentials, defect count and review availability. They exclude external waiting, payment-provider onboarding and production infrastructure procurement.

| Next unit | Approximate engineering effort | Key dependency |
| --- | ---: | --- |
| P0 merged-main evidence and PR triage | Completed source merges need no additional feature effort; #539 merged-main push verification remains pending | CI/provider access |
| P1 authenticated localhost flight and evidence | 6–16 h | Ready local PostgreSQL/auth evaluator + explicit runtime permission |
| P2 local product UX, negative paths and repeatability | 12–32 h | P1 findings |
| P3 Android compiled/runtime proof | 8–24 h | Android toolchain and test target |
| P4 preview security/operations readiness plan | 24–72 h | Threat model, environment and authorized launch scope |
| **Illustrative remaining subtotal (P1–P4)** | **50–144 h** | **Not a commitment or countdown to production** |

Material bugs or external prerequisites may expand these figures. A public product launch, payment activation, legal readiness or Android distribution must not be inferred from the subtotal.

## Product decision boundary

**Next decisive deliverable:** complete and validate the real PostgreSQL-backed, authenticated, **loopback-only** two-user Agreement + seller-delivery browser flight. Source merges do not substitute for this evidence. The database-free MVP may be demonstrated independently, but must not be represented as the persistent authenticated product.

## Краткий статус (RU)

Базовые спецификации и локальный MVP готовы в пределах подтверждённых сценариев. Защита Web-аутентификации M17.8E, политика разработки v1.7, офлайн-проверка доказательств (#526, #529, #530) и безопасная диагностика локальных Web-ресурсов (#531, #532) объединены с `main`; отдельные CI-проверки `main` для этих изменений завершились успешно. Улучшение предпросмотра доказательств (#533) прошло отдельную проверку `main` #38113072116. Дополнительные исходные изменения #534–#539 объединены. Проверка PR #539 (#38128359016) завершилась успешно, но отдельная проверка `main` #38129774633 ещё выполнялась на момент этой записи; считать её успешной до завершения нельзя. Moon Commerce по-прежнему имеет лишь метаданные среды разработки; несоответствие модели heartbeat отслеживается в #528. Главная следующая задача — подтвердить в реальном браузере локальный сценарий с PostgreSQL: аутентификация двух участников, публикация Agreement и заявление продавца об исполнении обязательства seller-delivery. Запуск локального сервера, использование PostgreSQL и браузерная проверка требуют отдельного разрешения. Продакшен, публичный доступ, платежи и выпуск Android не активированы.
