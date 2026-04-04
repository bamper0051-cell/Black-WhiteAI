package com.blackbugsai.app

import android.app.Application
import androidx.datastore.core.DataStore
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.longPreferencesKey
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.blackbugsai.app.services.ServerApiService
import com.blackbugsai.app.services.TelegramBotService
import com.blackbugsai.app.ui.screens.AgentStatus
import com.blackbugsai.app.ui.screens.projectAgents
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.launch
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import java.util.UUID

val android.content.Context.dataStore: DataStore<Preferences>
        by preferencesDataStore(name = "blackbugsai_config")

object PrefKeys {
    val APP_MODE      = stringPreferencesKey("app_mode")
    val BOT_TOKEN     = stringPreferencesKey("bot_token")
    val SERVER_URL    = stringPreferencesKey("server_url")
    val ADMIN_TOKEN   = stringPreferencesKey("admin_token")
    val ADMIN_CHAT_ID = longPreferencesKey("admin_chat_id")
}

val knownChatIds = mutableSetOf<Long>()

data class AgentChatMsg(
    val id: String      = UUID.randomUUID().toString(),
    val sender: String,                       // "user" | "agent" | "system"
    val agentId: String,
    val text: String,
    val time: String    = SimpleDateFormat("HH:mm", Locale.getDefault()).format(Date()),
    val isLoading: Boolean = false
)

class AppViewModel(application: Application) : AndroidViewModel(application) {

    private val dataStore = application.dataStore

    // ── Core state ────────────────────────────────────────────────────────────
    private val _appMode     = MutableStateFlow("")
    val appMode: StateFlow<String> = _appMode

    private val _botToken    = MutableStateFlow("")
    val botToken: StateFlow<String> = _botToken

    private val _serverUrl   = MutableStateFlow("")
    val serverUrl: StateFlow<String> = _serverUrl

    private val _adminToken  = MutableStateFlow("")
    val adminToken: StateFlow<String> = _adminToken

    private val _adminChatId = MutableStateFlow(0L)
    val adminChatId: StateFlow<Long> = _adminChatId

    private val _botService  = MutableStateFlow<TelegramBotService?>(null)
    val botService: StateFlow<TelegramBotService?> = _botService

    private val _updates     = MutableStateFlow<List<TelegramBotService.Update>>(emptyList())
    val updates: StateFlow<List<TelegramBotService.Update>> = _updates

    private val _polling     = MutableStateFlow(false)
    val polling: StateFlow<Boolean> = _polling

    private val _agentMessages = MutableStateFlow<Map<String, List<AgentChatMsg>>>(emptyMap())
    val agentMessages: StateFlow<Map<String, List<AgentChatMsg>>> = _agentMessages

    // ── Server data state ──────────────────────────────────────────────────────
    private val _serverStatus = MutableStateFlow<ServerApiService.ServerStatus?>(null)
    val serverStatus: StateFlow<ServerApiService.ServerStatus?> = _serverStatus

    private val _sysInfo = MutableStateFlow<ServerApiService.SysInfo?>(null)
    val sysInfo: StateFlow<ServerApiService.SysInfo?> = _sysInfo

    // ── Lazy ServerApiService ──────────────────────────────────────────────────
    private var _serverApi: ServerApiService? = null
    val serverApi: ServerApiService?
        get() {
            val url   = _serverUrl.value
            val token = _adminToken.value
            return if (url.isNotBlank() && token.isNotBlank()) {
                _serverApi ?: ServerApiService(url, token).also { _serverApi = it }
            } else null
        }

    private var pollingJob: Job? = null
    private var serverRefreshJob: Job? = null
    private var lastOffset: Int = 0

    // ── Init ──────────────────────────────────────────────────────────────────
    init {
        viewModelScope.launch {
            val prefs  = dataStore.data.first()
            val mode   = prefs[PrefKeys.APP_MODE]      ?: ""
            val token  = prefs[PrefKeys.BOT_TOKEN]     ?: ""
            val url    = prefs[PrefKeys.SERVER_URL]    ?: ""
            val admin  = prefs[PrefKeys.ADMIN_TOKEN]   ?: ""
            val chatId = prefs[PrefKeys.ADMIN_CHAT_ID] ?: 0L

            _botToken.value    = token
            _serverUrl.value   = url
            _adminToken.value  = admin
            _appMode.value     = mode
            _adminChatId.value = chatId

            if (token.isNotBlank()) {
                val svc = TelegramBotService(token)
                _botService.value = svc
                startPolling(svc)
            }
            if (mode == "server" && url.isNotBlank() && admin.isNotBlank()) {
                startServerRefresh()
            }
        }
    }

