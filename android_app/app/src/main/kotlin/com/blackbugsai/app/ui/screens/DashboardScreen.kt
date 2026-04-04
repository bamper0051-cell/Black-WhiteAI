package com.blackbugsai.app.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.Message
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.blackbugsai.app.AppViewModel
import com.blackbugsai.app.knownChatIds
import com.blackbugsai.app.services.ServerApiService
import com.blackbugsai.app.services.TelegramBotService
import com.blackbugsai.app.ui.theme.*

@Composable
fun DashboardScreen(vm: AppViewModel) {
    val appMode      by vm.appMode.collectAsState()
    val botService   by vm.botService.collectAsState()
    val updates      by vm.updates.collectAsState()
    val polling      by vm.polling.collectAsState()
    val serverStatus by vm.serverStatus.collectAsState()
    val sysInfo      by vm.sysInfo.collectAsState()

    val totalMessages = updates.count { it.message != null }
    val activeUsers   = knownChatIds.size

    var botInfo     by remember { mutableStateOf<TelegramBotService.BotInfo?>(null) }
    var lastRefresh by remember { mutableStateOf("--") }

    LaunchedEffect(botService) {
        if (botService != null && botInfo == null) {
            botInfo = try { botService!!.getBotInfo() } catch (_: Exception) { null }
        }
    }

    LaunchedEffect(updates) {
        if (updates.isNotEmpty()) {
            lastRefresh = java.text.SimpleDateFormat("HH:mm:ss", java.util.Locale.getDefault())
                .format(java.util.Date())
        }
    }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(BgDeep)
            .verticalScroll(rememberScrollState())
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(14.dp)
    ) {
        // ── Header ────────────────────────────────────────────────────────────
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Column {
                Text(
                    "DASHBOARD",
                    fontSize   = 22.sp,
                    fontWeight = FontWeight.Bold,
                    color      = NeonCyan,
                    letterSpacing = 3.sp
                )
                Text("BlackBugsAI v2.0.0", color = TextSecondary, fontSize = 11.sp,
                    fontFamily = FontFamily.Monospace)
            }
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                if (polling) {
                    CircularProgressIndicator(
                        modifier = Modifier.size(16.dp),
                        color    = NeonCyan,
                        strokeWidth = 2.dp
                    )
                }
                IconButton(
                    onClick = { vm.refreshServerData() },
                    modifier = Modifier.size(32.dp)
                ) {
                    Icon(Icons.Filled.Refresh, contentDescription = "Refresh",
                        tint = NeonCyan, modifier = Modifier.size(18.dp))
                }
            }
        }

        // ── Mode card ─────────────────────────────────────────────────────────
        NeonCard(
            modifier    = Modifier.fillMaxWidth(),
            borderColor = if (appMode == "telegram") NeonCyan else NeonPurple
        ) {
            Row(
                modifier = Modifier.padding(16.dp),
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(12.dp)
            ) {
                Box(
                    modifier = Modifier
                        .size(10.dp)
                        .background(
                            color = if (botService != null || appMode == "server") NeonGreen else NeonPink,
                            shape = androidx.compose.foundation.shape.CircleShape
                        )
                )
                Column(modifier = Modifier.weight(1f)) {
                    Text(
                        when {
                            appMode == "telegram"                     -> "Telegram Bot Mode"
                            appMode == "server" && botService != null -> "Server + Bot Mode"
                            else                                      -> "Server Mode"
                        },
                        color      = TextPrimary,
                        fontWeight = FontWeight.SemiBold,
                        fontSize   = 14.sp
                    )
                    botInfo?.let {
                        Text("@${it.username}  •  ${it.firstName}", color = TextSecondary, fontSize = 12.sp)
                    } ?: run {
                        val serverUrl by vm.serverUrl.collectAsState()
                        Text(
                            if (appMode == "server") serverUrl else "Загрузка…",
                            color = TextSecondary, fontSize = 11.sp,
                            fontFamily = FontFamily.Monospace
                        )
                    }
                }
                Icon(
                    imageVector = if (appMode == "telegram") Icons.Filled.SmartToy else Icons.Filled.Cloud,
                    contentDescription = null,
                    tint = if (appMode == "telegram") NeonCyan else NeonPurple,
                    modifier = Modifier.size(20.dp)
                )
            }
        }

        // ── Stats row ─────────────────────────────────────────────────────────
        if (appMode == "server" && serverStatus != null) {
            // Server-mode stats from real API
            val s = serverStatus!!
            Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                MiniStatCard(Modifier.weight(1f), "ЗАДАЧИ",  s.taskCount.toString(),   Icons.Filled.Task,    NeonCyan)
                MiniStatCard(Modifier.weight(1f), "ПОЛЬЗ.",  s.userCount.toString(),   Icons.Filled.People,  NeonGreen)
                MiniStatCard(Modifier.weight(1f), "АПТАЙМ",
                    "${s.uptime / 3600}h",   Icons.Filled.AccessTime, NeonPurple)
            }
        } else if (appMode == "telegram") {
            Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                MiniStatCard(Modifier.weight(1f), "MSGS",  totalMessages.toString(), Icons.AutoMirrored.Filled.Message, NeonCyan)
                MiniStatCard(Modifier.weight(1f), "USERS", activeUsers.toString(),  Icons.Filled.People, NeonGreen)
            }
        }

        // ── Server sysinfo ────────────────────────────────────────────────────
        if (appMode == "server") {
            NeonCard(modifier = Modifier.fillMaxWidth(), borderColor = NeonPurple) {
                Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Text("СЕРВЕР", color = NeonPurple, fontWeight = FontWeight.Bold,
                            letterSpacing = 2.sp, fontSize = 12.sp,
                            fontFamily = FontFamily.Monospace)
                        if (serverStatus == null) {
                            Text("нет данных", color = TextSecondary, fontSize = 11.sp)
                        } else {
                            Text("v${serverStatus!!.version}", color = NeonPurple, fontSize = 11.sp,
                                fontFamily = FontFamily.Monospace)
                        }
                    }
                    HorizontalDivider(color = NeonPurple.copy(alpha = 0.3f))
                    if (sysInfo != null) {
                        val si = sysInfo!!
                        DRow("Хост",     si.hostname)
                        DRow("IP",       si.ip)
                        DRow("ОС",       si.os)
                        DRow("CPU",      "${si.cpu}%")
                        DRow("RAM",      "${si.ram}%")
                        DRow("Диск",     "${si.disk}%")
                    } else {
                        Text(
                            if (serverStatus != null) "Загрузка системной информации…"
                            else "Нет соединения с сервером",
                            color = TextSecondary, fontSize = 12.sp
                        )
                    }
                }
            }
        }

        // ── Agents summary ────────────────────────────────────────────────────
        NeonCard(modifier = Modifier.fillMaxWidth(), borderColor = NeonGreen) {
            Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Text("АГЕНТЫ", color = NeonGreen, fontWeight = FontWeight.Bold,
                    letterSpacing = 2.sp, fontSize = 12.sp, fontFamily = FontFamily.Monospace)
                HorizontalDivider(color = NeonGreen.copy(alpha = 0.3f))
                val onlineCount  = projectAgents.count { it.status == AgentStatus.ONLINE || it.status == AgentStatus.RUNNING }
                val runningCount = projectAgents.count { it.status == AgentStatus.RUNNING }
                DRow("Всего",      "${projectAgents.size}", TextSecondary)
                DRow("Активных",   "$onlineCount",          NeonGreen)
                DRow("Запущено",   "$runningCount",         NeonCyan)
                DRow("Оффлайн",    "${projectAgents.count { it.status == AgentStatus.OFFLINE }}", TextSecondary)
                if (runningCount > 0) {
                    HorizontalDivider(color = NeonGreen.copy(alpha = 0.2f))
                    projectAgents.filter { it.status == AgentStatus.RUNNING }.forEach { agent ->
                        Row(
                            verticalAlignment = Alignment.CenterVertically,
                            modifier = Modifier.fillMaxWidth()
                        ) {
                            Box(
                                Modifier
                                    .size(6.dp)
                                    .background(NeonCyan, androidx.compose.foundation.shape.CircleShape)
                            )
                            Spacer(Modifier.width(8.dp))
                            Text(agent.name, color = TextPrimary, fontSize = 11.sp,
                                fontFamily = FontFamily.Monospace, modifier = Modifier.weight(1f))
                            Text("RUN", color = NeonCyan, fontSize = 9.sp,
                                fontFamily = FontFamily.Monospace, fontWeight = FontWeight.Bold)
                        }
                    }
                }
            }
        }

        // ── Bot status ────────────────────────────────────────────────────────
        NeonCard(modifier = Modifier.fillMaxWidth(), borderColor = NeonCyan) {
            Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Text("BOT STATUS", color = NeonCyan, fontWeight = FontWeight.Bold,
                    letterSpacing = 2.sp, fontSize = 12.sp, fontFamily = FontFamily.Monospace)
                HorizontalDivider(color = NeonCyan.copy(alpha = 0.3f))
                DRow("Бот", if (botService != null) "ONLINE" else "OFFLINE",
                    if (botService != null) NeonGreen else NeonPink)
                DRow("Режим", appMode.uppercase())
                DRow("Чатов", "${knownChatIds.size}")
                DRow("Обновлено", lastRefresh)
            }
        }

        Spacer(Modifier.height(8.dp))
    }
}

// ── Helpers ───────────────────────────────────────────────────────────────────

@Composable
private fun MiniStatCard(
    modifier: Modifier,
    label: String,
    value: String,
    icon: ImageVector,
    color: androidx.compose.ui.graphics.Color
) {
    NeonCard(modifier = modifier, borderColor = color) {
        Column(
            modifier = Modifier.padding(12.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.spacedBy(6.dp)
        ) {
            Icon(icon, contentDescription = null, tint = color, modifier = Modifier.size(22.dp))
            Text(value, fontSize = 22.sp, fontWeight = FontWeight.Bold, color = color,
                fontFamily = FontFamily.Monospace)
            Text(label, fontSize = 9.sp, color = TextSecondary, letterSpacing = 1.sp,
                fontFamily = FontFamily.Monospace)
        }
    }
}

@Composable
private fun DRow(
    key: String, value: String,
    valueColor: androidx.compose.ui.graphics.Color = TextPrimary
) {
    Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
        Text(key,   color = TextSecondary, fontSize = 12.sp, fontFamily = FontFamily.Monospace)
        Text(value, color = valueColor,    fontSize = 12.sp, fontFamily = FontFamily.Monospace,
            fontWeight = FontWeight.SemiBold)
    }
}
