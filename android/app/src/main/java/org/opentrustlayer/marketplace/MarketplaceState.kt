package org.opentrustlayer.marketplace

internal const val MAX_LIST_PAGES = 4
internal const val MAX_SYNC_PAGES = 4
internal const val MAX_RESPONSE_PAGES = 4

data class MarketplaceUiState(
    val rootRecords: List<RawRecord> = emptyList(),
    val selectedRecord: RawRecord? = null,
    val responses: List<RawRecord> = emptyList(),
    val syncCursor: Long? = null,
    val syncStatus: String = "Not synchronized",
)

class MarketplaceState(
    private val client: MarketplaceApiClient,
) {
    var uiState: MarketplaceUiState = MarketplaceUiState()
        private set

    suspend fun fullResync() {
        val watermark = captureSyncWatermark()
        val records = hydrateCurrentIntents()
        uiState = uiState.copy(
            rootRecords = records,
            selectedRecord = null,
            responses = emptyList(),
            syncCursor = watermark,
            syncStatus = "Synchronized at local cursor $watermark",
        )
    }

    suspend fun selectRootIntent(recordId: String) {
        val record = client.getIntent(recordId)
        val responses = hydrateResponses(recordId)
        uiState = uiState.copy(
            selectedRecord = record,
            responses = responses,
        )
    }

    suspend fun createIntent(rawRecordJson: String) {
        client.createIntent(rawRecordJson)
        fullResync()
    }

    suspend fun respondToIntent(parentId: String, rawRecordJson: String) {
        client.respondToIntent(parentId, rawRecordJson)
        fullResync()
        selectRootIntent(parentId)
    }

    private suspend fun hydrateResponses(parentId: String): List<RawRecord> {
        val responses = LinkedHashMap<String, RawRecord>()
        val seenResponseCursors = mutableSetOf<String>()
        var cursor: String? = null
        repeat(MAX_RESPONSE_PAGES) {
            val page = client.listResponses(parentId, cursor)
            for (recordId in page.recordIds) {
                if (responses.containsKey(recordId)) {
                    throw MarketplaceClientException("RESPONSE_LIST_INVALID", "duplicate response id")
                }
                responses[recordId] = client.getIntent(recordId)
            }
            val nextCursor = page.nextCursor
            if (nextCursor == null) return responses.values.toList()
            if (!seenResponseCursors.add(nextCursor)) {
                throw MarketplaceClientException("RESPONSE_LIST_INVALID", "repeated response cursor")
            }
            cursor = nextCursor
        }
        throw MarketplaceClientException("RESPONSE_LIST_TRUNCATED", "bounded response hydration incomplete")
    }

    private suspend fun captureSyncWatermark(): Long = client.captureSyncWatermark()

    private suspend fun hydrateCurrentIntents(): List<RawRecord> {
        val records = LinkedHashMap<String, RawRecord>()
        val seenCursors = mutableSetOf<String>()
        var cursor: String? = null
        repeat(MAX_LIST_PAGES) {
            val page = client.listIntents(cursor)
            for (recordId in page.recordIds) {
                if (records.containsKey(recordId)) {
                    throw MarketplaceClientException("INTENT_LIST_INVALID", "duplicate root intent")
                }
                records[recordId] = client.getIntent(recordId)
            }
            val nextCursor = page.nextCursor
            if (nextCursor == null) return records.values.toList()
            if (nextCursor.isEmpty() || !seenCursors.add(nextCursor)) {
                throw MarketplaceClientException("INTENT_LIST_INVALID", "invalid list cursor")
            }
            cursor = nextCursor
        }
        throw MarketplaceClientException("INTENT_LIST_TRUNCATED", "bounded root hydration incomplete")
    }

    suspend fun incrementalSync() {
        var cursor = uiState.syncCursor ?: return fullResync()
        var browseDirty = false
        var hasMore = false
        try {
            for (pageNumber in 0 until MAX_SYNC_PAGES) {
                val page = client.sync(cursor)
                validateSyncPage(page, cursor)
                if (page.changes.isNotEmpty()) browseDirty = true
                cursor = page.nextCursor
                hasMore = page.hasMore
                if (!hasMore) break
            }
            val refreshed = if (browseDirty) hydrateCurrentIntents() else uiState.rootRecords
            val status = if (hasMore) {
                "Sync paused at local cursor $cursor; more changes remain"
            } else {
                "Synchronized at local cursor $cursor"
            }
            uiState = uiState.copy(
                rootRecords = refreshed,
                selectedRecord = null,
                responses = emptyList(),
                syncCursor = cursor,
                syncStatus = status,
            )
        } catch (error: MarketplaceClientException) {
            if (error.code == "SYNC_CURSOR_EXPIRED") {
                fullResync()
                return
            }
            throw error
        }
    }

    private fun validateSyncPage(page: SyncPage, priorCursor: Long) {
        var cursor = priorCursor
        for (change in page.changes) {
            if (change.cursor <= cursor) {
                throw MarketplaceClientException("SYNC_PAGE_INVALID", "non-monotonic sync change")
            }
            if (change.kind != "UPSERT" && change.kind != "DELETE") {
                throw MarketplaceClientException("SYNC_PAGE_INVALID", "invalid sync change kind")
            }
            cursor = change.cursor
        }
        if (page.nextCursor < cursor) {
            throw MarketplaceClientException("SYNC_PAGE_INVALID", "sync cursor regressed")
        }
    }
}
