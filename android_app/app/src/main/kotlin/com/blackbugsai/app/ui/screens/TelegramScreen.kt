package com.blackbugsai.app.ui.screens

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.material3.TabRowDefaults.tabIndicatorOffset
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.blackbugsai.app.AppViewModel
import com.blackbugsai.app.knownChatIds
import com.blackbugsai.app.services.TelegramBotService
import com.blackbugsai.app.ui.theme.*
import kotlinx.coroutines.launch
import java.text.SimpleDateFormat
import java.util.*

@Composable
fun TelegramScreen(vm: AppViewModel) {
    val botService by vm.botService.collectAsState()
    var selectedTab by remember { mutableIntStateOf(0) }
    val tabs = listOf("STATUS", "MESSAGES", "BROADCAST", "КОМАНДЫ")

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(BgDeep)
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 16.dp, vertical = 12.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Text(
                "BOT PANEL",
                fontSize = 22.sp,
                fontWeight = FontWeight.Bold,
                color = NeonCyan,
                letterSpacing = 3.sp
            )
        }

        TabRow(
            selectedTabIndex = selectedTab,
            containerColor   = BgDark,
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
                            letterSpacing = 1.sp,
                            fontSize = 12.sp
                        )
                    }
                )
            }
        }

        when (selectedTab) {
            0 -> StatusTab(botService = botService)
            1 -> MessagesTab(vm = vm)
            2 -> BroadcastTab(botService = botService)
            3 -> CommandsTab(botService = botService)
        }
    }
}

// ── STATUS ────────────────────────────────────────────────────────────────────
@Composable
private fun StatusTab(botService: TelegramBotService?) {
    var botInfo  by remember { mutableStateOf<TelegramBotService.BotInfo?>(null) }
    var isOnline by remember { mutableStateOf(false) }
    var loading  by remember { mutableStateOf(true) }

    LaunchedEffect(botService) {
        if (botService != null) {
            loading  = true
            botInfo  = try { botService.getBotInfo() } catch (_: Exception) { null }
            isOnline = botInfo != null
            loading  = false
        } else {
            loading = false
        }
    }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(16.dp)
            .verticalScroll(rememberScrollState()),
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        if (loading) {
            Box(Modifier.fillMaxWidth().padding(40.dp), Alignment.Center) {
                CircularProgressIndicator(color = NeonCyan)
            }
        } else if (botService == null) {
            NeonCard(modifier = Modifier.fillMaxWidth(), borderColor = NeonPink) {
                Row(
                    modifier = Modifier.padding(16.dp),
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(12.dp)
                ) {
                    Icon(Icons.Filled.ErrorOutline, contentDescription = null, tint = NeonPink)
                    Text("No bot configured. Go to Setup screen.", color = NeonPink)
                }
            }
        } else {
            NeonCard(
                modifier    = Modifier.fillMaxWidth(),
                borderColor = if (isOnline) NeonGreen else NeonPink
            ) {
                Column(modifier = Modifier.padding(20.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
                    Row(
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.spacedBy(10.dp)
                    ) {
                        Box(
                            modifier = Modifier
                                .size(14.dp)
                                .background(
                                    color = if (isOnline) NeonGreen else NeonPink,
                                    shape = androidx.compose.foundation.shape.CircleShape
                                )
                        )
                        Text(
                            if (isOnline) "ONLINE" else "OFFLINE",
                            color      = if (isOnline) NeonGreen else NeonPink,
                            fontWeight = FontWeight.Bold,
                            letterSpacing = 2.sp
                        )
                    }
                    HorizontalDivider(color = NeonGreen.copy(alpha = 0.3f))
                    botInfo?.let { info ->
                        InfoRow("Bot Name",    info.firstName)
                        InfoRow("Username",    "@${info.username}")
                        InfoRow("Bot ID",      info.id.toString())
                        InfoRow("Known Chats", "${knownChatIds.size}")
                    } ?: InfoRow("Status", "Could not retrieve bot info")
                }
            }
        }
    }
}

@Composable
private fun InfoRow(key: String, value: String) {
    Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
        Text(key,   color = TextSecondary, fontSize = 14.sp)
        Text(value, color = TextPrimary,   fontSize = 14.sp, fontWeight = FontWeight.SemiBold)
    }
}

