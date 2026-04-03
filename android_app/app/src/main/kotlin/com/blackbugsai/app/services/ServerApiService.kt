package com.blackbugsai.app.services

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import kotlinx.serialization.json.*
import java.io.*
import java.net.HttpURLConnection
import java.net.URL

/**
 * REST client for BlackBugsAI admin_web.py running on a GCE VM.
 * Base URL: http://<VM_EXTERNAL_IP>:8080
 * Auth: X-Admin-Token header
 */
class ServerApiService(val baseUrl: String, val token: String) {

    // ── Low-level helpers ─────────────────────────────────────────────────────

    private fun cleanBase() = baseUrl.trimEnd('/')

    private fun get(path: String): JsonObject? = runCatching {
        val conn = (URL("${cleanBase()}$path").openConnection() as HttpURLConnection).apply {
            requestMethod = "GET"
            setRequestProperty("X-Admin-Token", token)
            connectTimeout = 10_000; readTimeout = 15_000
            connect()
        }
        if (conn.responseCode != 200) return null
        Json.parseToJsonElement(conn.inputStream.bufferedReader().readText()).jsonObject
    }.getOrNull()

    private fun post(path: String, body: Map<String, String> = emptyMap()): JsonObject? = runCatching {
        val json = buildJsonObject { body.forEach { (k, v) -> put(k, v) } }.toString()
        val conn = (URL("${cleanBase()}$path").openConnection() as HttpURLConnection).apply {
            requestMethod = "POST"
            setRequestProperty("X-Admin-Token", token)
            setRequestProperty("Content-Type", "application/json")
            doOutput = true
            connectTimeout = 10_000; readTimeout = 30_000
            connect()
            OutputStreamWriter(outputStream).use { it.write(json) }
        }
        if (conn.responseCode !in 200..299) return null
        Json.parseToJsonElement(conn.inputStream.bufferedReader().readText()).jsonObject
    }.getOrNull()

    // ── Health ────────────────────────────────────────────────────────────────

    suspend fun ping(): Boolean = withContext(Dispatchers.IO) {
        runCatching {
            val conn = (URL("${cleanBase()}/ping").openConnection() as HttpURLConnection).apply {
                connectTimeout = 5_000; readTimeout = 5_000; connect()
            }
            conn.responseCode == 200
        }.getOrElse { false }
    }

    // ── Status / sysinfo ─────────────────────────────────────────────────────

    suspend fun getStatus(): ServerStatus? = withContext(Dispatchers.IO) {
        val j = get("/api/status") ?: return@withContext null
        ServerStatus(
            uptime     = j["uptime"]?.jsonPrimitive?.intOrNull ?: 0,
            botRunning = j["bot_running"]?.jsonPrimitive?.booleanOrNull ?: false,
            taskCount  = j["task_count"]?.jsonPrimitive?.intOrNull ?: 0,
            userCount  = j["user_count"]?.jsonPrimitive?.intOrNull ?: 0,
            version    = j["version"]?.jsonPrimitive?.contentOrNull ?: "?"
        )
    }

    suspend fun getSysInfo(): SysInfo? = withContext(Dispatchers.IO) {
        val j = get("/api/sysinfo") ?: return@withContext null
        SysInfo(
            os       = j["os"]?.jsonPrimitive?.contentOrNull ?: "?",
            cpu      = j["cpu_percent"]?.jsonPrimitive?.contentOrNull ?: "?",
            ram      = j["ram_percent"]?.jsonPrimitive?.contentOrNull ?: "?",
            disk     = j["disk_percent"]?.jsonPrimitive?.contentOrNull ?: "?",
            hostname = j["hostname"]?.jsonPrimitive?.contentOrNull ?: "?",
            ip       = j["ip"]?.jsonPrimitive?.contentOrNull ?: "?"
        )
    }

    // ── Users ─────────────────────────────────────────────────────────────────

    suspend fun getUsers(): List<BotUser> = withContext(Dispatchers.IO) {
        val j = get("/api/users") ?: return@withContext emptyList()
        j["users"]?.jsonArray?.mapNotNull { el ->
            val u = el.jsonObject
            BotUser(
                id        = u["id"]?.jsonPrimitive?.longOrNull ?: return@mapNotNull null,
                username  = u["username"]?.jsonPrimitive?.contentOrNull ?: "",
                firstName = u["first_name"]?.jsonPrimitive?.contentOrNull ?: "",
                role      = u["role"]?.jsonPrimitive?.contentOrNull ?: "user",
                banned    = u["banned"]?.jsonPrimitive?.booleanOrNull ?: false,
                msgCount  = u["msg_count"]?.jsonPrimitive?.intOrNull ?: 0
            )
        } ?: emptyList()
    }

    suspend fun banUser(uid: Long): Boolean = withContext(Dispatchers.IO) {
        post("/api/users/$uid/ban") != null
    }

    suspend fun unbanUser(uid: Long): Boolean = withContext(Dispatchers.IO) {
        post("/api/users/$uid/unban") != null
    }

    suspend fun setPriv(uid: Long, role: String): Boolean = withContext(Dispatchers.IO) {
        post("/api/users/$uid/priv", mapOf("role" to role)) != null
    }

    // ── Messages ──────────────────────────────────────────────────────────────

    suspend fun sendToUser(uid: Long, text: String): Boolean = withContext(Dispatchers.IO) {
        post("/api/msg/user", mapOf("uid" to uid.toString(), "text" to text)) != null
    }

