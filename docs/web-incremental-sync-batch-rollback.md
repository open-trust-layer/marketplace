# Browser incremental synchronization: failed-batch cursor rollback

An incremental sync may successfully validate one page, advance the browser cursor, and then fail on a later page or during list rehydration. The displayed record cache is not accepted until rehydration succeeds. Preserving the newer cursor after such a failure could cause a subsequent retry to overlook changes.

The browser now takes a batch-entry cursor snapshot when running incremental synchronization. Each page continues to use the existing per-page validation from #558, with the same max-page limit and normal success/pause behavior. On any thrown failure within the batch (including a later fetch, invalid page or list hydration failure), it restores the original cursor before propagating the error. For SYNC_CURSOR_EXPIRED, rollback occurs first and the existing fullResync() fallback then runs.

The offline regression tests/test_product_web_incremental_sync_batch_rollback.py executes the actual JavaScript handlers in Node.js with deterministic stubs for HTTP, record hydration and UI. It checks successful multi-page/empty/bounded behavior, failed later pages, hydration failure, and cursor expiry recovery. It does **not** start a server, browser, database, authentication session or payment flow.

Scope is **the current incremental batch**, not a transactional guarantee across separately completed user sync operations, and not live PostgreSQL/browser acceptance. Existing source-only rollback is a Git revert.
