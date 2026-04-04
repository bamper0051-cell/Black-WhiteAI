package com.blackbugsai.app.ui.screens

import androidx.compose.animation.core.*
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.Send
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.blackbugsai.app.AgentChatMsg
import com.blackbugsai.app.AppViewModel
import com.blackbugsai.app.ui.theme.*
import kotlinx.coroutines.launch
import java.text.SimpleDateFormat
import java.util.*

// ── Legacy chat message model (kept for backward compat) ──────────────────────
enum class ChatSender { USER, AGENT, SYSTEM }

data class ChatMessage(
    val id: Long = System.currentTimeMillis(),
    val sender: ChatSender,
    val agentName: String = "SYSTEM",
    val text: String,
    val time: String = SimpleDateFormat("HH:mm", Locale.getDefault()).format(Date())
)

// ── Agent persona model ───────────────────────────────────────────────────────
data class AgentPersona(
    val id: String,
    val name: String,
    val color: Color,
    val icon: ImageVector,
    val cmdPrefix: String,
    val description: String
)

val agentPersonas = listOf(
    AgentPersona("neo",       "Agent NEO",    NeonCyan,   Icons.Filled.Psychology,  "/neo",    "Автономный планировщик задач"),
    AgentPersona("matrix",    "MATRIX",       NeonPurple, Icons.Filled.AutoAwesome, "/matrix", "Универсальный агент-оркестратор"),
    AgentPersona("smith",     "AGENT_SMITH",  NeonYellow, Icons.Filled.Code,        "/smith",  "Автономный кодер и аналитик"),
    AgentPersona("coder3",    "CODER3",       NeonGreen,  Icons.Filled.Terminal,    "/code3",  "Специалист по написанию кода"),
    AgentPersona("assistant", "Ассистент",    NeonPink,   Icons.Filled.SmartToy,   "",        "Умный помощник"),
)

// ── Exposed global state for backward compat ──────────────────────────────────
val selectedLlmModel = mutableStateOf("Claude Sonnet")

// ── Quick command chips ───────────────────────────────────────────────────────
private val quickCommands = listOf("/status", "/agents", "/help")

