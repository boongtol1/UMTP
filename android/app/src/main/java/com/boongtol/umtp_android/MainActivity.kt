package com.boongtol.umtp_android

import android.os.Bundle
import android.widget.Toast
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.runtime.*
import androidx.compose.ui.platform.LocalContext
import androidx.lifecycle.viewmodel.compose.viewModel
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
                val units by viewModel.units.collectAsState()
                val userSettings by viewModel.userSettings.collectAsState()
                val toastMessage by viewModel.toastMessage.collectAsState()
                val savingItemKey by viewModel.savingItemKey.collectAsState()
                
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
                        onRegister = { viewModel.registerUser(it) }
                    )
                } else {
                    var currentScreen by remember { mutableStateOf<Screen>(Screen.ChipList) }

                    when (val screen = currentScreen) {
                        is Screen.ChipList -> {
                            val chips = units.map { it.chip }.distinct().sorted()
                            ChipListScreen(
                                userId = userId!!,
                                chips = chips,
                                onChipClick = { currentScreen = Screen.ScreenSizeList(it) },
                                onLogout = { viewModel.logout() }
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
                                onSave = { unit, price, rate, enabled ->
                                    viewModel.upsertItem(unit, price, rate, enabled)
                                },
                                onBack = { currentScreen = Screen.ScreenSizeList(screen.chip) }
                            )
                        }
                    }
                }
            }
        }
    }
}

sealed class Screen {
    object ChipList : Screen()
    data class ScreenSizeList(val chip: String) : Screen()
    data class RamSsdSettings(val chip: String, val screenSize: Int) : Screen()
}
