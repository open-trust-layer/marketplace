package org.opentrustlayer.marketplace

import java.io.ByteArrayOutputStream
import java.net.HttpURLConnection
import java.net.URI
import java.nio.ByteBuffer
import java.nio.charset.CodingErrorAction
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

private const val LOOPBACK_BASE_URL = "http://localhost:18080"
private const val CONNECT_TIMEOUT_MS = 5_000
private const val READ_TIMEOUT_MS = 5_000
private const val MAX_REQUEST_BYTES = 256 * 1024
private const val MAX_RESPONSE_BYTES = 300 * 1024
private const val MAX_REQUEST_PATH_CHARS = 4_096

class LoopbackMarketplaceTransport : MarketplaceTransport, EphemeralAuthorizationTransport {
    private val baseUri = URI(LOOPBACK_BASE_URL)

    override suspend fun execute(request: ApiRequest): ApiResponse =
        executeEphemeral(request, null)

    override suspend fun executeEphemeral(request: ApiRequest, authorization: String?): ApiResponse =
        withContext(Dispatchers.IO) {
            executeBlocking(request, authorization)
        }
    private fun executeBlocking(request: ApiRequest, authorization: String?): ApiResponse {
        val target = reviewedTarget(request)
        if (authorization != null) {
            if (!reviewedBearerAuthorization(authorization) ||
                !reviewedAuthenticatedClientRoute(request.method, request.path)
            ) {
                fail("AUTH_SESSION_INVALID", "Marketplace authorization is invalid")
            }
        }
        val connection = target.toURL().openConnection() as HttpURLConnection
        try {
            connection.instanceFollowRedirects = false
            connection.connectTimeout = CONNECT_TIMEOUT_MS
            connection.readTimeout = READ_TIMEOUT_MS
            connection.requestMethod = request.method
            connection.setRequestProperty("Accept", "application/json")
            if (authorization != null) {
                connection.setRequestProperty("Authorization", authorization)
            }
            val body = request.body
            if (body != null) writeBody(connection, body)
            val status = connection.responseCode
            val stream = if (status >= 400) connection.errorStream else connection.inputStream
            val responseBody = stream?.use(::readBoundedUtf8) ?: ""
            return ApiResponse(status = status, body = responseBody)
        } catch (error: MarketplaceClientException) {
            throw error
        } catch (_: Exception) {
            throw MarketplaceClientException("APPLICATION_HTTP_TRANSPORT_FAILED", "Marketplace loopback request failed")
        } finally {
            connection.disconnect()
        }
    }
    private fun reviewedTarget(request: ApiRequest): URI {
        if (request.method != "GET" && request.method != "POST") {
            fail("APPLICATION_HTTP_METHOD_INVALID", "Marketplace request method is not allowed")
        }
        val emptyLogout = request.method == "POST" && request.path == API_AUTH_LOGOUT && request.body == null
        if ((request.method == "GET" && request.body != null) ||
            (request.method == "POST" && request.body == null && !emptyLogout)
        ) {
            fail("APPLICATION_HTTP_ENTITY_INVALID", "Marketplace request entity does not match the reviewed method")
        }
        if (request.path.length !in 1..MAX_REQUEST_PATH_CHARS || !request.path.startsWith("/") || request.path.startsWith("//")) {
            fail("APPLICATION_HTTP_PATH_INVALID", "Marketplace request path is invalid")
        }
        val relative = try {
            URI(request.path)
        } catch (_: Exception) {
            fail("APPLICATION_HTTP_PATH_INVALID", "Marketplace request path is invalid")
        }
        if (relative.isAbsolute || relative.rawAuthority != null || relative.rawFragment != null) {
            fail("APPLICATION_HTTP_PATH_INVALID", "Marketplace request path is invalid")
        }
        val resolved = baseUri.resolve(relative)
        if (
            resolved.scheme != "http" || resolved.host != "localhost" || resolved.port != 18080 ||
            resolved.rawUserInfo != null || resolved.rawFragment != null
        ) {
            fail("APPLICATION_HTTP_ORIGIN_INVALID", "Marketplace request left the reviewed loopback origin")
        }
        return resolved
    }
    private fun writeBody(connection: HttpURLConnection, body: String) {
        val bytes = body.encodeToByteArray()
        if (bytes.size !in 1..MAX_REQUEST_BYTES) {
            fail("APPLICATION_HTTP_REQUEST_TOO_LARGE", "Marketplace request body is outside the reviewed bound")
        }
        connection.doOutput = true
        connection.setFixedLengthStreamingMode(bytes.size)
        connection.setRequestProperty("Content-Type", "application/json")
        connection.outputStream.use { it.write(bytes) }
    }

    private fun readBoundedUtf8(stream: java.io.InputStream): String {
        val output = ByteArrayOutputStream()
        val buffer = ByteArray(8 * 1024)
        while (true) {
            val count = stream.read(buffer)
            if (count < 0) break
            if (output.size() + count > MAX_RESPONSE_BYTES) {
                fail("APPLICATION_HTTP_RESPONSE_TOO_LARGE", "Marketplace API response exceeded the reviewed bound")
            }
            output.write(buffer, 0, count)
        }
        val bytes = output.toByteArray()
        return try {
            Charsets.UTF_8.newDecoder()
                .onMalformedInput(CodingErrorAction.REPORT)
                .onUnmappableCharacter(CodingErrorAction.REPORT)
                .decode(ByteBuffer.wrap(bytes))
                .toString()
        } catch (_: Exception) {
            fail("APPLICATION_HTTP_RESPONSE_INVALID", "Marketplace API response is not valid UTF-8")
        }
    }

    private fun fail(code: String, message: String): Nothing =
        throw MarketplaceClientException(code, message)
}
