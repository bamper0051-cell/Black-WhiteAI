package com.blackbugsai.app.ui.screens

import androidx.compose.animation.*
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.foundation.text.KeyboardOptions
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
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.blackbugsai.app.AppViewModel
import com.blackbugsai.app.ui.theme.*
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import java.text.SimpleDateFormat
import java.util.*

// ── Message model ─────────────────────────────────────────────────────────────
enum class ChatSender { USER, AGENT, SYSTEM }

data class ChatMessage(
    val id: Long = System.currentTimeMillis(),
    val sender: ChatSender,
    val agentName: String = "SYSTEM",
    val text: String,
    val time: String = SimpleDateFormat("HH:mm", Locale.getDefault()).format(Date())
)

// ── Agent personas ────────────────────────────────────────────────────────────
data class AgentPersona(
    val id: String,
    val name: String,
    val color: Color,
    val replies: Map<String, String>   // keyword → reply
)

val agentPersonas = listOf(
    AgentPersona("neo", "NEO", NeonCyan, mapOf(
        "привет"   to "Приветствую. Я Agent NEO — главный оркестратор. Чем могу помочь?",
        "статус"   to "Все системы работают штатно. 3 агента активны. Очередь задач: 0.",
        "задача"   to "Принято. Создаю задачу, передаю планировщику...",
        "помощь"   to "Команды: /status /task <описание> /agents /memory /clear",
        "агенты"   to "Активные: CODER3, PLANNER, EXEC, SESSION, LLM Router. Offline: ROLES, AutoFix.",
        "default"  to "Обрабатываю запрос... Передаю в очередь задач."
    )),
    AgentPersona("coder3", "CODER3", NeonGreen, mapOf(
        "привет"   to "Coder3 онлайн. Готов к написанию и исправлению кода.",
        "код"      to "Напишите задачу — сгенерирую код на Python/Kotlin/JS.",
        "ошибка"   to "Запускаю autofix... анализирую трейсбэк...",
        "помощь"   to "Я пишу код, исправляю баги, делаю рефакторинг.",
        "default"  to "Анализирую задачу... Генерирую решение."
    )),
    AgentPersona("planner", "PLANNER", NeonPurple, mapOf(
        "привет"   to "Planner активен. Разбиваю сложные задачи на шаги.",
        "план"     to "Опишите цель — создам пошаговый план выполнения.",
        "задача"   to "Декомпозирую: 1) Анализ → 2) Реализация → 3) Тест → 4) Деплой",
        "помощь"   to "Я планирую и координирую многошаговые задачи.",
        "default"  to "Составляю план действий..."
    )),
    AgentPersona("llm", "LLM Router", NeonYellow, mapOf(
        "привет"   to "LLM Router online. Маршрутизирую запросы к моделям AI.",
        "модель"   to "Доступные модели: Claude Sonnet, Claude Haiku, GPT-4o, Gemini Pro.",
        "помощь"   to "Выбери модель в Настройках и я направлю запрос к ней.",
        "default"  to "Маршрутизирую запрос к активной LLM модели..."
    )),
)

