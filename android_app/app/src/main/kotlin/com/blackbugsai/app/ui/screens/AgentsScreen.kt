package com.blackbugsai.app.ui.screens

import androidx.compose.animation.core.*
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.blackbugsai.app.AppViewModel
import com.blackbugsai.app.ui.theme.*
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch

// ── Data models ───────────────────────────────────────────────────────────────
enum class AgentStatus { ONLINE, OFFLINE, RUNNING, ERROR }

data class Agent(
    val id: String,
    val name: String,
    val description: String,
    val type: String,
    val status: AgentStatus,
    val tasksHandled: Int = 0,
    val lastActive: String = "—"
)

val projectAgents = listOf(
    Agent("neo",      "Agent NEO",     "Главный AI-агент, управляет всеми задачами",       "CORE",    AgentStatus.ONLINE,  142, "только что"),
    Agent("coder3",   "Agent CODER3",  "Автоматическое написание и исправление кода",       "CODER",   AgentStatus.ONLINE,  89,  "1 мин назад"),
    Agent("planner",  "Agent PLANNER", "Планирование и разбивка задач на шаги",            "PLANNER", AgentStatus.RUNNING, 57,  "30 сек назад"),
    Agent("matrix",   "Agent MATRIX",  "Оркестрация нескольких агентов параллельно",        "ORCHESTR",AgentStatus.ONLINE,  34,  "2 мин назад"),
    Agent("executor", "Agent EXEC",    "Выполнение команд и инструментов",                  "EXEC",    AgentStatus.RUNNING, 201, "5 сек назад"),
    Agent("memory",   "Agent MEMORY",  "Долгосрочная и краткосрочная память агентов",       "MEMORY",  AgentStatus.ONLINE,  0,   "3 мин назад"),
    Agent("roles",    "Agent ROLES",   "Управление ролями пользователей и правами доступа", "ROLES",   AgentStatus.OFFLINE, 0,   "10 мин назад"),
    Agent("session",  "Agent SESSION", "Управление сессиями и контекстом разговора",        "SESSION", AgentStatus.ONLINE,  76,  "15 сек назад"),
    Agent("tools",    "Tool Registry", "Реестр инструментов и плагинов для агентов",        "TOOLS",   AgentStatus.ONLINE,  0,   "5 мин назад"),
    Agent("autofix",  "AutoFix",       "Автоматическое исправление ошибок в коде",          "CODER",   AgentStatus.OFFLINE, 12,  "1 ч назад"),
    Agent("bot",      "Telegram Bot",  "Обработка входящих сообщений от пользователей",     "BOT",     AgentStatus.RUNNING, 310, "только что"),
    Agent("llm",      "LLM Router",    "Маршрутизация запросов к AI-моделям",               "LLM",     AgentStatus.ONLINE,  98,  "2 мин назад"),
)

