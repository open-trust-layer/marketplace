# Hello, World! Marketplace — Roadmap

**Checkpoint date:** 2026-10-12
**Reviewed baseline:** `main` merge `89c4492f27dcefa6ed43de703ef18405c49e304b` ([PR #555](https://github.com/open-trust-layer/marketplace/pull/555), Web detail record identity check), with successful exact-head [acceptance #38230561938](https://github.com/open-trust-layer/marketplace/actions/runs/38230561938). Its independent merged-main [acceptance #38242297232](https://github.com/open-trust-layer/marketplace/actions/runs/38242297232) was **IN PROGRESS** at this checkpoint; do not claim it passed. Previous [PR #554](https://github.com/open-trust-layer/marketplace/pull/554) exact-head [#38226104154](https://github.com/open-trust-layer/marketplace/actions/runs/38226104154) and independent merged-main [#38229917116](https://github.com/open-trust-layer/marketplace/actions/runs/38229917116) both succeeded.
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
| October 11 source-only hardening / housekeeping | [PR #534](https://github.com/open-trust-layer/marketplace/pull/534) roadmap, [#535](https://github.com/open-trust-layer/marketplace/pull/535) static-asset regular-file checks, [#536](https://github.com/open-trust-layer/marketplace/pull/536) Moon inspector parser guard, [#537](https://github.com/open-trust-layer/marketplace/pull/537) Moon metadata-token hygiene, [#538](https://github.com/open-trust-layer/marketplace/pull/538) evidence-file regular-file guard, [#539](https://github.com/open-trust-layer/marketplace/pull/539) readable Web auth placeholders | MERGED / SOURCE ONLY; #539 EXACT-HEAD AND MAIN-PUSH CI GREEN |
| October 11 offline evaluator preparation | [PR #541](https://github.com/open-trust-layer/marketplace/pull/541) restored RU auth/Proposal guidance; [#542](https://github.com/open-trust-layer/marketplace/pull/542) normalized malformed evidence-path errors; [#543](https://github.com/open-trust-layer/marketplace/pull/543) added inert prerequisite presence checks; [#544](https://github.com/open-trust-layer/marketplace/pull/544) checks exact clean Marketplace/OLP Git roots and SHAs; [#545](https://github.com/open-trust-layer/marketplace/pull/545) rejects concealed assume-unchanged/skip-worktree index flags. [Main CI #38135146860](https://github.com/open-trust-layer/marketplace/actions/runs/38135146860), [#38137222318](https://github.com/open-trust-layer/marketplace/actions/runs/38137222318), [#38141362001](https://github.com/open-trust-layer/marketplace/actions/runs/38141362001) all succeeded; latest [#545 post-merge CI #38143703077](https://github.com/open-trust-layer/marketplace/actions/runs/38143703077) also succeeded. | SOURCE MERGED / LOCAL PROVENANCE VERIFIED; MAIN CI GREEN |
| Consolidated offline evaluator readiness | [PR #546](https://github.com/open-trust-layer/marketplace/pull/546)–[#548](https://github.com/open-trust-layer/marketplace/pull/548) extended inert dependency/pin/provenance reporting; #548 exact-head [CI #38152712256](https://github.com/open-trust-layer/marketplace/actions/runs/38152712256) and merged-main [CI #38156716441](https://github.com/open-trust-layer/marketplace/actions/runs/38156716441) succeeded; local report remains BLOCKED on missing optional dependencies, evaluator DSN and auth provisioning | MERGED / SOURCE & OFFLINE EVIDENCE ONLY |
| October 12 Web reliability / recovery | [PRs #549–#555](https://github.com/open-trust-layer/marketplace/pulls?q=is%3Apr+is%3Amerged+sort%3Aupdated-desc) harden bounded responses, error codes, loading/error recovery, response-ID uniqueness and detail identity checking. Exact-head CI passed through [#555](https://github.com/open-trust-layer/marketplace/actions/runs/38230561938); independent merged-main CI passed through [#554](https://github.com/open-trust-layer/marketplace/actions/runs/38229917116), with #555 main CI still running | SOURCE MERGED THROUGH #555 / LATEST MAIN CI PENDING; BROWSER RUNTIME UNVERIFIED |
| PostgreSQL-backed authenticated localhost browser flight | [Issue #525](https://github.com/open-trust-layer/marketplace/issues/525) tracks fresh *post-M17.7P* two-party Agreement publication and seller-delivery completion; requires separately authorized loopback execution and non-secret evidence | LIVE ACCEPTANCE PENDING |
| Android | Source/contract/toolchain wiring exists; no evidenced compiled, installed, signed, or distributed Android build | NOT RUNTIME ACCEPTED |
| Production Marketplace, payments and settlement | No production hosting, public-network activation, persistent production PostgreSQL, payment/settlement, or Android distribution | NOT ACTIVATED |
| Moon Commerce integration | Root Marketplace and Moon Core fallback manifests now both declare development `workspace` after [Moon Core PR #582](https://github.com/tehki/ai-automation-department/pull/582), independently verified by [merged-main CI #38158336011](https://github.com/tehki/ai-automation-department/actions/runs/38158336011). [Issue #528](https://github.com/open-trust-layer/marketplace/issues/528) still tracks authoritative live host and deployment classification; workspace metadata is not runtime liveness | SOURCE MANIFESTS ALIGNED / LIVE HOST UNVERIFIED |

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
- [x] Independently verified [#539 merged-main push acceptance #38129774633](https://github.com/open-trust-layer/marketplace/actions/runs/38129774633) **succeeded** on `b753548137845694db88b9f2c1b5757a5d57ccdf`.
- [x] Merged source-only PRs #541–#545 after individual exact-head CI and zero unresolved review threads; their independent main-push acceptance is also verified through [#545's successful #38143703077](https://github.com/open-trust-layer/marketplace/actions/runs/38143703077).
- [x] On X230i, prepared a clean detached Marketplace evaluator checkout and matched the workflow-pinned OLP revision `4e57057d5d946797814f33125f77c4b6732cbfda`; confirmed the source verifier against both without starting a server, browser, or PostgreSQL.
- [x] Independently verified [#545 merged-main push acceptance #38143703077](https://github.com/open-trust-layer/marketplace/actions/runs/38143703077) completed successfully for exact merge `b4e45bd42a4672aea896a63f80749cb09297d123`.
- [ ] Record any additional server-side, enrollment, or Agreement URI validation concerns as separately reviewed scopes; M17.8E does not claim to fix them.

**Exit:** exact-head CI succeeded through #555 and independent merged-main CI succeeded through #554. Latest #555 merged-main acceptance remains pending at this checkpoint. Source-only checks do not establish an authenticated PostgreSQL browser flight, runtime liveness or production readiness.

### P1 — Complete the authenticated PostgreSQL-backed localhost product flight

**Tracking:** [Issue #525](https://github.com/open-trust-layer/marketplace/issues/525). Offline validator input is bounded by merged PR #526; this does **not** establish live browser acceptance.

Prerequisites: approved evaluator host, reviewed dependencies and pinned OLP checkout, locally provisioned auth evidence, a local PostgreSQL evaluator DSN, and **separate authorization for runtime execution**. Do not copy DSNs, keys, session values, or provisioning contents into GitHub.

**2026-10-11 evaluator readiness:** X230i has a fresh, separate clean checkout at the reviewed #544 merged commit and the exact clean CI-pinned OLP source. The presence-only checker confirmed the selected default Python environment still lacks `psycopg`, `uvicorn`, and `cryptography`, and has neither an evaluator DSN nor an identified local authentication-provisioning directory; the separately attempted virtualenv setup was blocked by platform safety checks, so no dependency install is claimed. The offline Git verifier passed on the clean checkouts, including synthetic negative tests for hidden Git index flags. The real PostgreSQL/browser journey and official graph preflight remain **UNPERFORMED**, not accepted. Current source revisions and prerequisites must be rechecked just before authorized execution.

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
- [x] Align Moon Core fallback manifest with Marketplace owner-owned development `workspace` declaration via [Moon Core PR #582](https://github.com/tehki/ai-automation-department/pull/582) (independent main CI success).
- [ ] Resolve the remaining [Issue #528](https://github.com/open-trust-layer/marketplace/issues/528) *authoritative host and deployment lifecycle* with Moon Company; do not treat workspace presence as an active service or publish fake heartbeats.
- [ ] Recheck latest main, PR queue, and provider-visible acceptance status at each release checkpoint.

## Engineering effort — rough planning ranges, not measured work

The ranges below are **forward-looking engineering estimates only**, now updated for the 2026-10-11 checkpoint. They are not supported by time tracking, and depend on available evaluator hosts, toolchains, credentials, defect count and review availability. They exclude external waiting, payment-provider onboarding and production infrastructure procurement.

| Next unit | Approximate engineering effort | Key dependency |
| --- | ---: | --- |
| P0 merged-main evidence and PR triage | Exact-head CI through #555, independent main CI through #554; #555 main CI pending | Future CI/provider access |
| P1 authenticated localhost flight and evidence | 6–16 h | Ready local PostgreSQL/auth evaluator + explicit runtime permission |
| P2 local product UX, negative paths and repeatability | 12–32 h | P1 findings |
| P3 Android compiled/runtime proof | 8–24 h | Android toolchain and test target |
| P4 preview security/operations readiness plan | 24–72 h | Threat model, environment and authorized launch scope |
| **Illustrative remaining subtotal (P1–P4)** | **50–144 h** | **Not a commitment or countdown to production** |

Material bugs or external prerequisites may expand these figures. A public product launch, payment activation, legal readiness or Android distribution must not be inferred from the subtotal.

## Product decision boundary

**Next decisive deliverable:** complete and validate the real PostgreSQL-backed, authenticated, **loopback-only** two-user Agreement + seller-delivery browser flight. Source merges do not substitute for this evidence. The database-free MVP may be demonstrated independently, but must not be represented as the persistent authenticated product.

## Краткий статус (RU)

Базовые спецификации и локальный демонстрационный MVP подтверждены, но это **не** подтверждение промышленной эксплуатации. Изменения #546–#548 добавили объединённую офлайн-диагностику готовности среды; PR #549–#555 повысили надёжность Web-клиента. Для PR #555 успешно завершена CI точного коммита #38230561938 и код объединён с `main` в `89c4492f`. Его отдельная CI-проверка `main` #38242297232 ещё выполнялась на момент этого обновления. Для PR #554 независимая CI-проверка #38229917116 успешно завершилась.

Тестовая среда всё ещё не подготовлена для полноценного сценария с PostgreSQL: отсутствуют подтверждённые зависимости, тестовый DSN и подготовленные материалы аутентификации. Реальный браузерный сценарий двух участников после M17.7P **не был проведён и не принят**. Он требует отдельного разрешения на локальный runtime, проверки безопасности и хранения только несекретных доказательств.

Moon Core PR #582 согласовал декларации `development/workspace` с Marketplace, и независимая CI #38158336011 прошла успешно. Но рабочее пространство **не является** доказательством запущенного сервиса; настоящий хост и модель развертывания остаются открытыми в #528. Продакшен, публичный доступ, платежи и выпуск Android не активированы.
