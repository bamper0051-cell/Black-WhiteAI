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
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.blackbugsai.app.AppViewModel
import com.blackbugsai.app.services.ServerApiService
import com.blackbugsai.app.ui.theme.*
import kotlinx.coroutines.launch

// ── LLM Provider data model ───────────────────────────────────────────────────
data class LlmProvider(
    val id: String,
    val name: String,
    val models: List<String>,
    val isFree: Boolean = false
)

val llmProviders = listOf(
    LlmProvider("groq",       "Groq",          listOf("llama-3.3-70b-versatile", "llama-3.1-8b-instant", "gemma2-9b-it"), isFree = true),
    LlmProvider("cerebras",   "Cerebras",       listOf("llama-3.3-70b", "qwen-3-32b"), isFree = true),
    LlmProvider("gemini",     "Google Gemini",  listOf("gemini-2.0-flash", "gemini-1.5-pro", "gemini-1.5-flash")),
    LlmProvider("openai",     "OpenAI",         listOf("gpt-4o-mini", "gpt-4o", "gpt-4.1-mini")),
    LlmProvider("claude",     "Anthropic",      listOf("claude-sonnet-4-6", "claude-haiku-4-5-20251001", "claude-opus-4-6")),
    LlmProvider("deepseek",   "DeepSeek",       listOf("deepseek-chat", "deepseek-coder", "deepseek-r1")),
    LlmProvider("mistral",    "Mistral",        listOf("mistral-small-latest", "codestral-latest", "mistral-large-latest")),
    LlmProvider("openrouter", "OpenRouter",     listOf("meta-llama/llama-3.3-70b-instruct:free", "deepseek/deepseek-r1:free", "google/gemini-2.0-flash-001"), isFree = true),
    LlmProvider("together",   "Together AI",    listOf("meta-llama/Llama-3.3-70B-Instruct-Turbo", "deepseek-ai/DeepSeek-R1")),
    LlmProvider("xai",        "xAI / Grok",    listOf("grok-3-mini", "grok-3")),
    LlmProvider("perplexity", "Perplexity",    listOf("sonar", "sonar-pro")),
    LlmProvider("ollama",     "Ollama (local)", listOf("llama3.2", "codellama", "mistral"), isFree = true),
)

// ── Agent role model ──────────────────────────────────────────────────────────
data class AgentRole(
    val key: String,
    val label: String,
    val envPrefix: String
)

val agentRoles = listOf(
    AgentRole("chat",  "Чат / Ассистент",  "LLM"),
    AgentRole("code",  "Кодер / CODER3",   "CODE"),
    AgentRole("agent", "Агент NEO/MATRIX", "AGENT"),
)

// ── Default selections ────────────────────────────────────────────────────────
private val defaultProvider = llmProviders.first()
private fun defaultModel(provider: LlmProvider) = provider.models.first()

// ── Role card accent colors ───────────────────────────────────────────────────
private val roleColors = mapOf(
    "chat"  to NeonCyan,
    "code"  to NeonGreen,
    "agent" to NeonPurple
)