// ── Screen ────────────────────────────────────────────────────────────────────
@Composable
fun AgentsScreen(vm: AppViewModel) {
    val scope = rememberCoroutineScope()
    var agents       by remember { mutableStateOf(projectAgents) }
    var logDialog    by remember { mutableStateOf<Agent?>(null) }
    var filter       by remember { mutableStateOf("ALL") }

    val filters  = listOf("ALL", "ONLINE", "RUNNING", "OFFLINE")
    val filtered = if (filter == "ALL") agents else agents.filter { it.status.name == filter }

    val onlineCount  = agents.count { it.status == AgentStatus.ONLINE  || it.status == AgentStatus.RUNNING }
    val runningCount = agents.count { it.status == AgentStatus.RUNNING }
    val offlineCount = agents.count { it.status == AgentStatus.OFFLINE }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(BgDeep)
    ) {
        // ── Top bar ───────────────────────────────────────────────────────────
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .background(BgDark)
                .padding(horizontal = 16.dp, vertical = 10.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Text("> АГЕНТЫ", color = NeonCyan, fontSize = 15.sp,
                fontWeight = FontWeight.Bold, fontFamily = FontFamily.Monospace,
                modifier = Modifier.weight(1f))
            StatChip("$onlineCount", NeonGreen)
            Spacer(Modifier.width(4.dp))
            StatChip("$runningCount run", NeonCyan)
            Spacer(Modifier.width(4.dp))
            StatChip("$offlineCount off", TextSecondary)
        }

        // ── Filter chips ──────────────────────────────────────────────────────
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .background(BgDark)
                .padding(horizontal = 12.dp, vertical = 4.dp),
            horizontalArrangement = Arrangement.spacedBy(6.dp)
        ) {
            filters.forEach { f ->
                FilterChip(
                    selected = filter == f,
                    onClick  = { filter = f },
                    label    = { Text(f, fontSize = 10.sp, fontFamily = FontFamily.Monospace) },
                    colors   = FilterChipDefaults.filterChipColors(
                        selectedContainerColor = NeonCyan.copy(alpha = 0.2f),
                        selectedLabelColor     = NeonCyan,
                        labelColor             = TextSecondary
                    )
                )
            }
        }

        // ── Agent list ────────────────────────────────────────────────────────
        LazyColumn(
            modifier = Modifier.fillMaxSize(),
            contentPadding = PaddingValues(12.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            items(filtered, key = { it.id }) { agent ->
                AgentCard(
                    agent   = agent,
                    vm      = vm,
                    onStart = {
                        agents = agents.map {
                            if (it.id == agent.id) it.copy(status = AgentStatus.RUNNING) else it
                        }
                        scope.launch {
                            delay(2000)
                            agents = agents.map {
                                if (it.id == agent.id) it.copy(status = AgentStatus.ONLINE, lastActive = "только что") else it
                            }
                        }
                    },
                    onStop = {
                        agents = agents.map {
                            if (it.id == agent.id) it.copy(status = AgentStatus.OFFLINE) else it
                        }
                    },
                    onRestart = {
                        agents = agents.map {
                            if (it.id == agent.id) it.copy(status = AgentStatus.RUNNING) else it
                        }
                        scope.launch {
                            delay(1500)
                            agents = agents.map {
                                if (it.id == agent.id) it.copy(status = AgentStatus.ONLINE, lastActive = "только что") else it
                            }
                        }
                    },
                    onLogs = { logDialog = agent }
                )
            }
            item { Spacer(Modifier.height(8.dp)) }
        }
    }

    logDialog?.let { AgentLogDialog(agent = it, onDismiss = { logDialog = null }) }
}

