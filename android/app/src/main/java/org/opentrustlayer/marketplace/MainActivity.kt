package org.opentrustlayer.marketplace

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import kotlinx.coroutines.launch

class MainActivity : ComponentActivity() {
    private val marketplaceCodec by lazy { AndroidMarketplaceJsonCodec() }
    private val marketplaceState by lazy {
        MarketplaceState(
            client = MarketplaceApiClient(
                transport = LoopbackMarketplaceTransport(),
                codec = marketplaceCodec,
            ),
            cache = AndroidFileMarketplaceOfflineCache(
                context = applicationContext,
                codec = marketplaceCodec,
            ),
            nowEpochMillis = System::currentTimeMillis,
        )
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            MarketplaceRuntimeApplication(marketplaceState)
        }
    }
}

@Composable
private fun MarketplaceRuntimeApplication(state: MarketplaceState) {
    var uiState by remember { mutableStateOf(state.uiState) }
    var operationStatus by remember { mutableStateOf("Connecting to localhost Marketplace…") }
    val scope = rememberCoroutineScope()

    suspend fun runOperation(operation: suspend () -> Unit) {
        operationStatus = "Working…"
        try {
            operation()
            uiState = state.uiState
            operationStatus = "Ready"
        } catch (error: MarketplaceClientException) {
            operationStatus = "Operation failed: ${error.code}"
        } catch (_: Exception) {
            operationStatus = "Operation failed: CLIENT_FAILURE"
        }
    }

    LaunchedEffect(Unit) {
        runOperation { state.startupSync() }
    }

    MarketplaceScreen(
        uiState = uiState,
        operationStatus = operationStatus,
        onSync = { scope.launch { runOperation { state.incrementalSync() } } },
        onSelectIntent = { recordId ->
            scope.launch { runOperation { state.selectRootIntent(recordId) } }
        },
        onCreateProductListing = { fields ->
            scope.launch { runOperation { state.createProductListing(fields) } }
        },
        onCreateProposal = { parentId, fields ->
            scope.launch { runOperation { state.createProposal(parentId, fields) } }
        },
    )
}
