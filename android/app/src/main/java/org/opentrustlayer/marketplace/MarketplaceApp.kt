package org.opentrustlayer.marketplace

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.Button
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp

@Composable
private fun ListingField(
    label: String,
    value: String,
    onValueChange: (String) -> Unit,
) {
    OutlinedTextField(
        value = value,
        onValueChange = onValueChange,
        label = { Text(label) },
        modifier = Modifier.fillMaxWidth(),
    )
}

@Composable
fun MarketplaceScreen(
    uiState: MarketplaceUiState,
    onSync: () -> Unit,
    onSelectIntent: (String) -> Unit,
    onCreateProductListing: (ProductListingInput) -> Unit,
    onRespondToIntent: (String, String) -> Unit,
) {
    var createFields by remember { mutableStateOf(ProductListingInput()) }
    var responseJson by remember { mutableStateOf("") }

    MaterialTheme {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(16.dp),
        ) {
            Row(modifier = Modifier.fillMaxWidth()) {
                Text("Marketplace", style = MaterialTheme.typography.headlineSmall)
                Button(onClick = onSync, modifier = Modifier.padding(start = 12.dp)) {
                    Text("Sync")
                }
            }
            Text(uiState.syncStatus, style = MaterialTheme.typography.bodySmall)
            Text("WGS84 map projection", style = MaterialTheme.typography.titleMedium)
            Text(
                "Presentation-only map surface; root intent coordinates remain display data.",
                style = MaterialTheme.typography.bodySmall,
            )

            Text("Intent list", style = MaterialTheme.typography.titleMedium)
            LazyColumn(modifier = Modifier.fillMaxWidth()) {
                items(uiState.rootRecords, key = { it.id }) { record ->
                    Text(
                        record.id,
                        modifier = Modifier
                            .fillMaxWidth()
                            .clickable { onSelectIntent(record.id) }
                            .padding(vertical = 8.dp),
                    )
                }
            }
            Text("Intent detail", style = MaterialTheme.typography.titleMedium)
            Text(
                uiState.selectedRecord?.rawJson ?: "Select an intent to inspect exact record JSON.",
                style = MaterialTheme.typography.bodySmall,
            )
            Text("Responses", style = MaterialTheme.typography.titleSmall)
            Text(uiState.responseStatus, style = MaterialTheme.typography.bodySmall)
            uiState.responses.forEach { response ->
                Text(response.id, style = MaterialTheme.typography.bodySmall)
            }

            Text("Create product listing", style = MaterialTheme.typography.titleMedium)
            Text(
                "Transport fields only; M17.1Q/M72 owns Marketplace semantics.",
                style = MaterialTheme.typography.bodySmall,
            )
            ListingField(
                label = "Seller principal URI",
                value = createFields.seller_principal,
                onValueChange = { createFields = createFields.copy(seller_principal = it) },
            )
            ListingField(
                label = "Subject URI",
                value = createFields.subject_uri,
                onValueChange = { createFields = createFields.copy(subject_uri = it) },
            )
            ListingField(
                label = "Title",
                value = createFields.title,
                onValueChange = { createFields = createFields.copy(title = it) },
            )
            ListingField(
                label = "Description",
                value = createFields.description,
                onValueChange = { createFields = createFields.copy(description = it) },
            )
            ListingField(
                label = "Price coefficient (integer)",
                value = createFields.consideration_coefficient,
                onValueChange = { createFields = createFields.copy(consideration_coefficient = it) },
            )
            ListingField(
                label = "Price scale (integer)",
                value = createFields.consideration_scale,
                onValueChange = { createFields = createFields.copy(consideration_scale = it) },
            )
            ListingField(
                label = "Currency code",
                value = createFields.currency_code,
                onValueChange = { createFields = createFields.copy(currency_code = it) },
            )
            ListingField(
                label = "Quantity coefficient (integer)",
                value = createFields.quantity_coefficient,
                onValueChange = { createFields = createFields.copy(quantity_coefficient = it) },
            )
            ListingField(
                label = "Quantity scale (integer)",
                value = createFields.quantity_scale,
                onValueChange = { createFields = createFields.copy(quantity_scale = it) },
            )
            ListingField(
                label = "Unit URI",
                value = createFields.unit_uri,
                onValueChange = { createFields = createFields.copy(unit_uri = it) },
            )
            ListingField(
                label = "Latitude E6 (integer)",
                value = createFields.latitude_e6,
                onValueChange = { createFields = createFields.copy(latitude_e6 = it) },
            )
            ListingField(
                label = "Longitude E6 (integer)",
                value = createFields.longitude_e6,
                onValueChange = { createFields = createFields.copy(longitude_e6 = it) },
            )
            Button(onClick = { onCreateProductListing(createFields) }) {
                Text("Submit product listing")
            }
            Text("Respond to intent", style = MaterialTheme.typography.titleMedium)
            OutlinedTextField(
                value = responseJson,
                onValueChange = { responseJson = it },
                label = { Text("Reviewed raw response record JSON") },
                modifier = Modifier.fillMaxWidth(),
            )
            val parentId = uiState.selectedRecord?.id
            Button(
                onClick = {
                    if (parentId != null) onRespondToIntent(parentId, responseJson)
                },
                enabled = parentId != null,
            ) {
                Text("Submit response")
            }
        }
    }
}
