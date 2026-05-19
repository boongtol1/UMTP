package com.boongtol.umtp_android

import android.Manifest
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import android.provider.Settings
import android.util.Log
import android.widget.Toast
import androidx.activity.ComponentActivity
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.padding
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.List
import androidx.compose.material.icons.filled.Archive
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.core.content.ContextCompat
import androidx.lifecycle.viewmodel.compose.viewModel
import com.boongtol.umtp_android.fcm.PushTokenManager
import com.boongtol.umtp_android.ui.*
import com.boongtol.umtp_android.ui.theme.UMTP_ANDROIDTheme
import com.boongtol.umtp_android.user.UserPreferences

class MainActivity : ComponentActivity() {
    private var pushTokenManager: PushTokenManager? = null
    private val _deepLinkAlertId = mutableStateOf<String?>(null)

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        
        val userPreferences = UserPreferences(this)
        pushTokenManager = PushTokenManager(this)

        handleIntent(intent)

        enableEdgeToEdge()
        setContent {
            UMTP_ANDROIDTheme {
                val viewModel: MacBookAirSettingsViewModel = viewModel(
                    factory = MacBookAirSettingsViewModel.Factory(userPreferences)
                )
                
                val userId by viewModel.userId.collectAsState()
                val isLoading by viewModel.isLoading.collectAsState()
                val toastMessage by viewModel.toastMessage.collectAsState()
                val deepLinkAlertId by _deepLinkAlertId
                
                val context = LocalContext.current

                val permissionLauncher = rememberLauncherForActivityResult(
                    contract = ActivityResultContracts.RequestPermission()
                ) { isGranted ->
                    if (isGranted) {
                        Log.d("MainActivity", "Notification permission granted")
                    } else {
                        Log.d("MainActivity", "Notification permission denied")
                    }
                }

                LaunchedEffect(Unit) {
                    if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
                        if (ContextCompat.checkSelfPermission(
                                context,
                                Manifest.permission.POST_NOTIFICATIONS
                            ) != PackageManager.PERMISSION_GRANTED
                        ) {
                            permissionLauncher.launch(Manifest.permission.POST_NOTIFICATIONS)
                        }
                    }
                }
                
                LaunchedEffect(toastMessage) {
                    toastMessage?.let {
                        Toast.makeText(context, it, Toast.LENGTH_SHORT).show()
                        viewModel.clearToastMessage()
                    }
                }

                LaunchedEffect(userId) {
                    if (userId != null) {
                        pushTokenManager?.checkAndRegisterToken()
                    }
                }

                if (userId == null) {
                    UserSetupScreen(
                        isLoading = isLoading,
                        onRegister = {
                            val androidId = Settings.Secure.getString(
                                contentResolver,
                                Settings.Secure.ANDROID_ID
                            )
                            viewModel.registerUser(it, androidId)
                        }
                    )
                } else {
                    MainTabScreen(
                        viewModel = viewModel, 
                        userId = userId!!,
                        initialAlertId = deepLinkAlertId,
                        onAlertNavigated = { _deepLinkAlertId.value = null }
                    )
                }
            }
        }
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        handleIntent(intent)
    }

    private fun handleIntent(intent: Intent?) {
        val alertId = intent?.getStringExtra("alert_id")
        if (alertId != null) {
            _deepLinkAlertId.value = alertId
            Log.d("MainActivity", "Received Alert ID via Push: $alertId")
        }
    }
}

