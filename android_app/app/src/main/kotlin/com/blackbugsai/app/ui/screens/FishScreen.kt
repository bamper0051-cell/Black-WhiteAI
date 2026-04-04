package com.blackbugsai.app.ui.screens

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalClipboardManager
import androidx.compose.ui.text.AnnotatedString
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.window.Dialog
import com.blackbugsai.app.AppViewModel
import com.blackbugsai.app.ui.theme.*
import kotlinx.coroutines.launch

@Composable
fun FishScreen(vm: AppViewModel) {
    val scope     = rememberCoroutineScope()
    val appMode   by vm.appMode.collectAsState()
    val api       = vm.serverApi
    val clipboard = LocalClipboardManager.current

    // Tunnel state
    var selectedProvider by remember { mutableStateOf("cloudflared") }
    var tunnelUrl        by remember { mutableStateOf("") }
    var loading          by remember { mutableStateOf(false) }
    var statusMsg        by remember { mutableStateOf("") }

    // Shell output / dialog
    var shellOutput by remember { mutableStateOf("") }
    var showDialog  by remember { mutableStateOf(false) }
    var dialogTitle by remember { mutableStateOf("") }

    val tunnelActive = tunnelUrl.isNotBlank()

    val tunnelProviders = listOf("cloudflared", "bore", "serveo")

    // On mount in server mode: check if tunnel already running
    LaunchedEffect(appMode) {
        if (appMode == "server") {
            val result = try { api?.shell("pgrep -a cloudflared 2>/dev/null | head -1 || echo ''") } catch (_: Exception) { null }
            if (result != null && result.stdout.contains("cloudflared")) {
                // tunnel might be running; leave url blank but don't error
            }
        }
    }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(BgDeep)
    ) {
        // ── Header ────────────────────────────────────────────────────────────
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .background(BgDark)
                .padding(horizontal = 16.dp, vertical = 12.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Icon(
                Icons.Filled.Phishing, contentDescription = null,
                tint = NeonPink, modifier = Modifier.size(20.dp)
            )
            Spacer(modifier = Modifier.width(8.dp))
            Text(
                "🎣 FISH MODULE", color = NeonPink, fontSize = 15.sp,
                fontWeight = FontWeight.Bold, fontFamily = FontFamily.Monospace,
                modifier = Modifier.weight(1f)
            )
            Box(
                modifier = Modifier
                    .background(
                        if (appMode == "server") NeonGreen.copy(alpha = 0.15f) else NeonPink.copy(alpha = 0.15f),
                        RoundedCornerShape(6.dp)
                    )
                    .border(
                        1.dp,
                        if (appMode == "server") NeonGreen.copy(alpha = 0.5f) else NeonPink.copy(alpha = 0.5f),
                        RoundedCornerShape(6.dp)
                    )
                    .padding(horizontal = 8.dp, vertical = 2.dp)
            ) {
                Text(
                    if (appMode == "server") "SERVER" else "OFFLINE",
                    color = if (appMode == "server") NeonGreen else NeonPink,
                    fontSize = 9.sp, fontFamily = FontFamily.Monospace, fontWeight = FontWeight.Bold
                )
            }
        }

        Column(
            modifier = Modifier
                .fillMaxSize()
                .verticalScroll(rememberScrollState())
                .padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp)
        ) {

            // ── 2. Mode check card ────────────────────────────────────────────
            if (appMode != "server") {
                NeonCard(modifier = Modifier.fillMaxWidth(), borderColor = NeonPink) {
                    Row(modifier = Modifier.padding(16.dp), verticalAlignment = Alignment.CenterVertically) {
                        Icon(
                            Icons.Filled.ErrorOutline, contentDescription = null,
                            tint = NeonPink, modifier = Modifier.size(22.dp)
                        )
                        Spacer(modifier = Modifier.width(12.dp))
                        Column {
                            Text(
                                "Требуется подключение к серверу",
                                color = NeonPink, fontWeight = FontWeight.Bold,
                                fontFamily = FontFamily.Monospace, fontSize = 13.sp
                            )
                            Text(
                                "Перейдите в настройки и подключитесь к серверу для использования Fish-модуля.",
                                color = TextSecondary, fontSize = 11.sp,
                                fontFamily = FontFamily.Monospace, lineHeight = 15.sp
                            )
                        }
                    }
                }
            }

            // ── 3. Tunnel control card ────────────────────────────────────────
            NeonCard(modifier = Modifier.fillMaxWidth(), borderColor = NeonCyan) {
                Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
                    // Title
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Icon(Icons.Filled.Link, contentDescription = null,
                            tint = NeonCyan, modifier = Modifier.size(16.dp))
                        Spacer(modifier = Modifier.width(8.dp))
                        Text("ТУННЕЛЬ", color = NeonCyan, fontWeight = FontWeight.Bold,
                            fontFamily = FontFamily.Monospace, fontSize = 12.sp,
                            letterSpacing = 1.sp)
                    }

                    HorizontalDivider(color = NeonCyan.copy(alpha = 0.3f))

                    // Status row
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Box(
                            modifier = Modifier.size(10.dp).clip(CircleShape)
                                .background(if (tunnelActive) NeonGreen else TextSecondary.copy(alpha = 0.5f))
                        )
                        Spacer(modifier = Modifier.width(8.dp))
                        if (tunnelActive) {
                            Text(tunnelUrl, color = NeonGreen, fontSize = 11.sp,
                                fontFamily = FontFamily.Monospace, modifier = Modifier.weight(1f))
                            IconButton(
                                onClick = { clipboard.setText(AnnotatedString(tunnelUrl)) },
                                modifier = Modifier.size(30.dp)
                            ) {
                                Icon(Icons.Filled.ContentCopy, contentDescription = "Копировать",
                                    tint = NeonGreen, modifier = Modifier.size(16.dp))
                            }
                        } else {
                            Text("Неактивен", color = TextSecondary.copy(alpha = 0.7f),
                                fontSize = 11.sp, fontFamily = FontFamily.Monospace,
                                modifier = Modifier.weight(1f))
                        }
                    }

                    // Provider selector
                    Text("Провайдер:", color = TextSecondary, fontSize = 10.sp,
                        fontFamily = FontFamily.Monospace)
                    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        tunnelProviders.forEach { provider ->
                            val selected = selectedProvider == provider
                            Surface(
                                onClick = { if (!tunnelActive && !loading) selectedProvider = provider },
                                shape   = RoundedCornerShape(6.dp),
                                color   = if (selected) NeonCyan.copy(alpha = 0.2f) else BgDeep,
                                border  = androidx.compose.foundation.BorderStroke(
                                    1.dp, if (selected) NeonCyan else TextSecondary.copy(alpha = 0.4f)
                                )
                            ) {
                                Text(
                                    provider,
                                    modifier = Modifier.padding(horizontal = 10.dp, vertical = 5.dp),
                                    color    = if (selected) NeonCyan else TextSecondary,
                                    fontSize = 10.sp, fontFamily = FontFamily.Monospace,
                                    fontWeight = if (selected) FontWeight.Bold else FontWeight.Normal
                                )
                            }
                        }
                    }

                    // Status/error message
                    AnimatedVisibility(statusMsg.isNotEmpty()) {
                        Text(statusMsg,
                            color = if (statusMsg.startsWith("Ошибка")) NeonPink else NeonGreen,
                            fontSize = 11.sp, fontFamily = FontFamily.Monospace)
                    }

                    // Control buttons
                    Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                        // ЗАПУСТИТЬ
                        NeonButton(
                            onClick = {
                                scope.launch {
                                    loading = true; statusMsg = ""
                                    val result = try { api?.startTunnel(selectedProvider) } catch (_: Exception) { null }
                                    if (result != null && result.ok) {
                                        tunnelUrl = result.url
                                        statusMsg = ""
                                    } else {
                                        statusMsg = result?.error?.ifBlank { "Ошибка запуска туннеля" }
                                            ?: "Не удалось подключиться к серверу"
                                    }
                                    loading = false
                                }
                            },
                            modifier    = Modifier.weight(1f).height(40.dp),
                            borderColor = NeonGreen,
                            enabled     = !tunnelActive && !loading && appMode == "server"
                        ) {
                            if (loading && !tunnelActive) {
                                CircularProgressIndicator(modifier = Modifier.size(16.dp),
                                    color = NeonGreen, strokeWidth = 2.dp)
                            } else {
                                Icon(Icons.Filled.PlayArrow, null, modifier = Modifier.size(14.dp))
                                Spacer(modifier = Modifier.width(4.dp))
                                Text("ЗАПУСТИТЬ", fontSize = 10.sp, fontFamily = FontFamily.Monospace,
                                    fontWeight = FontWeight.Bold)
                            }
                        }

                        // ОСТАНОВИТЬ
                        NeonButton(
                            onClick = {
                                scope.launch {
                                    loading = true; statusMsg = ""
                                    val ok = try { api?.stopTunnel() ?: false } catch (_: Exception) { false }
                                    if (ok) {
                                        tunnelUrl = ""
                                    } else {
                                        statusMsg = "Ошибка остановки туннеля"
                                    }
                                    loading = false
                                }
                            },
                            modifier    = Modifier.weight(1f).height(40.dp),
                            borderColor = NeonPink,
                            enabled     = tunnelActive && !loading && appMode == "server"
                        ) {
                            if (loading && tunnelActive) {
                                CircularProgressIndicator(modifier = Modifier.size(16.dp),
                                    color = NeonPink, strokeWidth = 2.dp)
                            } else {
                                Icon(Icons.Filled.Stop, null, modifier = Modifier.size(14.dp))
                                Spacer(modifier = Modifier.width(4.dp))
                                Text("ОСТАНОВИТЬ", fontSize = 10.sp, fontFamily = FontFamily.Monospace,
                                    fontWeight = FontWeight.Bold)
                            }
                        }
                    }
                }
            }

            // ── 4. Quick commands card ────────────────────────────────────────
            NeonCard(modifier = Modifier.fillMaxWidth(), borderColor = NeonPurple) {
                Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Icon(Icons.Filled.Build, contentDescription = null,
                            tint = NeonPurple, modifier = Modifier.size(16.dp))
                        Spacer(modifier = Modifier.width(8.dp))
                        Text("ИНСТРУМЕНТЫ", color = NeonPurple, fontWeight = FontWeight.Bold,
                            fontFamily = FontFamily.Monospace, fontSize = 12.sp, letterSpacing = 1.sp)
                    }
                    HorizontalDivider(color = NeonPurple.copy(alpha = 0.3f))

                    // 2x2 grid layout
                    val quickTools = listOf(
                        Triple("📊 Статистика", "python3 fish_utils.py stats 2>/dev/null || echo 'N/A'", "Статистика"),
                        Triple("🌐 Страницы",   "ls -la fish_pages/ 2>/dev/null | head -20",              "Страницы"),
                        Triple("📝 Логи",        "tail -30 fish.log 2>/dev/null || echo 'No log'",         "Логи"),
                        Triple("🗑 Очистить",    "python3 -c \"import fish_db; fish_db.clear_all()\" 2>/dev/null", "Очистка")
                    )

                    // Row 1
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.spacedBy(8.dp)
                    ) {
                        quickTools.take(2).forEach { (label, cmd, title) ->
                            OutlinedButton(
                                onClick = {
                                    if (appMode != "server") return@OutlinedButton
                                    scope.launch {
                                        loading = true
                                        val res = try { api?.shell(cmd) } catch (_: Exception) { null }
                                        shellOutput = if (res != null) {
                                            (res.stdout + if (res.stderr.isNotBlank()) "\n[stderr]\n${res.stderr}" else "")
                                                .ifBlank { "Exit: ${res.exitCode}" }
                                        } else "Ошибка соединения с сервером"
                                        dialogTitle = title
                                        showDialog  = true
                                        loading     = false
                                    }
                                },
                                modifier = Modifier.weight(1f),
                                colors   = ButtonDefaults.outlinedButtonColors(contentColor = NeonPurple),
                                border   = androidx.compose.foundation.BorderStroke(1.dp, NeonPurple.copy(alpha = 0.5f)),
                                shape    = RoundedCornerShape(8.dp),
                                enabled  = appMode == "server" && !loading,
                                contentPadding = PaddingValues(horizontal = 8.dp, vertical = 10.dp)
                            ) {
                                Text(label, fontSize = 11.sp, fontFamily = FontFamily.Monospace)
                            }
                        }
                    }
                    // Row 2
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.spacedBy(8.dp)
                    ) {
                        quickTools.drop(2).forEach { (label, cmd, title) ->
                            OutlinedButton(
                                onClick = {
                                    if (appMode != "server") return@OutlinedButton
                                    scope.launch {
                                        loading = true
                                        val res = try { api?.shell(cmd) } catch (_: Exception) { null }
                                        shellOutput = if (res != null) {
                                            (res.stdout + if (res.stderr.isNotBlank()) "\n[stderr]\n${res.stderr}" else "")
                                                .ifBlank { "Exit: ${res.exitCode}" }
                                        } else "Ошибка соединения с сервером"
                                        dialogTitle = title
                                        showDialog  = true
                                        loading     = false
                                    }
                                },
                                modifier = Modifier.weight(1f),
                                colors   = ButtonDefaults.outlinedButtonColors(contentColor = NeonPurple),
                                border   = androidx.compose.foundation.BorderStroke(1.dp, NeonPurple.copy(alpha = 0.5f)),
                                shape    = RoundedCornerShape(8.dp),
                                enabled  = appMode == "server" && !loading,
                                contentPadding = PaddingValues(horizontal = 8.dp, vertical = 10.dp)
                            ) {
                                Text(label, fontSize = 11.sp, fontFamily = FontFamily.Monospace)
                            }
                        }
                    }

                    if (loading) {
                        Box(modifier = Modifier.fillMaxWidth().padding(4.dp), contentAlignment = Alignment.Center) {
                            CircularProgressIndicator(
                                modifier = Modifier.size(20.dp),
                                color = NeonPurple, strokeWidth = 2.dp
                            )
                        }
                    }
                }
            }

            // ── 5. Stats card ─────────────────────────────────────────────────
            FishStatsCard(appMode = appMode, api = api, scope = scope)

            Spacer(modifier = Modifier.height(8.dp))
        }
    }

    // ── Shell output dialog ───────────────────────────────────────────────────
    if (showDialog) {
        Dialog(onDismissRequest = { showDialog = false }) {
            Surface(
                shape = RoundedCornerShape(14.dp),
                color = BgDark,
                border = androidx.compose.foundation.BorderStroke(1.dp, NeonPurple.copy(alpha = 0.5f))
            ) {
                Column(modifier = Modifier.padding(20.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Icon(Icons.Filled.Terminal, contentDescription = null,
                            tint = NeonPurple, modifier = Modifier.size(18.dp))
                        Spacer(modifier = Modifier.width(8.dp))
                        Text(dialogTitle, color = NeonPurple, fontSize = 13.sp,
                            fontWeight = FontWeight.Bold, fontFamily = FontFamily.Monospace)
                    }
                    Box(
                        modifier = Modifier
                            .fillMaxWidth()
                            .background(BgDeep, RoundedCornerShape(8.dp))
                            .border(1.dp, NeonPurple.copy(alpha = 0.3f), RoundedCornerShape(8.dp))
                            .padding(12.dp)
                            .heightIn(max = 320.dp)
                    ) {
                        Text(
                            shellOutput.take(2000),
                            color = NeonGreen, fontSize = 10.sp,
                            fontFamily = FontFamily.Monospace, lineHeight = 15.sp
                        )
                    }
                    Row(horizontalArrangement = Arrangement.End, modifier = Modifier.fillMaxWidth()) {
                        TextButton(onClick = {
                            clipboard.setText(AnnotatedString(shellOutput))
                        }) {
                            Text("КОПИРОВАТЬ", color = NeonCyan, fontFamily = FontFamily.Monospace, fontSize = 11.sp)
                        }
                        Spacer(modifier = Modifier.width(8.dp))
                        TextButton(onClick = { showDialog = false }) {
                            Text("ЗАКРЫТЬ", color = NeonPurple, fontFamily = FontFamily.Monospace, fontSize = 11.sp)
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun FishStatsCard(
    appMode: String,
    api: com.blackbugsai.app.services.ServerApiService?,
    scope: kotlinx.coroutines.CoroutineScope
) {
    var statsText  by remember { mutableStateOf("") }
    var statsLoading by remember { mutableStateOf(false) }

    fun loadStats() {
        scope.launch {
            statsLoading = true
            val cmd = "python3 -c \"" +
                "import fish_db; d=fish_db.FishDB(); " +
                "visits=d.get_all_visits(); " +
                "print('Визиты:', len(visits)); " +
                "print('Кампании: N/A')" +
                "\" 2>/dev/null"
            val res = try { api?.shell(cmd) } catch (_: Exception) { null }
            statsText = if (appMode != "server") {
                "— — —"
            } else if (res != null) {
                res.stdout.ifBlank { res.stderr.ifBlank { "Exit: ${res.exitCode}" } }
            } else {
                "Ошибка соединения с сервером"
            }
            statsLoading = false
        }
    }

    NeonCard(modifier = Modifier.fillMaxWidth(), borderColor = NeonGreen) {
        Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Icon(Icons.Filled.BarChart, contentDescription = null,
                    tint = NeonGreen, modifier = Modifier.size(16.dp))
                Spacer(modifier = Modifier.width(8.dp))
                Text("СТАТИСТИКА", color = NeonGreen, fontWeight = FontWeight.Bold,
                    fontFamily = FontFamily.Monospace, fontSize = 12.sp, letterSpacing = 1.sp,
                    modifier = Modifier.weight(1f))
                IconButton(
                    onClick  = { loadStats() },
                    modifier = Modifier.size(28.dp),
                    enabled  = appMode == "server" && !statsLoading
                ) {
                    if (statsLoading) {
                        CircularProgressIndicator(modifier = Modifier.size(16.dp),
                            color = NeonGreen, strokeWidth = 2.dp)
                    } else {
                        Icon(Icons.Filled.Refresh, null, tint = NeonGreen, modifier = Modifier.size(16.dp))
                    }
                }
            }
            HorizontalDivider(color = NeonGreen.copy(alpha = 0.3f))

            if (appMode != "server") {
                Text("— — —", color = TextSecondary, fontSize = 12.sp, fontFamily = FontFamily.Monospace)
                Text("Подключитесь к серверу для просмотра статистики",
                    color = TextSecondary.copy(alpha = 0.6f), fontSize = 10.sp, fontFamily = FontFamily.Monospace)
            } else if (statsText.isBlank()) {
                Text("Нажмите кнопку обновления для загрузки статистики",
                    color = TextSecondary, fontSize = 11.sp, fontFamily = FontFamily.Monospace)
            } else {
                Text(statsText, color = NeonGreen, fontSize = 12.sp,
                    fontFamily = FontFamily.Monospace, lineHeight = 18.sp)
            }
        }
    }
}
