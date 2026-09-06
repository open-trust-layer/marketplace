package org.opentrustlayer.marketplace

import android.content.Context
import java.io.File
import java.io.FileOutputStream
import java.nio.ByteBuffer
import java.nio.charset.CodingErrorAction
import java.nio.file.Files
import java.nio.file.StandardCopyOption
import java.security.MessageDigest
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.json.JSONArray
import org.json.JSONException
import org.json.JSONObject
import org.json.JSONTokener

private const val CACHE_FILE_NAME = "marketplace_offline_cache_v1.json"
private const val CACHE_TEMP_FILE_NAME = "marketplace_offline_cache_v1.tmp"
private const val CACHE_FORMAT_VERSION = 1
private const val MAX_ENCODED_CACHE_BYTES = 40 * 1024 * 1024
private const val OFFLINE_CACHE_EXPIRED_CODE = "OFFLINE_CACHE_EXPIRED"

class AndroidFileMarketplaceOfflineCache(
    context: Context,
    private val codec: MarketplaceJsonCodec,
) : MarketplaceOfflineCache {
    private val cacheFile = File(context.filesDir, CACHE_FILE_NAME)
    private val tempFile = File(context.filesDir, CACHE_TEMP_FILE_NAME)
    private val lock = Any()

    override suspend fun load(nowEpochMillis: Long): MarketplaceOfflineSnapshot? = withContext(Dispatchers.IO) {
        synchronized(lock) {
            if (!cacheFile.exists()) return@synchronized null
            if (cacheFile.length() !in 1..MAX_ENCODED_CACHE_BYTES.toLong()) {
                deleteCorruptCache()
            }
            val encoded = try {
                decodeUtf8Strict(cacheFile.readBytes())
            } catch (_: Exception) {
                deleteCorruptCache()
            }
            val snapshot = try {
                decodeEnvelope(encoded)
            } catch (_: MarketplaceClientException) {
                deleteCorruptCache()
            } catch (_: Exception) {
                deleteCorruptCache()
            }
            if (nowEpochMillis < snapshot.synchronizedAtEpochMillis) {
                deleteCacheFile("OFFLINE_CACHE_CLOCK_DELETE_FAILED")
                throw MarketplaceClientException("OFFLINE_CACHE_CLOCK_INVALID", "offline cache clock moved backwards")
            }
            if (nowEpochMillis - snapshot.synchronizedAtEpochMillis > MAX_OFFLINE_CACHE_AGE_MILLIS) {
                deleteExpiredCache()
                return@synchronized null
            }
            validateOfflineSnapshotAge(snapshot, nowEpochMillis)
        }
    }

    override suspend fun replace(snapshot: MarketplaceOfflineSnapshot) = withContext(Dispatchers.IO) {
        val reviewed = validateOfflineSnapshot(snapshot)
        validateCanonicalRecords(reviewed)
        val encoded = encodeEnvelope(reviewed).encodeToByteArray()
        if (encoded.size > MAX_ENCODED_CACHE_BYTES) {
            throw MarketplaceClientException("OFFLINE_CACHE_BOUNDS", "offline cache encoded form exceeded byte limit")
        }
        synchronized(lock) {
            try {
                Files.deleteIfExists(tempFile.toPath())
                FileOutputStream(tempFile).use { output ->
                    output.write(encoded)
                    output.fd.sync()
                }
                Files.move(
                    tempFile.toPath(),
                    cacheFile.toPath(),
                    StandardCopyOption.ATOMIC_MOVE,
                    StandardCopyOption.REPLACE_EXISTING,
                )
            } catch (_: Exception) {
                try { Files.deleteIfExists(tempFile.toPath()) } catch (_: Exception) { }
                throw MarketplaceClientException("OFFLINE_CACHE_WRITE_FAILED", "offline cache write failed")
            }
        }
    }

    override suspend fun clear() = withContext(Dispatchers.IO) {
        synchronized(lock) { deleteCacheFile("OFFLINE_CACHE_DELETE_FAILED") }
    }

    private fun validateCanonicalRecords(snapshot: MarketplaceOfflineSnapshot) {
        for (record in snapshot.rootRecords + snapshot.selectedResponses) {
            val decoded = try {
                codec.decodeRecord(record.rawJson, record.id)
            } catch (_: Exception) {
                throw MarketplaceClientException("OFFLINE_CACHE_INVALID", "offline cache record JSON is invalid")
            }
            if (decoded.id != record.id || decoded.rawJson != record.rawJson) {
                throw MarketplaceClientException("OFFLINE_CACHE_INVALID", "offline cache record identity mismatch")
            }
        }
    }

    private fun encodeEnvelope(snapshot: MarketplaceOfflineSnapshot): String {
        val payload = JSONObject()
            .put("version", CACHE_FORMAT_VERSION)
            .put("synchronized_at_ms", snapshot.synchronizedAtEpochMillis)
            .put("sync_cursor", snapshot.syncCursor)
            .put("root_records", encodeRecords(snapshot.rootRecords))
            .put("selected_parent_id", snapshot.selectedParentId ?: JSONObject.NULL)
            .put("selected_responses", encodeRecords(snapshot.selectedResponses))
            .toString()
        return JSONObject()
            .put("version", CACHE_FORMAT_VERSION)
            .put("payload", payload)
            .put("sha256", sha256Hex(payload))
            .toString()
    }

    private fun encodeRecords(records: List<RawRecord>): JSONArray {
        val array = JSONArray()
        for (record in records) {
            array.put(JSONObject().put("id", record.id).put("raw_json", record.rawJson))
        }
        return array
    }

    private fun decodeEnvelope(encoded: String): MarketplaceOfflineSnapshot {
        val envelope = parseObject(encoded)
        requireExactKeys(envelope, setOf("version", "payload", "sha256"))
        if (exactLong(envelope, "version") != CACHE_FORMAT_VERSION.toLong()) corrupt()
        val payload = exactString(envelope, "payload")
        val expectedDigest = exactString(envelope, "sha256")
        if (expectedDigest.length != 64 || expectedDigest != sha256Hex(payload)) corrupt()

        val document = parseObject(payload)
        requireExactKeys(
            document,
            setOf("version", "synchronized_at_ms", "sync_cursor", "root_records", "selected_parent_id", "selected_responses"),
        )
        if (exactLong(document, "version") != CACHE_FORMAT_VERSION.toLong()) corrupt()
        val snapshot = MarketplaceOfflineSnapshot(
            synchronizedAtEpochMillis = exactLong(document, "synchronized_at_ms"),
            syncCursor = exactLong(document, "sync_cursor"),
            rootRecords = decodeRecords(document, "root_records"),
            selectedParentId = nullableString(document, "selected_parent_id"),
            selectedResponses = decodeRecords(document, "selected_responses"),
        )
        return validateOfflineSnapshot(snapshot)
    }

    private fun decodeRecords(document: JSONObject, name: String): List<RawRecord> {
        val raw = document.opt(name) as? JSONArray ?: corrupt()
        val records = ArrayList<RawRecord>(raw.length())
        for (index in 0 until raw.length()) {
            val item = raw.opt(index) as? JSONObject ?: corrupt()
            requireExactKeys(item, setOf("id", "raw_json"))
            val id = exactString(item, "id")
            val rawJson = exactString(item, "raw_json")
            val decoded = try {
                codec.decodeRecord(rawJson, id)
            } catch (_: Exception) {
                corrupt()
            }
            if (decoded.id != id || decoded.rawJson != rawJson) corrupt()
            records.add(decoded)
        }
        return records
    }

    private fun parseObject(raw: String): JSONObject = try {
        val tokener = JSONTokener(raw)
        val value = tokener.nextValue()
        if (value !is JSONObject || tokener.nextClean() != '\u0000') corrupt()
        value
    } catch (error: MarketplaceClientException) {
        throw error
    } catch (_: JSONException) {
        corrupt()
    }

    private fun requireExactKeys(value: JSONObject, expected: Set<String>) {
        val actual = LinkedHashSet<String>()
        val keys = value.keys()
        while (keys.hasNext()) actual.add(keys.next())
        if (actual != expected) corrupt()
    }

    private fun exactString(value: JSONObject, name: String): String =
        value.opt(name) as? String ?: corrupt()

    private fun nullableString(value: JSONObject, name: String): String? {
        if (!value.has(name)) corrupt()
        if (value.isNull(name)) return null
        return exactString(value, name)
    }

    private fun exactLong(value: JSONObject, name: String): Long = when (val item = value.opt(name)) {
        is Int -> item.toLong()
        is Long -> item
        else -> corrupt()
    }

    private fun sha256Hex(value: String): String =
        MessageDigest.getInstance("SHA-256")
            .digest(value.encodeToByteArray())
            .joinToString("") { byte -> "%02x".format(byte.toInt() and 0xff) }

    private fun decodeUtf8Strict(bytes: ByteArray): String =
        Charsets.UTF_8.newDecoder()
            .onMalformedInput(CodingErrorAction.REPORT)
            .onUnmappableCharacter(CodingErrorAction.REPORT)
            .decode(ByteBuffer.wrap(bytes))
            .toString()

    private fun deleteExpiredCache() {
        deleteCacheFile(OFFLINE_CACHE_EXPIRED_CODE + "_DELETE_FAILED")
    }

    private fun deleteCorruptCache(): Nothing {
        deleteCacheFile("OFFLINE_CACHE_DELETE_FAILED")
        throw MarketplaceClientException("OFFLINE_CACHE_CORRUPT", "offline cache is corrupt")
    }

    private fun deleteCacheFile(failureCode: String) {
        try {
            Files.deleteIfExists(tempFile.toPath())
            Files.deleteIfExists(cacheFile.toPath())
        } catch (_: Exception) {
            throw MarketplaceClientException(failureCode, "offline cache deletion failed")
        }
    }

    private fun corrupt(): Nothing =
        throw MarketplaceClientException("OFFLINE_CACHE_CORRUPT", "offline cache is corrupt")
}
