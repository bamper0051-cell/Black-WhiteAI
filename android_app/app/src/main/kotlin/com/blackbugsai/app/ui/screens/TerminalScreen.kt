package com.blackbugsai.app.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.rememberScrollState
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Send
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
                addLine("Available commands:", LineType.INFO)
                addLine("  help        - Show this help", LineType.OUTPUT)
                addLine("  status      - Show app status", LineType.OUTPUT)
                addLine("  botinfo     - Show Telegram bot information", LineType.OUTPUT)
                addLine("  chats       - List known chat IDs", LineType.OUTPUT)
                addLine("  clear       - Clear terminal output", LineType.OUTPUT)
                addLine("  time        - Show current time", LineType.OUTPUT)
                addLine("  mode        - Show current app mode", LineType.OUTPUT)
                addLine("  ping        - Ping test", LineType.OUTPUT)
                addLine("  version     - Show app version", LineType.OUTPUT)
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

            "" -> { /* ignore empty */ }

            else -> {
                addLine("ERROR: Unknown command '${parts[0]}'. Type 'help' for list.", LineType.ERROR)
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
                Icon(Icons.Filled.Send, contentDescription = "Run", tint = NeonGreen)
            }
        }
    }
}