// ── Agent card ────────────────────────────────────────────────────────────────
@Composable
private fun AgentCard(
    agent: Agent,
    vm: AppViewModel,
    onStart: () -> Unit,
    onStop: () -> Unit,
    onRestart: () -> Unit,
    onLogs: () -> Unit
) {
    var expanded  by remember { mutableStateOf(false) }
    var taskInput by remember { mutableStateOf("") }

    val statusColor = when (agent.status) {
        AgentStatus.ONLINE  -> NeonGreen
        AgentStatus.RUNNING -> NeonCyan
        AgentStatus.ERROR   -> NeonPink
        AgentStatus.OFFLINE -> TextSecondary
    }

    // Pulse dot for RUNNING
    val inf = rememberInfiniteTransition(label = "p_${agent.id}")
    val dotAlpha by inf.animateFloat(
        initialValue = 1f, targetValue = 0.3f,
        animationSpec = infiniteRepeatable(
            animation = tween(800, easing = FastOutSlowInEasing),
            repeatMode = RepeatMode.Reverse
        ), label = "a_${agent.id}"
    )

    Box(
        modifier = Modifier
            .fillMaxWidth()
            .background(BgCard, RoundedCornerShape(12.dp))
            .border(1.dp, statusColor.copy(alpha = 0.35f), RoundedCornerShape(12.dp))
            .clickable { expanded = !expanded }
    ) {
        Column(modifier = Modifier.padding(12.dp)) {
            // ── Header row ────────────────────────────────────────────────────
            Row(verticalAlignment = Alignment.CenterVertically) {
                Box(
                    modifier = Modifier
                        .size(8.dp)
                        .clip(CircleShape)
                        .background(
                            statusColor.copy(alpha = if (agent.status == AgentStatus.RUNNING) dotAlpha else 1f)
                        )
                )
                Spacer(Modifier.width(10.dp))
                Column(modifier = Modifier.weight(1f)) {
                    Text(agent.name, color = TextPrimary, fontSize = 13.sp,
                        fontWeight = FontWeight.Bold, fontFamily = FontFamily.Monospace)
                    Text(agent.type, color = statusColor.copy(alpha = 0.8f), fontSize = 9.sp,
                        fontFamily = FontFamily.Monospace, letterSpacing = 1.5.sp)
                }
                Text("${agent.tasksHandled} tasks", color = TextSecondary, fontSize = 10.sp,
                    fontFamily = FontFamily.Monospace)
                Spacer(Modifier.width(8.dp))
                Box(
                    modifier = Modifier
                        .background(statusColor.copy(alpha = 0.15f), RoundedCornerShape(4.dp))
                        .padding(horizontal = 6.dp, vertical = 2.dp)
                ) {
                    Text(agent.status.name, color = statusColor, fontSize = 9.sp,
                        fontWeight = FontWeight.Bold, fontFamily = FontFamily.Monospace)
                }
                Spacer(Modifier.width(4.dp))
                Icon(
                    if (expanded) Icons.Filled.ExpandLess else Icons.Filled.ExpandMore,
                    contentDescription = null, tint = TextSecondary, modifier = Modifier.size(18.dp)
                )
            }

            // ── Expanded content ──────────────────────────────────────────────
            if (expanded) {
                Spacer(Modifier.height(10.dp))
                Text(agent.description, color = TextSecondary, fontSize = 11.sp,
                    fontFamily = FontFamily.Monospace)
                Text("Последняя активность: ${agent.lastActive}",
                    color = TextSecondary.copy(alpha = 0.6f), fontSize = 10.sp,
                    fontFamily = FontFamily.Monospace)
                Spacer(Modifier.height(10.dp))

                // Task input
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    OutlinedTextField(
                        value         = taskInput,
                        onValueChange = { taskInput = it },
                        placeholder   = { Text("Задача для ${agent.name}…",
                            color = TextSecondary, fontSize = 11.sp) },
                        modifier      = Modifier.weight(1f),
                        singleLine    = true,
                        textStyle     = LocalTextStyle.current.copy(
                            color = TextPrimary, fontSize = 12.sp,
                            fontFamily = FontFamily.Monospace
                        ),
                        colors = OutlinedTextFieldDefaults.colors(
                            focusedBorderColor   = statusColor,
                            unfocusedBorderColor = statusColor.copy(alpha = 0.4f),
                            cursorColor          = statusColor
                        ),
                        shape = RoundedCornerShape(8.dp)
                    )
                    IconButton(
                        onClick = {
                            val task = taskInput.trim()
                            if (task.isNotBlank()) {
                                vm.sendAgentTask(agent.id, task)
                                taskInput = ""
                            }
                        },
                        modifier = Modifier
                            .size(40.dp)
                            .background(statusColor.copy(alpha = 0.2f), RoundedCornerShape(8.dp))
                            .border(1.dp, statusColor.copy(alpha = 0.5f), RoundedCornerShape(8.dp))
                    ) {
                        Icon(Icons.Filled.PlayArrow, contentDescription = "Send",
                            tint = statusColor, modifier = Modifier.size(18.dp))
                    }
                }

                Spacer(Modifier.height(10.dp))

                // Control buttons
                Row(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                    if (agent.status == AgentStatus.OFFLINE || agent.status == AgentStatus.ERROR) {
                        ABtn("СТАРТ",   NeonGreen,  Icons.Filled.PlayArrow,  onStart)
                    }
                    if (agent.status == AgentStatus.ONLINE || agent.status == AgentStatus.RUNNING) {
                        ABtn("СТОП",    NeonPink,   Icons.Filled.Stop,       onStop)
                    }
                    if (agent.status != AgentStatus.OFFLINE) {
                        ABtn("RESTART", NeonYellow, Icons.Filled.RestartAlt, onRestart)
                    }
                    ABtn("ЛОГИ",    NeonPurple, Icons.Filled.Article,    onLogs)
                }
            }
        }
    }
}

