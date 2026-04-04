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

    private fun post(path: String, body: Map<String, String> = emptyMap()): JsonObject? =
        postWithTimeout(path, body, 30_000)

    private fun postWithTimeout(
        path: String,
        body: Map<String, String> = emptyMap(),
        timeoutMs: Int = 30_000
    ): JsonObject? = runCatching {
        val json = buildJsonObject { body.forEach { (k, v) -> put(k, v) } }.toString()
        val conn = (URL("${cleanBase()}$path").openConnection() as HttpURLConnection).apply {
            requestMethod = "POST"
            setRequestProperty("X-Admin-Token", token)
            setRequestProperty("Content-Type", "application/json")
            doOutput = true
            connectTimeout = 10_000
            readTimeout = timeoutMs
            connect()
            OutputStreamWriter(outputStream).use { it.write(json) }
        }
        if (conn.responseCode !in 200..299) return null
        Json.parseToJsonElement(conn.inputStream.bufferedReader().readText()).jsonObject
    }.getOrNull()

    private fun postJsonObject(path: String, body: JsonObject, timeoutMs: Int = 30_000): JsonObject? =
        runCatching {
            val json = body.toString()
            val conn = (URL("${cleanBase()}$path").openConnection() as HttpURLConnection).apply {
                requestMethod = "POST"
                setRequestProperty("X-Admin-Token", token)
                setRequestProperty("Content-Type", "application/json")
                doOutput = true
                connectTimeout = 10_000
                readTimeout = timeoutMs
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

    /**
     * Returns HTTP status code from GET /api/status with auth header.
     * -1 = network error / unreachable
     * 200 = OK
     * 401 = wrong token
     * other = unexpected server response
     */
    suspend fun testConnection(): Int = withContext(Dispatchers.IO) {
        runCatching {
            val conn = (URL("${cleanBase()}/api/status").openConnection() as HttpURLConnection).apply {
                requestMethod = "GET"
                setRequestProperty("X-Admin-Token", token)
                connectTimeout = 8_000; readTimeout = 8_000
                connect()
            }
            conn.responseCode
        }.getOrElse { -1 }
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

    suspend fun deleteNeoTool(toolName: String): Boolean = withContext(Dispatchers.IO) {
        post("/api/neo/tool/delete", mapOf("name" to toolName)) != null
    }

    // ── Agent task execution ──────────────────────────────────────────────────

    /**
     * Run a task through the unified agent API with a 120-second timeout.
     * All agents (matrix/neo/smith) → POST /api/agent/run {"task": task, "agent": agentId}
     */
    suspend fun runAgentTask(agentId: String, task: String): AgentResult? = withContext(Dispatchers.IO) {
        // Use the unified /api/agent/run endpoint for all agents
        val j = postWithTimeout("/api/agent/run", mapOf("task" to task, "agent" to agentId), 120_000)
            ?: return@withContext null

        AgentResult(
            ok     = j["ok"]?.jsonPrimitive?.booleanOrNull ?: false,
            result = j["result"]?.jsonPrimitive?.contentOrNull ?: "",
            steps  = j["steps"]?.jsonArray?.mapNotNull {
                runCatching { it.jsonPrimitive.contentOrNull }.getOrNull()
                    ?: runCatching { it.jsonObject.toString() }.getOrNull()
            } ?: emptyList(),
            error  = j["error"]?.jsonPrimitive?.contentOrNull ?: ""
        )
    }

    // ── LLM configuration ─────────────────────────────────────────────────────

    /** POST /api/config — set LLM provider/model configuration */
    suspend fun setLlmConfig(configs: Map<String, String>): Boolean = withContext(Dispatchers.IO) {
        val j = post("/api/config", configs) ?: return@withContext false
        j["ok"]?.jsonPrimitive?.booleanOrNull ?: false
    }

    // ── Provider status ───────────────────────────────────────────────────────

    /** GET /api/providers/status */
    suspend fun getProviderStatus(): ProviderStatus? = withContext(Dispatchers.IO) {
        val j = get("/api/providers/status") ?: return@withContext null
        ProviderStatus(
            activeLlm   = j["active_llm"]?.jsonPrimitive?.contentOrNull ?: "?",
            bestLlm     = j["best_llm"]?.jsonPrimitive?.contentOrNull ?: "?",
            activeImage = j["active_image"]?.jsonPrimitive?.contentOrNull ?: "?"
        )
    }

    // ── Tunnel control ────────────────────────────────────────────────────────

    /** POST /api/tunnel/start {"type": type} */
    suspend fun startTunnel(type: String): TunnelResult? = withContext(Dispatchers.IO) {
        val j = post("/api/tunnel/start", mapOf("type" to type)) ?: return@withContext null
        TunnelResult(
            ok    = j["ok"]?.jsonPrimitive?.booleanOrNull ?: false,
            url   = j["url"]?.jsonPrimitive?.contentOrNull ?: "",
            error = j["error"]?.jsonPrimitive?.contentOrNull ?: ""
        )
    }

    /** POST /api/tunnel/stop */
    suspend fun stopTunnel(): Boolean = withContext(Dispatchers.IO) {
        val j = post("/api/tunnel/stop") ?: return@withContext false
        j["ok"]?.jsonPrimitive?.booleanOrNull ?: false
    }

    // ── Skills evolution ──────────────────────────────────────────────────────

    /** GET /api/skills/evolution -> ok, skills[] */
    suspend fun getSkillsEvolution(): List<Skill> = withContext(Dispatchers.IO) {
        val j = get("/api/skills/evolution") ?: return@withContext emptyList()
        j["skills"]?.jsonArray?.mapNotNull { el ->
            runCatching {
                val s = el.jsonObject
                Skill(
                    pattern = s["pattern"]?.jsonPrimitive?.contentOrNull ?: return@mapNotNull null,
                    tools   = s["tools"]?.jsonArray?.mapNotNull { it.jsonPrimitive.contentOrNull } ?: emptyList(),
                    success = s["success"]?.jsonPrimitive?.intOrNull ?: 0,
                    fail    = s["fail"]?.jsonPrimitive?.intOrNull ?: 0,
                    rate    = s["rate"]?.jsonPrimitive?.intOrNull ?: 0,
                    level   = s["level"]?.jsonPrimitive?.contentOrNull ?: "?"
                )
            }.getOrNull()
        } ?: emptyList()
    }

    // ── Server restart ────────────────────────────────────────────────────────

    /** POST /api/restart */
    suspend fun restartServer(): Boolean = withContext(Dispatchers.IO) {
        val j = post("/api/restart") ?: return@withContext false
        j["ok"]?.jsonPrimitive?.booleanOrNull ?: false
    }

    // ── System info ───────────────────────────────────────────────────────────

    /** GET /api/system — parse relevant fields into string map */
    suspend fun getSystemInfo(): Map<String, String>? = withContext(Dispatchers.IO) {
        val j = get("/api/system") ?: return@withContext null
        buildMap {
            j.forEach { (key, value) ->
                val strVal = runCatching { value.jsonPrimitive.content }.getOrElse { value.toString() }
                put(key, strVal)
            }
        }
    }

    // ── Learning stats ────────────────────────────────────────────────────────

    /** GET /api/learning/stats */
    suspend fun getLearningStats(): Map<String, String> = withContext(Dispatchers.IO) {
        val j = get("/api/learning/stats") ?: return@withContext emptyMap()
        j.entries.associate { (k, v) ->
            k to (runCatching { v.jsonPrimitive.content }.getOrElse { v.toString() })
        }
    }

    // ── Memory users ──────────────────────────────────────────────────────────

    /** GET /api/memory/users */
    suspend fun getMemoryUsers(): Map<String, String> = withContext(Dispatchers.IO) {
        val j = get("/api/memory/users") ?: return@withContext emptyMap()
        j.entries.associate { (k, v) ->
            k to (runCatching { v.jsonPrimitive.content }.getOrElse { v.toString() })
        }
    }

    // ── Models discovery ──────────────────────────────────────────────────────

    /** GET /api/models/discover */
    suspend fun discoverModels(): Map<String, List<String>> = withContext(Dispatchers.IO) {
        val j = get("/api/models/discover") ?: return@withContext emptyMap()
        val models = j["models"]?.jsonObject ?: return@withContext emptyMap()
        models.entries.associate { (provider, arr) ->
            provider to (arr.jsonArray.mapNotNull { it.jsonPrimitive.contentOrNull })
        }
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
    data class AgentResult(val ok: Boolean, val result: String, val steps: List<String>, val error: String)
    data class ProviderStatus(val activeLlm: String, val bestLlm: String, val activeImage: String)
    data class TunnelResult(val ok: Boolean, val url: String, val error: String)
    data class Skill(val pattern: String, val tools: List<String>, val success: Int,
                     val fail: Int, val rate: Int, val level: String)
}
