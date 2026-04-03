package com.blackbugsai.app.ui.screens

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.material3.TabRowDefaults.tabIndicatorOffset
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.blackbugsai.app.AppViewModel
import com.blackbugsai.app.knownChatIds
import com.blackbugsai.app.services.TelegramBotService
import com.blackbugsai.app.ui.theme.*
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import java.text.SimpleDateFormat
import java.util.*

@Composable
fun TelegramScreen(vm: AppViewModel) {
    val botService by vm.botService.collectAsState()
    var selectedTab by remember { mutableIntStateOf(0) }
    val tabs = listOf("STATUS", "MESSAGES", "BROADCAST")

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(BgDeep)
    ) {
        // ── Header ────────────────────────────────────────────────────────────
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 16.dp, vertical = 12.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Text(
                "BOT PANEL",
                fontSize   = 22.sp,
                fontWeight = FontWeight.Bold,
                color      = NeonCyan,
                letterSpacing = 3.sp
            )
        }

        // ── Tabs ──────────────────────────────────────────────────────────────
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
                            fontSize = 13.sp
                        )
                    }
                )
            }
        }

        // ── Tab content ───────────────────────────────────────────────────────
        when (selectedTab) {
            0 -> StatusTab(botService = botService)
            1 -> MessagesTab(botService = botService)
            2 -> BroadcastTab(botService = botService)
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
            botInfo  = try { botService.getBotInfo() } catch (e: Exception) { null }
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
            NeonCard(modifier = Modifier.fillMaxWidth(), borderColor = if (isOnline) NeonGreen else NeonPink) {
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
                                .neonGlow(if (isOnline) NeonGreen else NeonPink, 8.dp, 7.dp)
                        )
                        Text(
                            if (isOnline) "ONLINE" else "OFFLINE",
                            color      = if (isOnline) NeonGreen else NeonPink,
                            fontWeight = FontWeight.Bold,
                            letterSpacing = 2.sp
                        )
                    }

                    Divider(color = NeonGreen.copy(alpha = 0.3f))

                    botInfo?.let { info ->
                        InfoRow("Bot Name",     info.firstName)
                        InfoRow("Username",     "@${info.username}")
                        InfoRow("Bot ID",       info.id.toString())
                        InfoRow("Known Chats",  "${knownChatIds.size}")
                    } ?: InfoRow("Status", "Could not retrieve bot info")
                }
            }
        }
    }
}

@Composable
private fun InfoRow(key: String, value: String) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.SpaceBetween
    ) {
        Text(key,   color = TextSecondary, fontSize = 14.sp)
        Text(value, color = TextPrimary,   fontSize = 14.sp, fontWeight = FontWeight.SemiBold)
    }
}

// ── MESSAGES ──────────────────────────────────────────────────────────────────
@Composable
private fun MessagesTab(botService: TelegramBotService?) {
    var messages by remember { mutableStateOf<List<TelegramBotService.Update>>(emptyList()) }
    var loading  by remember { mutableStateOf(false) }
    var lastOffset by remember { mutableIntStateOf(0) }
    val listState  = rememberLazyListState()
    val scope      = rememberCoroutineScope()

    fun refresh() {
        scope.launch {
            if (botService == null) return@launch
            loading = true
            val updates = try { botService.getUpdates(0) } catch (e: Exception) { emptyList() }
            updates.forEach { u -> u.message?.from?.let { knownChatIds.add(it.id) } }
            messages   = updates.filter { it.message != null }
            loading    = false
        }
    }

    LaunchedEffect(botService) { refresh() }

    Column(modifier = Modifier.fillMaxSize()) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 16.dp, vertical = 8.dp),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Text("${messages.size} messages", color = TextSecondary, fontSize = 13.sp)
            IconButton(onClick = { refresh() }) {
                Icon(Icons.Filled.Refresh, contentDescription = "Refresh", tint = NeonCyan)
            }
        }

        if (loading) {
            Box(Modifier.fillMaxWidth().padding(40.dp), Alignment.Center) {
                CircularProgressIndicator(color = NeonCyan)
            }
        } else if (messages.isEmpty()) {
            Box(
                modifier = Modifier.fillMaxSize().padding(40.dp),
                contentAlignment = Alignment.Center
            ) {
                Text("No messages yet", color = TextSecondary, fontSize = 14.sp)
            }
        } else {
            LazyColumn(
                state = listState,
                modifier = Modifier.fillMaxSize().padding(horizontal = 16.dp),
                verticalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                items(messages.reversed()) { update ->
                    val msg = update.message ?: return@items
                    val time = SimpleDateFormat("HH:mm", Locale.getDefault())
                        .format(Date(msg.date * 1000))
                    NeonCard(modifier = Modifier.fillMaxWidth(), borderColor = NeonPurple) {
                        Column(modifier = Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                            Row(
                                modifier = Modifier.fillMaxWidth(),
                                horizontalArrangement = Arrangement.SpaceBetween
                            ) {
                                Text(
                                    msg.from?.let { "@${it.username ?: it.firstName}" } ?: "Unknown",
                                    color = NeonCyan, fontWeight = FontWeight.SemiBold, fontSize = 13.sp
                                )
                                Text(time, color = TextSecondary, fontSize = 12.sp)
                            }
                            Text(
                                msg.text ?: "(no text)",
                                color    = TextPrimary,
                                fontSize = 14.sp,
                                lineHeight = 20.sp
                            )
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
                    Text("Broadcast to all users", color = TextPrimary, fontWeight = FontWeight.SemiBold)
                }
                Text(
                    "Sends to ${knownChatIds.size} known chat IDs (stored locally this session)",
                    color = TextSecondary, fontSize = 12.sp
                )
            }
        }

        NeonTextField(
            value         = message,
            onValueChange = { message = it; result = "" },
            label         = "Message",
            placeholder   = "Type your broadcast message…",
            modifier      = Modifier.fillMaxWidth().heightIn(min = 120.dp),
            singleLine    = false,
            accentColor   = NeonYellow
        )

        AnimatedVisibility(result.isNotEmpty()) {
            NeonCard(
                modifier    = Modifier.fillMaxWidth(),
                borderColor = if (result.startsWith("Sent")) NeonGreen else NeonPink
            ) {
                Text(
                    result,
                    modifier = Modifier.padding(12.dp),
                    color    = if (result.startsWith("Sent")) NeonGreen else NeonPink,
                    fontSize = 13.sp
                )
            }
        }

        NeonButton(
            onClick = {
                scope.launch {
                    if (botService == null) { result = "No bot configured"; return@launch }
                    if (message.isBlank()) { result = "Message is empty"; return@launch }
                    if (knownChatIds.isEmpty()) { result = "No known chats yet. Wait for users to message the bot."; return@launch }

                    sending = true
                    result  = ""
                    var ok = 0; var fail = 0
                    knownChatIds.forEach { chatId ->
                        val sent = try { botService.sendMessage(chatId, message) } catch (e: Exception) { false }
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
            if (sending) {
                CircularProgressIndicator(modifier = Modifier.size(20.dp), color = NeonYellow, strokeWidth = 2.dp)
            } else {
                Text("BROADCAST", letterSpacing = 2.sp, fontWeight = FontWeight.Bold)
            }
        }
    }
}
