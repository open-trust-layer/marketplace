# Marketplace Web detail record identity consistency

When the user opens a response card, the browser requests `GET /api/intents/{record_id}`. The existing handler tracks the current request serial and uses the requested ID as the selection key. Previously, it did not verify the returned JSON against that key, so a malformed/wrong-id record could be presented as the selected record.

The browser now rejects **malformed non-object detail payloads** and any object that explicitly contains a `record_id` different from the requested ID. Rejection uses the stable `INTENT_DETAIL_INVALID` error and the already-reviewed terminal failure cleanup: the selected record, parent-navigation context and response-state fields are cleared. Stale request completions remain ignored **before** this validation. The matching-ID path works as before; document-shaped canonical record objects that omit `record_id` are still supported for compatibility.

This is a consistency guard, not a cryptographic identity proof. The server-side record identity/evidence validation remains authoritative; a well-shaped response could still be dishonest about other fields. No new API requests, retries, session changes, database operations or live browser evaluation are introduced.

Regression coverage is in `tests/test_product_failed_inspection_state.py`. The actual handler is executed offline in Node.js with matching, missing, mismatched and malformed identities plus existing stale, success and fetch failure cases. Cross-platform focused tests and complete exact-head CI are required before merge.

Rollback is a source-only revert; no persistent product or runtime state changes.
