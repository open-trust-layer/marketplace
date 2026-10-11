# Web API declared-response-length early guard

Scope: local Marketplace browser UI (`web/app.js`) and authenticated session client's response decoder (`web/client_session.js`).

Both clients already enforce the shared M17.1G 300 KiB response-body limit after decoding text. Before this change, a server response with a declared oversized `Content-Length` could still be fully buffered by `response.text()` before that limit was checked.

The clients now reject a valid decimal Content-Length greater than 300 KiB **before** calling `response.text()`, with the existing stable code `APPLICATION_HTTP_RESPONSE_TOO_LARGE`. The existing UTF-8 byte-length bound after text materialization remains unchanged, including for missing, malformed, underreported or chunked lengths. Accepted 300 KiB values and all existing API, authentication and failure semantics are unchanged.

**Boundary:** This is an early-failure optimization for declared oversized bodies, **not** a claim that all HTTP response buffering is bounded. Servers that omit or underreport Content-Length may still cause `response.text()` to buffer a large body before the existing post-read limit rejects it. Full streamed byte enforcement would be a separate, cross-client compatibility scope.

Verification: `python -m unittest tests.test_product_web_http_length_preflight` checks both source call sites, retained post-read guards, and uses Node.js (when installed) to execute the helper on oversized, boundary-sized, invalid and missing headers without any network access. Full Marketplace conformance on the exact PR head and independent merged-main CI are required before acceptance.

No server, protocol, storage, credentials, session policy, PostgreSQL, payment or production behavior changes. Revert the source-only PR to roll back.