// ── LlmScreen ─────────────────────────────────────────────────────────────────
@Composable
fun LlmScreen(vm: AppViewModel) {
    val scope   = rememberCoroutineScope()
    val appMode by vm.appMode.collectAsState()
    val api     = vm.serverApi

    // ── Server provider status ────────────────────────────────────────────────
    var providerStatus by remember { mutableStateOf<ServerApiService.ProviderStatus?>(null) }
    var statusLoading  by remember { mutableStateOf(false) }

    // ── Per-role state: provider + model ──────────────────────────────────────
    var chatProvider  by remember { mutableStateOf(defaultProvider) }
    var chatModel     by remember { mutableStateOf(defaultModel(defaultProvider)) }
    var codeProvider  by remember { mutableStateOf(defaultProvider) }
    var codeModel     by remember { mutableStateOf(defaultModel(defaultProvider)) }
    var agentProvider by remember { mutableStateOf(defaultProvider) }
    var agentModel    by remember { mutableStateOf(defaultModel(defaultProvider)) }

    // ── Apply result state ────────────────────────────────────────────────────
    var applyLoading by remember { mutableStateOf(false) }
    var applyResult  by remember { mutableStateOf("") }
    var applySuccess by remember { mutableStateOf(false) }

    // ── Load provider status on entry (server mode only) ──────────────────────
    LaunchedEffect(appMode, api) {
        if (appMode == "server" && api != null) {
            statusLoading  = true
            providerStatus = try { api.getProviderStatus() } catch (_: Exception) { null }
            statusLoading  = false
        }
    }

    fun resetToDefaults() {
        chatProvider  = defaultProvider
        chatModel     = defaultModel(defaultProvider)
        codeProvider  = defaultProvider
        codeModel     = defaultModel(defaultProvider)
        agentProvider = defaultProvider
        agentModel    = defaultModel(defaultProvider)
        applyResult   = ""
    }

    fun buildConfigMap(): Map<String, String> = mapOf(
        "${agentRoles[0].envPrefix}_PROVIDER" to chatProvider.id,
        "${agentRoles[0].envPrefix}_MODEL"    to chatModel,
        "${agentRoles[1].envPrefix}_PROVIDER" to codeProvider.id,
        "${agentRoles[1].envPrefix}_MODEL"    to codeModel,
        "${agentRoles[2].envPrefix}_PROVIDER" to agentProvider.id,
        "${agentRoles[2].envPrefix}_MODEL"    to agentModel,
    )

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(BgDeep)
            .verticalScroll(rememberScrollState())
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {

        // ── Header ────────────────────────────────────────────────────────────
        Row(
            verticalAlignment     = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(10.dp)
        ) {
            Icon(
                imageVector        = Icons.Filled.Psychology,
                contentDescription = null,
                tint               = NeonPurple,
                modifier           = Modifier.size(22.dp)
            )
            Text(
                text       = "LLM КОНФИГУРАЦИЯ",
                color      = NeonPurple,
                fontSize   = 16.sp,
                fontWeight = FontWeight.Bold,
                fontFamily = FontFamily.Monospace,
                letterSpacing = 1.sp
            )
        }

        // ── Provider status card ──────────────────────────────────────────────
        if (appMode == "server") {
            NeonCard(modifier = Modifier.fillMaxWidth(), borderColor = NeonCyan) {
                Column(
                    modifier            = Modifier.padding(16.dp),
                    verticalArrangement = Arrangement.spacedBy(10.dp)
                ) {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Icon(
                            imageVector        = Icons.Filled.AutoAwesome,
                            contentDescription = null,
                            tint               = NeonCyan,
                            modifier           = Modifier.size(16.dp)
                        )
                        Spacer(modifier = Modifier.width(8.dp))
                        Text(
                            text       = "СТАТУС ПРОВАЙДЕРОВ",
                            color      = NeonCyan,
                            fontWeight = FontWeight.Bold,
                            fontFamily = FontFamily.Monospace,
                            fontSize   = 12.sp,
                            modifier   = Modifier.weight(1f)
                        )
                        // Refresh button
                        IconButton(
                            onClick = {
                                scope.launch {
                                    statusLoading  = true
                                    providerStatus = try { api?.getProviderStatus() } catch (_: Exception) { null }
                                    statusLoading  = false
                                }
                            },
                            modifier = Modifier.size(32.dp)
                        ) {
                            Icon(
                                imageVector        = Icons.Filled.Refresh,
                                contentDescription = "Обновить",
                                tint               = NeonCyan,
                                modifier           = Modifier.size(18.dp)
                            )
                        }
                    }

                    HorizontalDivider(color = NeonCyan.copy(alpha = 0.3f))

                    when {
                        statusLoading -> {
                            Box(
                                modifier         = Modifier
                                    .fillMaxWidth()
                                    .padding(vertical = 8.dp),
                                contentAlignment = Alignment.Center
                            ) {
                                Row(
                                    verticalAlignment     = Alignment.CenterVertically,
                                    horizontalArrangement = Arrangement.spacedBy(10.dp)
                                ) {
                                    CircularProgressIndicator(
                                        color       = NeonCyan,
                                        modifier    = Modifier.size(20.dp),
                                        strokeWidth = 2.dp
                                    )
                                    Text(
                                        text       = "Загрузка...",
                                        color      = TextSecondary,
                                        fontSize   = 12.sp,
                                        fontFamily = FontFamily.Monospace
                                    )
                                }
                            }
                        }
                        providerStatus != null -> {
                            StatusInfoRow("Активный LLM",    providerStatus!!.activeLlm,   NeonGreen)
                            StatusInfoRow("Лучший LLM",      providerStatus!!.bestLlm,      NeonCyan)
                            StatusInfoRow("Image Provider",  providerStatus!!.activeImage,  NeonPurple)
                        }
                        else -> {
                            Row(
                                verticalAlignment = Alignment.CenterVertically,
                                horizontalArrangement = Arrangement.spacedBy(8.dp)
                            ) {
                                Icon(
                                    imageVector        = Icons.Filled.ErrorOutline,
                                    contentDescription = null,
                                    tint               = NeonPink,
                                    modifier           = Modifier.size(14.dp)
                                )
                                Text(
                                    text       = "Не удалось получить статус провайдеров",
                                    color      = NeonPink,
                                    fontSize   = 11.sp,
                                    fontFamily = FontFamily.Monospace
                                )
                            }
                        }
                    }
                }
            }
        } else {
            // Telegram mode info banner
            NeonCard(modifier = Modifier.fillMaxWidth(), borderColor = NeonYellow) {
                Row(
                    modifier          = Modifier.padding(16.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Icon(
                        imageVector        = Icons.Filled.Info,
                        contentDescription = null,
                        tint               = NeonYellow,
                        modifier           = Modifier.size(16.dp)
                    )
                    Spacer(modifier = Modifier.width(8.dp))
                    Text(
                        text       = "Для применения настроек LLM на сервере\nтребуется подключение к серверу.",
                        color      = NeonYellow,
                        fontSize   = 11.sp,
                        fontFamily = FontFamily.Monospace,
                        lineHeight = 16.sp
                    )
                }
            }
        }

        // ── Per-role configuration cards ──────────────────────────────────────

        // CHAT / Ассистент card
        RoleConfigCard(
            role           = agentRoles[0],
            accentColor    = roleColors["chat"] ?: NeonCyan,
            selectedProvider = chatProvider,
            selectedModel    = chatModel,
            onProviderChange = { p ->
                chatProvider = p
                chatModel    = p.models.first()
            },
            onModelChange    = { chatModel = it }
        )

        // CODE / CODER3 card
        RoleConfigCard(
            role             = agentRoles[1],
            accentColor      = roleColors["code"] ?: NeonGreen,
            selectedProvider = codeProvider,
            selectedModel    = codeModel,
            onProviderChange = { p ->
                codeProvider = p
                codeModel    = p.models.first()
            },
            onModelChange    = { codeModel = it }
        )

        // AGENT / NEO + MATRIX card
        RoleConfigCard(
            role             = agentRoles[2],
            accentColor      = roleColors["agent"] ?: NeonPurple,
            selectedProvider = agentProvider,
            selectedModel    = agentModel,
            onProviderChange = { p ->
                agentProvider = p
                agentModel    = p.models.first()
            },
            onModelChange    = { agentModel = it }
        )

        // ── Apply result message ──────────────────────────────────────────────
        if (applyResult.isNotEmpty()) {
            NeonCard(
                modifier    = Modifier.fillMaxWidth(),
                borderColor = if (applySuccess) NeonGreen else NeonPink
            ) {
                Row(
                    modifier          = Modifier.padding(12.dp),
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    Icon(
                        imageVector        = if (applySuccess) Icons.Filled.CheckCircle else Icons.Filled.ErrorOutline,
                        contentDescription = null,
                        tint               = if (applySuccess) NeonGreen else NeonPink,
                        modifier           = Modifier.size(16.dp)
                    )
                    Text(
                        text       = applyResult,
                        color      = if (applySuccess) NeonGreen else NeonPink,
                        fontSize   = 12.sp,
                        fontFamily = FontFamily.Monospace,
                        lineHeight = 16.sp
                    )
                }
            }
        }

        // ── Apply button ──────────────────────────────────────────────────────
        NeonButton(
            onClick = {
                if (appMode != "server") {
                    applyResult  = "Требуется подключение к серверу"
                    applySuccess = false
                    selectedLlmModel.value = "${chatProvider.id}/${chatModel}"
                    return@NeonButton
                }
                scope.launch {
                    applyLoading = true
                    applyResult  = ""
                    val configs = buildConfigMap()
                    val ok = try { api?.setLlmConfig(configs) ?: false } catch (_: Exception) { false }
                    applySuccess = ok
                    applyResult  = if (ok)
                        "OK — конфигурация обновлена на сервере"
                    else
                        "Ошибка — не удалось обновить конфигурацию"
                    if (ok) selectedLlmModel.value = "${chatProvider.id}/${chatModel}"
                    applyLoading = false
                }
            },
            modifier    = Modifier
                .fillMaxWidth()
                .height(50.dp),
            borderColor = NeonYellow,
            enabled     = !applyLoading
        ) {
            if (applyLoading) {
                CircularProgressIndicator(
                    modifier    = Modifier.size(20.dp),
                    color       = NeonYellow,
                    strokeWidth = 2.dp
                )
            } else {
                Icon(
                    imageVector        = Icons.Filled.Check,
                    contentDescription = null,
                    modifier           = Modifier.size(18.dp)
                )
                Spacer(modifier = Modifier.width(8.dp))
                Text(
                    text          = if (appMode == "server") "ПРИМЕНИТЬ НА СЕРВЕРЕ" else "СОХРАНИТЬ ЛОКАЛЬНО",
                    fontWeight    = FontWeight.Bold,
                    fontFamily    = FontFamily.Monospace,
                    letterSpacing = 1.sp
                )
            }
        }

        // ── Reset to defaults button ──────────────────────────────────────────
        NeonButton(
            onClick     = { resetToDefaults() },
            modifier    = Modifier
                .fillMaxWidth()
                .height(44.dp),
            borderColor = TextSecondary,
            enabled     = !applyLoading
        ) {
            Icon(
                imageVector        = Icons.Filled.RestartAlt,
                contentDescription = null,
                tint               = TextSecondary,
                modifier           = Modifier.size(16.dp)
            )
            Spacer(modifier = Modifier.width(8.dp))
            Text(
                text          = "СБРОСИТЬ К УМОЛЧАНИЯМ",
                fontWeight    = FontWeight.Normal,
                fontFamily    = FontFamily.Monospace,
                fontSize      = 12.sp,
                color         = TextSecondary,
                letterSpacing = 0.5.sp
            )
        }

        Spacer(modifier = Modifier.height(16.dp))
    }
}

