package org.opentrustlayer.marketplace

import org.json.JSONArray
import org.json.JSONException
import org.json.JSONObject
import org.json.JSONTokener

private val APPLICATION_RECORD_ALLOWED_FIELDS = setOf(
    "envelope_version",
    "type",
    "content",
    "semantic_bindings",
    "profiles",
    "relationships",
    "extensions",
)
private val APPLICATION_RECORD_REQUIRED_FIELDS = setOf("envelope_version", "type", "content")

class AndroidMarketplaceJsonCodec : MarketplaceJsonCodec {
    override fun decodeIntentPage(rawJson: String): IntentPage {
        val document = parseObject(rawJson, "INTENT_PAGE_INVALID")
        requireExactKeys(document, setOf("record_ids", "next_cursor"), "INTENT_PAGE_INVALID")
        return IntentPage(
            recordIds = stringArray(document, "record_ids", "INTENT_PAGE_INVALID"),
            nextCursor = nullableString(document, "next_cursor", "INTENT_PAGE_INVALID"),
        )
    }

    override fun decodeResponseList(rawJson: String): ResponseList {
        val document = parseObject(rawJson, "RESPONSE_LIST_INVALID")
        requireExactKeys(document, setOf("record_ids"), "RESPONSE_LIST_INVALID")
        return ResponseList(stringArray(document, "record_ids", "RESPONSE_LIST_INVALID"))
    }

    override fun decodeWriteReceipt(rawJson: String): WriteReceipt {
        val document = parseObject(rawJson, "WRITE_RECEIPT_INVALID")
        requireExactKeys(document, setOf("change_seq", "disposition"), "WRITE_RECEIPT_INVALID")
        return WriteReceipt(
            changeSeq = nullableLong(document, "change_seq", "WRITE_RECEIPT_INVALID"),
            disposition = exactString(document, "disposition", "WRITE_RECEIPT_INVALID"),
        )
    }

    override fun decodeRecord(rawJson: String, expectedRecordId: String): RawRecord {
        if (expectedRecordId.isEmpty()) fail("RECORD_RESPONSE_INVALID", "record route identity is empty")
        val document = parseObject(rawJson, "RECORD_RESPONSE_INVALID")
        val keys = keySet(document)
        if (!keys.containsAll(APPLICATION_RECORD_REQUIRED_FIELDS) || !APPLICATION_RECORD_ALLOWED_FIELDS.containsAll(keys)) {
            fail("RECORD_RESPONSE_INVALID", "record JSON field set is invalid")
        }
        return RawRecord(expectedRecordId, rawJson)
    }

    override fun decodeSyncPage(rawJson: String): SyncPage {
        val document = parseObject(rawJson, "SYNC_PAGE_INVALID")
        requireExactKeys(document, setOf("changes", "next_cursor", "has_more"), "SYNC_PAGE_INVALID")
        val rawChanges = exactArray(document, "changes", "SYNC_PAGE_INVALID")
        val changes = ArrayList<SyncChange>(rawChanges.length())
        for (index in 0 until rawChanges.length()) {
            val item = rawChanges.opt(index) as? JSONObject
                ?: fail("SYNC_PAGE_INVALID", "sync change must be an object")
            requireExactKeys(item, setOf("change_kind", "record_id", "seq"), "SYNC_PAGE_INVALID")
            changes.add(
                SyncChange(
                    cursor = exactLong(item, "seq", "SYNC_PAGE_INVALID"),
                    kind = exactString(item, "change_kind", "SYNC_PAGE_INVALID"),
                    recordId = exactString(item, "record_id", "SYNC_PAGE_INVALID"),
                )
            )
        }
        return SyncPage(
            changes = changes,
            nextCursor = exactLong(document, "next_cursor", "SYNC_PAGE_INVALID"),
            hasMore = exactBoolean(document, "has_more", "SYNC_PAGE_INVALID"),
        )
    }

    override fun decodeErrorCode(rawJson: String): String? {
        return try {
            val document = JSONObject(rawJson)
            val error = document.opt("error") as? JSONObject
            error?.opt("code") as? String
        } catch (_: JSONException) {
            null
        }
    }

    private fun parseObject(rawJson: String, code: String): JSONObject = try {
        val tokener = JSONTokener(rawJson)
        val value = tokener.nextValue()
        if (value !is JSONObject || tokener.nextClean() != '\u0000') {
            fail(code, "Marketplace API JSON is malformed")
        }
        value
    } catch (error: MarketplaceClientException) {
        throw error
    } catch (_: JSONException) {
        fail(code, "Marketplace API JSON is malformed")
    }

    private fun keySet(value: JSONObject): Set<String> {
        val result = LinkedHashSet<String>()
        val keys = value.keys()
        while (keys.hasNext()) result.add(keys.next())
        return result
    }

    private fun requireExactKeys(value: JSONObject, expected: Set<String>, code: String) {
        if (keySet(value) != expected) fail(code, "Marketplace API JSON field set is invalid")
    }

    private fun exactArray(value: JSONObject, name: String, code: String): JSONArray =
        value.opt(name) as? JSONArray ?: fail(code, "$name must be an array")

    private fun stringArray(value: JSONObject, name: String, code: String): List<String> {
        val array = exactArray(value, name, code)
        val result = ArrayList<String>(array.length())
        for (index in 0 until array.length()) {
            val item = array.opt(index) as? String ?: fail(code, "$name must contain strings")
            result.add(item)
        }
        return result
    }

    private fun exactString(value: JSONObject, name: String, code: String): String =
        value.opt(name) as? String ?: fail(code, "$name must be a string")

    private fun nullableString(value: JSONObject, name: String, code: String): String? {
        if (!value.has(name)) fail(code, "$name is required")
        if (value.isNull(name)) return null
        return exactString(value, name, code)
    }

    private fun exactLong(value: JSONObject, name: String, code: String): Long = when (val item = value.opt(name)) {
        is Int -> item.toLong()
        is Long -> item
        else -> fail(code, "$name must be an integer")
    }

    private fun nullableLong(value: JSONObject, name: String, code: String): Long? {
        if (!value.has(name)) fail(code, "$name is required")
        if (value.isNull(name)) return null
        return exactLong(value, name, code)
    }

    private fun exactBoolean(value: JSONObject, name: String, code: String): Boolean =
        value.opt(name) as? Boolean ?: fail(code, "$name must be a boolean")

    private fun fail(code: String, message: String): Nothing = throw MarketplaceClientException(code, message)
}
