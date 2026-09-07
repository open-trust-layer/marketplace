package org.opentrustlayer.marketplace

private val MARKETPLACE_SESSION_TOKEN = Regex("mkt1_[A-Za-z0-9_-]{43}")
private val MARKETPLACE_BEARER_AUTHORIZATION = Regex("Bearer mkt1_[A-Za-z0-9_-]{43}")
private val MARKETPLACE_PRINCIPAL_URI = Regex("[A-Za-z][A-Za-z0-9+.-]*:\\S+")

internal const val API_AUTH_SESSION = "/api/auth/session"
internal const val API_AUTH_LOGOUT = "/api/auth/logout"

internal fun reviewedAuthenticatedClientRoute(method: String, path: String): Boolean {
    if (method == "GET") return path == "/api/auth/session"
    if (method != "POST") return false
    if (path == "/api/auth/logout") return true
    if (path == "/api/product-listings") return true
    if (path == "/api/intents") return true
    if (!path.startsWith("/api/intents/")) return false
    val parts = path.removePrefix("/api/intents/").split('/')
    if (parts.size != 2 || parts[0].isEmpty()) return false
    if (parts[0].contains('?') || parts[0].contains('#')) return false
    val tail = parts[1]
    return tail == "responses" || tail == "proposals"
}

internal fun reviewedBearerAuthorization(value: String): Boolean =
    MARKETPLACE_BEARER_AUTHORIZATION.matches(value)

interface EphemeralAuthorizationTransport {
    suspend fun executeEphemeral(request: ApiRequest, authorization: String?): ApiResponse
}
class MarketplaceMemorySession {
    private var bearerToken: String? = null
    private var principalValue: String? = null

    val isActive: Boolean
        get() = bearerToken != null

    fun adoptEstablishedSession(principal: String, sessionToken: String) {
        if (!MARKETPLACE_PRINCIPAL_URI.matches(principal) || !MARKETPLACE_SESSION_TOKEN.matches(sessionToken)) {
            throw MarketplaceClientException("AUTH_SESSION_INVALID", "Marketplace session is invalid")
        }
        principalValue = principal
        bearerToken = sessionToken
    }

    fun requirePrincipal(): String {
        if (bearerToken == null || principalValue == null) {
            throw MarketplaceClientException("AUTH_REQUIRED", "Marketplace session is required")
        }
        return principalValue!!
    }

    internal fun authorizationFor(method: String, path: String): String? {
        if (!reviewedAuthenticatedClientRoute(method, path)) return null
        val token = bearerToken
            ?: throw MarketplaceClientException("AUTH_REQUIRED", "Marketplace session is required")
        return "Bearer $token"
    }

    internal fun detachAuthorizationForLogout(): String {
        val token = bearerToken
            ?: throw MarketplaceClientException("AUTH_REQUIRED", "Marketplace session is required")
        val authorization = "Bearer $token"
        clear()
        return authorization
    }

    fun invalidateForServerCode(code: String) {
        if (code == "AUTH_SESSION_INVALID") clear()
    }

    fun clear() {
        bearerToken = null
        principalValue = null
    }

    override fun toString(): String = "MarketplaceMemorySession(active=$isActive)"
}

private class SessionAwareMarketplaceTransport(
    private val delegate: EphemeralAuthorizationTransport,
    private val session: MarketplaceMemorySession,
) : MarketplaceTransport {
    override suspend fun execute(request: ApiRequest): ApiResponse {
        val authorization = session.authorizationFor(request.method, request.path)
        return delegate.executeEphemeral(request, authorization)
    }
}

data class AuthenticatedProductListingInput(
    val subject_uri: String = "",
    val title: String = "",
    val description: String = "",
    val consideration_coefficient: String = "",
    val consideration_scale: String = "",
    val currency_code: String = "",
    val quantity_coefficient: String = "",
    val quantity_scale: String = "",
    val unit_uri: String = "",
    val latitude_e6: String = "",
    val longitude_e6: String = "",
)

data class AuthenticatedProposalInput(
    val subject_uri: String = "",
    val action_uri: String = "",
)