    // ── Admin chat ID ──────────────────────────────────────────────────────────
    fun saveAdminChatId(id: Long) {
        _adminChatId.value = id
        viewModelScope.launch {
            dataStore.edit { prefs -> prefs[PrefKeys.ADMIN_CHAT_ID] = id }
        }
    }

    // ── Telegram config ────────────────────────────────────────────────────────
    fun saveTelegramConfig(token: String) {
        viewModelScope.launch {
            dataStore.edit { prefs ->
                prefs[PrefKeys.APP_MODE]  = "telegram"
                prefs[PrefKeys.BOT_TOKEN] = token
            }
            _botToken.value  = token
            _appMode.value   = "telegram"
            _serverApi       = null
            serverRefreshJob?.cancel()
            val svc = TelegramBotService(token)
            _botService.value = svc
            startPolling(svc)
        }
    }

    // ── Server config ─────────────────────────────────────────────────────────
    fun saveServerConfig(url: String, adminToken: String, botToken: String = "") {
        viewModelScope.launch {
            dataStore.edit { prefs ->
                prefs[PrefKeys.APP_MODE]    = "server"
                prefs[PrefKeys.SERVER_URL]  = url
                prefs[PrefKeys.ADMIN_TOKEN] = adminToken
                if (botToken.isNotBlank()) prefs[PrefKeys.BOT_TOKEN] = botToken
                else prefs.remove(PrefKeys.BOT_TOKEN)
            }
            _serverUrl.value  = url
            _adminToken.value = adminToken
            _appMode.value    = "server"
            _botToken.value   = botToken
            _serverApi        = null
            if (botToken.isNotBlank()) {
                val svc = TelegramBotService(botToken)
                _botService.value = svc
                startPolling(svc)
            } else {
                pollingJob?.cancel()
                _botService.value = null
            }
            startServerRefresh()
        }
    }

    // ── Server data refresh (every 30s) ───────────────────────────────────────
    private fun startServerRefresh() {
        serverRefreshJob?.cancel()
        serverRefreshJob = viewModelScope.launch {
            while (true) {
                val api = serverApi
                if (api != null) {
                    try { _serverStatus.value = api.getStatus() } catch (_: Exception) {}
                    try { _sysInfo.value      = api.getSysInfo() } catch (_: Exception) {}
                }
                delay(30_000)
            }
        }
    }

    fun refreshServerData() {
        viewModelScope.launch {
            val api = serverApi ?: return@launch
            try { _serverStatus.value = api.getStatus() } catch (_: Exception) {}
            try { _sysInfo.value      = api.getSysInfo() } catch (_: Exception) {}
        }
    }

    // ── Send task to agent ────────────────────────────────────────────────────
    fun sendAgentTask(agentId: String, task: String) {
        val userMsg = AgentChatMsg(sender = "user", agentId = agentId, text = task)
        appendAgentMsg(agentId, userMsg)

        val loadingId  = UUID.randomUUID().toString()
        val loadingMsg = AgentChatMsg(
            id = loadingId, sender = "agent", agentId = agentId,
            text = "Выполняю задачу…", isLoading = true
        )
        appendAgentMsg(agentId, loadingMsg)

        viewModelScope.launch {
            if (_appMode.value == "server") {
                val api = serverApi
                if (api == null) {
                    replaceLoadingMsg(agentId, loadingId, "Ошибка: сервер не настроен")
                    return@launch
                }
                val result = try { api.runAgentTask(agentId, task) } catch (_: Exception) { null }
                val text = when {
                    result == null  -> "Ошибка соединения с сервером"
                    !result.ok      -> "Ошибка: ${result.error.ifBlank { "неизвестная ошибка" }}"
                    else            -> result.result.ifBlank { result.steps.joinToString("\n").ifBlank { "Выполнено" } }
                }
                replaceLoadingMsg(agentId, loadingId, text)
            } else {
                val svc    = _botService.value
                val chatId = _adminChatId.value
                if (svc == null || chatId == 0L) {
                    replaceLoadingMsg(agentId, loadingId,
                        "Укажите Admin Chat ID в настройках для отправки задач")
                    return@launch
                }
                val cmd = when (agentId) {
                    "neo"       -> "/neo $task"
                    "matrix"    -> "/matrix $task"
                    "smith"     -> "/smith $task"
                    "coder3"    -> "/code3 $task"
                    else        -> task
                }
                val ok = try { svc.sendMessage(chatId, cmd) } catch (_: Exception) { false }
                replaceLoadingMsg(agentId, loadingId,
                    if (ok) "Команда отправлена: $cmd" else "Ошибка отправки в Telegram")
            }
        }
    }