// ── MESSAGES ──────────────────────────────────────────────────────────────────
@Composable
private fun MessagesTab(vm: AppViewModel) {
    val updates   by vm.updates.collectAsState()
    val listState = rememberLazyListState()
    val messages  = updates.filter { it.message != null }

    Column(modifier = Modifier.fillMaxSize()) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 16.dp, vertical = 8.dp),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Text("${messages.size} messages", color = TextSecondary, fontSize = 13.sp)
            Icon(Icons.Filled.Sync, contentDescription = null, tint = NeonGreen, modifier = Modifier.size(18.dp))
        }

        if (messages.isEmpty()) {
            Box(Modifier.fillMaxSize().padding(40.dp), Alignment.Center) {
                Text(
                    "No messages yet.\nSend a message to your bot in Telegram.",
                    color = TextSecondary, fontSize = 14.sp, textAlign = TextAlign.Center
                )
            }
        } else {
            LazyColumn(
                state    = listState,
                modifier = Modifier.fillMaxSize().padding(horizontal = 16.dp),
                verticalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                items(messages.reversed()) { update ->
                    val msg  = update.message ?: return@items
                    val time = SimpleDateFormat("HH:mm", Locale.getDefault()).format(Date(msg.date * 1000))
                    NeonCard(modifier = Modifier.fillMaxWidth(), borderColor = NeonPurple) {
                        Column(modifier = Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                            Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                                Text(
                                    msg.from?.let { "@${it.username ?: it.firstName}" } ?: "Unknown",
                                    color = NeonCyan, fontWeight = FontWeight.SemiBold, fontSize = 13.sp
                                )
                                Text(time, color = TextSecondary, fontSize = 12.sp)
                            }
                            Text(msg.text ?: "(no text)", color = TextPrimary, fontSize = 14.sp, lineHeight = 20.sp)
                        }
                    }
                }
                item { Spacer(Modifier.height(8.dp)) }
            }
        }
    }
}

// ── BROADCAST ─────────────────────────────────────────────────────────────────
@Composable
private fun BroadcastTab(botService: TelegramBotService?) {
    var message by remember { mutableStateOf("") }
    var sending by remember { mutableStateOf(false) }
    var result  by remember { mutableStateOf("") }
    val scope   = rememberCoroutineScope()

    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(16.dp)
            .verticalScroll(rememberScrollState()),
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        NeonCard(modifier = Modifier.fillMaxWidth(), borderColor = NeonYellow) {
            Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    Icon(Icons.Filled.Campaign, contentDescription = null, tint = NeonYellow)
                    Text("Broadcast", color = TextPrimary, fontWeight = FontWeight.SemiBold)
                }
                Text("Отправить всем ${knownChatIds.size} известным чатам",
                    color = TextSecondary, fontSize = 12.sp)
            }
        }

        NeonTextField(
            value         = message,
            onValueChange = { message = it; result = "" },
            label         = "Message",
            placeholder   = "Текст рассылки…",
            modifier      = Modifier.fillMaxWidth().heightIn(min = 120.dp),
            singleLine    = false,
            accentColor   = NeonYellow
        )

        AnimatedVisibility(result.isNotEmpty()) {
            NeonCard(
                modifier    = Modifier.fillMaxWidth(),
                borderColor = if (result.startsWith("Sent")) NeonGreen else NeonPink
            ) {
                Text(result, modifier = Modifier.padding(12.dp),
                    color = if (result.startsWith("Sent")) NeonGreen else NeonPink, fontSize = 13.sp)
            }
        }

        NeonButton(
            onClick = {
                scope.launch {
                    if (botService == null) { result = "No bot configured"; return@launch }
                    if (message.isBlank()) { result = "Message is empty"; return@launch }
                    if (knownChatIds.isEmpty()) { result = "No known chats yet."; return@launch }
                    sending = true; result = ""
                    var ok = 0; var fail = 0
                    knownChatIds.forEach { chatId ->
                        val sent = try { botService.sendMessage(chatId, message) } catch (_: Exception) { false }
                        if (sent) ok++ else fail++
                    }
                    sending = false
                    result  = "Sent: $ok  Failed: $fail"
                    if (ok > 0) message = ""
                }
            },
            modifier    = Modifier.fillMaxWidth().height(48.dp),
            borderColor = NeonYellow,
            enabled     = message.isNotBlank() && !sending && botService != null
        ) {
            if (sending) CircularProgressIndicator(modifier = Modifier.size(20.dp), color = NeonYellow, strokeWidth = 2.dp)
            else Text("BROADCAST", letterSpacing = 2.sp, fontWeight = FontWeight.Bold)
        }
    }
}