@Composable
fun ChatScreen(vm: AppViewModel) {
    val scope = rememberCoroutineScope()
    val listState = rememberLazyListState()

    var selectedPersona by remember { mutableStateOf(agentPersonas[0]) }
    var messages by remember {
        mutableStateOf(listOf(
            ChatMessage(sender = ChatSender.SYSTEM, text = "Выберите агента и начните диалог"),
            ChatMessage(sender = ChatSender.AGENT, agentName = selectedPersona.name,
                text = "Привет! Я ${selectedPersona.name}. Чем могу помочь?")
        ))
    }
    var inputText by remember { mutableStateOf("") }
    var isTyping  by remember { mutableStateOf(false) }
    var showPersonaMenu by remember { mutableStateOf(false) }

    fun sendMessage() {
        val text = inputText.trim()
        if (text.isEmpty()) return
        inputText = ""

        val userMsg = ChatMessage(sender = ChatSender.USER, text = text)
        messages = messages + userMsg

        scope.launch {
            isTyping = true
            delay(600 + (200..800).random().toLong())

            val lowerText = text.lowercase()
            val reply = selectedPersona.replies.entries
                .firstOrNull { lowerText.contains(it.key) }?.value
                ?: selectedPersona.replies["default"]
                ?: "Обрабатываю..."

            // Handle /commands
            val finalReply = when {
                text.startsWith("/status")  -> "✅ Все агенты: ${projectAgents.count { it.status == AgentStatus.ONLINE || it.status == AgentStatus.RUNNING }} online."
                text.startsWith("/agents")  -> projectAgents.joinToString("\n") { "• ${it.name}: ${it.status.name}" }
                text.startsWith("/clear")   -> { messages = listOf(ChatMessage(sender = ChatSender.SYSTEM, text = "Чат очищен")); isTyping = false; return@launch }
                text.startsWith("/task ")   -> "📋 Задача принята: \"${text.removePrefix("/task ")}\"\nПередаю PLANNER → EXEC..."
                text.startsWith("/memory")  -> "🧠 Память: ${knownChatIdsChatMemory.size} записей. Последние: ${knownChatIdsChatMemory.takeLast(3).joinToString(", ")}"
                text.startsWith("/help")    -> "/status /agents /task <текст> /memory /clear /models"
                text.startsWith("/models")  -> "Активная модель: ${selectedLlmModel.value}\nДоступно: Claude Sonnet, Claude Haiku, GPT-4o, Gemini Pro"
                else -> reply
            }
            knownChatIdsChatMemory.add(text)

            val agentMsg = ChatMessage(sender = ChatSender.AGENT, agentName = selectedPersona.name, text = finalReply)
            messages = messages + agentMsg
            isTyping = false

            listState.animateScrollToItem(messages.size - 1)
        }

        scope.launch { delay(100); listState.animateScrollToItem(messages.size - 1) }
    }

    Column(modifier = Modifier.fillMaxSize().background(BgDeep)) {

        // ── Top bar ───────────────────────────────────────────────────────────
        Row(
            modifier = Modifier.fillMaxWidth().background(BgDark).padding(horizontal = 16.dp, vertical = 10.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            // Agent avatar
            Box(
                modifier = Modifier.size(36.dp).clip(CircleShape)
                    .background(selectedPersona.color.copy(alpha = 0.2f))
                    .border(1.5.dp, selectedPersona.color, CircleShape),
                contentAlignment = Alignment.Center
            ) {
                Text(selectedPersona.name[0].toString(), color = selectedPersona.color,
                    fontWeight = FontWeight.Bold, fontSize = 14.sp, fontFamily = FontFamily.Monospace)
            }
            Spacer(modifier = Modifier.width(10.dp))
            Column(modifier = Modifier.weight(1f)) {
                Text(selectedPersona.name, color = selectedPersona.color,
                    fontWeight = FontWeight.Bold, fontSize = 14.sp, fontFamily = FontFamily.Monospace)
                Text("Агент • онлайн", color = NeonGreen, fontSize = 10.sp, fontFamily = FontFamily.Monospace)
            }
            // Switch agent button
            Box {
                IconButton(onClick = { showPersonaMenu = true }) {
                    Icon(Icons.Filled.SwapHoriz, contentDescription = "Сменить агента", tint = NeonCyan)
                }
                DropdownMenu(
                    expanded = showPersonaMenu,
                    onDismissRequest = { showPersonaMenu = false },
                    modifier = Modifier.background(BgCard)
                ) {
                    agentPersonas.forEach { persona ->
                        DropdownMenuItem(
                            text = {
                                Row(verticalAlignment = Alignment.CenterVertically) {
                                    Box(modifier = Modifier.size(8.dp).clip(CircleShape).background(persona.color))
                                    Spacer(Modifier.width(8.dp))
                                    Text(persona.name, color = if (persona == selectedPersona) persona.color else TextPrimary,
                                        fontFamily = FontFamily.Monospace)
                                }
                            },
                            onClick = {
                                selectedPersona = persona
                                showPersonaMenu = false
                                messages = messages + ChatMessage(
                                    sender = ChatSender.SYSTEM,
                                    text = "Переключено на ${persona.name}"
                                )
                            }
                        )
                    }
                }
            }
            // Clear chat
            IconButton(onClick = {
                messages = listOf(ChatMessage(sender = ChatSender.SYSTEM, text = "Чат очищен"))
            }) {
                Icon(Icons.Filled.DeleteSweep, contentDescription = "Очистить", tint = TextSecondary)
            }
        }

        // ── Messages ──────────────────────────────────────────────────────────
        LazyColumn(
            state = listState,
            modifier = Modifier.weight(1f).padding(horizontal = 12.dp),
            contentPadding = PaddingValues(vertical = 8.dp),
            verticalArrangement = Arrangement.spacedBy(6.dp)
        ) {
            items(messages, key = { it.id }) { msg ->
                ChatBubble(msg = msg, accentColor = selectedPersona.color)
            }
            if (isTyping) {
                item {
                    TypingIndicator(agentName = selectedPersona.name, color = selectedPersona.color)
                }
            }
        }

        // ── Quick commands ────────────────────────────────────────────────────
        Row(
            modifier = Modifier.fillMaxWidth().background(BgDark).padding(horizontal = 8.dp, vertical = 4.dp),
            horizontalArrangement = Arrangement.spacedBy(6.dp)
        ) {
            listOf("/status", "/agents", "/help", "/task").forEach { cmd ->
                QuickCmdChip(cmd) { inputText = cmd + (if (cmd == "/task") " " else ""); if (cmd != "/task") sendMessage() }
            }
        }

        // ── Input ─────────────────────────────────────────────────────────────
        Row(
            modifier = Modifier.fillMaxWidth().background(BgDark).padding(8.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            OutlinedTextField(
                value = inputText,
                onValueChange = { inputText = it },
                modifier = Modifier.weight(1f),
                placeholder = { Text("Сообщение агенту...", color = TextSecondary, fontSize = 13.sp, fontFamily = FontFamily.Monospace) },
                colors = OutlinedTextFieldDefaults.colors(
                    focusedBorderColor = selectedPersona.color,
                    unfocusedBorderColor = selectedPersona.color.copy(alpha = 0.3f),
                    focusedTextColor = TextPrimary,
                    unfocusedTextColor = TextPrimary,
                    cursorColor = selectedPersona.color
                ),
                shape = RoundedCornerShape(12.dp),
                maxLines = 3,
                keyboardOptions = KeyboardOptions(imeAction = ImeAction.Send),
                keyboardActions = KeyboardActions(onSend = { sendMessage() }),
                textStyle = LocalTextStyle.current.copy(fontFamily = FontFamily.Monospace, fontSize = 13.sp)
            )
            Spacer(modifier = Modifier.width(8.dp))
            IconButton(
                onClick = { sendMessage() },
                modifier = Modifier.size(48.dp).background(selectedPersona.color, CircleShape)
            ) {
                Icon(Icons.Filled.Send, contentDescription = "Отправить", tint = BgDeep)
            }
        }
    }
}

// ── Chat bubble ───────────────────────────────────────────────────────────────
@Composable
private fun ChatBubble(msg: ChatMessage, accentColor: Color) {
    when (msg.sender) {
        ChatSender.SYSTEM -> {
            Box(modifier = Modifier.fillMaxWidth(), contentAlignment = Alignment.Center) {
                Text(msg.text, color = TextSecondary, fontSize = 10.sp, fontFamily = FontFamily.Monospace)
            }
        }
        ChatSender.USER -> {
            Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.End) {
                Column(horizontalAlignment = Alignment.End, modifier = Modifier.widthIn(max = 280.dp)) {
                    Box(
                        modifier = Modifier
                            .background(NeonCyan.copy(alpha = 0.15f), RoundedCornerShape(12.dp, 2.dp, 12.dp, 12.dp))
                            .border(1.dp, NeonCyan.copy(alpha = 0.4f), RoundedCornerShape(12.dp, 2.dp, 12.dp, 12.dp))
                            .padding(horizontal = 12.dp, vertical = 8.dp)
                    ) {
                        Text(msg.text, color = TextPrimary, fontSize = 13.sp, fontFamily = FontFamily.Monospace, lineHeight = 18.sp)
                    }
                    Text(msg.time, color = TextSecondary, fontSize = 9.sp, fontFamily = FontFamily.Monospace, modifier = Modifier.padding(top = 2.dp))
                }
            }
        }
        ChatSender.AGENT -> {
            Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.Start) {
                Box(
                    modifier = Modifier.size(28.dp).clip(CircleShape)
                        .background(accentColor.copy(alpha = 0.15f))
                        .border(1.dp, accentColor, CircleShape),
                    contentAlignment = Alignment.Center
                ) {
                    Text(msg.agentName[0].toString(), color = accentColor, fontSize = 11.sp, fontWeight = FontWeight.Bold, fontFamily = FontFamily.Monospace)
                }
                Spacer(modifier = Modifier.width(6.dp))
                Column(modifier = Modifier.widthIn(max = 280.dp)) {
                    Text(msg.agentName, color = accentColor, fontSize = 9.sp, fontFamily = FontFamily.Monospace, letterSpacing = 1.sp)
                    Spacer(modifier = Modifier.height(2.dp))
                    Box(
                        modifier = Modifier
                            .background(accentColor.copy(alpha = 0.08f), RoundedCornerShape(2.dp, 12.dp, 12.dp, 12.dp))
                            .border(1.dp, accentColor.copy(alpha = 0.3f), RoundedCornerShape(2.dp, 12.dp, 12.dp, 12.dp))
                            .padding(horizontal = 12.dp, vertical = 8.dp)
                    ) {
                        Text(msg.text, color = TextPrimary, fontSize = 13.sp, fontFamily = FontFamily.Monospace, lineHeight = 18.sp)
                    }
                    Text(msg.time, color = TextSecondary, fontSize = 9.sp, fontFamily = FontFamily.Monospace, modifier = Modifier.padding(top = 2.dp))
                }
            }
        }
    }
}

