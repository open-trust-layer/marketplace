package org.opentrustlayer.marketplace

private const val API_INTENTS = "/api/intents"
private const val API_SYNC = "/api/sync"
private const val RESPONSES_SUFFIX = "/responses"
private const val PAGE_LIMIT = 64
private const val MAX_ID_CHARS = 512
private const val MAX_RAW_JSON_BYTES = 256 * 1024
private const val MAX_RESPONSE_JSON_BYTES = 300 * 1024

data class ApiRequest(
    val method: String,
    val path: String,
    val body: String? = null,
)

data class ApiResponse(
    val status: Int,
    val body: String,
)

interface MarketplaceTransport {
    suspend fun execute(request: ApiRequest): ApiResponse
}

data class RawRecord(
    val id: String,
    val rawJson: String,
)

data class IntentPage(
    val recordIds: List<String>,
    val nextCursor: String?,
)

data class SyncChange(
    val cursor: Long,
    val kind: String,
    val recordId: String,
)

data class SyncPage(
    val changes: List<SyncChange>,
    val nextCursor: Long,
    val hasMore: Boolean,
)

interface MarketplaceJsonCodec {
    fun decodeIntentPage(rawJson: String): IntentPage
    fun decodeRecord(rawJson: String): RawRecord
    fun decodeSyncPage(rawJson: String): SyncPage
    fun decodeErrorCode(rawJson: String): String?
}

class MarketplaceClientException(
    val code: String,
    message: String,
) : IllegalStateException(message)

