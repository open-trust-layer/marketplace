# Web full-resync record ID consistency

During the browser's `hydrateCurrentIntents()` full-list recovery, the API returns a bounded page of record IDs and the client fetches each detail individually. Previously the fetched JSON was stored into the local map under the **requested** record ID without checking an explicitly embedded `record_id`. A mismatched response could be cached under the wrong listing identity despite the newer direct-detail inspection check.

The resync client now rejects a non-object detail payload or an object that contains an explicitly mismatched `record_id`, using stable `INTENT_LIST_INVALID`, **before** the record is inserted into the staging map. Canonical document-shaped records lacking `record_id` remain supported. A successful page still updates the cache only when all paginated details pass validation. Any invalid detail leaves the previously committed cache and selected state intact: no partial staging map is published.

The offline regression `tests/test_product_web_hydration_detail_identity.py` executes the real JavaScript hydrate function with mocked HTTP responses. Cases cover valid and legacy records, wrong or malformed identifiers, null/non-object data, a mismatch on the second page, prior cache retention and bounded request paths. No live HTTP calls, real browser, app runtime, credentials or PostgreSQL are required.

This checks simple client representation consistency, **not** cryptographic identity, server authenticity or an end-to-end product flight. Existing API, auth, database, Agreement, payment and production behavior are unchanged. Rollback is a source-only revert. Full exact-head and independent merged-main CI remain release requirements.
