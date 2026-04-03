package com.blackbugsai.app.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.rememberScrollState
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.Send
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.SpanStyle
import androidx.compose.ui.text.buildAnnotatedString
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.withStyle
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.blackbugsai.app.AppViewModel
import com.blackbugsai.app.knownChatIds
import com.blackbugsai.app.ui.theme.*
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import java.text.SimpleDateFormat
import java.util.*

data class TerminalLine(val text: String, val type: LineType)
enum class LineType { INPUT, OUTPUT, ERROR, INFO, SUCCESS }

@Composable
fun TerminalScreen(vm: AppViewModel) {
    val appMode   by vm.appMode.collectAsState()
    val botService by vm.botService.collectAsState()
    val botToken   by vm.botToken.collectAsState()

    var input  by remember { mutableStateOf("") }
    val lines  = remember {
        mutableStateListOf(
            TerminalLine("BlackBugsAI Terminal v1.1.0", LineType.SUCCESS),
            TerminalLine("Type 'help' for available commands", LineType.INFO),
            TerminalLine("", LineType.INFO)
        )
    }
    val listState = rememberLazyListState()
    val scope     = rememberCoroutineScope()

    fun timestamp() = SimpleDateFormat("HH:mm:ss", Locale.getDefault()).format(Date())

    fun addLine(text: String, type: LineType = LineType.OUTPUT) = lines.add(TerminalLine(text, type))

    fun executeCommand(cmd: String) {
        addLine("> $cmd", LineType.INPUT)
        val parts = cmd.trim().split(" ")
        when (parts[0].lowercase()) {

            "help" -> {
                addLine("═══ BlackBugsAI Commands ═══", LineType.INFO)
                addLine("── SYSTEM ──", LineType.INFO)
                addLine("  help               Show this list", LineType.OUTPUT)
                addLine("  status             Full system status", LineType.OUTPUT)
                addLine("  version            App version info", LineType.OUTPUT)
                addLine("  time               Current date/time", LineType.OUTPUT)
                addLine("  mode               Current app mode", LineType.OUTPUT)
                addLine("  clear              Clear terminal", LineType.OUTPUT)
                addLine("── BOT ──", LineType.INFO)
                addLine("  botinfo            Telegram bot details", LineType.OUTPUT)
                addLine("  chats              Known chat IDs", LineType.OUTPUT)
                addLine("  send <id> <text>   Send message to chat", LineType.OUTPUT)
                addLine("  broadcast <text>   Broadcast to all chats", LineType.OUTPUT)
                addLine("  getmsgs            Fetch recent messages", LineType.OUTPUT)
                addLine("── AGENTS ──", LineType.INFO)
                addLine("  agents             List all agents", LineType.OUTPUT)
                addLine("  agent <name>       Agent info", LineType.OUTPUT)
                addLine("  start <name>       Start agent", LineType.OUTPUT)
                addLine("  stop <name>        Stop agent", LineType.OUTPUT)
                addLine("── LLM ──", LineType.INFO)
                addLine("  model              Current AI model", LineType.OUTPUT)
                addLine("  models             List models", LineType.OUTPUT)
                addLine("  setmodel <name>    Switch model", LineType.OUTPUT)
                addLine("── NETWORK ──", LineType.INFO)
                addLine("  ping               Ping test", LineType.OUTPUT)
                addLine("  whoami             Show token/mode", LineType.OUTPUT)
                addLine("  sysinfo            System information", LineType.OUTPUT)
            }

            "status" -> {
                addLine("[${timestamp()}] Status Report:", LineType.INFO)
                addLine("  App Mode : $appMode", LineType.OUTPUT)
                addLine("  Bot      : ${if (botService != null) "configured" else "not configured"}", LineType.OUTPUT)
                addLine("  Chats    : ${knownChatIds.size} known", LineType.OUTPUT)
            }

            "botinfo" -> {
                if (botService == null) {
                    addLine("ERROR: No bot configured", LineType.ERROR)
                } else {
                    scope.launch {
                        addLine("[${timestamp()}] Fetching bot info...", LineType.INFO)
                        val info = try { botService!!.getBotInfo() } catch (e: Exception) { null }
                        if (info != null) {
                            addLine("  Name     : ${info.firstName}", LineType.OUTPUT)
                            addLine("  Username : @${info.username}", LineType.OUTPUT)
                            addLine("  ID       : ${info.id}", LineType.OUTPUT)
                            addLine("[OK] Bot is online", LineType.SUCCESS)
                        } else {
                            addLine("ERROR: Could not reach Telegram API", LineType.ERROR)
                        }
                        listState.animateScrollToItem(lines.size - 1)
                    }
                    return
                }
            }

            "chats" -> {
                if (knownChatIds.isEmpty()) {
                    addLine("No known chat IDs yet", LineType.INFO)
                } else {
                    addLine("Known chat IDs (${knownChatIds.size}):", LineType.INFO)
                    knownChatIds.forEach { id -> addLine("  $id", LineType.OUTPUT) }
                }
            }

            "clear" -> {
                lines.clear()
                addLine("Terminal cleared", LineType.INFO)
            }

            "time" -> {
                addLine(SimpleDateFormat("yyyy-MM-dd HH:mm:ss z", Locale.getDefault()).format(Date()), LineType.OUTPUT)
            }

            "mode" -> {
                addLine("Current mode: $appMode", LineType.INFO)
                when (appMode) {
                    "telegram" -> addLine("  Token: ${botToken.take(10)}...", LineType.OUTPUT)
                    "server"   -> addLine("  URL: ${vm.serverUrl.value}", LineType.OUTPUT)
                }
            }

            "ping" -> {
                scope.launch {
                    addLine("[${timestamp()}] Pinging...", LineType.INFO)
                    delay(300)
                    addLine("PONG! 302ms", LineType.SUCCESS)
                    listState.animateScrollToItem(lines.size - 1)
                }
                return
            }

            "version" -> {
                addLine("BlackBugsAI v1.1.0", LineType.SUCCESS)
                addLine("Android Jetpack Compose edition", LineType.OUTPUT)
                addLine("minSdk 26 / targetSdk 35", LineType.OUTPUT)
            }

            // ── BOT commands ─────────────────────────────────────────────
            "send" -> {
                if (parts.size < 3) { addLine("Usage: send <chat_id> <message>", LineType.ERROR); return }
                if (botService == null) { addLine("ERROR: No bot configured", LineType.ERROR); return }
                scope.launch {
                    addLine("[${timestamp()}] Sending message...", LineType.INFO)
                    val chatId = parts[1].toLongOrNull()
                    if (chatId == null) { addLine("ERROR: Invalid chat ID", LineType.ERROR); return@launch }
                    val text = parts.drop(2).joinToString(" ")
                    val ok = try { botService!!.sendMessage(chatId, text) } catch (e: Exception) { false }
                    if (ok) addLine("[OK] Message sent to $chatId", LineType.SUCCESS)
                    else addLine("ERROR: Failed to send message", LineType.ERROR)
                    listState.animateScrollToItem(lines.size - 1)
                }
                return
            }

            "broadcast" -> {
                if (parts.size < 2) { addLine("Usage: broadcast <message>", LineType.ERROR); return }
                if (botService == null) { addLine("ERROR: No bot configured", LineType.ERROR); return }
                if (knownChatIds.isEmpty()) { addLine("No known chats to broadcast to", LineType.INFO); return }
                scope.launch {
                    val text = parts.drop(1).joinToString(" ")
                    addLine("[${timestamp()}] Broadcasting to ${knownChatIds.size} chats...", LineType.INFO)
                    var sent = 0
                    knownChatIds.forEach { chatId ->
                        try { if (botService!!.sendMessage(chatId, text)) sent++ } catch (_: Exception) {}
                    }
                    addLine("[OK] Sent to $sent/${knownChatIds.size} chats", LineType.SUCCESS)
                    listState.animateScrollToItem(lines.size - 1)
                }
                return
            }

            "getmsgs" -> {
                if (botService == null) { addLine("ERROR: No bot configured", LineType.ERROR); return }
                scope.launch {
                    addLine("[${timestamp()}] Fetching updates...", LineType.INFO)
                    val updates = try { botService!!.getUpdates() } catch (e: Exception) { emptyList() }
                    if (updates.isEmpty()) {
                        addLine("No recent messages", LineType.INFO)
                    } else {
                        addLine("Recent ${updates.size} message(s):", LineType.SUCCESS)
                        updates.takeLast(5).forEach { u ->
                            val from = u.message?.from?.username ?: u.message?.from?.firstName ?: "?"
                            val text = u.message?.text ?: "(media)"
                            addLine("  @$from: $text", LineType.OUTPUT)
                        }
                    }
                    listState.animateScrollToItem(lines.size - 1)
                }
                return
            }

            // ── AGENT commands ───────────────────────────────────────────
            "agents" -> {
                addLine("All agents (${projectAgents.size}):", LineType.INFO)
                projectAgents.forEach { a ->
                    val icon = when (a.status) {
                        AgentStatus.ONLINE  -> "✓"
                        AgentStatus.RUNNING -> "▶"
                        AgentStatus.OFFLINE -> "○"
                        AgentStatus.ERROR   -> "✗"
                    }
                    addLine("  $icon ${a.name.padEnd(16)} ${a.type.padEnd(10)} ${a.status.name}", LineType.OUTPUT)
                }
            }

            "agent" -> {
                val name = parts.getOrNull(1) ?: ""
                val agent = projectAgents.firstOrNull { it.name.lowercase().contains(name.lowercase()) }
                if (agent == null) { addLine("Agent not found: $name", LineType.ERROR); return }
                addLine("Agent: ${agent.name}", LineType.SUCCESS)
                addLine("  Type    : ${agent.type}", LineType.OUTPUT)
                addLine("  Status  : ${agent.status.name}", LineType.OUTPUT)
                addLine("  Tasks   : ${agent.tasksHandled}", LineType.OUTPUT)
                addLine("  Active  : ${agent.lastActive}", LineType.OUTPUT)
                addLine("  Info    : ${agent.description}", LineType.OUTPUT)
            }

            "start" -> {
                val name = parts.getOrNull(1) ?: ""
                val agent = projectAgents.firstOrNull { it.name.lowercase().contains(name.lowercase()) }
                if (agent == null) { addLine("Agent not found: $name", LineType.ERROR); return }
                addLine("[${timestamp()}] Starting ${agent.name}...", LineType.INFO)
                scope.launch { delay(500); addLine("[OK] ${agent.name} started", LineType.SUCCESS); listState.animateScrollToItem(lines.size - 1) }
                return
            }

            "stop" -> {
                val name = parts.getOrNull(1) ?: ""
                val agent = projectAgents.firstOrNull { it.name.lowercase().contains(name.lowercase()) }
                if (agent == null) { addLine("Agent not found: $name", LineType.ERROR); return }
                addLine("[${timestamp()}] Stopping ${agent.name}...", LineType.INFO)
                scope.launch { delay(300); addLine("[OK] ${agent.name} stopped", LineType.SUCCESS); listState.animateScrollToItem(lines.size - 1) }
                return
            }

            // ── LLM commands ─────────────────────────────────────────────
            "model" -> {
                addLine("Active model: ${selectedLlmModel.value}", LineType.SUCCESS)
            }

            "models" -> {
                addLine("Available models:", LineType.INFO)
                listOf("Claude Sonnet","Claude Haiku","Claude Opus","GPT-4o","GPT-4o mini","Gemini Pro","Gemini Flash","Llama 3.3 70B")
                    .forEach { addLine("  ${if (it == selectedLlmModel.value) "▶" else "○"} $it", LineType.OUTPUT) }
            }

            "setmodel" -> {
                val name = parts.drop(1).joinToString(" ")
                if (name.isBlank()) { addLine("Usage: setmodel <model name>", LineType.ERROR); return }
                selectedLlmModel.value = name
                addLine("[OK] Model set to: $name", LineType.SUCCESS)
            }

            // ── MISC commands ─────────────────────────────────────────────
            "whoami" -> {
                addLine("Mode : $appMode", LineType.OUTPUT)
                when (appMode) {
                    "telegram" -> addLine("Token: ${botToken.take(12)}...", LineType.OUTPUT)
                    "server"   -> addLine("Server: ${vm.serverUrl.value}", LineType.OUTPUT)
                }
                addLine("Model: ${selectedLlmModel.value}", LineType.OUTPUT)
            }

            "sysinfo" -> {
                addLine("BlackBugsAI System Info:", LineType.INFO)
                addLine("  Version  : 1.1.0", LineType.OUTPUT)
                addLine("  Mode     : $appMode", LineType.OUTPUT)
                addLine("  Model    : ${selectedLlmModel.value}", LineType.OUTPUT)
                addLine("  Agents   : ${projectAgents.size} total, ${projectAgents.count { it.status == AgentStatus.ONLINE || it.status == AgentStatus.RUNNING }} online", LineType.OUTPUT)
                addLine("  Chats    : ${knownChatIds.size} known", LineType.OUTPUT)
                addLine("  Memory   : ${knownChatIdsChatMemory.size} entries", LineType.OUTPUT)
                addLine("  Android  : ${android.os.Build.VERSION.RELEASE} (API ${android.os.Build.VERSION.SDK_INT})", LineType.OUTPUT)
                addLine("  Device   : ${android.os.Build.MODEL}", LineType.OUTPUT)
            }

            "" -> { /* ignore empty */ }

            else -> {
                addLine("ERROR: Unknown command '${parts[0]}'. Type 'help'.", LineType.ERROR)
            }
        }

        scope.launch {
            delay(50)
            if (lines.isNotEmpty()) listState.animateScrollToItem(lines.size - 1)
        }
    }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(BgDeep)
    ) {
        // ── Header ─────────────────────────────────────────────────────────
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .background(BgDark)
                .padding(horizontal = 16.dp, vertical = 10.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.SpaceBetween
        ) {
            Text(
                "TERMINAL",
                fontSize   = 18.sp,
                fontWeight = FontWeight.Bold,
                color      = NeonGreen,
                letterSpacing = 3.sp,
                fontFamily = FontFamily.Monospace
            )
            Row(horizontalArrangement = Arrangement.spacedBy(4.dp)) {
                listOf(NeonPink, NeonYellow, NeonGreen).forEach { c ->
                    Box(
                        modifier = Modifier
                            .size(10.dp)
                            .background(c, androidx.compose.foundation.shape.CircleShape)
                            .neonGlow(c, 4.dp, 5.dp)
                    )
                }
            }
        }

        // ── Output area ────────────────────────────────────────────────────
        LazyColumn(
            state = listState,
            modifier = Modifier
                .weight(1f)
                .fillMaxWidth()
                .padding(horizontal = 12.dp, vertical = 8.dp),
            verticalArrangement = Arrangement.spacedBy(2.dp)
        ) {
            items(lines) { line ->
                val color = when (line.type) {
                    LineType.INPUT   -> NeonCyan
                    LineType.OUTPUT  -> TextPrimary
                    LineType.ERROR   -> NeonPink
                    LineType.INFO    -> TextSecondary
                    LineType.SUCCESS -> NeonGreen
                }
                Text(
                    text       = line.text,
                    color      = color,
                    fontSize   = 13.sp,
                    fontFamily = FontFamily.Monospace,
                    lineHeight = 18.sp
                )
            }
        }

        // ── Input bar ──────────────────────────────────────────────────────
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .background(BgDark)
                .padding(horizontal = 12.dp, vertical = 8.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            Text(">", color = NeonGreen, fontFamily = FontFamily.Monospace, fontSize = 16.sp)
            OutlinedTextField(
                value         = input,
                onValueChange = { input = it },
                modifier      = Modifier.weight(1f),
                singleLine    = true,
                placeholder   = { Text("Enter command…", color = TextSecondary, fontFamily = FontFamily.Monospace, fontSize = 13.sp) },
                colors = OutlinedTextFieldDefaults.colors(
                    focusedTextColor      = NeonGreen,
                    unfocusedTextColor    = NeonGreen,
                    cursorColor           = NeonGreen,
                    focusedBorderColor    = NeonGreen,
                    unfocusedBorderColor  = NeonGreen.copy(alpha = 0.3f),
                    focusedContainerColor    = BgDeep,
                    unfocusedContainerColor  = BgDeep
                ),
                textStyle = LocalTextStyle.current.copy(
                    fontFamily = FontFamily.Monospace,
                    fontSize   = 13.sp
                )
            )
            IconButton(
                onClick = {
                    val cmd = input.trim()
                    input = ""
                    executeCommand(cmd)
                },
                modifier = Modifier
                    .background(NeonGreen.copy(alpha = 0.15f), androidx.compose.foundation.shape.CircleShape)
                    .neonGlow(NeonGreen, 4.dp, 20.dp)
            ) {
                Icon(Icons.AutoMirrored.Filled.Send, contentDescription = "Run", tint = NeonGreen)
            }
        }
    }
}
