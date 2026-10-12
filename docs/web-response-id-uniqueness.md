# Marketplace Web response ID uniqueness

When browsing responses to a selected listing, the API returns a bounded `record_ids` array. Before this change, the Web UI verified each record ID and the page-length limit, but a response containing the **same record ID twice** would render duplicate clickable cards and make the listing appear to have more distinct proposals than it does.

The client now treats duplicate IDs as `RESPONSE_LIST_INVALID` **before storing or rendering** that response page. The existing current-selection/request-serial guard still runs before validation; the failed page clears the loading placeholder and shows the normal localized error state. Empty and unique-ID pages remain accepted, and there is no deduplication that might silently mask a malformed server response.

Focused real-JavaScript offline tests in `tests/test_product_response_loading_error_state.py` exercise distinct IDs, duplicate IDs, an active fetch failure, stale failure and success. Existing bilingual and parent-navigation tests stay in scope. This only changes browser-side validation—no server contract, API endpoint, retry, authentication state, order, database, payment or production behavior changes. It does not claim that a live API has returned duplicate IDs.

Rollback: revert the source-only PR. Full exact-head acceptance and independent merged-main CI remain required.