@Composable
fun MainTabScreen(
    viewModel: MacBookAirSettingsViewModel, 
    userId: String,
    initialAlertId: String? = null,
    onAlertNavigated: () -> Unit = {}
) {
    var selectedTab by remember { mutableIntStateOf(0) }
    
    val alerts by viewModel.alerts.collectAsState()
    val readGroupedAlerts by viewModel.readGroupedAlerts.collectAsState()
    val units by viewModel.units.collectAsState()
    val userSettings by viewModel.userSettings.collectAsState()
    val savingItemKey by viewModel.savingItemKey.collectAsState()
    val isRefreshingAlerts by viewModel.isRefreshingAlerts.collectAsState()
    val isRefreshingReadArchive by viewModel.isRefreshingReadArchive.collectAsState()
    val isMarkingAllAlertsRead by viewModel.isMarkingAllAlertsRead.collectAsState()
    val isClearingReadArchiveAll by viewModel.isClearingReadArchiveAll.collectAsState()
    val isClearingReadArchiveSelected by viewModel.isClearingReadArchiveSelected.collectAsState()
    val alertsRefreshStatusMessage by viewModel.alertsRefreshStatusMessage.collectAsState()
    val readArchiveRefreshStatusMessage by viewModel.readArchiveRefreshStatusMessage.collectAsState()
    val lastAlertsRefreshLabel by viewModel.lastAlertsRefreshLabel.collectAsState()
    val isRefreshingSettings by viewModel.isRefreshingSettings.collectAsState()
    val settingsRefreshStatusMessage by viewModel.settingsRefreshStatusMessage.collectAsState()
    val lastSettingsRefreshLabel by viewModel.lastSettingsRefreshLabel.collectAsState()
    val refreshingRuleIds by viewModel.refreshingRuleIds.collectAsState()
    val ruleRefreshStatusMessages by viewModel.ruleRefreshStatusMessages.collectAsState()
    val ruleLastRefreshLabels by viewModel.ruleLastRefreshLabels.collectAsState()

    var targetAlertId by remember { mutableStateOf<String?>(null) }

    LaunchedEffect(initialAlertId) {
        if (initialAlertId != null) {
            targetAlertId = initialAlertId
            selectedTab = 0
            onAlertNavigated()
        }
    }

    Scaffold(
        bottomBar = {
            NavigationBar {
                NavigationBarItem(
                    selected = selectedTab == 0,
                    onClick = { selectedTab = 0 },
                    icon = { Icon(Icons.AutoMirrored.Filled.List, contentDescription = "Alerts") },
                    label = { Text("알림") }
                )
                NavigationBarItem(
                    selected = selectedTab == 1,
                    onClick = {
                        selectedTab = 1
                        viewModel.fetchReadGroupedAlerts(userId, showFeedback = false)
                    },
                    icon = { Icon(Icons.Default.Archive, contentDescription = "Read Archive") },
                    label = { Text("읽음 보관함") }
                )
                NavigationBarItem(
                    selected = selectedTab == 2,
                    onClick = { selectedTab = 2 },
                    icon = { Icon(Icons.Default.Settings, contentDescription = "Settings") },
                    label = { Text("설정") }
                )
            }
        }
    ) { innerPadding ->
        Surface(modifier = Modifier.padding(innerPadding)) {
            when (selectedTab) {
                0 -> AlertFeedScreen(
                    alerts = alerts,
                    isRefreshing = isRefreshingAlerts,
                    isMarkingAllRead = isMarkingAllAlertsRead,
                    refreshStatusMessage = alertsRefreshStatusMessage,
                    lastRefreshAtText = lastAlertsRefreshLabel,
                    onRefresh = { viewModel.fetchAlerts(userId, showFeedback = true) },
                    onMarkAlertRead = { alertId, completion ->
                        viewModel.markAlertAsRead(
                            uid = userId,
                            alertEventId = alertId,
                            showFeedback = true,
                            onComplete = completion,
                        )
                    },
                    onMarkAllAsRead = { viewModel.markAllAlertsAsRead(userId) },
                    initialTargetAlertId = targetAlertId,
                    onTargetAlertFound = { targetAlertId = null }
                )
                1 -> ReadAlertArchiveScreen(
                    groupedAlerts = readGroupedAlerts,
                    isRefreshing = isRefreshingReadArchive,
                    isClearingAll = isClearingReadArchiveAll,
                    isClearingSelected = isClearingReadArchiveSelected,
                    refreshStatusMessage = readArchiveRefreshStatusMessage,
                    onRefresh = { viewModel.fetchReadGroupedAlerts(userId, showFeedback = true) },
                    onClearAll = { viewModel.clearAllReadArchive(userId) },
                    onClearSelected = { alertIds ->
                        viewModel.clearSelectedReadArchive(userId, alertIds)
                    },
                )
                2 -> SettingsNavigator(
                    userId = userId,
                    units = units,
                    userSettings = userSettings,
                    savingItemKey = savingItemKey,
                    isRefreshing = isRefreshingSettings,
                    refreshStatusMessage = settingsRefreshStatusMessage,
                    lastRefreshAtText = lastSettingsRefreshLabel,
                    onRefresh = { viewModel.refreshSettings(userId, showFeedback = true) },
                    refreshingRuleIds = refreshingRuleIds,
                    ruleRefreshStatusMessages = ruleRefreshStatusMessages,
                    ruleLastRefreshLabels = ruleLastRefreshLabels,
                    onUpsert = { unit, fairPrice, desiredPrice, alertPriceDirection, enabled, searchKeyword, boundPrice ->
                        viewModel.upsertItem(
                            unit,
                            fairPrice,
                            desiredPrice,
                            alertPriceDirection,
                            enabled,
                            searchKeyword,
                            boundPrice,
                        )
                    },
                    onRefreshRule = { ruleId ->
                        viewModel.refreshSingleRuleSavedAt(userId, ruleId)
                    },
                )
            }
        }
    }
}

