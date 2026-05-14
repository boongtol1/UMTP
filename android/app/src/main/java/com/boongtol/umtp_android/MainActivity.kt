package com.boongtol.umtp_android

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.runtime.*
import androidx.lifecycle.viewmodel.compose.viewModel
import com.boongtol.umtp_android.ui.MacBookAirSettingsViewModel
import com.boongtol.umtp_android.ui.UmtpUrlAnalyzeScreen
import com.boongtol.umtp_android.ui.UserFairPriceSettingsScreen
import com.boongtol.umtp_android.ui.theme.UMTP_ANDROIDTheme
import com.boongtol.umtp_android.user.UserPreferences

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        
        val userPreferences = UserPreferences(this)

        enableEdgeToEdge()
        setContent {
            UMTP_ANDROIDTheme {
                var currentScreen by remember { mutableStateOf("main") }
                val settingsViewModel: MacBookAirSettingsViewModel = viewModel(
                    factory = MacBookAirSettingsViewModel.Factory(userPreferences)
                )

                when (currentScreen) {
                    "main" -> UmtpUrlAnalyzeScreen(
                        userId = userPreferences.getUserId(),
                        onNavigateToSettings = { currentScreen = "settings" }
                    )
                    "settings" -> UserFairPriceSettingsScreen(
                        viewModel = settingsViewModel,
                        onBack = { currentScreen = "main" }
                    )
                }
            }
        }
    }
}
