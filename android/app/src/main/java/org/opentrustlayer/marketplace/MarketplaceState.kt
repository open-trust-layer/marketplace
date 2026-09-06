package org.opentrustlayer.marketplace

internal const val MAX_LIST_PAGES = 4
internal const val MAX_SYNC_PAGES = 4
private const val ONLINE_RESPONSE_STATUS = "Bounded response view; completeness is not claimed"

data class MarketplaceUiState(
    val rootRecords: List<RawRecord> = emptyList(),
    val selectedRecord: RawRecord? = null,
    val responses: List<RawRecord> = emptyList(),
    val responseStatus: String = ONLINE_RESPONSE_STATUS,
    val syncCursor: Long? = null,
    val syncStatus: String = "Not synchronized",
    val isOfflineCached: Boolean = false,
)

class MarketplaceState(
    private val client: MarketplaceApiClient,
    private val cache: MarketplaceOfflineCache,
    private val nowEpochMillis: () -> Long,
) {
    var uiState: MarketplaceUiState = MarketplaceUiState()
        private set
    private var offlineSnapshot: MarketplaceOfflineSnapshot? = null

    suspend fun startupSync() {
        try {
            fullResync()
        } catch (error: MarketplaceClientException) {
            if (error.code != "APPLICATION_HTTP_TRANSPORT_FAILED" || !adoptOfflineCache()) throw error
        }
    }

    suspend fun fullResync() {
        val watermark = captureSyncWatermark()
        val records = hydrateCurrentIntents()
        val snapshot = MarketplaceOfflineSnapshot(
            synchronizedAtEpochMillis = nowEpochMillis(),
            syncCursor = watermark,
            rootRecords = records,
        )
        cache.replace(snapshot)
        offlineSnapshot = snapshot
        uiState = MarketplaceUiState(
            rootRecords = records,
            syncCursor = watermark,
            syncStatus = "Synchronized at local cursor $watermark",
            isOfflineCached = false,
        )
    }

    suspend fun selectRootIntent(recordId: String) {
        if (uiState.isOfflineCached) {
            selectOfflineIntent(recordId)
            return
        }
        val record = client.getIntent(recordId)
        val responses = hydrateBoundedResponses(recordId)
        cacheSelectedResponses(record, responses)
        uiState = uiState.copy(
            selectedRecord = record,
            responses = responses,
            responseStatus = ONLINE_RESPONSE_STATUS,
        )
    }

    suspend fun createProductListing(fields: ProductListingInput) {
        requireOnlineWrite()
        client.createProductListing(fields)
        fullResync()
    }

    suspend fun createProposal(parentId: String, fields: ProposalInput) {
        requireOnlineWrite()
        client.createProposal(parentId, fields)
        fullResync()
        selectRootIntent(parentId)
    }

    private fun requireOnlineWrite() {
        if (uiState.isOfflineCached) {
            throw MarketplaceClientException("OFFLINE_WRITE_UNAVAILABLE", "Marketplace writes require an online application API")
        }
    }

    private suspend fun hydrateBoundedResponses(parentId: String): List<RawRecord> {
        val responseList = client.listResponses(parentId)
        return responseList.recordIds.map { client.getIntent(it) }
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
            if (!hasMore) {
                val snapshot = MarketplaceOfflineSnapshot(
                    synchronizedAtEpochMillis = nowEpochMillis(),
                    syncCursor = cursor,
                    rootRecords = refreshed,
                )
                cache.replace(snapshot)
                offlineSnapshot = snapshot
            }
            val status = if (hasMore) {
                "Sync paused at local cursor $cursor; more changes remain"
            } else {
                "Synchronized at local cursor $cursor"
            }
            uiState = uiState.copy(
                rootRecords = refreshed,
                selectedRecord = null,
                responses = emptyList(),
                responseStatus = ONLINE_RESPONSE_STATUS,
                syncCursor = cursor,
                syncStatus = status,
                isOfflineCached = false,
            )
        } catch (error: MarketplaceClientException) {
            if (error.code == "SYNC_CURSOR_EXPIRED") {
                fullResync()
                return
            }
            throw error
        }
    }

    private suspend fun adoptOfflineCache(): Boolean {
        val snapshot = cache.load(nowEpochMillis()) ?: return false
        offlineSnapshot = snapshot
        uiState = MarketplaceUiState(
            rootRecords = snapshot.rootRecords,
            syncCursor = snapshot.syncCursor,
            syncStatus = offlineCacheStatus(snapshot),
            responseStatus = "$OFFLINE_CACHE_STATUS_PREFIX - cached responses are bounded and may be absent",
            isOfflineCached = true,
        )
        return true
    }

    private fun selectOfflineIntent(recordId: String) {
        val snapshot = offlineSnapshot
            ?: throw MarketplaceClientException("OFFLINE_CACHE_UNAVAILABLE", "offline cache is unavailable")
        val record = snapshot.rootRecords.firstOrNull { it.id == recordId }
            ?: throw MarketplaceClientException("OFFLINE_CACHE_RECORD_MISSING", "record is not available in offline cache")
        val hasCachedResponses = snapshot.selectedParentId == recordId
        val responses = if (hasCachedResponses) snapshot.selectedResponses else emptyList()
        uiState = uiState.copy(
            selectedRecord = record,
            responses = responses,
            responseStatus = if (hasCachedResponses) {
                "$OFFLINE_CACHE_STATUS_PREFIX - cached responses; completeness is not claimed"
            } else {
                "$OFFLINE_CACHE_STATUS_PREFIX - no cached responses for this intent"
            },
        )
    }

    private suspend fun cacheSelectedResponses(record: RawRecord, responses: List<RawRecord>) {
        val prior = offlineSnapshot ?: return
        if (prior.rootRecords.none { it.id == record.id }) return
        val updated = prior.copy(
            selectedParentId = record.id,
            selectedResponses = responses,
        )
        cache.replace(updated)
        offlineSnapshot = updated
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