    suspend fun broadcast(text: String): BroadcastResult? = withContext(Dispatchers.IO) {
        val j = post("/api/msg/broadcast", mapOf("text" to text)) ?: return@withContext null
        BroadcastResult(
            sent   = j["sent"]?.jsonPrimitive?.intOrNull ?: 0,
            failed = j["failed"]?.jsonPrimitive?.intOrNull ?: 0
        )
    }

    // ── Logs ─────────────────────────────────────────────────────────────────

    suspend fun getLogs(limit: Int = 100): List<LogEntry> = withContext(Dispatchers.IO) {
        val j = get("/api/logs?limit=$limit") ?: return@withContext emptyList()
        j["logs"]?.jsonArray?.mapNotNull { el ->
            val e = el.jsonObject
            LogEntry(
                ts    = e["ts"]?.jsonPrimitive?.contentOrNull ?: "",
                level = e["level"]?.jsonPrimitive?.contentOrNull ?: "INFO",
                text  = e["text"]?.jsonPrimitive?.contentOrNull ?: ""
            )
        } ?: emptyList()
    }

    // ── Shell ─────────────────────────────────────────────────────────────────

    suspend fun shell(cmd: String): ShellResult? = withContext(Dispatchers.IO) {
        val j = post("/api/shell", mapOf("cmd" to cmd)) ?: return@withContext null
        ShellResult(
            stdout   = j["stdout"]?.jsonPrimitive?.contentOrNull ?: "",
            stderr   = j["stderr"]?.jsonPrimitive?.contentOrNull ?: "",
            exitCode = j["exit_code"]?.jsonPrimitive?.intOrNull ?: -1
        )
    }

    // ── Processes ─────────────────────────────────────────────────────────────

    suspend fun getProcesses(): List<ServerProcess> = withContext(Dispatchers.IO) {
        val j = get("/api/processes") ?: return@withContext emptyList()
        j["processes"]?.jsonArray?.mapNotNull { el ->
            val p = el.jsonObject
            ServerProcess(
                pid    = p["pid"]?.jsonPrimitive?.intOrNull ?: return@mapNotNull null,
                name   = p["name"]?.jsonPrimitive?.contentOrNull ?: "?",
                status = p["status"]?.jsonPrimitive?.contentOrNull ?: "?",
                cpu    = p["cpu_percent"]?.jsonPrimitive?.contentOrNull ?: "0",
                mem    = p["mem_percent"]?.jsonPrimitive?.contentOrNull ?: "0"
            )
        } ?: emptyList()
    }

    suspend fun killProcess(pid: Int): Boolean = withContext(Dispatchers.IO) {
        post("/api/processes/$pid/kill") != null
    }

    // ── Tasks ─────────────────────────────────────────────────────────────────

    suspend fun getTasks(): List<ServerTask> = withContext(Dispatchers.IO) {
        val j = get("/api/tasks") ?: return@withContext emptyList()
        j["tasks"]?.jsonArray?.mapNotNull { el ->
            val t = el.jsonObject
            ServerTask(
                id      = t["id"]?.jsonPrimitive?.contentOrNull ?: return@mapNotNull null,
                type    = t["type"]?.jsonPrimitive?.contentOrNull ?: "?",
                status  = t["status"]?.jsonPrimitive?.contentOrNull ?: "?",
                created = t["created"]?.jsonPrimitive?.contentOrNull ?: ""
            )
        } ?: emptyList()
    }

    suspend fun cancelTask(tid: String): Boolean = withContext(Dispatchers.IO) {
        post("/api/tasks/$tid/cancel") != null
    }

    suspend fun retryTask(tid: String): Boolean = withContext(Dispatchers.IO) {
        post("/api/tasks/$tid/retry") != null
    }

    // ── Agent tools (NEO / MATRIX) ────────────────────────────────────────────

    suspend fun getNeoTools(): List<AgentTool> = withContext(Dispatchers.IO) {
        val j = get("/api/neo/tools") ?: return@withContext emptyList()
        j["tools"]?.jsonArray?.mapNotNull { el ->
            val t = el.jsonObject
            AgentTool(
                name = t["name"]?.jsonPrimitive?.contentOrNull ?: return@mapNotNull null,
                desc = t["description"]?.jsonPrimitive?.contentOrNull ?: ""
            )
        } ?: emptyList()
    }

    suspend fun runMatrixTool(tool: String, params: Map<String, String>): String? = withContext(Dispatchers.IO) {
        val j = post("/api/matrix/run", mapOf("tool" to tool) + params) ?: return@withContext null
        j["result"]?.jsonPrimitive?.contentOrNull
    }

    // ── Data models ───────────────────────────────────────────────────────────

    data class ServerStatus(val uptime: Int, val botRunning: Boolean,
                            val taskCount: Int, val userCount: Int, val version: String)
    data class SysInfo(val os: String, val cpu: String, val ram: String,
                       val disk: String, val hostname: String, val ip: String)
    data class BotUser(val id: Long, val username: String, val firstName: String,
                       val role: String, val banned: Boolean, val msgCount: Int)
    data class BroadcastResult(val sent: Int, val failed: Int)
    data class LogEntry(val ts: String, val level: String, val text: String)
    data class ShellResult(val stdout: String, val stderr: String, val exitCode: Int)
    data class ServerProcess(val pid: Int, val name: String, val status: String,
                             val cpu: String, val mem: String)
    data class ServerTask(val id: String, val type: String, val status: String, val created: String)
    data class AgentTool(val name: String, val desc: String)
}
