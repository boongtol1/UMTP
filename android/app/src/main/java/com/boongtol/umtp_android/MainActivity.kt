package com.boongtol.umtp_android

import android.os.Bundle
import android.provider.Settings
import android.widget.Toast
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.foundation.layout.padding
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.List
import androidx.compose.material.icons.filled.Search
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.lifecycle.viewmodel.compose.viewModel
import com.boongtol.umtp_android.network.WatchRuleUpsertRequest
import com.boongtol.umtp_android.ui.*
import com.boongtol.umtp_android.ui.theme.UMTP_ANDROIDTheme
import com.boongtol.umtp_android.user.UserPreferences

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        
        val userPreferences = UserPreferences(this)

        enableEdgeToEdge()
        setContent {
            UMTP_ANDROIDTheme {
                val viewModel: MacBookAirSettingsViewModel = viewModel(
                    factory = MacBookAirSettingsViewModel.Factory(userPreferences)
                )
                
                val userId by viewModel.userId.collectAsState()
                val isLoading by viewModel.isLoading.collectAsState()
                val toastMessage by viewModel.toastMessage.collectAsState()
                
                val context = LocalContext.current
                
                LaunchedEffect(toastMessage) {
                    toastMessage?.let {
                        Toast.makeText(context, it, Toast.LENGTH_SHORT).show()
                        viewModel.clearToastMessage()
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
                            viewModel.registerUser(it, androidId ?: "")
                        }
                    )
                } else {
                    MainTabScreen(viewModel, userId!!)
                }
            }
        }
    }
}

@Composable
fun MainTabScreen(viewModel: MacBookAirSettingsViewModel, userId: String) {
    var selectedTab by remember { mutableIntStateOf(0) }
    
    val alerts by viewModel.alerts.collectAsState()
    val units by viewModel.units.collectAsState()
    val userSettings by viewModel.userSettings.collectAsState()
    val savingItemKey by viewModel.savingItemKey.collectAsState()
    val recommendedKeywords by viewModel.recommendedKeywords.collectAsState()
    val watchRuleSaving by viewModel.watchRuleSaving.collectAsState()
    val watchRuleRequestingNow by viewModel.watchRuleRequestingNow.collectAsState()
    val watchRuleLastAlertDropRatePercent by viewModel.watchRuleLastAlertDropRatePercent.collectAsState()

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
                    onClick = { selectedTab = 1 },
                    icon = { Icon(Icons.Default.Settings, contentDescription = "Settings") },
                    label = { Text("설정") }
                )
                NavigationBarItem(
                    selected = selectedTab == 2,
                    onClick = { selectedTab = 2 },
                    icon = { Icon(Icons.Default.Search, contentDescription = "Watch Rules") },
                    label = { Text("감시") }
                )
            }
        }
    ) { innerPadding ->
        Surface(modifier = Modifier.padding(innerPadding)) {
            when (selectedTab) {
                0 -> AlertFeedScreen(
                    alerts = alerts,
                    onRefresh = { viewModel.fetchAlerts(userId) }
                )
                1 -> SettingsNavigator(
                    userId = userId,
                    units = units,
                    userSettings = userSettings,
                    savingItemKey = savingItemKey,
                    onUpsert = { unit, price, rate, enabled ->
                        viewModel.upsertItem(unit, price, rate, enabled)
                    }
                )
                2 -> WatchRuleSettingsScreen(
                    userId = userId,
                    recommendedKeywords = recommendedKeywords,
                    isSaving = watchRuleSaving,
                    isRequestingNow = watchRuleRequestingNow,
                    lastServerDropRatePercent = watchRuleLastAlertDropRatePercent,
                    onFetchRecommendedKeywords = { productType, chip, ramGb, ssdGb ->
                        viewModel.fetchRecommendedKeywords(productType, chip, ramGb, ssdGb)
                    },
                    onUpsertWatchRule = { request: WatchRuleUpsertRequest ->
                        viewModel.upsertWatchRule(request)
                    },
                    onRequestPollNow = { uid, keyword ->
                        viewModel.requestWatchRulePollNow(uid, keyword)
                    }
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
    onUpsert: (com.boongtol.umtp_android.network.MacBookAirUnit, Int, Int, Boolean) -> Unit
) {
    var currentScreen by remember { mutableStateOf<Screen>(Screen.ChipList) }

    when (val screen = currentScreen) {
        is Screen.ChipList -> {
            val chips = units.map { it.chip }.distinct().sorted()
            ChipListScreen(
                userId = userId,
                chips = chips,
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
                onScreenSizeClick = { currentScreen = Screen.RamSsdSettings(screen.chip, it) },
                onBack = { currentScreen = Screen.ChipList }
            )
        }
        is Screen.RamSsdSettings -> {
            val filteredUnits = units.filter { 
                it.chip == screen.chip && it.screen_inch == screen.screenSize 
            }
            RamSsdSettingsScreen(
                chip = screen.chip,
                screenSize = screen.screenSize,
                units = filteredUnits,
                userSettings = userSettings,
                savingItemKey = savingItemKey,
                onSave = onUpsert,
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