// ── Main ChatScreen composable ────────────────────────────────────────────────
@Composable
fun ChatScreen(vm: AppViewModel) {
    val scope       = rememberCoroutineScope()
    val listState   = rememberLazyListState()
    val appMode     by vm.appMode.collectAsState()
    val allMessages by vm.agentMessages.collectAsState()
    val updates     by vm.updates.collectAsState()
    val polling     by vm.polling.collectAsState()

    var selectedPersona by remember { mutableStateOf(agentPersonas[0]) }
    var inputText       by remember { mutableStateOf("") }

    val isServerMode = appMode == "server"
    val messages     = allMessages[selectedPersona.id] ?: emptyList()

    // Scroll to bottom whenever messages change for current agent
    LaunchedEffect(messages.size, selectedPersona.id) {
        if (messages.isNotEmpty()) {
            listState.animateScrollToItem(messages.size - 1)
        }
    }

    fun sendMessage() {
        val text = inputText.trim()
        if (text.isEmpty()) return
        inputText = ""
        scope.launch {
            vm.sendAgentTask(selectedPersona.id, text)
        }
    }

    Column(modifier = Modifier
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
            // Title
            Text(
                text       = "АГЕНТ-ЧАТ",
                color      = NeonCyan,
                fontSize   = 16.sp,
                fontWeight = FontWeight.Bold,
                fontFamily = FontFamily.Monospace,
                modifier   = Modifier.weight(1f)
            )

            // Connection status indicator
            val (dotColor, statusLabel) = when {
                isServerMode -> Pair(NeonGreen, "СЕРВЕР")
                polling      -> Pair(NeonCyan,  "TELEGRAM")
                else         -> Pair(Color.Gray, "ОФЛАЙН")
            }
            Row(
                verticalAlignment     = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(5.dp)
            ) {
                Box(
                    modifier = Modifier
                        .size(8.dp)
                        .clip(CircleShape)
                        .background(dotColor)
                )
                Text(
                    text       = statusLabel,
                    color      = dotColor,
                    fontSize   = 10.sp,
                    fontFamily = FontFamily.Monospace
                )
            }

            Spacer(modifier = Modifier.width(8.dp))

            // Clear current agent chat
            IconButton(
                onClick  = { vm.clearAgentChat(selectedPersona.id) },
                modifier = Modifier.size(36.dp)
            ) {
                Icon(
                    imageVector        = Icons.Filled.DeleteSweep,
                    contentDescription = "Очистить чат",
                    tint               = TextSecondary,
                    modifier           = Modifier.size(18.dp)
                )
            }
        }

        // ── Agent selector chips ──────────────────────────────────────────────
        LazyRow(
            modifier              = Modifier
                .fillMaxWidth()
                .background(BgDark)
                .padding(horizontal = 10.dp, vertical = 6.dp),
            horizontalArrangement = Arrangement.spacedBy(8.dp),
            contentPadding        = PaddingValues(horizontal = 2.dp)
        ) {
            items(agentPersonas) { persona ->
                val isSelected = persona.id == selectedPersona.id
                Surface(
                    onClick = { selectedPersona = persona },
                    shape   = RoundedCornerShape(20.dp),
                    color   = if (isSelected) persona.color.copy(alpha = 0.22f) else BgCard,
                    border  = BorderStroke(
                        width = if (isSelected) 1.5.dp else 1.dp,
                        color = if (isSelected) persona.color else persona.color.copy(alpha = 0.35f)
                    )
                ) {
                    Row(
                        modifier              = Modifier.padding(horizontal = 12.dp, vertical = 6.dp),
                        verticalAlignment     = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.spacedBy(5.dp)
                    ) {
                        Icon(
                            imageVector        = persona.icon,
                            contentDescription = null,
                            tint               = if (isSelected) persona.color else persona.color.copy(alpha = 0.55f),
                            modifier           = Modifier.size(14.dp)
                        )
                        Text(
                            text       = persona.name,
                            color      = if (isSelected) persona.color else persona.color.copy(alpha = 0.7f),
                            fontSize   = 11.sp,
                            fontFamily = FontFamily.Monospace,
                            fontWeight = if (isSelected) FontWeight.Bold else FontWeight.Normal
                        )
                    }
                }
            }
        }

        // ── Telegram mode banner ──────────────────────────────────────────────
        if (!isServerMode) {
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .background(NeonYellow.copy(alpha = 0.08f))
                    .border(
                        width = 1.dp,
                        color = NeonYellow.copy(alpha = 0.35f),
                        shape = RoundedCornerShape(0.dp)
                    )
                    .padding(horizontal = 14.dp, vertical = 8.dp),
                verticalAlignment     = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                Icon(
                    imageVector        = Icons.Filled.Info,
                    contentDescription = null,
                    tint               = NeonYellow,
                    modifier           = Modifier.size(15.dp)
                )
                Text(
                    text       = "Для общения с агентами нужен сервер",
                    color      = NeonYellow,
                    fontSize   = 11.sp,
                    fontFamily = FontFamily.Monospace
                )
            }
        }

        // ── Message list ──────────────────────────────────────────────────────
        Box(modifier = Modifier.weight(1f)) {
            if (isServerMode) {
                // Server mode: real agent messages
                if (messages.isEmpty()) {
                    // Empty state
                    Box(
                        modifier         = Modifier.fillMaxSize(),
                        contentAlignment = Alignment.Center
                    ) {
                        Column(
                            horizontalAlignment = Alignment.CenterHorizontally,
                            verticalArrangement = Arrangement.spacedBy(14.dp)
                        ) {
                            Icon(
                                imageVector        = selectedPersona.icon,
                                contentDescription = null,
                                tint               = selectedPersona.color.copy(alpha = 0.38f),
                                modifier           = Modifier.size(56.dp)
                            )
                            Text(
                                text       = "Введите задачу для агента",
                                color      = TextSecondary,
                                fontSize   = 14.sp,
                                fontFamily = FontFamily.Monospace
                            )
                            Text(
                                text       = selectedPersona.description,
                                color      = selectedPersona.color.copy(alpha = 0.6f),
                                fontSize   = 11.sp,
                                fontFamily = FontFamily.Monospace
                            )
                        }
                    }
                } else {
                    LazyColumn(
                        state               = listState,
                        modifier            = Modifier
                            .fillMaxSize()
                            .padding(horizontal = 12.dp),
                        contentPadding      = PaddingValues(vertical = 10.dp),
                        verticalArrangement = Arrangement.spacedBy(8.dp)
                    ) {
                        items(messages, key = { it.id }) { msg ->
                            AgentChatBubble(msg = msg, persona = selectedPersona)
                        }
                        item { Spacer(modifier = Modifier.height(4.dp)) }
                    }
                }
            } else {
                // Telegram mode: read-only last 10 updates
                val recentUpdates = updates.takeLast(10)
                if (recentUpdates.isEmpty()) {
                    Box(
                        modifier         = Modifier.fillMaxSize(),
                        contentAlignment = Alignment.Center
                    ) {
                        Column(
                            horizontalAlignment = Alignment.CenterHorizontally,
                            verticalArrangement = Arrangement.spacedBy(12.dp)
                        ) {
                            Icon(
                                imageVector        = Icons.Filled.Forum,
                                contentDescription = null,
                                tint               = NeonCyan.copy(alpha = 0.35f),
                                modifier           = Modifier.size(48.dp)
                            )
                            Text(
                                text       = "Нет сообщений от пользователей",
                                color      = TextSecondary,
                                fontSize   = 13.sp,
                                fontFamily = FontFamily.Monospace
                            )
                        }
                    }
                } else {
                    LazyColumn(
                        modifier            = Modifier
                            .fillMaxSize()
                            .padding(horizontal = 12.dp),
                        contentPadding      = PaddingValues(vertical = 10.dp),
                        verticalArrangement = Arrangement.spacedBy(8.dp)
                    ) {
                        item {
                            Text(
                                text       = "Входящие сообщения бота (последние ${recentUpdates.size})",
                                color      = TextSecondary,
                                fontSize   = 10.sp,
                                fontFamily = FontFamily.Monospace,
                                modifier   = Modifier.padding(bottom = 4.dp)
                            )
                        }
                        items(recentUpdates, key = { it.updateId }) { update ->
                            TelegramUpdateBubble(update = update)
                        }
                    }
                }
            }
        }

        // ── Quick command chips ───────────────────────────────────────────────
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .background(BgDark)
                .horizontalScroll(rememberScrollState())
                .padding(horizontal = 10.dp, vertical = 5.dp),
            horizontalArrangement = Arrangement.spacedBy(6.dp)
        ) {
            quickCommands.forEach { cmd ->
                Surface(
                    onClick = {
                        inputText = cmd
                        sendMessage()
                    },
                    shape  = RoundedCornerShape(6.dp),
                    color  = NeonCyan.copy(alpha = 0.07f),
                    border = BorderStroke(1.dp, NeonCyan.copy(alpha = 0.35f))
                ) {
                    Text(
                        text       = cmd,
                        modifier   = Modifier.padding(horizontal = 10.dp, vertical = 5.dp),
                        color      = NeonCyan,
                        fontSize   = 10.sp,
                        fontFamily = FontFamily.Monospace
                    )
                }
            }
        }

        // ── Input row ─────────────────────────────────────────────────────────
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .background(BgDark)
                .padding(horizontal = 10.dp, vertical = 8.dp),
            verticalAlignment     = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            OutlinedTextField(
                value         = inputText,
                onValueChange = { inputText = it },
                modifier      = Modifier.weight(1f),
                placeholder   = {
                    Text(
                        text       = "Сообщение для ${selectedPersona.name}...",
                        color      = TextSecondary,
                        fontSize   = 12.sp,
                        fontFamily = FontFamily.Monospace
                    )
                },
                colors = OutlinedTextFieldDefaults.colors(
                    focusedBorderColor      = selectedPersona.color,
                    unfocusedBorderColor    = selectedPersona.color.copy(alpha = 0.3f),
                    focusedTextColor        = TextPrimary,
                    unfocusedTextColor      = TextPrimary,
                    cursorColor             = selectedPersona.color,
                    focusedContainerColor   = BgCard,
                    unfocusedContainerColor = BgCard
                ),
                shape           = RoundedCornerShape(12.dp),
                maxLines        = 3,
                keyboardOptions = KeyboardOptions(imeAction = ImeAction.Send),
                keyboardActions = KeyboardActions(onSend = { sendMessage() }),
                textStyle       = LocalTextStyle.current.copy(
                    fontFamily = FontFamily.Monospace,
                    fontSize   = 13.sp
                )
            )

            NeonButton(
                onClick     = { sendMessage() },
                modifier    = Modifier.size(48.dp),
                borderColor = selectedPersona.color,
                enabled     = inputText.isNotBlank()
            ) {
                Icon(
                    imageVector        = Icons.AutoMirrored.Filled.Send,
                    contentDescription = "Отправить",
                    tint               = selectedPersona.color,
                    modifier           = Modifier.size(20.dp)
                )
            }
        }
    }
}

