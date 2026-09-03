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
fun MarketplaceScreen(
    uiState: MarketplaceUiState,
    onSync: () -> Unit,
    onSelectIntent: (String) -> Unit,
    onCreateIntent: (String) -> Unit,
    onRespondToIntent: (String, String) -> Unit,
) {
    var createJson by remember { mutableStateOf("") }
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
            if (uiState.responses.isNotEmpty()) {
                Text("Responses", style = MaterialTheme.typography.titleSmall)
                uiState.responses.forEach { response ->
                    Text(response.id, style = MaterialTheme.typography.bodySmall)
                }
            }

            Text("Create intent", style = MaterialTheme.typography.titleMedium)
            OutlinedTextField(
                value = createJson,
                onValueChange = { createJson = it },
                label = { Text("Reviewed raw record JSON") },
                modifier = Modifier.fillMaxWidth(),
            )
            Button(onClick = { onCreateIntent(createJson) }) {
                Text("Submit intent")
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