// ── Per-role configuration card ───────────────────────────────────────────────
@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun RoleConfigCard(
    role: AgentRole,
    accentColor: Color,
    selectedProvider: LlmProvider,
    selectedModel: String,
    onProviderChange: (LlmProvider) -> Unit,
    onModelChange: (String) -> Unit
) {
    var providerMenuExpanded by remember { mutableStateOf(false) }
    var modelMenuExpanded    by remember { mutableStateOf(false) }

    NeonCard(modifier = Modifier.fillMaxWidth(), borderColor = accentColor) {
        Column(
            modifier            = Modifier.padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            // Card header
            Row(
                verticalAlignment     = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                Icon(
                    imageVector        = Icons.Filled.Memory,
                    contentDescription = null,
                    tint               = accentColor,
                    modifier           = Modifier.size(16.dp)
                )
                Column(modifier = Modifier.weight(1f)) {
                    Text(
                        text       = role.label,
                        color      = accentColor,
                        fontWeight = FontWeight.Bold,
                        fontFamily = FontFamily.Monospace,
                        fontSize   = 13.sp
                    )
                    Text(
                        text          = "${role.envPrefix}_PROVIDER / ${role.envPrefix}_MODEL",
                        color         = TextSecondary,
                        fontSize      = 9.sp,
                        fontFamily    = FontFamily.Monospace,
                        letterSpacing = 0.8.sp
                    )
                }
                // Free badge
                if (selectedProvider.isFree) {
                    Box(
                        modifier = Modifier
                            .background(NeonGreen.copy(alpha = 0.15f), RoundedCornerShape(4.dp))
                            .border(1.dp, NeonGreen.copy(alpha = 0.5f), RoundedCornerShape(4.dp))
                            .padding(horizontal = 6.dp, vertical = 2.dp)
                    ) {
                        Text(
                            text       = "FREE",
                            color      = NeonGreen,
                            fontSize   = 8.sp,
                            fontFamily = FontFamily.Monospace,
                            fontWeight = FontWeight.Bold
                        )
                    }
                }
            }

            HorizontalDivider(color = accentColor.copy(alpha = 0.3f))

            // Provider dropdown
            Row(
                modifier          = Modifier.fillMaxWidth(),
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(
                    text       = "Провайдер:",
                    color      = TextSecondary,
                    fontSize   = 11.sp,
                    fontFamily = FontFamily.Monospace,
                    modifier   = Modifier.width(95.dp)
                )
                Box(modifier = Modifier.weight(1f)) {
                    ExposedDropdownMenuBox(
                        expanded        = providerMenuExpanded,
                        onExpandedChange = { providerMenuExpanded = !providerMenuExpanded }
                    ) {
                        OutlinedButton(
                            onClick  = { providerMenuExpanded = true },
                            modifier = Modifier
                                .fillMaxWidth()
                                .menuAnchor(MenuAnchorType.PrimaryNotEditable),
                            border   = androidx.compose.foundation.BorderStroke(1.dp, accentColor.copy(alpha = 0.6f)),
                            colors   = ButtonDefaults.outlinedButtonColors(contentColor = accentColor),
                            shape    = RoundedCornerShape(8.dp),
                            contentPadding = PaddingValues(horizontal = 12.dp, vertical = 6.dp)
                        ) {
                            Text(
                                text       = selectedProvider.name,
                                fontFamily = FontFamily.Monospace,
                                fontSize   = 12.sp,
                                modifier   = Modifier.weight(1f)
                            )
                            Icon(
                                imageVector        = Icons.Filled.ExpandMore,
                                contentDescription = null,
                                modifier           = Modifier.size(16.dp)
                            )
                        }
                        ExposedDropdownMenu(
                            expanded         = providerMenuExpanded,
                            onDismissRequest = { providerMenuExpanded = false },
                            modifier         = Modifier.background(BgCard)
                        ) {
                            llmProviders.forEach { provider ->
                                DropdownMenuItem(
                                    text = {
                                        Row(
                                            verticalAlignment     = Alignment.CenterVertically,
                                            horizontalArrangement = Arrangement.spacedBy(6.dp)
                                        ) {
                                            Text(
                                                text       = provider.name,
                                                color      = if (provider.id == selectedProvider.id) accentColor else TextPrimary,
                                                fontFamily = FontFamily.Monospace,
                                                fontSize   = 13.sp,
                                                modifier   = Modifier.weight(1f)
                                            )
                                            if (provider.isFree) {
                                                Text(
                                                    text       = "FREE",
                                                    color      = NeonGreen,
                                                    fontSize   = 8.sp,
                                                    fontFamily = FontFamily.Monospace,
                                                    fontWeight = FontWeight.Bold
                                                )
                                            }
                                            if (provider.id == selectedProvider.id) {
                                                Icon(
                                                    imageVector        = Icons.Filled.Check,
                                                    contentDescription = null,
                                                    tint               = accentColor,
                                                    modifier           = Modifier.size(14.dp)
                                                )
                                            }
                                        }
                                    },
                                    onClick = {
                                        onProviderChange(provider)
                                        providerMenuExpanded = false
                                    }
                                )
                            }
                        }
                    }
                }
            }

            // Model dropdown
            Row(
                modifier          = Modifier.fillMaxWidth(),
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(
                    text       = "Модель:",
                    color      = TextSecondary,
                    fontSize   = 11.sp,
                    fontFamily = FontFamily.Monospace,
                    modifier   = Modifier.width(95.dp)
                )
                Box(modifier = Modifier.weight(1f)) {
                    ExposedDropdownMenuBox(
                        expanded         = modelMenuExpanded,
                        onExpandedChange = { modelMenuExpanded = !modelMenuExpanded }
                    ) {
                        OutlinedButton(
                            onClick  = { modelMenuExpanded = true },
                            modifier = Modifier
                                .fillMaxWidth()
                                .menuAnchor(MenuAnchorType.PrimaryNotEditable),
                            border   = androidx.compose.foundation.BorderStroke(1.dp, accentColor.copy(alpha = 0.6f)),
                            colors   = ButtonDefaults.outlinedButtonColors(contentColor = accentColor),
                            shape    = RoundedCornerShape(8.dp),
                            contentPadding = PaddingValues(horizontal = 12.dp, vertical = 6.dp)
                        ) {
                            Text(
                                text       = selectedModel.take(28) + if (selectedModel.length > 28) "…" else "",
                                fontFamily = FontFamily.Monospace,
                                fontSize   = 11.sp,
                                modifier   = Modifier.weight(1f)
                            )
                            Icon(
                                imageVector        = Icons.Filled.ExpandMore,
                                contentDescription = null,
                                modifier           = Modifier.size(16.dp)
                            )
                        }
                        ExposedDropdownMenu(
                            expanded         = modelMenuExpanded,
                            onDismissRequest = { modelMenuExpanded = false },
                            modifier         = Modifier.background(BgCard)
                        ) {
                            selectedProvider.models.forEach { model ->
                                DropdownMenuItem(
                                    text = {
                                        Row(
                                            verticalAlignment = Alignment.CenterVertically,
                                            horizontalArrangement = Arrangement.spacedBy(6.dp)
                                        ) {
                                            Text(
                                                text       = model,
                                                color      = if (model == selectedModel) accentColor else TextPrimary,
                                                fontFamily = FontFamily.Monospace,
                                                fontSize   = 12.sp,
                                                modifier   = Modifier.weight(1f)
                                            )
                                            if (model == selectedModel) {
                                                Icon(
                                                    imageVector        = Icons.Filled.Check,
                                                    contentDescription = null,
                                                    tint               = accentColor,
                                                    modifier           = Modifier.size(14.dp)
                                                )
                                            }
                                        }
                                    },
                                    onClick = {
                                        onModelChange(model)
                                        modelMenuExpanded = false
                                    }
                                )
                            }
                        }
                    }
                }
            }

            // Current selection summary
            Box(
                modifier = Modifier
                    .fillMaxWidth()
                    .background(accentColor.copy(alpha = 0.06f), RoundedCornerShape(6.dp))
                    .border(1.dp, accentColor.copy(alpha = 0.2f), RoundedCornerShape(6.dp))
                    .padding(horizontal = 10.dp, vertical = 6.dp)
            ) {
                Text(
                    text = "${role.envPrefix}_PROVIDER=${selectedProvider.id}  |  " +
                           "${role.envPrefix}_MODEL=${selectedModel}",
                    color      = accentColor.copy(alpha = 0.75f),
                    fontSize   = 9.sp,
                    fontFamily = FontFamily.Monospace,
                    letterSpacing = 0.3.sp
                )
            }
        }
    }
}

// ── Status info row ───────────────────────────────────────────────────────────
@Composable
private fun StatusInfoRow(label: String, value: String, valueColor: Color) {
    Row(
        modifier              = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment     = Alignment.CenterVertically
    ) {
        Text(
            text       = label,
            color      = TextSecondary,
            fontSize   = 12.sp,
            fontFamily = FontFamily.Monospace
        )
        Box(
            modifier = Modifier
                .background(valueColor.copy(alpha = 0.1f), RoundedCornerShape(4.dp))
                .padding(horizontal = 8.dp, vertical = 3.dp)
        ) {
            Text(
                text       = value,
                color      = valueColor,
                fontSize   = 11.sp,
                fontFamily = FontFamily.Monospace,
                fontWeight = FontWeight.Bold
            )
        }
    }
}