@Composable
private fun TypingIndicator(agentName: String, color: Color) {
    Row(verticalAlignment = Alignment.CenterVertically) {
        Box(
            modifier = Modifier.size(28.dp).clip(CircleShape)
                .background(color.copy(alpha = 0.15f))
                .border(1.dp, color, CircleShape),
            contentAlignment = Alignment.Center
        ) {
            Text(agentName[0].toString(), color = color, fontSize = 11.sp, fontWeight = FontWeight.Bold, fontFamily = FontFamily.Monospace)
        }
        Spacer(modifier = Modifier.width(6.dp))
        Box(
            modifier = Modifier
                .background(color.copy(alpha = 0.08f), RoundedCornerShape(2.dp, 12.dp, 12.dp, 12.dp))
                .border(1.dp, color.copy(alpha = 0.3f), RoundedCornerShape(2.dp, 12.dp, 12.dp, 12.dp))
                .padding(horizontal = 16.dp, vertical = 10.dp)
        ) {
            Text("• • •", color = color, fontSize = 14.sp, fontFamily = FontFamily.Monospace)
        }
    }
}

@Composable
private fun QuickCmdChip(label: String, onClick: () -> Unit) {
    Surface(
        onClick = onClick,
        shape = RoundedCornerShape(6.dp),
        color = NeonCyan.copy(alpha = 0.1f),
        border = androidx.compose.foundation.BorderStroke(1.dp, NeonCyan.copy(alpha = 0.4f))
    ) {
        Text(label, modifier = Modifier.padding(horizontal = 8.dp, vertical = 4.dp),
            color = NeonCyan, fontSize = 10.sp, fontFamily = FontFamily.Monospace)
    }
}

// Memory for chat (simple in-memory list per session)
val knownChatIdsChatMemory = mutableListOf<String>()
val selectedLlmModel = mutableStateOf("Claude Sonnet")
