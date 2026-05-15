package com.boongtol.umtp_android.ui

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.boongtol.umtp_android.network.MacBookAirUnit
import com.boongtol.umtp_android.network.UserFairPriceItem

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun RamSsdSettingsScreen(
    chip: String,
    screenSize: Int,
    units: List<MacBookAirUnit>,
    userSettings: List<UserFairPriceItem>,
    savingItemKey: String?,
    onSave: (MacBookAirUnit, Int, Int, Boolean, String?) -> Unit,
    onBack: () -> Unit
) {
    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("$chip Air ${screenSize}인치 설정", fontSize = 18.sp) },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "Back")
                    }
                }
            )
        }
    ) { innerPadding ->
        if (units.isEmpty()) {
            Box(modifier = Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                CircularProgressIndicator()
            }
        } else {
            LazyColumn(
                modifier = Modifier
                    .fillMaxSize()
                    .padding(innerPadding),
                contentPadding = PaddingValues(16.dp)
            ) {
                items(units) { unit ->
                    val setting = userSettings.find { 
                        it.chip == unit.chip && 
                        it.screen_inch == unit.screen_inch && 
                        it.ram_gb == unit.ram_gb && 
                        it.ssd_gb == unit.ssd_gb 
                    }
                    val itemKey = "${unit.chip}-${unit.screen_inch}-${unit.ram_gb}-${unit.ssd_gb}"
                    
                    MacBookAirSettingCard(
                        unit = unit,
                        userSetting = setting,
                        isSaving = savingItemKey == itemKey,
                        onSave = { fairPrice, dropRate, enabled, searchKeyword ->
                            onSave(unit, fairPrice, dropRate, enabled, searchKeyword)
                        }
                    )
                }
            }
        }
    }
}