class MarketplaceSessionClient(
    private val transport: EphemeralAuthorizationTransport,
    private val codec: MarketplaceJsonCodec,
    private val session: MarketplaceMemorySession,
    private val rawIssuerPrincipal: (String) -> String,
) {
    private val delegate = MarketplaceApiClient(
        transport = SessionAwareMarketplaceTransport(transport, session),
        codec = codec,
    )

    suspend fun listIntents(cursor: String? = null): IntentPage = delegate.listIntents(cursor)
    suspend fun getIntent(recordId: String): RawRecord = delegate.getIntent(recordId)
    suspend fun listResponses(parentId: String): ResponseList = delegate.listResponses(parentId)

    suspend fun createProductListing(fields: AuthenticatedProductListingInput): WriteReceipt = authenticated {
        delegate.createProductListing(
            ProductListingInput(
                seller_principal = session.requirePrincipal(),
                subject_uri = fields.subject_uri,
                title = fields.title,
                description = fields.description,
                consideration_coefficient = fields.consideration_coefficient,
                consideration_scale = fields.consideration_scale,
                currency_code = fields.currency_code,
                quantity_coefficient = fields.quantity_coefficient,
                quantity_scale = fields.quantity_scale,
                unit_uri = fields.unit_uri,
                latitude_e6 = fields.latitude_e6,
                longitude_e6 = fields.longitude_e6,
            )
        )
    }

    suspend fun createProposal(parentId: String, fields: AuthenticatedProposalInput): WriteReceipt = authenticated {
        delegate.createProposal(
            parentId,
            ProposalInput(
                buyer_principal = session.requirePrincipal(),
                subject_uri = fields.subject_uri,
                action_uri = fields.action_uri,
            ),
        )
    }
    suspend fun createIntent(rawRecordJson: String): WriteReceipt = authenticated {
        requireRawIssuer(rawRecordJson)
        delegate.createIntent(rawRecordJson)
    }

    suspend fun respondToIntent(parentId: String, rawRecordJson: String): WriteReceipt = authenticated {
        requireRawIssuer(rawRecordJson)
        delegate.respondToIntent(parentId, rawRecordJson)
    }

    suspend fun captureSyncWatermark(): Long = delegate.captureSyncWatermark()
    suspend fun sync(cursor: Long): SyncPage = delegate.sync(cursor)

    suspend fun inspectSession(): ApiResponse = authenticated {
        val authorization = session.authorizationFor("GET", API_AUTH_SESSION)
        expectSuccessfulAuthResponse(
            transport.executeEphemeral(ApiRequest("GET", API_AUTH_SESSION), authorization)
        )
    }

    suspend fun logout(): ApiResponse {
        val authorization = session.detachAuthorizationForLogout()
        val response = try {
            transport.executeEphemeral(ApiRequest("POST", API_AUTH_LOGOUT), authorization)
        } catch (error: MarketplaceClientException) {
            throw error
        } catch (_: Exception) {
            throw MarketplaceClientException("APPLICATION_HTTP_TRANSPORT_FAILED", "Marketplace logout failed")
        }
        return expectSuccessfulAuthResponse(response)
    }

    private suspend fun <T> authenticated(block: suspend () -> T): T {
        return try {
            block()
        } catch (error: MarketplaceClientException) {
            session.invalidateForServerCode(error.code)
            throw error
        }
    }
    private fun requireRawIssuer(rawRecordJson: String) {
        val issuer = try {
            rawIssuerPrincipal(rawRecordJson)
        } catch (_: Exception) {
            throw MarketplaceClientException("AUTH_PRINCIPAL_MISMATCH", "raw record issuer does not match session")
        }
        if (issuer != session.requirePrincipal()) {
            throw MarketplaceClientException("AUTH_PRINCIPAL_MISMATCH", "raw record issuer does not match session")
        }
    }

    private fun expectSuccessfulAuthResponse(response: ApiResponse): ApiResponse {
        if (response.status in 200..299) return response
        val code = try {
            codec.decodeErrorCode(response.body)
        } catch (_: Exception) {
            null
        } ?: "APPLICATION_HTTP_ERROR"
        session.invalidateForServerCode(code)
        throw MarketplaceClientException(code, "Marketplace auth request failed")
    }
}
