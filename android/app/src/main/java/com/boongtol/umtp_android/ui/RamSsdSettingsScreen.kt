package com.boongtol.umtp_android.ui

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.boongtol.umtp_android.network.MacBookAirUnit
import com.boongtol.umtp_android.network.UserFairPriceItem

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun RamSsdSettingsScreen(
    userId: String?,
    chip: String,
    screenSize: Int,
    units: List<MacBookAirUnit>,
    userSettings: List<UserFairPriceItem>,
    savingItemKey: String?,
    isRefreshing: Boolean,
    refreshStatusMessage: String?,
    lastRefreshAtText: String?,
    onRefresh: () -> Unit,
    refreshingRuleIds: Set<Long>,
    ruleRefreshStatusMessages: Map<Long, String>,
    ruleLastRefreshLabels: Map<Long, String>,
    onSave: (MacBookAirUnit, Int, Int, String, Boolean, String?, Int?) -> Unit,
    onRefreshRule: (Long) -> Unit,
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
                },
                actions = {
                    IconButton(onClick = onRefresh, enabled = !isRefreshing) {
                        if (isRefreshing) {
                            CircularProgressIndicator(
                                modifier = Modifier.size(18.dp),
                                strokeWidth = 2.dp,
                            )
                        } else {
                            Icon(Icons.Default.Refresh, contentDescription = "새로고침")
                        }
                    }
                },
            )
        }
    ) { innerPadding ->
        if (units.isEmpty()) {
            Box(
                modifier = Modifier
                    .fillMaxSize()
                    .padding(innerPadding),
                contentAlignment = Alignment.Center,
            ) {
                Text(
                    text = "설정 데이터를 불러오지 못했습니다.\n상단 새로고침을 눌러 다시 시도해주세요.",
                    style = MaterialTheme.typography.bodyMedium,
                    color = Color.Gray,
                )
            }
        } else {
            LazyColumn(
                modifier = Modifier
                    .fillMaxSize()
                    .padding(innerPadding),
                contentPadding = PaddingValues(16.dp)
            ) {
                item {
                    if (isRefreshing) {
                        Text(
                            text = "새로고침 중...",
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.primary,
                            modifier = Modifier.padding(bottom = 8.dp),
                        )
                    } else if (!refreshStatusMessage.isNullOrBlank()) {
                        Text(
                            text = refreshStatusMessage,
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.primary,
                            modifier = Modifier.padding(bottom = 4.dp),
                        )
                        if (!lastRefreshAtText.isNullOrBlank()) {
                            Text(
                                text = lastRefreshAtText,
                                style = MaterialTheme.typography.labelSmall,
                                color = Color.Gray,
                                modifier = Modifier.padding(bottom = 8.dp),
                            )
                        }
                    }
                    Text(
                        text = "지금부터 새로 올라오는 매물만 다시 조회합니다.",
                        style = MaterialTheme.typography.labelSmall,
                        color = Color.Gray,
                        modifier = Modifier.padding(bottom = 8.dp),
                    )
                }
                items(units) { unit ->
                    val setting = userSettings.find { 
                        it.chip == unit.chip && 
                        it.screen_inch == unit.screen_inch && 
                        it.ram_gb == unit.ram_gb && 
                        it.ssd_gb == unit.ssd_gb 
                    }
                    val ruleId = setting?.id
                    val canRefreshRule = setting?.let { it.id != null && it.enabled && it.has_user_override } == true
                    val itemKey = "${unit.chip}-${unit.screen_inch}-${unit.ram_gb}-${unit.ssd_gb}"
                    
                    MacBookAirSettingCard(
                        userId = userId,
                        unit = unit,
                        userSetting = setting,
                        isSaving = savingItemKey == itemKey,
                        canRefreshRuleSavedAt = canRefreshRule,
                        isRefreshingRuleSavedAt = ruleId != null && refreshingRuleIds.contains(ruleId),
                        ruleRefreshStatusMessage = ruleId?.let { ruleRefreshStatusMessages[it] },
                        ruleLastRefreshAtText = ruleId?.let { ruleLastRefreshLabels[it] },
                        onRefreshRuleSavedAt = if (ruleId != null) {
                            { onRefreshRule(ruleId) }
                        } else {
                            null
                        },
                        onSave = { fairPrice, desiredPrice, alertPriceDirection, enabled, searchKeyword, boundPrice ->
                            onSave(
                                unit,
                                fairPrice,
                                desiredPrice,
                                alertPriceDirection,
                                enabled,
                                searchKeyword,
                                boundPrice,
                            )
                        }
                    )
                }
            }
        }
    }
}
