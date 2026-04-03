package com.blackbugsai.app.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.blackbugsai.app.AppViewModel
import com.blackbugsai.app.knownChatIds
import com.blackbugsai.app.services.TelegramBotService
import com.blackbugsai.app.ui.theme.*
import kotlinx.coroutines.delay

@Composable
fun DashboardScreen(vm: AppViewModel) {
    val appMode   by vm.appMode.collectAsState()
    val botService by vm.botService.collectAsState()

    var totalMessages by remember { mutableIntStateOf(0) }
    var activeUsers   by remember { mutableIntStateOf(0) }
    var botInfo       by remember { mutableStateOf<TelegramBotService.BotInfo?>(null) }
    var lastRefresh   by remember { mutableStateOf("--") }
    var isLoading     by remember { mutableStateOf(false) }

    // Auto-refresh every 30 s
    LaunchedEffect(botService) {
        while (true) {
            if (botService != null) {
                isLoading = true
                val updates = try { botService!!.getUpdates() } catch (e: Exception) { emptyList() }
                updates.forEach { u ->
                    u.message?.from?.let { knownChatIds.add(it.id) }
                }
                totalMessages = updates.size + totalMessages.coerceAtLeast(updates.size)
                activeUsers   = knownChatIds.size
                if (botInfo == null) {
                    botInfo = try { botService!!.getBotInfo() } catch (e: Exception) { null }
                }
                lastRefresh = java.text.SimpleDateFormat("HH:mm:ss", java.util.Locale.getDefault())
                    .format(java.util.Date())
                isLoading = false
            }
            delay(30_000)
        }
    }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(BgDeep)
            .verticalScroll(rememberScrollState())
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        // ── Header ────────────────────────────────────────────────────────────
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Text(
                "DASHBOARD",
                fontSize   = 22.sp,
                fontWeight = FontWeight.Bold,
                color      = NeonCyan,
                letterSpacing = 3.sp
            )
            if (isLoading) {
                CircularProgressIndicator(
                    modifier = Modifier.size(20.dp),
                    color    = NeonCyan,
                    strokeWidth = 2.dp
                )
            } else {
                Text("Updated: $lastRefresh", color = TextSecondary, fontSize = 11.sp)
            }
        }

        // ── Mode badge ────────────────────────────────────────────────────────
        NeonCard(
            modifier = Modifier.fillMaxWidth(),
            borderColor = if (appMode == "telegram") NeonCyan else NeonPurple
        ) {
            Row(
                modifier = Modifier.padding(16.dp),
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(12.dp)
            ) {
                Icon(
                    imageVector = if (appMode == "telegram") Icons.Filled.SmartToy else Icons.Filled.Cloud,
                    contentDescription = null,
                    tint = if (appMode == "telegram") NeonCyan else NeonPurple
                )
                Column {
                    Text(
                        if (appMode == "telegram") "Telegram Bot Mode" else "Server Mode",
                        color      = TextPrimary,
                        fontWeight = FontWeight.SemiBold
                    )
                    botInfo?.let {
                        Text("@${it.username}  •  ${it.firstName}", color = TextSecondary, fontSize = 12.sp)
                    } ?: Text(
                        if (appMode == "server") vm.serverUrl.collectAsState().value else "Loading bot info…",
                        color = TextSecondary, fontSize = 12.sp
                    )
                }
            }
        }

        // ── Stats cards ───────────────────────────────────────────────────────
        if (appMode == "telegram") {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(12.dp)
            ) {
                StatCard(
                    modifier    = Modifier.weight(1f),
                    label       = "MESSAGES",
                    value       = totalMessages.toString(),
                    icon        = Icons.Filled.Message,
                    borderColor = NeonCyan
                )
                StatCard(
                    modifier    = Modifier.weight(1f),
                    label       = "ACTIVE USERS",
                    value       = activeUsers.toString(),
                    icon        = Icons.Filled.People,
                    borderColor = NeonGreen
                )
            }
        }

        // ── System status ─────────────────────────────────────────────────────
        NeonCard(modifier = Modifier.fillMaxWidth(), borderColor = NeonPurple) {
            Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
                Text("SYSTEM STATUS", color = NeonPurple, fontWeight = FontWeight.Bold, letterSpacing = 2.sp, fontSize = 13.sp)
                Divider(color = NeonPurple.copy(alpha = 0.3f))
                StatusRow("App Mode",    appMode.uppercase(),          NeonCyan)
                StatusRow("Bot Status",  if (botService != null) "ONLINE" else "OFFLINE",
                    if (botService != null) NeonGreen else NeonPink)
                StatusRow("Known Chats", "${knownChatIds.size} chat IDs stored", NeonYellow)
                StatusRow("Version",     "1.1.0",                       TextSecondary)
            }
        }

        // ── Quick actions ─────────────────────────────────────────────────────
        NeonCard(modifier = Modifier.fillMaxWidth(), borderColor = NeonYellow) {
            Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Text("INFO", color = NeonYellow, fontWeight = FontWeight.Bold, letterSpacing = 2.sp, fontSize = 13.sp)
                Divider(color = NeonYellow.copy(alpha = 0.3f))
                Text(
                    "BlackBugsAI operates entirely on-device.\n" +
                    "All data is stored locally via DataStore.\n" +
                    "Use the BOT tab to view messages and broadcast.",
                    color    = TextSecondary,
                    fontSize = 13.sp,
                    lineHeight = 20.sp
                )
            }
        }
    }
}

@Composable
private fun StatCard(
    modifier: Modifier,
    label: String,
    value: String,
    icon: ImageVector,
    borderColor: androidx.compose.ui.graphics.Color
) {
    NeonCard(modifier = modifier, borderColor = borderColor) {
        Column(
            modifier = Modifier.padding(16.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            Icon(icon, contentDescription = null, tint = borderColor, modifier = Modifier.size(28.dp))
            Text(value, fontSize = 28.sp, fontWeight = FontWeight.Bold, color = borderColor)
            Text(label, fontSize = 11.sp, color = TextSecondary, letterSpacing = 1.sp)
        }
    }
}

@Composable
private fun StatusRow(key: String, value: String, valueColor: androidx.compose.ui.graphics.Color) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.SpaceBetween
    ) {
        Text(key,   color = TextSecondary, fontSize = 13.sp)
        Text(value, color = valueColor,    fontSize = 13.sp, fontWeight = FontWeight.SemiBold)
    }
}
