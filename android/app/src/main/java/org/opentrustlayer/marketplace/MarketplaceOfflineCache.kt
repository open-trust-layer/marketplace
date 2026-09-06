package org.opentrustlayer.marketplace

internal const val MAX_OFFLINE_CACHE_RECORDS = 320
internal const val MAX_OFFLINE_ROOT_RECORDS = 256
internal const val MAX_OFFLINE_RESPONSE_RECORDS = 64
internal const val MAX_OFFLINE_CACHE_CANONICAL_BYTES = 32 * 1024 * 1024
internal const val MAX_OFFLINE_CACHE_AGE_MILLIS = 24L * 60L * 60L * 1000L
private const val MAX_OFFLINE_RECORD_JSON_BYTES = 300 * 1024
private const val MAX_OFFLINE_RECORD_ID_CHARS = 512
internal const val OFFLINE_CACHE_STATUS_PREFIX = "OFFLINE / CACHED"

data class MarketplaceOfflineSnapshot(
    val synchronizedAtEpochMillis: Long,
    val syncCursor: Long,
    val rootRecords: List<RawRecord>,
    val selectedParentId: String? = null,
    val selectedResponses: List<RawRecord> = emptyList(),
)

interface MarketplaceOfflineCache {
    suspend fun load(nowEpochMillis: Long): MarketplaceOfflineSnapshot?
    suspend fun replace(snapshot: MarketplaceOfflineSnapshot)
    suspend fun clear()
}

internal fun validateOfflineSnapshot(snapshot: MarketplaceOfflineSnapshot): MarketplaceOfflineSnapshot {
    if (snapshot.synchronizedAtEpochMillis < 0L || snapshot.syncCursor < 0L) {
        offlineCacheFail("OFFLINE_CACHE_INVALID", "offline cache metadata is invalid")
    }
    if (snapshot.rootRecords.size > MAX_OFFLINE_ROOT_RECORDS || snapshot.selectedResponses.size > MAX_OFFLINE_RESPONSE_RECORDS) {
        offlineCacheFail("OFFLINE_CACHE_BOUNDS", "offline cache record count exceeded")
    }
    if (snapshot.rootRecords.size + snapshot.selectedResponses.size > MAX_OFFLINE_CACHE_RECORDS) {
        offlineCacheFail("OFFLINE_CACHE_BOUNDS", "offline cache record count exceeded")
    }
    if (snapshot.selectedParentId == null && snapshot.selectedResponses.isNotEmpty()) {
        offlineCacheFail("OFFLINE_CACHE_INVALID", "offline response cache has no parent")
    }
    val allIds = LinkedHashSet<String>()
    var canonicalBytes = 0L
    fun inspect(record: RawRecord) {
        if (record.id.isEmpty() || record.id.length > MAX_OFFLINE_RECORD_ID_CHARS || !allIds.add(record.id)) {
            offlineCacheFail("OFFLINE_CACHE_INVALID", "offline cache record identity is invalid")
        }
        val bytes = record.rawJson.encodeToByteArray().size
        if (bytes !in 1..MAX_OFFLINE_RECORD_JSON_BYTES) {
            offlineCacheFail("OFFLINE_CACHE_BOUNDS", "offline cache record JSON is outside bounds")
        }
        canonicalBytes += bytes.toLong()
        if (canonicalBytes > MAX_OFFLINE_CACHE_CANONICAL_BYTES.toLong()) {
            offlineCacheFail("OFFLINE_CACHE_BOUNDS", "offline cache canonical JSON exceeded byte limit")
        }
    }
    snapshot.rootRecords.forEach(::inspect)
    snapshot.selectedResponses.forEach(::inspect)
    val parentId = snapshot.selectedParentId
    if (parentId != null && snapshot.rootRecords.none { it.id == parentId }) {
        offlineCacheFail("OFFLINE_CACHE_INVALID", "offline response parent is not a cached root")
    }
    return snapshot
}

internal fun validateOfflineSnapshotAge(
    snapshot: MarketplaceOfflineSnapshot,
    nowEpochMillis: Long,
): MarketplaceOfflineSnapshot {
    validateOfflineSnapshot(snapshot)
    if (nowEpochMillis < snapshot.synchronizedAtEpochMillis) {
        offlineCacheFail("OFFLINE_CACHE_CLOCK_INVALID", "offline cache clock moved backwards")
    }
    if (nowEpochMillis - snapshot.synchronizedAtEpochMillis > MAX_OFFLINE_CACHE_AGE_MILLIS) {
        offlineCacheFail("OFFLINE_CACHE_EXPIRED", "offline cache is expired")
    }
    return snapshot
}

internal fun offlineCacheStatus(snapshot: MarketplaceOfflineSnapshot): String =
    "$OFFLINE_CACHE_STATUS_PREFIX - last authoritative sync ${snapshot.synchronizedAtEpochMillis}"

private fun offlineCacheFail(code: String, message: String): Nothing =
    throw MarketplaceClientException(code, message)