// ── Agent chat bubble (server mode) ──────────────────────────────────────────
@Composable
private fun AgentChatBubble(msg: AgentChatMsg, persona: AgentPersona) {
    when (msg.sender) {
        "system" -> {
            Box(
                modifier         = Modifier.fillMaxWidth(),
                contentAlignment = Alignment.Center
            ) {
                Text(
                    text       = msg.text,
                    color      = TextSecondary,
                    fontSize   = 10.sp,
                    fontFamily = FontFamily.Monospace
                )
            }
        }

        "user" -> {
            // Right-aligned, NeonCyan background
            Row(
                modifier              = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.End
            ) {
                Column(
                    horizontalAlignment = Alignment.End,
                    modifier            = Modifier.widthIn(max = 310.dp)
                ) {
                    Box(
                        modifier = Modifier
                            .background(
                                NeonCyan.copy(alpha = 0.15f),
                                RoundedCornerShape(12.dp, 2.dp, 12.dp, 12.dp)
                            )
                            .border(
                                1.dp,
                                NeonCyan.copy(alpha = 0.45f),
                                RoundedCornerShape(12.dp, 2.dp, 12.dp, 12.dp)
                            )
                            .padding(horizontal = 12.dp, vertical = 9.dp)
                    ) {
                        Text(
                            text       = msg.text,
                            color      = TextPrimary,
                            fontSize   = 13.sp,
                            fontFamily = FontFamily.Monospace,
                            lineHeight = 18.sp
                        )
                    }
                    Text(
                        text       = msg.time,
                        color      = TextSecondary,
                        fontSize   = 9.sp,
                        fontFamily = FontFamily.Monospace,
                        modifier   = Modifier.padding(top = 3.dp, end = 2.dp)
                    )
                }
            }
        }

        else -> {
            // Left-aligned agent message with agent color border and dark background
            val agentColor = agentPersonas.firstOrNull { it.id == msg.agentId }?.color ?: persona.color
            val agentIcon  = agentPersonas.firstOrNull { it.id == msg.agentId }?.icon  ?: Icons.Filled.SmartToy
            val agentName  = agentPersonas.firstOrNull { it.id == msg.agentId }?.name  ?: msg.agentId

            Row(
                modifier              = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.Start,
                verticalAlignment     = Alignment.Top
            ) {
                // Agent avatar
                Box(
                    modifier = Modifier
                        .size(30.dp)
                        .clip(CircleShape)
                        .background(agentColor.copy(alpha = 0.14f))
                        .border(1.dp, agentColor, CircleShape),
                    contentAlignment = Alignment.Center
                ) {
                    Icon(
                        imageVector        = agentIcon,
                        contentDescription = null,
                        tint               = agentColor,
                        modifier           = Modifier.size(15.dp)
                    )
                }

                Spacer(modifier = Modifier.width(7.dp))

                Column(modifier = Modifier.widthIn(max = 300.dp)) {
                    // Agent name header
                    Text(
                        text          = agentName.uppercase(),
                        color         = agentColor,
                        fontSize      = 9.sp,
                        fontFamily    = FontFamily.Monospace,
                        letterSpacing = 1.sp,
                        fontWeight    = FontWeight.Bold
                    )
                    Spacer(modifier = Modifier.height(3.dp))

                    if (msg.isLoading) {
                        LoadingBubble(color = agentColor)
                    } else {
                        Box(
                            modifier = Modifier
                                .background(
                                    BgCard,
                                    RoundedCornerShape(2.dp, 12.dp, 12.dp, 12.dp)
                                )
                                .border(
                                    1.dp,
                                    agentColor.copy(alpha = 0.4f),
                                    RoundedCornerShape(2.dp, 12.dp, 12.dp, 12.dp)
                                )
                                .padding(horizontal = 12.dp, vertical = 9.dp)
                        ) {
                            Text(
                                text       = msg.text,
                                color      = TextPrimary,
                                fontSize   = 13.sp,
                                fontFamily = FontFamily.Monospace,
                                lineHeight = 18.sp
                            )
                        }
                    }

                    Text(
                        text       = msg.time,
                        color      = TextSecondary,
                        fontSize   = 9.sp,
                        fontFamily = FontFamily.Monospace,
                        modifier   = Modifier.padding(top = 3.dp)
                    )
                }
            }
        }
    }
}

