# Bounded streamed API response handling (Web)

Scope: the primary Marketplace browser (`web/app.js`) and authenticated-session client (`web/client_session.js`). Issue: source-only response-buffer bounds and product robustness. This follows the declared Content-Length early guard in PR #549.

Before this change both clients used `response.text()` and only then checked UTF-8 bytes against the reviewed **300 KiB** limit. Underreported, malformed, or absent Content-Length could still force an unbounded materialization of the response before rejection.

Both clients now call `readBoundedResponseText(response)` after the existing declared-length guard. Where Fetch supplies a `ReadableStream` body, the client reads and decodes each `Uint8Array` chunk incrementally. Before appending a chunk, it fails closed with existing `APPLICATION_HTTP_RESPONSE_TOO_LARGE` when cumulative wire-body bytes would exceed 300 KiB. On read/shape errors, it reports the stable non-reflective code `RESPONSE_BODY_READ_FAILED`. It makes a best-effort cancel and releases the stream reader on completion or failure. `TextDecoder(..., {stream:true})` preserves multibyte UTF-8 across chunk boundaries.

**Compatibility and limits:** Synthetic/fallback `Response` objects without a stream retain the old `response.text()` behavior and post-read UTF-8 encoded-length bound. Both existing callers also retain their post-read checks. The improvement does **not** claim to avoid all browser/network buffering: the transport may buffer a single large chunk before exposing it, and legacy responses without streams still use a full text read. Byte limits apply to Fetch's exposed body (after HTTP decoding), not raw wire framing. No new network requests, retries, response parsing rules, bearer-token handling, server/provider imports, payment/settlement or production behavior.

**Evidence:** `python -m unittest tests.test_product_web_streaming_response_bound tests.test_product_web_http_length_preflight tests.test_m17_1g_cross_client_api_contract` exercises the helper in real Node.js without network, covering exact 300 KiB, oversize by one byte, a single huge chunk, UTF-8 multi-byte splits, reader errors, cancellation, no-stream compatibility and unchanged cross-client contract. Full exact-head and independent merged-main acceptance remain required.

Rollback: revert this source-only change. No persistent runtime state is changed.
