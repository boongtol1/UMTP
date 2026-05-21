package com.boongtol.umtp_android.ui

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.foundation.text.KeyboardOptions
import com.boongtol.umtp_android.network.MacBookAirUnit
import com.boongtol.umtp_android.network.UserFairPriceItem

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun RamSsdSettingsScreen(
    userId: String?,
    productType: String,
    chip: String,
    screenSize: Int,
    units: List<MacBookAirUnit>,
    userSettings: List<UserFairPriceItem>,
    savingItemKey: String?,
    isRefreshing: Boolean,
    isApplyingBulkSettings: Boolean,
    refreshStatusMessage: String?,
    lastRefreshAtText: String?,
    onRefresh: () -> Unit,
    refreshingRuleIds: Set<Long>,
    ruleRefreshStatusMessages: Map<Long, String>,
    ruleLastRefreshLabels: Map<Long, String>,
    bulkEnabledForCurrentScope: Boolean,
    bulkEnabledForProductType: Boolean,
    bulkConditionChangeNoticeForCurrentScope: Boolean,
    bulkConditionChangeNoticeForProductType: Boolean,
    onBulkEnabledChange: (Boolean, Boolean) -> Unit,
    onBulkConditionChangeNoticeChange: (Boolean, Boolean) -> Unit,
    onBulkDropRateApply: (Double, Boolean) -> Unit,
    onResetToSystemMarketPrices: (Boolean) -> Unit,
    onSave: (MacBookAirUnit, Int, Int, String, Boolean, Boolean, String?, String, Int?) -> Unit,
    onRefreshRule: (Long) -> Unit,
    onBack: () -> Unit
) {
    var showEnableConfirmDialog by remember { mutableStateOf(false) }
    var applyToProductType by remember(productType, chip, screenSize) { mutableStateOf(false) }
    val effectiveBulkEnabled = if (applyToProductType) bulkEnabledForProductType else bulkEnabledForCurrentScope
    val effectiveBulkConditionChangeNotice =
        if (applyToProductType) bulkConditionChangeNoticeForProductType else bulkConditionChangeNoticeForCurrentScope
    var pendingEnabledValue by remember { mutableStateOf(effectiveBulkEnabled) }
    var showConditionChangeNoticeConfirmDialog by remember { mutableStateOf(false) }
    var pendingConditionChangeNoticeEnabled by remember { mutableStateOf(effectiveBulkConditionChangeNotice) }
    var showDropRateConfirmDialog by remember { mutableStateOf(false) }
    var pendingDropRatePercent by remember { mutableStateOf(0.0) }
    var showResetConfirmDialog by remember { mutableStateOf(false) }
    var bulkDropRateInput by remember { mutableStateOf("") }
    var bulkDropRateInputError by remember { mutableStateOf<String?>(null) }
    val bulkScopeLabel = buildBulkScopeLabel(
        productType = productType,
        chip = chip,
        screenSize = screenSize,
        applyToProductType = applyToProductType,
    )

    Scaffold(
        topBar = {
            TopAppBar(
                title = {
                    if (productType == "Mac mini") {
                        Text("$chip $productType 설정", fontSize = 18.sp)
                    } else {
                        Text("$chip $productType ${screenSize}인치 설정", fontSize = 18.sp)
                    }
                },
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
                    Card(
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(bottom = 12.dp),
                        colors = CardDefaults.cardColors(
                            containerColor = MaterialTheme.colorScheme.surfaceVariant
                        )
                    ) {
                        Column(
                            modifier = Modifier.padding(12.dp),
                            verticalArrangement = Arrangement.spacedBy(10.dp),
                        ) {
                            Text(
                                text = "적용 범위",
                                style = MaterialTheme.typography.labelMedium,
                            )
                            Row(
                                horizontalArrangement = Arrangement.spacedBy(8.dp),
                            ) {
                                FilterChip(
                                    selected = !applyToProductType,
                                    onClick = { applyToProductType = false },
                                    label = {
                                        Text(
                                            if (productType == "Mac mini") {
                                                "현재 칩"
                                            } else {
                                                "현재 칩/인치"
                                            }
                                        )
                                    },
                                    enabled = !isApplyingBulkSettings,
                                )
                                FilterChip(
                                    selected = applyToProductType,
                                    onClick = { applyToProductType = true },
                                    label = { Text("제품 전체") },
                                    enabled = !isApplyingBulkSettings,
                                )
                            }
                            Text(
                                text = "$bulkScopeLabel 범위에 적용됩니다.",
                                style = MaterialTheme.typography.labelSmall,
                                color = Color.Gray,
                            )
                            Row(
                                modifier = Modifier.fillMaxWidth(),
                                verticalAlignment = Alignment.CenterVertically,
                                horizontalArrangement = Arrangement.SpaceBetween,
                            ) {
                                Text(
                                    text = "전체 알림",
                                    style = MaterialTheme.typography.titleSmall,
                                )
                                Switch(
                                    checked = effectiveBulkEnabled,
                                    onCheckedChange = { checked ->
                                        pendingEnabledValue = checked
                                        showEnableConfirmDialog = true
                                    },
                                    enabled = !isApplyingBulkSettings,
                                )
                            }
                            Row(
                                modifier = Modifier.fillMaxWidth(),
                                verticalAlignment = Alignment.CenterVertically,
                                horizontalArrangement = Arrangement.SpaceBetween,
                            ) {
                                Text(
                                    text = "조건 변경 후보 알림",
                                    style = MaterialTheme.typography.titleSmall,
                                )
                                Switch(
                                    checked = effectiveBulkConditionChangeNotice,
                                    onCheckedChange = { checked ->
                                        pendingConditionChangeNoticeEnabled = checked
                                        showConditionChangeNoticeConfirmDialog = true
                                    },
                                    enabled = !isApplyingBulkSettings,
                                )
                            }
                            Text(
                                text = "조건 변경 사이에 새 기준에 맞는 매물 참고 알림을 범위 전체에 반영합니다.",
                                style = MaterialTheme.typography.labelSmall,
                                color = Color.Gray,
                            )
                            OutlinedTextField(
                                value = bulkDropRateInput,
                                onValueChange = {
                                    bulkDropRateInput = it
                                    bulkDropRateInputError = null
                                },
                                label = { Text("시장가와의 차이 %") },
                                singleLine = true,
                                keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Decimal),
                                enabled = !isApplyingBulkSettings,
                                isError = bulkDropRateInputError != null,
                                modifier = Modifier.fillMaxWidth(),
                            )
                            if (!bulkDropRateInputError.isNullOrBlank()) {
                                Text(
                                    text = bulkDropRateInputError ?: "",
                                    style = MaterialTheme.typography.labelSmall,
                                    color = MaterialTheme.colorScheme.error,
                                )
                            }
                            Button(
                                onClick = {
                                    val parsed = bulkDropRateInput.toDoubleOrNull()
                                    if (parsed == null) {
                                        bulkDropRateInputError = "숫자(예: 20)를 입력해주세요."
                                    } else if (parsed < -100.0 || parsed > 100.0) {
                                        bulkDropRateInputError = "-100 ~ 100 범위로 입력해주세요."
                                    } else {
                                        pendingDropRatePercent = parsed
                                        showDropRateConfirmDialog = true
                                    }
                                },
                                enabled = !isApplyingBulkSettings,
                                modifier = Modifier.fillMaxWidth(),
                            ) {
                                Text("전체 차이 % 적용")
                            }
                            OutlinedButton(
                                onClick = { showResetConfirmDialog = true },
                                enabled = !isApplyingBulkSettings,
                                modifier = Modifier.fillMaxWidth(),
                            ) {
                                Text("시스템 기준 시장가로 초기화")
                            }
                            if (isApplyingBulkSettings) {
                                Row(
                                    verticalAlignment = Alignment.CenterVertically,
                                    horizontalArrangement = Arrangement.spacedBy(8.dp),
                                ) {
                                    CircularProgressIndicator(
                                        modifier = Modifier.size(16.dp),
                                        strokeWidth = 2.dp,
                                    )
                                    Text(
                                        text = "일괄 적용 중...",
                                        style = MaterialTheme.typography.labelSmall,
                                        color = MaterialTheme.colorScheme.primary,
                                    )
                                }
                            }
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
                        it.product_type == unit.product_type &&
                        it.chip == unit.chip && 
                        it.screen_inch == unit.screen_inch && 
                        it.ram_gb == unit.ram_gb && 
                        it.ssd_gb == unit.ssd_gb 
                    }
                    val ruleId = setting?.id
                    val canRefreshRule = setting?.let { it.id != null && it.enabled && it.has_user_override } == true
                    val itemKey = "${unit.product_type}-${unit.chip}-${unit.screen_inch}-${unit.ram_gb}-${unit.ssd_gb}"
                    
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
                        onSave = { fairPrice, desiredPrice, alertPriceDirection, enabled, conditionChangeCandidateNoticeEnabled, searchKeyword, priority, boundPrice ->
                            onSave(
                                unit,
                                fairPrice,
                                desiredPrice,
                                alertPriceDirection,
                                enabled,
                                conditionChangeCandidateNoticeEnabled,
                                searchKeyword,
                                priority,
                                boundPrice,
                            )
                        }
                    )
                }
            }
        }
    }

    if (showEnableConfirmDialog) {
        AlertDialog(
            onDismissRequest = { showEnableConfirmDialog = false },
            title = { Text("전체 알림 변경") },
            text = {
                Text(
                    if (pendingEnabledValue) {
                        "$bulkScopeLabel 알림을 모두 켜시겠습니까?"
                    } else {
                        "$bulkScopeLabel 알림을 모두 끄시겠습니까?"
                    }
                )
            },
            confirmButton = {
                TextButton(
                    onClick = {
                        showEnableConfirmDialog = false
                        onBulkEnabledChange(pendingEnabledValue, applyToProductType)
                    }
                ) {
                    Text("확인")
                }
            },
            dismissButton = {
                TextButton(onClick = { showEnableConfirmDialog = false }) {
                    Text("취소")
                }
            },
        )
    }

    if (showDropRateConfirmDialog) {
        AlertDialog(
            onDismissRequest = { showDropRateConfirmDialog = false },
            title = { Text("전체 차이 % 변경") },
            text = {
                Text("$bulkScopeLabel 시장가 차이 기준을 ${pendingDropRatePercent}%로 변경할까요?")
            },
            confirmButton = {
                TextButton(
                    onClick = {
                        showDropRateConfirmDialog = false
                        onBulkDropRateApply(pendingDropRatePercent, applyToProductType)
                    }
                ) {
                    Text("확인")
                }
            },
            dismissButton = {
                TextButton(onClick = { showDropRateConfirmDialog = false }) {
                    Text("취소")
                }
            },
        )
    }

    if (showConditionChangeNoticeConfirmDialog) {
        AlertDialog(
            onDismissRequest = { showConditionChangeNoticeConfirmDialog = false },
            title = { Text("조건 변경 후보 알림 변경") },
            text = {
                Text(
                    if (pendingConditionChangeNoticeEnabled) {
                        "$bulkScopeLabel 조건 변경 후보 알림을 모두 켜시겠습니까?"
                    } else {
                        "$bulkScopeLabel 조건 변경 후보 알림을 모두 끄시겠습니까?"
                    }
                )
            },
            confirmButton = {
                TextButton(
                    onClick = {
                        showConditionChangeNoticeConfirmDialog = false
                        onBulkConditionChangeNoticeChange(
                            pendingConditionChangeNoticeEnabled,
                            applyToProductType,
                        )
                    }
                ) {
                    Text("확인")
                }
            },
            dismissButton = {
                TextButton(onClick = { showConditionChangeNoticeConfirmDialog = false }) {
                    Text("취소")
                }
            },
        )
    }

    if (showResetConfirmDialog) {
        AlertDialog(
            onDismissRequest = { showResetConfirmDialog = false },
            title = { Text("시장가 초기화") },
            text = {
                Text("$bulkScopeLabel 사용자가 생각한 시장가를 시스템 기준 시장가로 모두 바꿀까요? 기존 알림 방향과 차이 % 설정은 유지됩니다.")
            },
            confirmButton = {
                TextButton(
                    onClick = {
                        showResetConfirmDialog = false
                        onResetToSystemMarketPrices(applyToProductType)
                    }
                ) {
                    Text("확인")
                }
            },
            dismissButton = {
                TextButton(onClick = { showResetConfirmDialog = false }) {
                    Text("취소")
                }
            },
        )
    }
}

private fun buildBulkScopeLabel(
    productType: String,
    chip: String,
    screenSize: Int,
    applyToProductType: Boolean,
): String {
    if (applyToProductType) {
        return productType
    }
    if (productType == "Mac mini") {
        return "$chip $productType"
    }
    return "$chip $productType ${screenSize}인치"
}
