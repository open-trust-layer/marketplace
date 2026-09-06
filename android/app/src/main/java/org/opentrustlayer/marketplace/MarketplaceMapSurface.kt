package org.opentrustlayer.marketplace

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.matchParentSize
import androidx.compose.foundation.layout.offset
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.unit.dp
import org.json.JSONObject

private const val MAX_ANDROID_MAP_MARKERS = 64
private const val MAP_WIDTH = 720
private const val MAP_HEIGHT = 360
private const val MARKET_INTENT_TYPE =
    "https://open-trust-layer.github.io/marketplace/semantics/v1/record/market-intent"
private const val PRODUCT_PROFILE =
    "https://open-trust-layer.github.io/marketplace/semantics/v1/profile/product-listing-v1"
private const val PRODUCT_ACTION =
    "https://open-trust-layer.github.io/marketplace/semantics/v1/profile/product-listing-v1/action/sell"
private const val TITLE_TERM =
    "https://open-trust-layer.github.io/marketplace/semantics/v1/profile/product-listing-v1/term/title"
private const val LOCATION_TERM =
    "https://open-trust-layer.github.io/marketplace/semantics/v1/profile/product-listing-v1/term/location"
private const val LOCATION_SCHEME =
    "https://open-trust-layer.github.io/marketplace/semantics/v1/profile/product-listing-v1/location/wgs84-e6"

internal data class AndroidMapMarker(
    val recordId: String,
    val title: String,
    val latitudeE6: Int,
    val longitudeE6: Int,
)

internal data class AndroidMapPoint(val x: Int, val y: Int)

internal fun projectAndroidWgs84E6(latitudeE6: Int, longitudeE6: Int): AndroidMapPoint {
    require(latitudeE6 in -90_000_000..90_000_000) { "latitudeE6 outside WGS84 range" }
    require(longitudeE6 in -180_000_000..180_000_000) { "longitudeE6 outside WGS84 range" }
    val x = ((longitudeE6.toLong() + 180_000_000L) * (MAP_WIDTH - 1) / 360_000_000L).toInt()
    val y = ((90_000_000L - latitudeE6.toLong()) * (MAP_HEIGHT - 1) / 180_000_000L).toInt()
    return AndroidMapPoint(x, y)
}
internal fun extractAndroidMapMarkers(records: List<RawRecord>): List<AndroidMapMarker> {
    val markers = ArrayList<AndroidMapMarker>(minOf(records.size, MAX_ANDROID_MAP_MARKERS))
    for (record in records) {
        if (markers.size == MAX_ANDROID_MAP_MARKERS) break
        markerFromRecord(record)?.let(markers::add)
    }
    return markers
}

private fun markerFromRecord(record: RawRecord): AndroidMapMarker? = try {
    val root = JSONObject(record.rawJson)
    if (root.optString("type") != MARKET_INTENT_TYPE || !hasReviewedProductProfile(root)) return null
    val content = root.optJSONObject("content") ?: return null
    if (content.optJSONObject("action")?.optString("id") != PRODUCT_ACTION) return null
    val terms = content.optJSONObject("terms") ?: return null
    val title = terms.opt(TITLE_TERM) as? String ?: return null
    val location = terms.optJSONObject(LOCATION_TERM) ?: return null
    if (location.optString("scheme") != LOCATION_SCHEME) return null
    val value = location.optJSONObject("value") ?: return null
    val latitudeE6 = exactJsonInt(value.opt("latitude_e6")) ?: return null
    val longitudeE6 = exactJsonInt(value.opt("longitude_e6")) ?: return null
    projectAndroidWgs84E6(latitudeE6, longitudeE6)
    AndroidMapMarker(record.id, title, latitudeE6, longitudeE6)
} catch (_: Exception) {
    null
}