@Composable
fun SettingsNavigator(
    userId: String,
    units: List<com.boongtol.umtp_android.network.MacBookAirUnit>,
    userSettings: List<com.boongtol.umtp_android.network.UserFairPriceItem>,
    savingItemKey: String?,
    isRefreshing: Boolean,
    refreshStatusMessage: String?,
    lastRefreshAtText: String?,
    onRefresh: () -> Unit,
    refreshingRuleIds: Set<Long>,
    ruleRefreshStatusMessages: Map<Long, String>,
    ruleLastRefreshLabels: Map<Long, String>,
    onUpsert: (com.boongtol.umtp_android.network.MacBookAirUnit, Int, Int, String, Boolean, String?, Int?) -> Unit,
    onRefreshRule: (Long) -> Unit,
) {
    var currentScreen by remember { mutableStateOf<Screen>(Screen.ChipList) }

    when (val screen = currentScreen) {
        is Screen.ChipList -> {
            val chips = units.map { it.chip }.distinct().sorted()
            ChipListScreen(
                userId = userId,
                chips = chips,
                isRefreshing = isRefreshing,
                refreshStatusMessage = refreshStatusMessage,
                lastRefreshAtText = lastRefreshAtText,
                onRefresh = onRefresh,
                onChipClick = { currentScreen = Screen.ScreenSizeList(it) },
                onLogout = { /* Registration is locked, logout removed */ }
            )
        }
        is Screen.ScreenSizeList -> {
            val sizes = units.filter { it.chip == screen.chip }
                .map { it.screen_inch }.distinct().sorted()
            ScreenSizeListScreen(
                chip = screen.chip,
                screenSizes = sizes,
                isRefreshing = isRefreshing,
                refreshStatusMessage = refreshStatusMessage,
                lastRefreshAtText = lastRefreshAtText,
                onRefresh = onRefresh,
                onScreenSizeClick = { currentScreen = Screen.RamSsdSettings(screen.chip, it) },
                onBack = { currentScreen = Screen.ChipList }
            )
        }
        is Screen.RamSsdSettings -> {
            val filteredUnits = units.filter { 
                it.chip == screen.chip && it.screen_inch == screen.screenSize 
            }
            RamSsdSettingsScreen(
                userId = userId,
                chip = screen.chip,
                screenSize = screen.screenSize,
                units = filteredUnits,
                userSettings = userSettings,
                savingItemKey = savingItemKey,
                isRefreshing = isRefreshing,
                refreshStatusMessage = refreshStatusMessage,
                lastRefreshAtText = lastRefreshAtText,
                onRefresh = onRefresh,
                refreshingRuleIds = refreshingRuleIds,
                ruleRefreshStatusMessages = ruleRefreshStatusMessages,
                ruleLastRefreshLabels = ruleLastRefreshLabels,
                onSave = onUpsert,
                onRefreshRule = onRefreshRule,
                onBack = { currentScreen = Screen.ScreenSizeList(screen.chip) }
            )
        }
    }
}

sealed class Screen {
    object ChipList : Screen()
    data class ScreenSizeList(val chip: String) : Screen()
    data class RamSsdSettings(val chip: String, val screenSize: Int) : Screen()
}
