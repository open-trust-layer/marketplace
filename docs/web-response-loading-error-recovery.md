# Web response-loading error recovery

The Marketplace browser presents a localized loading indicator while fetching responses to the selected intent. Before this change, a failed response request appended its terminal error after the loading indicator, leaving **both “Loading responses…” and an error visible at once**.

`renderResponses` now replaces the loading indicator with the terminal error message once the active request fails. The existing selection/request-serial stale-response guard runs **before** the replacement. Success still renders the response list, and changing EN/RU still replaces the failed state with one localized error. There are no API route, retry, authentication, protocol, database or network behavior changes.

Tests: `python -m unittest tests.test_product_response_loading_error_state tests.test_product_mvp_response_parent_navigation tests.test_product_mvp_bilingual_ui`. The new Node.js offline test exercises real `renderResponses` with stubbed responses for success, active failure and a stale failure without any live API or browser.

Rollback: revert the source-only PR. The change does not start services or touch persistent state.