class MarketplaceApiClient(
    private val transport: MarketplaceTransport,
    private val codec: MarketplaceJsonCodec,
) {
    suspend fun listIntents(cursor: String? = null): IntentPage {
        val path = buildListPath(API_INTENTS, cursor)
        return validateIntentPage(codec.decodeIntentPage(expectOk(transport.execute(ApiRequest("GET", path)))))
    }

    suspend fun getIntent(recordId: String): RawRecord {
        val path = "$API_INTENTS/${encodeComponent(requireBoundedId(recordId))}"
        val record = validateRecord(codec.decodeRecord(expectOk(transport.execute(ApiRequest("GET", path)))))
        if (record.id != recordId) throw MarketplaceClientException("RECORD_ID_MISMATCH", "record identity mismatch")
        return record
    }

    suspend fun listResponses(parentId: String, cursor: String? = null): IntentPage {
        val path = "$API_INTENTS/${encodeComponent(requireBoundedId(parentId))}$RESPONSES_SUFFIX" +
            querySuffix(cursor)
        return validateIntentPage(codec.decodeIntentPage(expectOk(transport.execute(ApiRequest("GET", path)))))
    }

    suspend fun createIntent(rawRecordJson: String): RawRecord =
        validateRecord(codec.decodeRecord(
            expectOk(
                transport.execute(ApiRequest("POST", API_INTENTS, boundedRawJson(rawRecordJson)))
            )
        ))

    suspend fun respondToIntent(parentId: String, rawRecordJson: String): RawRecord {
        val path = "$API_INTENTS/${encodeComponent(requireBoundedId(parentId))}$RESPONSES_SUFFIX"
        return validateRecord(codec.decodeRecord(
            expectOk(
                transport.execute(ApiRequest("POST", path, boundedRawJson(rawRecordJson)))
            )
        ))
    }

    suspend fun captureSyncWatermark(): Long {
        val page = validateSyncPage(
            codec.decodeSyncPage(expectOk(transport.execute(ApiRequest("GET", "$API_SYNC?limit=$PAGE_LIMIT")))),
            0,
        )
        if (page.changes.isNotEmpty() || page.hasMore || page.nextCursor < 0) {
            throw MarketplaceClientException("SYNC_WATERMARK_INVALID", "invalid sync watermark")
        }
        return page.nextCursor
    }

    suspend fun sync(cursor: Long): SyncPage {
        require(cursor >= 0) { "cursor must be nonnegative" }
        val path = "$API_SYNC?cursor=$cursor&limit=$PAGE_LIMIT"
        val response = transport.execute(ApiRequest("GET", path))
        val boundedBody = boundedResponseBody(response)
        if (response.status == 409 && codec.decodeErrorCode(boundedBody) == "SYNC_CURSOR_EXPIRED") {
            throw MarketplaceClientException("SYNC_CURSOR_EXPIRED", "full resynchronization is required")
        }
        return validateSyncPage(codec.decodeSyncPage(expectOk(response)), cursor)
    }

    private fun validateSyncPage(page: SyncPage, priorCursor: Long): SyncPage {
        if (page.changes.size > PAGE_LIMIT || page.nextCursor < priorCursor) {
            throw MarketplaceClientException("SYNC_PAGE_INVALID", "invalid sync page bounds")
        }
        var cursor = priorCursor
        for (change in page.changes) {
            requireBoundedId(change.recordId)
            if (change.cursor <= cursor || (change.kind != "UPSERT" && change.kind != "DELETE")) {
                throw MarketplaceClientException("SYNC_PAGE_INVALID", "invalid sync change")
            }
            cursor = change.cursor
        }
        if (page.nextCursor < cursor) throw MarketplaceClientException("SYNC_PAGE_INVALID", "sync cursor regressed")
        return page
    }

    private fun validateIntentPage(page: IntentPage): IntentPage {
        if (page.recordIds.size > PAGE_LIMIT) throw MarketplaceClientException("INTENT_PAGE_INVALID", "intent page exceeds limit")
        val seen = mutableSetOf<String>()
        for (recordId in page.recordIds) {
            requireBoundedId(recordId)
            if (!seen.add(recordId)) throw MarketplaceClientException("INTENT_PAGE_INVALID", "duplicate record id")
        }
        val cursor = page.nextCursor
        if (cursor != null && (cursor.isEmpty() || cursor.length > MAX_ID_CHARS)) {
            throw MarketplaceClientException("INTENT_PAGE_INVALID", "invalid next cursor")
        }
        return page
    }

    private fun validateRecord(record: RawRecord): RawRecord {
        requireBoundedId(record.id)
        if (record.rawJson.encodeToByteArray().size !in 1..MAX_RESPONSE_JSON_BYTES) {
            throw MarketplaceClientException("RECORD_RESPONSE_INVALID", "record response outside byte bound")
        }
        return record
    }

    private fun buildListPath(base: String, cursor: String?): String = base + querySuffix(cursor)

    private fun querySuffix(cursor: String?): String {
        if (cursor == null) return "?limit=$PAGE_LIMIT"
        require(cursor.isNotEmpty() && cursor.length <= MAX_ID_CHARS) { "invalid cursor" }
        return "?cursor=${encodeComponent(cursor)}&limit=$PAGE_LIMIT"
    }

    private fun requireBoundedId(value: String): String {
        require(value.isNotEmpty() && value.length <= MAX_ID_CHARS) { "invalid record id" }
        return value
    }

    private fun boundedRawJson(rawRecordJson: String): String {
        val size = rawRecordJson.encodeToByteArray().size
        require(size in 1..MAX_RAW_JSON_BYTES) { "record JSON outside byte bound" }
        return rawRecordJson
    }

    private fun boundedResponseBody(response: ApiResponse): String {
        if (response.body.encodeToByteArray().size > MAX_RESPONSE_JSON_BYTES) {
            throw MarketplaceClientException("APPLICATION_HTTP_RESPONSE_TOO_LARGE", "Marketplace API response too large")
        }
        return response.body
    }

    private fun expectOk(response: ApiResponse): String {
        val boundedBody = boundedResponseBody(response)
        if (response.status !in 200..299) {
            val code = codec.decodeErrorCode(boundedBody) ?: "APPLICATION_HTTP_ERROR"
            throw MarketplaceClientException(code, "Marketplace API request failed")
        }
        return boundedBody
    }
}

private fun encodeComponent(value: String): String {
    val bytes = value.encodeToByteArray()
    val out = StringBuilder(bytes.size)
    for (byte in bytes) {
        val unsigned = byte.toInt() and 0xff
        val allowed =
            unsigned in 'a'.code..'z'.code ||
                unsigned in 'A'.code..'Z'.code ||
                unsigned in '0'.code..'9'.code ||
                unsigned == '-'.code || unsigned == '_'.code ||
                unsigned == '.'.code || unsigned == '~'.code
        if (allowed) {
            out.append(unsigned.toChar())
        } else {
            out.append('%')
            out.append("0123456789ABCDEF"[unsigned ushr 4])
            out.append("0123456789ABCDEF"[unsigned and 0x0f])
        }
    }
    return out.toString()
}