// ── КОМАНДЫ ───────────────────────────────────────────────────────────────────
@Composable
private fun CommandsTab(botService: TelegramBotService?) {
    val scope = rememberCoroutineScope()

    var commands  by remember { mutableStateOf<List<TelegramBotService.BotCommand>>(emptyList()) }
    var loading   by remember { mutableStateOf(false) }
    var saving    by remember { mutableStateOf(false) }
    var statusMsg by remember { mutableStateOf("") }
    var newCmd    by remember { mutableStateOf("") }
    var newDesc   by remember { mutableStateOf("") }

    val presets = listOf(
        TelegramBotService.BotCommand("start",  "Запустить бота / приветствие"),
        TelegramBotService.BotCommand("help",   "Список команд"),
        TelegramBotService.BotCommand("status", "Статус системы и агентов"),
        TelegramBotService.BotCommand("agents", "Список всех агентов"),
        TelegramBotService.BotCommand("online", "Только активные агенты"),
    )

    fun loadCommands() {
        scope.launch {
            if (botService == null) return@launch
            loading = true
            commands = try { botService.getMyCommands() } catch (_: Exception) { emptyList() }
            loading = false
        }
    }

    LaunchedEffect(botService) { loadCommands() }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(16.dp)
            .verticalScroll(rememberScrollState()),
        verticalArrangement = Arrangement.spacedBy(14.dp)
    ) {
        if (botService == null) {
            NeonCard(modifier = Modifier.fillMaxWidth(), borderColor = NeonPink) {
                Text("No bot configured.", modifier = Modifier.padding(16.dp), color = NeonPink)
            }
            return@Column
        }

        // ── Presets ───────────────────────────────────────────────────────────
        NeonCard(modifier = Modifier.fillMaxWidth(), borderColor = NeonCyan) {
            Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    Icon(Icons.Filled.AutoAwesome, contentDescription = null, tint = NeonCyan, modifier = Modifier.size(18.dp))
                    Text("Пресеты команд", color = NeonCyan, fontWeight = FontWeight.Bold)
                }
                presets.forEach { preset ->
                    val exists = commands.any { it.command == preset.command }
                    OutlinedButton(
                        onClick = { if (!exists) commands = commands + preset },
                        modifier = Modifier.fillMaxWidth(),
                        enabled  = !exists,
                        colors   = ButtonDefaults.outlinedButtonColors(
                            contentColor = if (exists) TextSecondary else NeonCyan),
                        border   = androidx.compose.foundation.BorderStroke(
                            1.dp, if (exists) TextSecondary.copy(alpha = 0.3f) else NeonCyan.copy(alpha = 0.5f)),
                        shape    = RoundedCornerShape(8.dp),
                        contentPadding = PaddingValues(horizontal = 12.dp, vertical = 8.dp)
                    ) {
                        Icon(
                            if (exists) Icons.Filled.Check else Icons.Filled.Add,
                            contentDescription = null, modifier = Modifier.size(14.dp)
                        )
                        Spacer(Modifier.width(6.dp))
                        Text("/${preset.command} — ${preset.description}", fontSize = 12.sp)
                    }
                }
            }
        }

        // ── Custom command input ──────────────────────────────────────────────
        NeonCard(modifier = Modifier.fillMaxWidth(), borderColor = NeonPurple) {
            Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
                Text("Добавить свою команду", color = NeonPurple, fontWeight = FontWeight.Bold)
                NeonTextField(
                    value         = newCmd,
                    onValueChange = { newCmd = it.lowercase().filter { c -> c.isLetterOrDigit() || c == '_' } },
                    label         = "Команда (без /)",
                    placeholder   = "my_command",
                    modifier      = Modifier.fillMaxWidth(),
                    accentColor   = NeonPurple
                )
                NeonTextField(
                    value         = newDesc,
                    onValueChange = { newDesc = it },
                    label         = "Описание",
                    placeholder   = "Что делает команда",
                    modifier      = Modifier.fillMaxWidth(),
                    accentColor   = NeonPurple
                )
                NeonButton(
                    onClick = {
                        val cmd = newCmd.trim()
                        if (cmd.isNotBlank() && newDesc.isNotBlank() && commands.none { it.command == cmd }) {
                            commands = commands + TelegramBotService.BotCommand(cmd, newDesc.trim())
                            newCmd = ""; newDesc = ""
                        }
                    },
                    modifier    = Modifier.fillMaxWidth().height(40.dp),
                    borderColor = NeonPurple,
                    enabled     = newCmd.isNotBlank() && newDesc.isNotBlank()
                ) {
                    Text("ДОБАВИТЬ", letterSpacing = 1.sp, fontSize = 12.sp)
                }
            }
        }

        // ── Command list ──────────────────────────────────────────────────────
        NeonCard(modifier = Modifier.fillMaxWidth(), borderColor = NeonGreen) {
            Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Text("Список (${commands.size})", color = NeonGreen, fontWeight = FontWeight.Bold)
                    IconButton(onClick = { loadCommands() }, modifier = Modifier.size(32.dp)) {
                        Icon(Icons.Filled.Refresh, contentDescription = "Reload",
                            tint = NeonGreen, modifier = Modifier.size(18.dp))
                    }
                }
                if (loading) {
                    Box(Modifier.fillMaxWidth().padding(8.dp), Alignment.Center) {
                        CircularProgressIndicator(color = NeonGreen, modifier = Modifier.size(24.dp), strokeWidth = 2.dp)
                    }
                } else if (commands.isEmpty()) {
                    Text("Нет команд. Добавьте из пресетов или вручную.",
                        color = TextSecondary, fontSize = 12.sp)
                } else {
                    commands.forEach { cmd ->
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Text("/${cmd.command}",
                                color = NeonCyan, fontSize = 13.sp, fontWeight = FontWeight.Bold,
                                modifier = Modifier.weight(1f))
                            Text(cmd.description,
                                color = TextSecondary, fontSize = 12.sp,
                                modifier = Modifier.weight(2f))
                            IconButton(
                                onClick = { commands = commands.filter { it.command != cmd.command } },
                                modifier = Modifier.size(28.dp)
                            ) {
                                Icon(Icons.Filled.Delete, contentDescription = "Remove",
                                    tint = NeonPink, modifier = Modifier.size(16.dp))
                            }
                        }
                    }
                }
            }
        }

        AnimatedVisibility(statusMsg.isNotEmpty()) {
            NeonCard(
                modifier    = Modifier.fillMaxWidth(),
                borderColor = if (statusMsg.startsWith("Сохранено") || statusMsg.startsWith("OK")) NeonGreen else NeonPink
            ) {
                Text(statusMsg, modifier = Modifier.padding(12.dp),
                    color = if (statusMsg.startsWith("Сохранено") || statusMsg.startsWith("OK")) NeonGreen else NeonPink,
                    fontSize = 13.sp)
            }
        }

        // ── Save / Reset ──────────────────────────────────────────────────────
        Row(horizontalArrangement = Arrangement.spacedBy(12.dp), modifier = Modifier.fillMaxWidth()) {
            NeonButton(
                onClick = {
                    scope.launch {
                        saving = true; statusMsg = ""
                        val ok = try { botService.setMyCommands(commands) } catch (_: Exception) { false }
                        saving = false
                        statusMsg = if (ok) "Сохранено ${commands.size} команд в Telegram" else "Ошибка сохранения"
                    }
                },
                modifier    = Modifier.weight(1f).height(48.dp),
                borderColor = NeonGreen,
                enabled     = !saving && commands.isNotEmpty()
            ) {
                if (saving) CircularProgressIndicator(modifier = Modifier.size(18.dp), color = NeonGreen, strokeWidth = 2.dp)
                else Text("СОХРАНИТЬ", fontSize = 11.sp, fontWeight = FontWeight.Bold, letterSpacing = 1.sp)
            }

            NeonButton(
                onClick = {
                    scope.launch {
                        saving = true; statusMsg = ""
                        val ok = try { botService.deleteMyCommands() } catch (_: Exception) { false }
                        if (ok) commands = emptyList()
                        saving = false
                        statusMsg = if (ok) "Команды удалены" else "Ошибка"
                    }
                },
                modifier    = Modifier.weight(1f).height(48.dp),
                borderColor = NeonPink,
                enabled     = !saving
            ) {
                Text("СБРОСИТЬ", fontSize = 11.sp, fontWeight = FontWeight.Bold, letterSpacing = 1.sp)
            }
        }
    }
}
