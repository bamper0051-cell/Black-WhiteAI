package com.blackbugsai.app.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ExitToApp
import androidx.compose.material.icons.automirrored.filled.Send
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.blackbugsai.app.AppViewModel
import com.blackbugsai.app.ui.screens.selectedLlmModel
import com.blackbugsai.app.ui.theme.*
import kotlinx.coroutines.launch

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SettingsScreen(vm: AppViewModel, onDisconnect: () -> Unit) {
    val scope      = rememberCoroutineScope()
    val appMode    by vm.appMode.collectAsState()
    val botToken   by vm.botToken.collectAsState()
    val serverUrl  by vm.serverUrl.collectAsState()
    val adminChatId by vm.adminChatId.collectAsState()

    var showDisconnectDialog by remember { mutableStateOf(false) }
    var currentLlm           by selectedLlmModel
    var showLlmMenu          by remember { mutableStateOf(false) }

    // Admin chat ID editing
    var chatIdInput  by remember { mutableStateOf(if (adminChatId != 0L) adminChatId.toString() else "") }
    var chatIdSaved  by remember { mutableStateOf(false) }

    val llmModels = listOf(
        "Claude Sonnet" to "Anthropic",
        "Claude Haiku"  to "Anthropic",
        "Claude Opus"   to "Anthropic",
        "GPT-4o"        to "OpenAI",
        "GPT-4o mini"   to "OpenAI",
        "Gemini 2.0 Flash" to "Google",
        "Gemini 1.5 Pro"   to "Google",
        "Llama 3.3 70B"    to "Meta/Groq",
        "DeepSeek R1"      to "DeepSeek",
        "Grok 3"           to "xAI",
    )

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(BgDeep)
            .verticalScroll(rememberScrollState())
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        Text(
            "> НАСТРОЙКИ",
            color = NeonCyan, fontSize = 14.sp,
            fontWeight = FontWeight.Bold, fontFamily = FontFamily.Monospace
        )

        // ── Current mode ──────────────────────────────────────────────────────
        SettingsCard(NeonCyan) {
            Column(modifier = Modifier.padding(16.dp)) {
                Text("> ТЕКУЩИЙ РЕЖИМ", color = NeonCyan, fontSize = 11.sp,
                    fontFamily = FontFamily.Monospace, modifier = Modifier.padding(bottom = 12.dp))
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Icon(
                        if (appMode == "telegram") Icons.AutoMirrored.Filled.Send else Icons.Filled.Cloud,
                        contentDescription = null,
                        tint = if (appMode == "telegram") NeonCyan else NeonPurple,
                        modifier = Modifier.size(24.dp)
                    )
                    Spacer(Modifier.width(8.dp))
                    Column {
                        Text(
                            when {
                                appMode == "telegram" -> "TELEGRAM BOT"
                                appMode == "server" && botToken.isNotBlank() -> "SERVER + BOT"
                                else -> "SERVER"
                            },
                            color = if (appMode == "telegram") NeonCyan else NeonPurple,
                            fontSize = 16.sp, fontWeight = FontWeight.Bold,
                            fontFamily = FontFamily.Monospace
                        )
                        if (appMode == "server") {
                            Text(serverUrl, color = TextSecondary, fontSize = 11.sp,
                                fontFamily = FontFamily.Monospace)
                        }
                    }
                }
            }
        }

        // ── Admin Chat ID ─────────────────────────────────────────────────────
        SettingsCard(NeonGreen) {
            Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
                Text("> ADMIN CHAT ID", color = NeonGreen, fontSize = 11.sp,
                    fontFamily = FontFamily.Monospace)
                Text(
                    "Ваш Telegram Chat ID — нужен для отправки задач агентам через бота",
                    color = TextSecondary, fontSize = 11.sp
                )
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    OutlinedTextField(
                        value         = chatIdInput,
                        onValueChange = { chatIdInput = it.filter { c -> c.isDigit() }; chatIdSaved = false },
                        placeholder   = { Text("123456789", color = TextSecondary, fontSize = 12.sp) },
                        modifier      = Modifier.weight(1f),
                        singleLine    = true,
                        textStyle     = LocalTextStyle.current.copy(
                            color = TextPrimary, fontSize = 13.sp,
                            fontFamily = FontFamily.Monospace
                        ),
                        colors = OutlinedTextFieldDefaults.colors(
                            focusedBorderColor   = NeonGreen,
                            unfocusedBorderColor = NeonGreen.copy(alpha = 0.4f),
                            cursorColor          = NeonGreen
                        ),
                        shape = RoundedCornerShape(8.dp)
                    )
                    IconButton(
                        onClick = {
                            val id = chatIdInput.trim().toLongOrNull()
                            if (id != null) {
                                vm.saveAdminChatId(id)
                                chatIdSaved = true
                            }
                        },
                        modifier = Modifier
                            .size(44.dp)
                            .background(NeonGreen.copy(alpha = 0.2f), RoundedCornerShape(8.dp))
                            .border(1.dp, NeonGreen.copy(alpha = 0.5f), RoundedCornerShape(8.dp))
                    ) {
                        Icon(
                            if (chatIdSaved) Icons.Filled.Check else Icons.Filled.Save,
                            contentDescription = null,
                            tint = NeonGreen, modifier = Modifier.size(20.dp)
                        )
                    }
                }
                if (adminChatId != 0L) {
                    Text("Сохранено: $adminChatId", color = NeonGreen, fontSize = 11.sp,
                        fontFamily = FontFamily.Monospace)
                }
            }
        }

        // ── LLM model ─────────────────────────────────────────────────────────
        SettingsCard(NeonYellow) {
            Column(modifier = Modifier.padding(16.dp)) {
                Text("> ВЫБОР МОДЕЛИ AI", color = NeonYellow, fontSize = 11.sp,
                    fontFamily = FontFamily.Monospace, modifier = Modifier.padding(bottom = 12.dp))
                Row(verticalAlignment = Alignment.CenterVertically, modifier = Modifier.fillMaxWidth()) {
                    Column(modifier = Modifier.weight(1f)) {
                        Text("Активная модель", color = TextSecondary, fontSize = 11.sp,
                            fontFamily = FontFamily.Monospace)
                        Text(currentLlm, color = NeonYellow, fontSize = 14.sp,
                            fontWeight = FontWeight.Bold, fontFamily = FontFamily.Monospace)
                    }
                    Box {
                        OutlinedButton(
                            onClick = { showLlmMenu = true },
                            border  = androidx.compose.foundation.BorderStroke(1.dp, NeonYellow.copy(alpha = 0.6f)),
                            colors  = ButtonDefaults.outlinedButtonColors(contentColor = NeonYellow),
                            shape   = RoundedCornerShape(8.dp)
                        ) {
                            Icon(Icons.Filled.ExpandMore, null, modifier = Modifier.size(16.dp))
                            Spacer(Modifier.width(4.dp))
                            Text("СМЕНИТЬ", fontSize = 10.sp, fontFamily = FontFamily.Monospace)
                        }
                        DropdownMenu(
                            expanded        = showLlmMenu,
                            onDismissRequest = { showLlmMenu = false },
                            modifier        = Modifier.background(BgCard)
                        ) {
                            llmModels.forEach { (model, provider) ->
                                DropdownMenuItem(
                                    text = {
                                        Row(verticalAlignment = Alignment.CenterVertically) {
                                            Column(modifier = Modifier.weight(1f)) {
                                                Text(model,
                                                    color = if (model == currentLlm) NeonYellow else TextPrimary,
                                                    fontFamily = FontFamily.Monospace, fontSize = 13.sp)
                                                Text(provider, color = TextSecondary, fontSize = 10.sp,
                                                    fontFamily = FontFamily.Monospace)
                                            }
                                            if (model == currentLlm)
                                                Icon(Icons.Filled.Check, null,
                                                    tint = NeonYellow, modifier = Modifier.size(16.dp))
                                        }
                                    },
                                    onClick = { currentLlm = model; showLlmMenu = false }
                                )
                            }
                        }
                    }
                }
            }
        }

        // ── App info ──────────────────────────────────────────────────────────
        SettingsCard(NeonPurple) {
            Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                Text("> INFO", color = NeonPurple, fontSize = 11.sp,
                    fontFamily = FontFamily.Monospace, modifier = Modifier.padding(bottom = 8.dp))
                CfgRow("Версия",    "2.0.0")
                CfgRow("Платформа", "Android")
                CfgRow("UI",        "Jetpack Compose")
                CfgRow("Тема",      "Neon Dark Matrix")
            }
        }

        Spacer(Modifier.height(8.dp))

        // ── Disconnect ────────────────────────────────────────────────────────
        Button(
            onClick = { showDisconnectDialog = true },
            modifier = Modifier.fillMaxWidth().height(48.dp),
            colors = ButtonDefaults.buttonColors(
                containerColor = NeonPink.copy(alpha = 0.15f),
                contentColor   = NeonPink
            ),
            shape  = RoundedCornerShape(8.dp),
            border = androidx.compose.foundation.BorderStroke(1.dp, NeonPink.copy(alpha = 0.6f))
        ) {
            Icon(Icons.AutoMirrored.Filled.ExitToApp, null, modifier = Modifier.size(18.dp))
            Spacer(Modifier.width(8.dp))
            Text("ОТКЛЮЧИТЬСЯ", fontFamily = FontFamily.Monospace, fontWeight = FontWeight.Bold)
        }
    }

    if (showDisconnectDialog) {
        AlertDialog(
            onDismissRequest = { showDisconnectDialog = false },
            containerColor   = BgDark,
            title  = { Text("ОТКЛЮЧИТЬ?", color = NeonPink,
                fontFamily = FontFamily.Monospace, fontWeight = FontWeight.Bold) },
            text   = { Text("Все сохранённые данные будут удалены.",
                color = TextSecondary, fontFamily = FontFamily.Monospace, fontSize = 13.sp) },
            confirmButton = {
                TextButton(onClick = {
                    showDisconnectDialog = false
                    vm.disconnect()
                    onDisconnect()
                }) {
                    Text("ОТКЛЮЧИТЬ", color = NeonPink, fontFamily = FontFamily.Monospace)
                }
            },
            dismissButton = {
                TextButton(onClick = { showDisconnectDialog = false }) {
                    Text("ОТМЕНА", color = TextSecondary, fontFamily = FontFamily.Monospace)
                }
            }
        )
    }
}

@Composable
private fun SettingsCard(
    color: androidx.compose.ui.graphics.Color = NeonCyan,
    content: @Composable () -> Unit
) {
    Box(
        modifier = Modifier
            .fillMaxWidth()
            .background(BgCard, RoundedCornerShape(12.dp))
            .border(1.dp, color.copy(alpha = 0.5f), RoundedCornerShape(12.dp))
    ) { content() }
}

@Composable
private fun CfgRow(label: String, value: String) {
    Row(
        modifier = Modifier.fillMaxWidth().padding(vertical = 3.dp),
        horizontalArrangement = Arrangement.SpaceBetween
    ) {
        Text(label, color = TextSecondary, fontSize = 12.sp, fontFamily = FontFamily.Monospace)
        Text(value, color = TextPrimary,   fontSize = 12.sp, fontFamily = FontFamily.Monospace)
    }
}