// ── Telegram update bubble (read-only) ───────────────────────────────────────
@Composable
private fun TelegramUpdateBubble(update: com.blackbugsai.app.services.TelegramBotService.Update) {
    val msg      = update.message ?: return
    val text     = msg.text ?: return
    val fromName = msg.from?.let { user ->
        user.firstName.ifBlank { user.username ?: "id:${user.id}" }
    } ?: "Unknown"
    val chatId = msg.chat?.id ?: msg.from?.id ?: 0L
    val time   = SimpleDateFormat("HH:mm", Locale.getDefault())
        .format(Date(msg.date * 1000L))

    Row(
        modifier              = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.Start,
        verticalAlignment     = Alignment.Top
    ) {
        Box(
            modifier = Modifier
                .size(28.dp)
                .clip(CircleShape)
                .background(NeonCyan.copy(alpha = 0.12f))
                .border(1.dp, NeonCyan.copy(alpha = 0.5f), CircleShape),
            contentAlignment = Alignment.Center
        ) {
            Icon(
                imageVector        = Icons.Filled.Person,
                contentDescription = null,
                tint               = NeonCyan,
                modifier           = Modifier.size(14.dp)
            )
        }
        Spacer(modifier = Modifier.width(7.dp))
        Column(modifier = Modifier.widthIn(max = 300.dp)) {
            Row(
                horizontalArrangement = Arrangement.spacedBy(6.dp),
                verticalAlignment     = Alignment.CenterVertically
            ) {
                Text(
                    text       = fromName,
                    color      = NeonCyan,
                    fontSize   = 9.sp,
                    fontFamily = FontFamily.Monospace,
                    fontWeight = FontWeight.Bold
                )
                Text(
                    text       = "chat:$chatId",
                    color      = TextSecondary,
                    fontSize   = 9.sp,
                    fontFamily = FontFamily.Monospace
                )
            }
            Spacer(modifier = Modifier.height(3.dp))
            Box(
                modifier = Modifier
                    .background(
                        NeonCyan.copy(alpha = 0.07f),
                        RoundedCornerShape(2.dp, 12.dp, 12.dp, 12.dp)
                    )
                    .border(
                        1.dp,
                        NeonCyan.copy(alpha = 0.25f),
                        RoundedCornerShape(2.dp, 12.dp, 12.dp, 12.dp)
                    )
                    .padding(horizontal = 12.dp, vertical = 8.dp)
            ) {
                Text(
                    text       = text,
                    color      = TextPrimary,
                    fontSize   = 12.sp,
                    fontFamily = FontFamily.Monospace,
                    lineHeight = 17.sp
                )
            }
            Text(
                text       = time,
                color      = TextSecondary,
                fontSize   = 9.sp,
                fontFamily = FontFamily.Monospace,
                modifier   = Modifier.padding(top = 3.dp)
            )
        }
    }
}

// ── Animated loading bubble ───────────────────────────────────────────────────
@Composable
private fun LoadingBubble(color: Color) {
    val infiniteTransition = rememberInfiniteTransition(label = "loading_dots")
    val alpha by infiniteTransition.animateFloat(
        initialValue  = 0.25f,
        targetValue   = 1f,
        animationSpec = infiniteRepeatable(
            animation  = tween(550, easing = FastOutSlowInEasing),
            repeatMode = RepeatMode.Reverse
        ),
        label = "dot_alpha"
    )
    Box(
        modifier = Modifier
            .background(
                color.copy(alpha = 0.08f),
                RoundedCornerShape(2.dp, 12.dp, 12.dp, 12.dp)
            )
            .border(
                1.dp,
                color.copy(alpha = 0.3f),
                RoundedCornerShape(2.dp, 12.dp, 12.dp, 12.dp)
            )
            .padding(horizontal = 18.dp, vertical = 12.dp)
    ) {
        Text(
            text       = "• • •",
            color      = color.copy(alpha = alpha),
            fontSize   = 15.sp,
            fontFamily = FontFamily.Monospace
        )
    }
}
