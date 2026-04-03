package com.blackbugsai.app.services

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import kotlinx.serialization.json.*
import java.io.BufferedReader
import java.io.InputStreamReader
import java.io.OutputStreamWriter
import java.net.HttpURLConnection
import java.net.URL

class TelegramBotService(val token: String) {

    private val baseUrl = "https://api.telegram.org/bot$token"

    // ── Data models ──────────────────────────────────────────────────────────

    data class BotInfo(
        val id: Long,
        val username: String,
        val firstName: String
    )

    data class Update(
        val updateId: Int,
        val message: Message?
    )

    data class Message(
        val messageId: Int,
        val from: User?,
        val text: String?,
        val date: Long
    )

    data class User(
        val id: Long,
        val username: String?,
        val firstName: String
    )

    // ── HTTP helpers ──────────────────────────────────────────────────────────

    private suspend fun get(endpoint: String): JsonObject? = withContext(Dispatchers.IO) {
        try {
            val url = URL("$baseUrl/$endpoint")
            val conn = (url.openConnection() as HttpURLConnection).apply {
                requestMethod = "GET"
                connectTimeout = 10_000
                readTimeout    = 15_000
                setRequestProperty("Accept", "application/json")
            }
            val code = conn.responseCode
            val stream = if (code in 200..299) conn.inputStream else conn.errorStream
            val body = stream.bufferedReader().use { it.readText() }
            conn.disconnect()
            Json.parseToJsonElement(body).jsonObject
        } catch (e: Exception) {
            null
        }
    }

    private suspend fun post(endpoint: String, payload: String): JsonObject? =
        withContext(Dispatchers.IO) {
            try {
                val url = URL("$baseUrl/$endpoint")
                val conn = (url.openConnection() as HttpURLConnection).apply {
                    requestMethod = "POST"
                    doOutput = true
                    connectTimeout = 10_000
                    readTimeout    = 15_000
                    setRequestProperty("Content-Type", "application/json")
                    setRequestProperty("Accept", "application/json")
                }
                OutputStreamWriter(conn.outputStream).use { it.write(payload) }
                val code = conn.responseCode
                val stream = if (code in 200..299) conn.inputStream else conn.errorStream
                val body = stream.bufferedReader().use { it.readText() }
                conn.disconnect()
                Json.parseToJsonElement(body).jsonObject
            } catch (e: Exception) {
                null
            }
        }

    // ── Public API ────────────────────────────────────────────────────────────

    suspend fun validateToken(): Boolean {
        val resp = get("getMe") ?: return false
        return resp["ok"]?.jsonPrimitive?.booleanOrNull == true
    }

    suspend fun getBotInfo(): BotInfo? {
        val resp = get("getMe") ?: return null
        if (resp["ok"]?.jsonPrimitive?.booleanOrNull != true) return null
        val result = resp["result"]?.jsonObject ?: return null
        return BotInfo(
            id        = result["id"]?.jsonPrimitive?.long ?: 0L,
            username  = result["username"]?.jsonPrimitive?.contentOrNull ?: "",
            firstName = result["first_name"]?.jsonPrimitive?.contentOrNull ?: ""
        )
    }

    suspend fun getUpdates(offset: Int = 0): List<Update> {
        val endpoint = if (offset > 0) "getUpdates?offset=$offset&limit=50"
                       else "getUpdates?limit=50"
        val resp = get(endpoint) ?: return emptyList()
        if (resp["ok"]?.jsonPrimitive?.booleanOrNull != true) return emptyList()

        val resultArray = resp["result"]?.jsonArray ?: return emptyList()
        return resultArray.mapNotNull { elem ->
            val obj      = elem.jsonObject
            val updateId = obj["update_id"]?.jsonPrimitive?.intOrNull ?: return@mapNotNull null
            val msgObj   = obj["message"]?.jsonObject
            val message  = msgObj?.let { m ->
                val fromObj = m["from"]?.jsonObject
                Message(
                    messageId = m["message_id"]?.jsonPrimitive?.intOrNull ?: 0,
                    from = fromObj?.let { u ->
                        User(
                            id        = u["id"]?.jsonPrimitive?.long ?: 0L,
                            username  = u["username"]?.jsonPrimitive?.contentOrNull,
                            firstName = u["first_name"]?.jsonPrimitive?.contentOrNull ?: ""
                        )
                    },
                    text = m["text"]?.jsonPrimitive?.contentOrNull,
                    date = m["date"]?.jsonPrimitive?.long ?: 0L
                )
            }
            Update(updateId = updateId, message = message)
        }
    }

    suspend fun sendMessage(chatId: Long, text: String): Boolean {
        val escaped = text.replace("\"", "\\\"")
        val payload = """{"chat_id":$chatId,"text":"$escaped"}"""
        val resp = post("sendMessage", payload) ?: return false
        return resp["ok"]?.jsonPrimitive?.booleanOrNull == true
    }
}
