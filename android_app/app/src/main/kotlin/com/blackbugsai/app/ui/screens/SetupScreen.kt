package com.blackbugsai.app.ui.screens

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Lock
import androidx.compose.material.icons.filled.Wifi
import androidx.compose.material3.*
import androidx.compose.material3.TabRowDefaults.tabIndicatorOffset
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.blackbugsai.app.AppViewModel
import com.blackbugsai.app.ui.theme.*
import kotlinx.coroutines.launch

@Composable
fun SetupScreen(vm: AppViewModel, onConnected: () -> Unit) {
    val scope = rememberCoroutineScope()
    var selectedTab by remember { mutableIntStateOf(0) }
    val tabs = listOf("TELEGRAM", "SERVER")

    // Telegram tab state
    var botToken   by remember { mutableStateOf("") }
    var tgLoading  by remember { mutableStateOf(false) }
    var tgError    by remember { mutableStateOf("") }

    // Server tab state
    var serverUrl       by remember { mutableStateOf("") }
    var adminToken      by remember { mutableStateOf("") }
    var srvBotToken     by remember { mutableStateOf("") }
    var srvLoading      by remember { mutableStateOf(false) }
    var srvError        by remember { mutableStateOf("") }

    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(BgDeep),
        contentAlignment = Alignment.Center
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(24.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.spacedBy(20.dp)
        ) {
            // ── Header ────────────────────────────────────────────────────────
            Text(
                text       = "BlackBugsAI",
                fontSize   = 32.sp,
                fontWeight = FontWeight.Bold,
                color      = NeonCyan,
                modifier   = Modifier.neonGlow(NeonCyan, 16.dp, 0.dp)
            )
            Text(
                text  = "ADMIN PANEL",
                fontSize  = 12.sp,
                color = TextSecondary,
                letterSpacing = 4.sp
            )

            Spacer(Modifier.height(8.dp))

            // ── Tab selector ──────────────────────────────────────────────────
            NeonCard(modifier = Modifier.fillMaxWidth(), borderColor = NeonPurple) {
                TabRow(
                    selectedTabIndex = selectedTab,
                    containerColor   = BgCard,
                    contentColor     = NeonCyan,
                    indicator        = { tabPositions ->
                        TabRowDefaults.SecondaryIndicator(
                            modifier = Modifier.tabIndicatorOffset(tabPositions[selectedTab]),
                            color    = NeonCyan
                        )
                    }
                ) {
                    tabs.forEachIndexed { index, title ->
                        Tab(
                            selected = selectedTab == index,
                            onClick  = { selectedTab = index },
                            text     = {
                                Text(
                                    title,
                                    color = if (selectedTab == index) NeonCyan else TextSecondary,
                                    fontWeight = if (selectedTab == index) FontWeight.Bold else FontWeight.Normal,
                                    letterSpacing = 2.sp
                                )
                            }
                        )
                    }
                }

                // ── TELEGRAM TAB ──────────────────────────────────────────────
                if (selectedTab == 0) {
                    Column(
                        modifier = Modifier.padding(20.dp),
                        verticalArrangement = Arrangement.spacedBy(16.dp)
                    ) {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Icon(Icons.Filled.Wifi, contentDescription = null, tint = NeonCyan)
                            Spacer(Modifier.width(8.dp))
                            Text("Telegram Bot Token", color = TextPrimary, fontWeight = FontWeight.SemiBold)
                        }

                        NeonTextField(
                            value         = botToken,
                            onValueChange = { botToken = it; tgError = "" },
                            label         = "Bot Token",
                            placeholder   = "1234567890:AABBcc...",
                            modifier      = Modifier.fillMaxWidth(),
                            accentColor   = NeonCyan
                        )

                        AnimatedVisibility(tgError.isNotEmpty()) {
                            Text(tgError, color = NeonPink, fontSize = 13.sp)
                        }

                        NeonButton(
                            onClick = {
                                scope.launch {
                                    tgLoading = true
                                    tgError   = ""
                                    val svc = com.blackbugsai.app.services.TelegramBotService(botToken.trim())
                                    val ok  = try { svc.validateToken() } catch (e: Exception) { false }
                                    tgLoading = false
                                    if (ok) {
                                        vm.saveTelegramConfig(botToken.trim())
                                        onConnected()
                                    } else {
                                        tgError = "Invalid token or network error"
                                    }
                                }
                            },
                            modifier    = Modifier.fillMaxWidth().height(48.dp),
                            borderColor = NeonCyan,
                            enabled     = botToken.isNotBlank() && !tgLoading
                        ) {
                            if (tgLoading) {
                                CircularProgressIndicator(
                                    modifier = Modifier.size(20.dp),
                                    color    = NeonCyan,
                                    strokeWidth = 2.dp
                                )
                            } else {
                                Text("CONNECT", letterSpacing = 2.sp, fontWeight = FontWeight.Bold)
                            }
                        }
                    }
                }

                // ── SERVER TAB ────────────────────────────────────────────────
                if (selectedTab == 1) {
                    Column(
                        modifier = Modifier.padding(20.dp),
                        verticalArrangement = Arrangement.spacedBy(16.dp)
                    ) {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Icon(Icons.Filled.Lock, contentDescription = null, tint = NeonPurple)
                            Spacer(Modifier.width(8.dp))
                            Text("Server Connection", color = TextPrimary, fontWeight = FontWeight.SemiBold)
                        }

                        NeonTextField(
                            value         = serverUrl,
                            onValueChange = { serverUrl = it; srvError = "" },
                            label         = "Server URL",
                            placeholder   = "https://your-server.com",
                            modifier      = Modifier.fillMaxWidth(),
                            accentColor   = NeonPurple
                        )

                        NeonTextField(
                            value         = adminToken,
                            onValueChange = { adminToken = it; srvError = "" },
                            label         = "Admin Token",
                            placeholder   = "secret-admin-token",
                            modifier      = Modifier.fillMaxWidth(),
                            accentColor   = NeonPurple
                        )

                        HorizontalDivider(color = NeonPurple.copy(alpha = 0.2f))

                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Icon(Icons.Filled.Wifi, contentDescription = null,
                                tint = NeonCyan, modifier = Modifier.size(18.dp))
                            Spacer(Modifier.width(8.dp))
                            Text("Telegram Bot Token (необязательно)", color = TextSecondary,
                                fontSize = 12.sp)
                        }

                        NeonTextField(
                            value         = srvBotToken,
                            onValueChange = { srvBotToken = it; srvError = "" },
                            label         = "Bot Token",
                            placeholder   = "1234567890:AABBcc…  (оставьте пустым если не нужно)",
                            modifier      = Modifier.fillMaxWidth(),
                            accentColor   = NeonCyan
                        )

                        AnimatedVisibility(srvError.isNotEmpty()) {
                            Text(
                                srvError,
                                color    = if (srvError.startsWith("✅")) NeonCyan else NeonPink,
                                fontSize = 13.sp
                            )
                        }

                        NeonButton(
                            onClick = {
                                scope.launch {
                                    srvLoading = true
                                    srvError   = ""

                                    val url = serverUrl.trim()
                                    val tkn = adminToken.trim()

                                    if (url.isBlank() || tkn.isBlank()) {
                                        srvError   = "Заполните Server URL и Admin Token"
                                        srvLoading = false
                                        return@launch
                                    }

                                    // Warn about localhost — points to the phone, not a remote server
                                    if (url.contains("localhost", ignoreCase = true) ||
                                        url.contains("127.0.0.1")) {
                                        srvError   = "⚠️ localhost — это ваш телефон, не сервер!\nУкажите внешний IP или домен (например http://34.x.x.x:8080)"
                                        srvLoading = false
                                        return@launch
                                    }

                                    val testSvc = com.blackbugsai.app.services.ServerApiService(url, tkn)

                                    // Step 1: check reachability + auth in one request
                                    srvError = "Проверяю подключение…"
                                    val code = try { testSvc.testConnection() } catch (_: Exception) { -1 }

                                    when {
                                        code == -1 -> {
                                            srvError = "❌ Сервер недоступен: $url\n" +
                                                "• Проверьте IP/домен и порт\n" +
                                                "• GCP: добавьте правило Firewall → allow TCP"
                                        }
                                        code == 401 -> {
                                            srvError = "❌ Авторизация отказана (401)\n" +
                                                "• Неверный Admin Token\n" +
                                                "• Токен передаётся в заголовке X-Admin-Token"
                                        }
                                        code == 403 -> {
                                            srvError = "❌ Доступ запрещён (403)\n" +
                                                "• Проверьте Admin Token и права доступа"
                                        }
                                        code == 404 -> {
                                            srvError = "❌ Эндпоинт не найден (404)\n" +
                                                "• Убедитесь что запущен BlackBugsAI server\n" +
                                                "• Проверьте URL (нет лишних слешей/путей)"
                                        }
                                        code !in 200..299 -> {
                                            srvError = "❌ Ошибка сервера (HTTP $code)\n" +
                                                "• Проверьте, что сервер запущен (python3 admin_web.py)"
                                        }
                                        else -> {
                                            // code 200 — all good
                                            srvError = "✅ Подключено успешно!"
                                            vm.saveServerConfig(url, tkn, srvBotToken.trim())
                                            srvLoading = false
                                            onConnected()
                                            return@launch
                                        }
                                    }
                                    srvLoading = false
                                }
                            },
                            modifier    = Modifier.fillMaxWidth().height(48.dp),
                            borderColor = NeonPurple,
                            enabled     = serverUrl.isNotBlank() && adminToken.isNotBlank() && !srvLoading
                        ) {
                            if (srvLoading) {
                                CircularProgressIndicator(
                                    modifier = Modifier.size(20.dp),
                                    color    = NeonPurple,
                                    strokeWidth = 2.dp
                                )
                            } else {
                                Text("CONNECT", letterSpacing = 2.sp, fontWeight = FontWeight.Bold)
                            }
                        }
                    }
                }
            }

            Text(
                "Standalone mode — no server required for Telegram bot",
                color     = TextSecondary,
                fontSize  = 11.sp,
                textAlign = TextAlign.Center
            )
        }
    }
}