@Composable
private fun ABtn(
    label: String, color: Color,
    icon: androidx.compose.ui.graphics.vector.ImageVector,
    onClick: () -> Unit
) {
    OutlinedButton(
        onClick        = onClick,
        contentPadding = PaddingValues(horizontal = 8.dp, vertical = 4.dp),
        modifier       = Modifier.height(30.dp),
        colors         = ButtonDefaults.outlinedButtonColors(contentColor = color),
        border         = androidx.compose.foundation.BorderStroke(1.dp, color.copy(alpha = 0.6f)),
        shape          = RoundedCornerShape(6.dp)
    ) {
        Icon(icon, contentDescription = null, modifier = Modifier.size(12.dp))
        Spacer(Modifier.width(3.dp))
        Text(label, fontSize = 9.sp, fontFamily = FontFamily.Monospace, fontWeight = FontWeight.Bold)
    }
}

@Composable
private fun StatChip(label: String, color: Color) {
    Box(
        modifier = Modifier
            .background(color.copy(alpha = 0.15f), RoundedCornerShape(6.dp))
            .border(1.dp, color.copy(alpha = 0.4f), RoundedCornerShape(6.dp))
            .padding(horizontal = 7.dp, vertical = 2.dp)
    ) {
        Text(label, color = color, fontSize = 9.sp,
            fontFamily = FontFamily.Monospace, fontWeight = FontWeight.Bold)
    }
}

// ── Log dialog ────────────────────────────────────────────────────────────────
@Composable
private fun AgentLogDialog(agent: Agent, onDismiss: () -> Unit) {
    val fakeLogs = remember(agent.id) {
        buildString {
            appendLine("[${agent.name}] Инициализация агента...")
            appendLine("[${agent.name}] Подключение к LLM Router...")
            appendLine("[${agent.name}] Загрузка контекста памяти...")
            appendLine("[${agent.name}] Статус: ${agent.status.name}")
            appendLine("[${agent.name}] Обработано задач: ${agent.tasksHandled}")
            appendLine("[${agent.name}] Последняя активность: ${agent.lastActive}")
            if (agent.status == AgentStatus.RUNNING) {
                appendLine("[${agent.name}] >> Выполняется задача...")
                appendLine("[${agent.name}] >> Ожидание ответа от LLM...")
            }
            appendLine("[${agent.name}] Тип модуля: ${agent.type}")
            appendLine("[${agent.name}] Лог инициализирован.")
        }
    }

    AlertDialog(
        onDismissRequest = onDismiss,
        containerColor   = BgDark,
        shape            = RoundedCornerShape(12.dp),
        title = {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Icon(Icons.Filled.Article, contentDescription = null,
                    tint = NeonPurple, modifier = Modifier.size(18.dp))
                Spacer(Modifier.width(8.dp))
                Text("ЛОГИ: ${agent.name}", color = NeonPurple,
                    fontFamily = FontFamily.Monospace, fontSize = 13.sp, fontWeight = FontWeight.Bold)
            }
        },
        text = {
            Box(
                modifier = Modifier
                    .fillMaxWidth()
                    .background(BgDeep, RoundedCornerShape(8.dp))
                    .border(1.dp, NeonPurple.copy(alpha = 0.3f), RoundedCornerShape(8.dp))
                    .padding(12.dp)
            ) {
                Text(fakeLogs, color = NeonGreen, fontSize = 10.sp,
                    fontFamily = FontFamily.Monospace, lineHeight = 16.sp)
            }
        },
        confirmButton = {
            TextButton(onClick = onDismiss) {
                Text("ЗАКРЫТЬ", color = NeonPurple, fontFamily = FontFamily.Monospace)
            }
        }
    )
}
