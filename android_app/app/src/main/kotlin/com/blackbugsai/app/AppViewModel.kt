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
    private val _appMode = MutableStateFlow("") // "" = not configured yet
    val appMode: StateFlow<String> = _appMode

    private val _botToken = MutableStateFlow("")
    val botToken: StateFlow<String> = _botToken

    private val _serverUrl = MutableStateFlow("")
    val serverUrl: StateFlow<String> = _serverUrl

    private val _adminToken = MutableStateFlow("")
    val adminToken: StateFlow<String> = _adminToken

    private val _botService = MutableStateFlow<TelegramBotService?>(null)
    val botService: StateFlow<TelegramBotService?> = _botService

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

            // Create botService whenever a token is present, regardless of mode
            if (token.isNotBlank()) {
                _botService.value = TelegramBotService(token)
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
            _botService.value = TelegramBotService(token)
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
            _botService.value = if (botToken.isNotBlank()) TelegramBotService(botToken) else null
        }
    }

    // ── Disconnect / reset ────────────────────────────────────────────────────
    fun disconnect() {
        viewModelScope.launch {
            dataStore.edit { it.clear() }
            _appMode.value    = ""
            _botToken.value   = ""
            _serverUrl.value  = ""
            _adminToken.value = ""
            _botService.value = null
            knownChatIds.clear()
        }
    }
}
