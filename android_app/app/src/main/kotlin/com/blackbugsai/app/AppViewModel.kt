package com.blackbugsai.app

import android.app.Application
import androidx.datastore.core.DataStore
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.blackbugsai.app.services.TelegramBotService
import com.blackbugsai.app.ui.screens.AgentStatus
import com.blackbugsai.app.ui.screens.projectAgents
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.launch

// DataStore extension on Application context
val android.content.Context.dataStore: DataStore<Preferences>
        by preferencesDataStore(name = "blackbugsai_config")

object PrefKeys {
    val APP_MODE      = stringPreferencesKey("app_mode")       // "telegram" | "server"
    val BOT_TOKEN     = stringPreferencesKey("bot_token")
    val SERVER_URL    = stringPreferencesKey("server_url")
    val ADMIN_TOKEN   = stringPreferencesKey("admin_token")
}

/** Tracks known user chat IDs for broadcast, kept in-memory per session. */
val knownChatIds = mutableSetOf<Long>()

class AppViewModel(application: Application) : AndroidViewModel(application) {

    private val dataStore = application.dataStore

    // ── Exposed state ─────────────────────────────────────────────────────────
    private val _appMode    = MutableStateFlow("") // "" = not configured yet
    val appMode: StateFlow<String> = _appMode

    private val _botToken   = MutableStateFlow("")
    val botToken: StateFlow<String> = _botToken

    private val _serverUrl  = MutableStateFlow("")
    val serverUrl: StateFlow<String> = _serverUrl

    private val _adminToken = MutableStateFlow("")
    val adminToken: StateFlow<String> = _adminToken

    private val _botService = MutableStateFlow<TelegramBotService?>(null)
    val botService: StateFlow<TelegramBotService?> = _botService

    /** All received updates (max 200 kept in memory). */
    private val _updates = MutableStateFlow<List<TelegramBotService.Update>>(emptyList())
    val updates: StateFlow<List<TelegramBotService.Update>> = _updates

    /** Whether the polling loop is currently running. */
    private val _polling = MutableStateFlow(false)
    val polling: StateFlow<Boolean> = _polling

    private var pollingJob: Job? = null
    private var lastOffset: Int = 0

    // ── Init: load config from DataStore ─────────────────────────────────────
    init {
        viewModelScope.launch {
            val prefs = dataStore.data.first()
            val mode  = prefs[PrefKeys.APP_MODE]  ?: ""
            val token = prefs[PrefKeys.BOT_TOKEN]  ?: ""
            val url   = prefs[PrefKeys.SERVER_URL]  ?: ""
            val admin = prefs[PrefKeys.ADMIN_TOKEN] ?: ""

            _botToken.value   = token
            _serverUrl.value  = url
            _adminToken.value = admin
            _appMode.value    = mode

            if (token.isNotBlank()) {
                val svc = TelegramBotService(token)
                _botService.value = svc
                startPolling(svc)
            }
        }
    }

    // ── Save telegram config ──────────────────────────────────────────────────
    fun saveTelegramConfig(token: String) {
        viewModelScope.launch {
            dataStore.edit { prefs ->
                prefs[PrefKeys.APP_MODE]  = "telegram"
                prefs[PrefKeys.BOT_TOKEN] = token
            }
            _botToken.value  = token
            _appMode.value   = "telegram"
            val svc = TelegramBotService(token)
            _botService.value = svc
            startPolling(svc)
        }
    }

    // ── Save server config ────────────────────────────────────────────────────
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
            if (botToken.isNotBlank()) {
                val svc = TelegramBotService(botToken)
                _botService.value = svc
                startPolling(svc)
            } else {
                pollingJob?.cancel()
                _botService.value = null
            }
        }
    }

    // ── Centralized polling ───────────────────────────────────────────────────
    /**
     * Starts a single long-poll loop. Cancels any previous loop first,
     * which fixes the 409 Conflict error caused by multiple concurrent getUpdates calls.
     */
    private fun startPolling(svc: TelegramBotService) {
        pollingJob?.cancel()
        lastOffset = 0
        _polling.value = true
        pollingJob = viewModelScope.launch {
            while (true) {
                try {
                    // long-poll with 10s server-side timeout
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
                    delay(5_000) // back-off on network error
                }
                // tiny pause before next long-poll request
                delay(500)
            }
        }
    }

    // ── Bot command handler ───────────────────────────────────────────────────
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
                "/start" -> svc.sendMessage(
                    chatId,
                    "BlackBugsAI Admin Bot\n\n" +
                    "Доступные команды:\n" +
                    "/status — статус системы\n" +
                    "/agents — список агентов\n" +
                    "/online — активные агенты\n" +
                    "/help — справка"
                )
                "/help" -> svc.sendMessage(
                    chatId,
                    "/status — статус системы\n" +
                    "/agents — все агенты\n" +
                    "/online — только активные\n" +
                    "/start — приветствие"
                )
                "/status" -> {
                    val online  = projectAgents.count { it.status == AgentStatus.ONLINE || it.status == AgentStatus.RUNNING }
                    val running = projectAgents.count { it.status == AgentStatus.RUNNING }
                    val offline = projectAgents.count { it.status == AgentStatus.OFFLINE }
                    svc.sendMessage(
                        chatId,
                        "Статус BlackBugsAI\n\n" +
                        "Всего агентов: ${projectAgents.size}\n" +
                        "Активных: $online\n" +
                        "Выполняются: $running\n" +
                        "Оффлайн: $offline\n" +
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
                    svc.sendMessage(chatId, if (list.isBlank()) "Нет активных агентов" else "Активные агенты:\n\n$list")
                }
            }
        }
    }

    // ── Disconnect / reset ────────────────────────────────────────────────────
    fun disconnect() {
        pollingJob?.cancel()
        pollingJob = null
        _polling.value = false
        viewModelScope.launch {
            dataStore.edit { it.clear() }
            _appMode.value    = ""
            _botToken.value   = ""
            _serverUrl.value  = ""
            _adminToken.value = ""
            _botService.value = null
            _updates.value    = emptyList()
            lastOffset        = 0
            knownChatIds.clear()
        }
    }
}
