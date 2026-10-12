# Web failed detail-inspection recovery

A response card in the Marketplace browser records its listing parent in transient client state before fetching the response detail. If that detail lookup fails, the existing browser flow clears the selected record. Previously, it **did not clear** the related transient parent ID, response IDs or response error code, retaining stale in-memory context after a terminal failure.

The current-request failure branch of `inspectIntent()` now clears `responseParentId`, `responseIds` and `responseErrorCode` together with the selected record and response loading state. It does so **only after** the existing detail request-serial stale guard. A stale completion cannot erase newer selection state. Successful response inspection still retains its exact listing parent so Back to parent, proposal context and Agreement UI behave unchanged.

The regression test `tests/test_product_failed_inspection_state.py` invokes the actual JavaScript `inspectIntent` function offline in Node.js with controlled API responses: failed lookup, superseded failed lookup and successful child lookup. Existing parent-navigation, bilingual UI and response-loading tests cover the surrounding contract.

This is a source-only cleanup of internal navigation state; no API route, server, credentials, database, payments, customer behavior or live browser session is activated. It does **not** claim end-to-end authenticated browser acceptance. Revert the PR to roll back.
