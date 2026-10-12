# Web API error code shape validation

Scope: Marketplace browser (`web/app.js`) and authenticated Web client session (`web/client_session.js`). This source-only change ensures application HTTP JSON `error.code` values are treated as **untrusted input**, not automatically safe to echo into user-visible status or session diagnostics.

Previously both clients passed every string in a server-provided JSON `error.code` through to a thrown error, even if it contained multiple lines, markup, paths, or arbitrarily long values. The clients now preserve protocol-shaped ASCII codes matching `[A-Z][A-Z0-9_]{1,79}`, including `AUTH_SESSION_INVALID` and `SYNC_CURSOR_EXPIRED`, and otherwise fall back to `HTTP_<status>` for integer HTTP status 100–599, or the stable `APPLICATION_HTTP_FAILED` code when the status itself is unavailable/invalid.

The session client continues to apply `session.invalidateForServerCode(stableCode)` **after validation**, so a well-formed `AUTH_SESSION_INVALID` still clears the in-memory session. Neither fallback ever formats a credential, error body, raw server code or exception text into UI-facing error codes.

**Limit:** format validation is not an exhaustive **semantic allowlist** of server error codes; any well-formed uppercase code up to 80 characters may still be exposed, and this check cannot establish server authenticity. Client paths, authentication authority, error JSON parsing, response limits, bearer-token behavior, Android contract and underlying HTTP status semantics are unchanged.

Verification: `python -m unittest tests.test_product_web_server_error_code_shape` runs static call-site checks and real JavaScript checks (when Node.js is available) covering valid server codes, auth invalidation order, multiline/markup/overlong/unexpected data, and stable fallbacks. Full exact-head CI and independent merged-main CI are required prior to qualifying the update.

Rollback: revert this source-only PR. No database, server, browser, payment, production deployment or persistent state is touched.