    fun clearAgentChat(agentId: String) {
        val m = _agentMessages.value.toMutableMap()
        m.remove(agentId)
        _agentMessages.value = m
    }

    private fun appendAgentMsg(agentId: String, msg: AgentChatMsg) {
        val m    = _agentMessages.value.toMutableMap()
        val list = (m[agentId] ?: emptyList()) + msg
        m[agentId] = list.takeLast(100)
        _agentMessages.value = m
    }

    private fun replaceLoadingMsg(agentId: String, loadingId: String, text: String) {
        val m    = _agentMessages.value.toMutableMap()
        val list = m[agentId] ?: return
        m[agentId] = list.map { if (it.id == loadingId) it.copy(text = text, isLoading = false) else it }
        _agentMessages.value = m
    }

    // ── Telegram polling (single loop, no 409) ────────────────────────────────
    private fun startPolling(svc: TelegramBotService) {
        pollingJob?.cancel()
        lastOffset     = 0
        _polling.value = true
        pollingJob = viewModelScope.launch {
            while (true) {
                try {
                    val batch = svc.getUpdates(offset = lastOffset, timeout = 10)
                    if (batch.isNotEmpty()) {
                        lastOffset = batch.maxOf { it.updateId } + 1
                        batch.forEach { u ->
                            u.message?.from?.let { knownChatIds.add(it.id) }
                            u.message?.chat?.let { knownChatIds.add(it.id) }
                        }
                        _updates.value = (_updates.value + batch).takeLast(200)
                        handleCommands(svc, batch)
                    }
                } catch (_: Exception) {
                    delay(5_000)
                }
                delay(500)
            }
        }
    }

    private suspend fun handleCommands(
        svc: TelegramBotService,
        updates: List<TelegramBotService.Update>
    ) {
        for (update in updates) {
            val msg    = update.message ?: continue
            val chatId = msg.chat?.id ?: msg.from?.id ?: continue
            val text   = msg.text?.trim() ?: continue
            if (!text.startsWith("/")) continue

            val cmd = text.substringBefore(" ").lowercase()
            when (cmd) {
                "/start" -> svc.sendMessage(chatId,
                    "BlackBugsAI Admin Bot\n\n" +
                    "/status — статус системы\n" +
                    "/agents — список агентов\n" +
                    "/online — активные агенты\n" +
                    "/help — справка"
                )
                "/help" -> svc.sendMessage(chatId,
                    "/status — статус системы\n" +
                    "/agents — все агенты\n" +
                    "/online — только активные\n" +
                    "/start — приветствие"
                )
                "/status" -> {
                    val online  = projectAgents.count { it.status == AgentStatus.ONLINE || it.status == AgentStatus.RUNNING }
                    val running = projectAgents.count { it.status == AgentStatus.RUNNING }
                    svc.sendMessage(chatId,
                        "Статус BlackBugsAI\n\n" +
                        "Агентов: ${projectAgents.size} (активных: $online, бегут: $running)\n" +
                        "Известных чатов: ${knownChatIds.size}"
                    )
                }
                "/agents" -> {
                    val list = projectAgents.joinToString("\n") {
                        val icon = when (it.status) {
                            AgentStatus.ONLINE  -> "[ON]"
                            AgentStatus.RUNNING -> "[RUN]"
                            AgentStatus.OFFLINE -> "[OFF]"
                            AgentStatus.ERROR   -> "[ERR]"
                        }
                        "$icon ${it.name} — ${it.type}"
                    }
                    svc.sendMessage(chatId, "Агенты BlackBugsAI:\n\n$list")
                }
                "/online" -> {
                    val list = projectAgents
                        .filter { it.status == AgentStatus.ONLINE || it.status == AgentStatus.RUNNING }
                        .joinToString("\n") { "[${it.status.name}] ${it.name}" }
                    svc.sendMessage(chatId,
                        if (list.isBlank()) "Нет активных агентов" else "Активные:\n\n$list")
                }
            }
        }
    }

    // ── Disconnect ────────────────────────────────────────────────────────────
    fun disconnect() {
        pollingJob?.cancel()
        serverRefreshJob?.cancel()
        pollingJob  = null
        serverRefreshJob = null
        _polling.value   = false
        _serverApi       = null
        viewModelScope.launch {
            dataStore.edit { it.clear() }
            _appMode.value       = ""
            _botToken.value      = ""
            _serverUrl.value     = ""
            _adminToken.value    = ""
            _adminChatId.value   = 0L
            _botService.value    = null
            _updates.value       = emptyList()
            _agentMessages.value = emptyMap()
            _serverStatus.value  = null
            _sysInfo.value       = null
            lastOffset           = 0
            knownChatIds.clear()
        }
    }
}
