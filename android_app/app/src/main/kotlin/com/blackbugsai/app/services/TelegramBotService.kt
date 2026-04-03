package com.blackbugsai.app.services

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import kotlinx.serialization.json.*
import java.io.OutputStreamWriter
import java.net.HttpURLConnection
import java.net.URL

class TelegramBotService(val token: String) {

    private val baseUrl = "https://api.telegram.org/bot$token"

    // ── Data models ──────────────────────────────────────────────────────────

    data class BotInfo(val id: Long, val username: String, val firstName: String)

    data class Update(val updateId: Int, val message: Message?)

    data class Message(
        val messageId: Int,
        val from: User?,
        val chat: Chat?,
        val text: String?,
        val date: Long
    )

    data class User(val id: Long, val username: String?, val firstName: String)

    data class Chat(val id: Long, val type: String)

    data class BotCommand(val command: String, val description: String)

    // ── HTTP helpers ──────────────────────────────────────────────────────────

    private suspend fun get(endpoint: String, readTimeoutMs: Int = 20_000): JsonObject? =
        withContext(Dispatchers.IO) {
            try {
                val conn = (URL("$baseUrl/$endpoint").openConnection() as HttpURLConnection).apply {
                    requestMethod = "GET"
                    connectTimeout = 10_000
                    readTimeout    = readTimeoutMs
                    setRequestProperty("Accept", "application/json")
                }
                val code = conn.responseCode
                val body = (if (code in 200..299) conn.inputStream else conn.errorStream)
                    .bufferedReader().use { it.readText() }
                conn.disconnect()
                Json.parseToJsonElement(body).jsonObject
            } catch (e: Exception) { null }
        }

    private suspend fun post(endpoint: String, payload: String): JsonObject? =
        withContext(Dispatchers.IO) {
            try {
                val conn = (URL("$baseUrl/$endpoint").openConnection() as HttpURLConnection).apply {
                    requestMethod = "POST"
                    doOutput = true
                    connectTimeout = 10_000
                    readTimeout    = 20_000
                    setRequestProperty("Content-Type", "application/json")
                    setRequestProperty("Accept",       "application/json")
                }
                OutputStreamWriter(conn.outputStream).use { it.write(payload) }
                val code = conn.responseCode
                val body = (if (code in 200..299) conn.inputStream else conn.errorStream)
                    .bufferedReader().use { it.readText() }
                conn.disconnect()
                Json.parseToJsonElement(body).jsonObject
            } catch (e: Exception) { null }
        }

    // ── Public API ────────────────────────────────────────────────────────────

    suspend fun validateToken(): Boolean {
        val resp = get("getMe") ?: return false
        return resp["ok"]?.jsonPrimitive?.booleanOrNull == true
    }

    suspend fun getBotInfo(): BotInfo? {
        val resp = get("getMe") ?: return null
        if (resp["ok"]?.jsonPrimitive?.booleanOrNull != true) return null
        val r = resp["result"]?.jsonObject ?: return null
        return BotInfo(
            id        = r["id"]?.jsonPrimitive?.long ?: 0L,
            username  = r["username"]?.jsonPrimitive?.contentOrNull ?: "",
            firstName = r["first_name"]?.jsonPrimitive?.contentOrNull ?: ""
        )
    }

    /**
     * Long-polling getUpdates.
     * [offset] = last_update_id + 1  →  acknowledges previous updates.
     * [timeout] = 0 for instant, >0 for long-poll (seconds).
     */
    suspend fun getUpdates(offset: Int = 0, timeout: Int = 0): List<Update> {
        val params = buildString {
            append("limit=50")
            if (offset > 0)  append("&offset=$offset")
            if (timeout > 0) append("&timeout=$timeout")
        }
        val readMs = if (timeout > 0) (timeout + 5) * 1000 else 15_000
        val resp = get("getUpdates?$params", readMs) ?: return emptyList()
        if (resp["ok"]?.jsonPrimitive?.booleanOrNull != true) return emptyList()

        return (resp["result"]?.jsonArray ?: return emptyList()).mapNotNull { elem ->
            val obj      = elem.jsonObject
            val updateId = obj["update_id"]?.jsonPrimitive?.intOrNull ?: return@mapNotNull null
            val msgObj   = obj["message"]?.jsonObject
            val message  = msgObj?.let { m ->
                val fromObj = m["from"]?.jsonObject
                val chatObj = m["chat"]?.jsonObject
                Message(
                    messageId = m["message_id"]?.jsonPrimitive?.intOrNull ?: 0,
                    from = fromObj?.let { u ->
                        User(
                            id        = u["id"]?.jsonPrimitive?.long ?: 0L,
                            username  = u["username"]?.jsonPrimitive?.contentOrNull,
                            firstName = u["first_name"]?.jsonPrimitive?.contentOrNull ?: ""
                        )
                    },
                    chat = chatObj?.let { c ->
                        Chat(
                            id   = c["id"]?.jsonPrimitive?.long ?: 0L,
                            type = c["type"]?.jsonPrimitive?.contentOrNull ?: "private"
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
        val escaped = text.replace("\\", "\\\\").replace("\"", "\\\"")
        val payload = """{"chat_id":$chatId,"text":"$escaped"}"""
        val resp = post("sendMessage", payload) ?: return false
        return resp["ok"]?.jsonPrimitive?.booleanOrNull == true
    }

    // ── Bot commands ──────────────────────────────────────────────────────────

    suspend fun getMyCommands(): List<BotCommand> {
        val resp = post("getMyCommands", "{}") ?: return emptyList()
        if (resp["ok"]?.jsonPrimitive?.booleanOrNull != true) return emptyList()
        return (resp["result"]?.jsonArray ?: return emptyList()).mapNotNull { el ->
            val o = el.jsonObject
            BotCommand(
                command     = o["command"]?.jsonPrimitive?.contentOrNull ?: return@mapNotNull null,
                description = o["description"]?.jsonPrimitive?.contentOrNull ?: ""
            )
        }
    }

    suspend fun setMyCommands(commands: List<BotCommand>): Boolean {
        val arr = commands.joinToString(",") {
            val cmd  = it.command.replace("\"", "\\\"")
            val desc = it.description.replace("\"", "\\\"")
            """{"command":"$cmd","description":"$desc"}"""
        }
        val payload = """{"commands":[$arr]}"""
        val resp = post("setMyCommands", payload) ?: return false
        return resp["ok"]?.jsonPrimitive?.booleanOrNull == true
    }

    suspend fun deleteMyCommands(): Boolean {
        val resp = post("deleteMyCommands", "{}") ?: return false
        return resp["ok"]?.jsonPrimitive?.booleanOrNull == true
    }
}