private fun hasReviewedProductProfile(root: JSONObject): Boolean {
    val profiles = root.optJSONArray("profiles") ?: return false
    for (index in 0 until profiles.length()) {
        if (profiles.opt(index) == PRODUCT_PROFILE) return true
    }
    return false
}

private fun exactJsonInt(value: Any?): Int? = when (value) {
    is Int -> value
    is Long -> if (value in Int.MIN_VALUE.toLong()..Int.MAX_VALUE.toLong()) value.toInt() else null
    else -> null
}
private fun formatE6(value: Int): String {
    val sign = if (value < 0) "-" else ""
    val absolute = kotlin.math.abs(value.toLong())
    return "$sign${absolute / 1_000_000}.${(absolute % 1_000_000).toString().padStart(6, '0')}"
}

@Composable
fun MarketplaceMapSurface(
    records: List<RawRecord>,
    onSelectIntent: (String) -> Unit,
) {
    val markers = remember(records) { extractAndroidMapMarkers(records) }
    Text("WGS84 map", style = MaterialTheme.typography.titleMedium)
    Text(
        "Offline deterministic coordinate view; issuer-attributed, not verified.",
        style = MaterialTheme.typography.bodySmall,
    )
    if (markers.isEmpty()) {
        Text(
            "No local listings in this bounded map view; this is not global nonexistence.",
            style = MaterialTheme.typography.bodySmall,
        )
        return
    }

    val gridColor = MaterialTheme.colorScheme.outlineVariant
    val backgroundColor = MaterialTheme.colorScheme.surfaceVariant
    val markerColor = MaterialTheme.colorScheme.primary
    val markerTextColor = MaterialTheme.colorScheme.onPrimary
    BoxWithConstraints(
        modifier = Modifier
            .fillMaxWidth()
            .height(180.dp)
            .background(backgroundColor),
    ) {
        Canvas(modifier = Modifier.matchParentSize()) {
            for (column in 0..4) {
                val x = size.width * column / 4f
                drawLine(gridColor, start = androidx.compose.ui.geometry.Offset(x, 0f), end = androidx.compose.ui.geometry.Offset(x, size.height))
            }
            for (row in 0..2) {
                val y = size.height * row / 2f
                drawLine(gridColor, start = androidx.compose.ui.geometry.Offset(0f, y), end = androidx.compose.ui.geometry.Offset(size.width, y))
            }
        }

        markers.forEachIndexed { index, marker ->
            val point = projectAndroidWgs84E6(marker.latitudeE6, marker.longitudeE6)
            val x = (maxWidth * (point.x.toFloat() / (MAP_WIDTH - 1))).coerceIn(10.dp, maxWidth - 10.dp)
            val y = (maxHeight * (point.y.toFloat() / (MAP_HEIGHT - 1))).coerceIn(10.dp, maxHeight - 10.dp)
            Box(
                modifier = Modifier
                    .offset(x = x - 10.dp, y = y - 10.dp)
                    .size(20.dp)
                    .background(markerColor, CircleShape)
                    .clickable { onSelectIntent(marker.recordId) }
                    .semantics { contentDescription = "Map marker ${index + 1}: ${marker.title}" },
                contentAlignment = Alignment.Center,
            ) {
                Text(
                    text = (index + 1).toString(),
                    color = markerTextColor,
                    style = MaterialTheme.typography.labelSmall,
                )
            }
        }
    }

    Text(
        "${markers.size} local listing marker(s) in this bounded view.",
        style = MaterialTheme.typography.bodySmall,
    )
    Column(modifier = Modifier.fillMaxWidth()) {
        markers.forEachIndexed { index, marker ->
            Text(
                "${index + 1}. ${marker.title} - ${formatE6(marker.latitudeE6)}, ${formatE6(marker.longitudeE6)}",
                modifier = Modifier
                    .fillMaxWidth()
                    .clickable { onSelectIntent(marker.recordId) },
                style = MaterialTheme.typography.bodySmall,
            )
        }
    }
}
