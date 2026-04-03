package com.blackbugsai.app.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
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
import com.blackbugsai.app.ui.theme.*

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SettingsScreen(vm: AppViewModel, onDisconnect: () -> Unit) {
    val appMode  by vm.appMode.collectAsState()
    val botToken by vm.botToken.collectAsState()
    val serverUrl by vm.serverUrl.collectAsState()
    val adminToken by vm.adminToken.collectAsState()

    var showDisconnectDialog by remember { mutableStateOf(false) }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(BgDeep)
            .verticalScroll(rememberScrollState())
            .padding(16.dp)
    ) {
        // Header
        Text(
            "> НАСТРОЙКИ",
            color = NeonCyan,
            fontSize = 14.sp,
            fontWeight = FontWeight.Bold,
            fontFamily = FontFamily.Monospace,
            modifier = Modifier.padding(bottom = 20.dp)
        )

        // Current mode card
        NeonCard(glowColor = NeonCyan) {
            Column(modifier = Modifier.padding(16.dp)) {
                Text(
                    "> ТЕКУЩИЙ РЕЖИМ",
                    color = NeonCyan,
                    fontSize = 11.sp,
                    fontFamily = FontFamily.Monospace,
                    modifier = Modifier.padding(bottom = 12.dp)
                )
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Icon(
                        if (appMode == "telegram") Icons.Filled.Send else Icons.Filled.Cloud,
                        contentDescription = null,
                        tint = if (appMode == "telegram") NeonCyan else NeonPurple,
                        modifier = Modifier.size(24.dp)
                    )
                    Spacer(modifier = Modifier.width(8.dp))
                    Text(
                        if (appMode == "telegram") "TELEGRAM BOT" else "SERVER",
                        color = if (appMode == "telegram") NeonCyan else NeonPurple,
                        fontSize = 16.sp,
                        fontWeight = FontWeight.Bold,
                        fontFamily = FontFamily.Monospace
                    )
                }
            }
        }

        Spacer(modifier = Modifier.height(12.dp))

        // Config card
        NeonCard(glowColor = NeonPurple) {
            Column(modifier = Modifier.padding(16.dp)) {
                Text(
                    "> КОНФИГУРАЦИЯ",
                    color = NeonPurple,
                    fontSize = 11.sp,
                    fontFamily = FontFamily.Monospace,
                    modifier = Modifier.padding(bottom = 12.dp)
                )
                if (appMode == "telegram") {
                    ConfigRow("Токен", "•".repeat(minOf(botToken.length, 8)) + botToken.takeLast(6))
                } else {
                    ConfigRow("Сервер", serverUrl)
                    ConfigRow("Токен", "•".repeat(8))
                }
            }
        }

        Spacer(modifier = Modifier.height(12.dp))

        // App info
        NeonCard(glowColor = NeonGreen) {
            Column(modifier = Modifier.padding(16.dp)) {
                Text(
                    "> INFO",
                    color = NeonGreen,
                    fontSize = 11.sp,
                    fontFamily = FontFamily.Monospace,
                    modifier = Modifier.padding(bottom = 12.dp)
                )
                ConfigRow("Версия", "1.1.0")
                ConfigRow("Платформа", "Android")
                ConfigRow("UI", "Jetpack Compose")
                ConfigRow("Тема", "Neon Dark")
            }
        }

        Spacer(modifier = Modifier.height(24.dp))

        // Disconnect
        Button(
            onClick = { showDisconnectDialog = true },
            modifier = Modifier
                .fillMaxWidth()
                .height(48.dp),
            colors = ButtonDefaults.buttonColors(
                containerColor = NeonPink.copy(alpha = 0.15f),
                contentColor = NeonPink
            ),
            shape = RoundedCornerShape(8.dp),
            border = androidx.compose.foundation.BorderStroke(1.dp, NeonPink.copy(alpha = 0.6f))
        ) {
            Icon(Icons.Filled.ExitToApp, contentDescription = null, modifier = Modifier.size(18.dp))
            Spacer(modifier = Modifier.width(8.dp))
            Text("ОТКЛЮЧИТЬСЯ", fontFamily = FontFamily.Monospace, fontWeight = FontWeight.Bold)
        }
    }

    if (showDisconnectDialog) {
        AlertDialog(
            onDismissRequest = { showDisconnectDialog = false },
            containerColor = BgDark,
            title = {
                Text("ОТКЛЮЧИТЬ?", color = NeonPink, fontFamily = FontFamily.Monospace, fontWeight = FontWeight.Bold)
            },
            text = {
                Text(
                    "Все сохранённые данные будут удалены.",
                    color = TextSecondary,
                    fontFamily = FontFamily.Monospace,
                    fontSize = 13.sp
                )
            },
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
private fun ConfigRow(label: String, value: String) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .padding(vertical = 4.dp),
        horizontalArrangement = Arrangement.SpaceBetween
    ) {
        Text(label, color = TextSecondary, fontSize = 12.sp, fontFamily = FontFamily.Monospace)
        Text(value, color = TextPrimary, fontSize = 12.sp, fontFamily = FontFamily.Monospace)
    }
}

@Composable
private fun NeonCard(
    glowColor: androidx.compose.ui.graphics.Color = NeonCyan,
    content: @Composable () -> Unit
) {
    Box(
        modifier = Modifier
            .fillMaxWidth()
            .background(BgCard, RoundedCornerShape(12.dp))
            .border(1.dp, glowColor.copy(alpha = 0.5f), RoundedCornerShape(12.dp))
    ) {
        content()
    }
}
