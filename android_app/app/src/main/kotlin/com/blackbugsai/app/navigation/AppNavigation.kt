package com.blackbugsai.app.navigation

import androidx.compose.foundation.layout.padding
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.navigation.NavGraph.Companion.findStartDestination
import androidx.navigation.compose.*
import com.blackbugsai.app.AppViewModel
import com.blackbugsai.app.ui.screens.*
import androidx.compose.ui.unit.dp
import com.blackbugsai.app.ui.theme.*

// ── Route constants ───────────────────────────────────────────────────────────
object Routes {
    const val SETUP     = "setup"
    const val MAIN      = "main"
}

// ── Bottom nav tab descriptor ─────────────────────────────────────────────────
data class NavTab(
    val route: String,
    val label: String,
    val icon: ImageVector
)

// ── Root navigation host ──────────────────────────────────────────────────────
@Composable
fun AppNavigation(vm: AppViewModel = viewModel()) {
    val appMode by vm.appMode.collectAsState()
    val navController = rememberNavController()

    // Decide start destination once the mode is loaded
    val startDest = remember(appMode) {
        if (appMode.isBlank()) Routes.SETUP else Routes.MAIN
    }

    // While appMode is still loading ("") show nothing (handled in MainActivity)
    NavHost(
        navController = navController,
        startDestination = startDest
    ) {
        composable(Routes.SETUP) {
            SetupScreen(vm = vm, onConnected = {
                navController.navigate(Routes.MAIN) {
                    popUpTo(Routes.SETUP) { inclusive = true }
                }
            })
        }
        composable(Routes.MAIN) {
            MainScreen(vm = vm, onDisconnect = {
                navController.navigate(Routes.SETUP) {
                    popUpTo(Routes.MAIN) { inclusive = true }
                }
            })
        }
    }
}

// ── Main screen with bottom navigation ───────────────────────────────────────
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun MainScreen(vm: AppViewModel, onDisconnect: () -> Unit) {
    val appMode by vm.appMode.collectAsState()

    val telegramTabs = listOf(
        NavTab("dashboard", "ПАНЕЛЬ",   Icons.Filled.Dashboard),
        NavTab("agents",    "АГЕНТЫ",   Icons.Filled.Psychology),
        NavTab("chat",      "ЧАТ",      Icons.Filled.Forum),
        NavTab("telegram",  "BOT",      Icons.Filled.SmartToy),
        NavTab("files",     "ФАЙЛЫ",    Icons.Filled.Folder),
        NavTab("terminal",  "ТЕРМИНАЛ", Icons.Filled.Terminal),
        NavTab("settings",  "⚙",        Icons.Filled.Settings)
    )
    val serverTabs = listOf(
        NavTab("dashboard", "ПАНЕЛЬ",   Icons.Filled.Dashboard),
        NavTab("agents",    "АГЕНТЫ",   Icons.Filled.Psychology),
        NavTab("chat",      "ЧАТ",      Icons.Filled.Forum),
        NavTab("tasks",     "ЗАДАЧИ",   Icons.Filled.Task),
        NavTab("telegram",  "BOT",      Icons.Filled.SmartToy),
        NavTab("files",     "ФАЙЛЫ",    Icons.Filled.Folder),
        NavTab("terminal",  "ТЕРМИНАЛ", Icons.Filled.Terminal),
        NavTab("settings",  "⚙",        Icons.Filled.Settings)
    )

    val tabs = if (appMode == "server") serverTabs else telegramTabs
    val innerNav = rememberNavController()
    val navBackStack by innerNav.currentBackStackEntryAsState()
    val currentRoute = navBackStack?.destination?.route

    Scaffold(
        bottomBar = {
            NavigationBar(
                containerColor = BgDark,
                tonalElevation = 0.dp
            ) {
                tabs.forEach { tab ->
                    NavigationBarItem(
                        selected = currentRoute == tab.route,
                        onClick  = {
                            innerNav.navigate(tab.route) {
                                popUpTo(innerNav.graph.findStartDestination().id) { saveState = true }
                                launchSingleTop = true
                                restoreState    = true
                            }
                        },
                        icon  = { Icon(tab.icon, contentDescription = tab.label) },
                        label = {
                            Text(
                                tab.label,
                                style = MaterialTheme.typography.labelSmall,
                                color = if (currentRoute == tab.route) NeonCyan else TextSecondary
                            )
                        },
                        colors = NavigationBarItemDefaults.colors(
                            selectedIconColor   = NeonCyan,
                            unselectedIconColor = TextSecondary,
                            indicatorColor      = NeonCyan.copy(alpha = 0.15f)
                        )
                    )
                }
            }
        },
        containerColor = BgDeep
    ) { innerPadding ->
        NavHost(
            navController = innerNav,
            startDestination = "dashboard",
            modifier = Modifier.padding(innerPadding)
        ) {
            composable("dashboard") { DashboardScreen(vm = vm) }
            composable("agents")    { AgentsScreen(vm = vm) }
            composable("chat")      { ChatScreen(vm = vm) }
            composable("telegram")  { TelegramScreen(vm = vm) }
            composable("files")     { FileManagerScreen(vm = vm) }
            composable("terminal")  { TerminalScreen(vm = vm) }
            composable("settings")  { SettingsScreen(vm = vm, onDisconnect = onDisconnect) }
            composable("tasks")     { TasksScreen(vm = vm) }
        }
    }
}

// tiny stub so the "tasks" route compiles even when server mode is used
@Composable
private fun TasksScreen(vm: AppViewModel) {
    com.blackbugsai.app.ui.screens.TasksScreen(vm = vm)
}
