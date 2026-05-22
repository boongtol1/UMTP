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
import androidx.compose.ui.text.font.FontWeight
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
    bulkWatchPriorityForCurrentScope: String,
    bulkWatchPriorityForProductType: String,
    onBulkEnabledChange: (Boolean, Boolean) -> Unit,
    onBulkConditionChangeNoticeChange: (Boolean, Boolean) -> Unit,
    onBulkWatchPriorityApply: (String, Boolean) -> Unit,
    onBulkDropRateApply: (Double, Boolean) -> Unit,
    onBulkMinPriceApply: (Int, Boolean) -> Unit,
    onBulkMaxPriceApply: (Int, Boolean) -> Unit,
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
    val effectiveBulkWatchPriority = normalizeWatchPriority(
        if (applyToProductType) bulkWatchPriorityForProductType else bulkWatchPriorityForCurrentScope
    )
    var pendingEnabledValue by remember { mutableStateOf(effectiveBulkEnabled) }
    var showConditionChangeNoticeConfirmDialog by remember { mutableStateOf(false) }
    var pendingConditionChangeNoticeEnabled by remember { mutableStateOf(effectiveBulkConditionChangeNotice) }
    var selectedBulkWatchPriority by remember(
        applyToProductType,
        bulkWatchPriorityForCurrentScope,
        bulkWatchPriorityForProductType,
    ) {
        mutableStateOf(effectiveBulkWatchPriority)
    }
    var showWatchPriorityConfirmDialog by remember { mutableStateOf(false) }
    var pendingBulkWatchPriority by remember { mutableStateOf(effectiveBulkWatchPriority) }
    var showDropRateConfirmDialog by remember { mutableStateOf(false) }
    var pendingDropRatePercent by remember { mutableStateOf(0.0) }
    var showMinPriceConfirmDialog by remember { mutableStateOf(false) }
    var showMaxPriceConfirmDialog by remember { mutableStateOf(false) }
    var pendingMinPrice by remember { mutableStateOf(0) }
    var pendingMaxPrice by remember { mutableStateOf(0) }
    var showResetConfirmDialog by remember { mutableStateOf(false) }
    var bulkDropRateInput by remember { mutableStateOf("") }
    var bulkDropRateInputError by remember { mutableStateOf<String?>(null) }
    var bulkMinPriceInputError by remember { mutableStateOf<String?>(null) }
    var bulkMaxPriceInputError by remember { mutableStateOf<String?>(null) }
    val currentScopeSettingsForBounds = remember(userSettings, productType, chip, screenSize) {
        userSettings.filter {
            it.product_type == productType &&
                it.chip == chip &&
                (productType == "Mac mini" || it.screen_inch == screenSize)
        }
    }
    val productScopeSettingsForBounds = remember(userSettings, productType) {
        userSettings.filter { it.product_type == productType }
    }
    val currentScopeBoundsState = remember(currentScopeSettingsForBounds) {
        resolveBulkPriceBoundsScopeState(currentScopeSettingsForBounds)
    }
    val productScopeBoundsState = remember(productScopeSettingsForBounds) {
        resolveBulkPriceBoundsScopeState(productScopeSettingsForBounds)
    }
    val effectiveBulkBoundsState = if (applyToProductType) productScopeBoundsState else currentScopeBoundsState
    val hasBelowDirectionInScope = effectiveBulkBoundsState.hasBelowDirection
    val hasAboveDirectionInScope = effectiveBulkBoundsState.hasAboveDirection
    var bulkMinPriceInput by remember(
        applyToProductType,
        currentScopeBoundsState.minPrice,
        productScopeBoundsState.minPrice,
    ) {
        mutableStateOf(effectiveBulkBoundsState.minPrice?.toString() ?: "")
    }
    var bulkMaxPriceInput by remember(
        applyToProductType,
        currentScopeBoundsState.maxPrice,
        productScopeBoundsState.maxPrice,
    ) {
        mutableStateOf(effectiveBulkBoundsState.maxPrice?.toString() ?: "")
    }
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
                                text = "조건을 바꾸면 최근 7일 안에 분석된 매물도 새 기준으로 다시 확인해요.\n" +
                                    "조건 변경 후보는 새 매물뿐 아니라 최근 분석된 매물도 포함될 수 있어요.\n" +
                                    "최근 7일은 매물 등록일이 아니라, 시스템이 매물을 확인한 시점부터 저장 시점까지를 기준으로 계산해요.",
                                style = MaterialTheme.typography.labelSmall,
                                color = Color.Gray,
                            )
                            Text(
                                text = "알림 속도",
                                style = MaterialTheme.typography.titleSmall,
                            )
                            Row(
                                horizontalArrangement = Arrangement.spacedBy(8.dp),
                            ) {
                                WATCH_PRIORITY_UI_OPTIONS.forEach { option ->
                                    FilterChip(
                                        selected = selectedBulkWatchPriority == option.value,
                                        onClick = { selectedBulkWatchPriority = option.value },
                                        label = { Text(option.label) },
                                        enabled = !isApplyingBulkSettings,
                                    )
                                }
                            }
                            Text(
                                text = WATCH_PRIORITY_UI_OPTIONS.firstOrNull { it.value == selectedBulkWatchPriority }?.description
                                    ?: "일반적인 속도",
                                style = MaterialTheme.typography.labelSmall,
                                color = Color.Gray,
                            )
                            Button(
                                onClick = {
                                    pendingBulkWatchPriority = selectedBulkWatchPriority
                                    showWatchPriorityConfirmDialog = true
                                },
                                enabled = !isApplyingBulkSettings,
                                modifier = Modifier.fillMaxWidth(),
                            ) {
                                Text("전체 알림 속도 적용")
                            }
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
                                leadingIcon = {
                                    TextButton(
                                        onClick = {
                                            bulkDropRateInput = if (bulkDropRateInput.startsWith("-")) {
                                                bulkDropRateInput.substring(1)
                                            } else {
                                                if (bulkDropRateInput.isEmpty()) "-" else "-$bulkDropRateInput"
                                            }
                                        },
                                        contentPadding = PaddingValues(0.dp)
                                    ) {
                                        Text(text = "+/-", fontWeight = FontWeight.Bold)
                                    }
                                }
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
                            OutlinedTextField(
                                value = bulkMinPriceInput,
                                onValueChange = {
                                    if (it.all { char -> char.isDigit() }) {
                                        bulkMinPriceInput = normalizePriceTextInput(it)
                                        bulkMinPriceInputError = null
                                    }
                                },
                                label = { Text("최소 가격 (원)") },
                                placeholder = { Text("예: 300000") },
                                singleLine = true,
                                keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
                                enabled = !isApplyingBulkSettings,
                                isError = bulkMinPriceInputError != null,
                                modifier = Modifier.fillMaxWidth(),
                            )
                            if (!bulkMinPriceInputError.isNullOrBlank()) {
                                Text(
                                    text = bulkMinPriceInputError ?: "",
                                    style = MaterialTheme.typography.labelSmall,
                                    color = MaterialTheme.colorScheme.error,
                                )
                            }
                            Text(
                                text = if (hasBelowDirectionInScope) {
                                    "이하 알림 항목에 최소 가격으로 적용됩니다."
                                } else {
                                    "현재 범위에는 이하 알림 항목이 없어 최소 가격은 적용되지 않습니다."
                                },
                                style = MaterialTheme.typography.labelSmall,
                                color = Color.Gray,
                            )
                            Button(
                                onClick = {
                                    val parsed = bulkMinPriceInput.toIntOrNull()
                                    if (parsed == null) {
                                        bulkMinPriceInputError = "숫자(예: 300000)를 입력해주세요."
                                    } else if (parsed < 0) {
                                        bulkMinPriceInputError = "0원 이상으로 입력해주세요."
                                    } else {
                                        pendingMinPrice = parsed
                                        showMinPriceConfirmDialog = true
                                    }
                                },
                                enabled = !isApplyingBulkSettings && hasBelowDirectionInScope,
                                modifier = Modifier.fillMaxWidth(),
                            ) {
                                Text("전체 최소 가격 적용")
                            }
                            OutlinedTextField(
                                value = bulkMaxPriceInput,
                                onValueChange = {
                                    if (it.all { char -> char.isDigit() }) {
                                        bulkMaxPriceInput = normalizePriceTextInput(it)
                                        bulkMaxPriceInputError = null
                                    }
                                },
                                label = { Text("최대 가격 (원)") },
                                placeholder = { Text("예: 900000") },
                                singleLine = true,
                                keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
                                enabled = !isApplyingBulkSettings,
                                isError = bulkMaxPriceInputError != null,
                                modifier = Modifier.fillMaxWidth(),
                            )
                            if (!bulkMaxPriceInputError.isNullOrBlank()) {
                                Text(
                                    text = bulkMaxPriceInputError ?: "",
                                    style = MaterialTheme.typography.labelSmall,
                                    color = MaterialTheme.colorScheme.error,
                                )
                            }
                            Text(
                                text = if (hasAboveDirectionInScope) {
                                    "이상 알림 항목에 최대 가격으로 적용됩니다."
                                } else {
                                    "현재 범위에는 이상 알림 항목이 없어 최대 가격은 적용되지 않습니다."
                                },
                                style = MaterialTheme.typography.labelSmall,
                                color = Color.Gray,
                            )
                            Button(
                                onClick = {
                                    val parsed = bulkMaxPriceInput.toIntOrNull()
                                    if (parsed == null) {
                                        bulkMaxPriceInputError = "숫자(예: 900000)를 입력해주세요."
                                    } else if (parsed < 0) {
                                        bulkMaxPriceInputError = "0원 이상으로 입력해주세요."
                                    } else {
                                        pendingMaxPrice = parsed
                                        showMaxPriceConfirmDialog = true
                                    }
                                },
                                enabled = !isApplyingBulkSettings && hasAboveDirectionInScope,
                                modifier = Modifier.fillMaxWidth(),
                            ) {
                                Text("전체 최대 가격 적용")
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

    if (showMinPriceConfirmDialog) {
        AlertDialog(
            onDismissRequest = { showMinPriceConfirmDialog = false },
            title = { Text("전체 최소 가격 변경") },
            text = {
                Text("$bulkScopeLabel 이하 알림 최소 가격을 ${formatKrwDisplay(pendingMinPrice)}로 변경할까요?")
            },
            confirmButton = {
                TextButton(
                    onClick = {
                        showMinPriceConfirmDialog = false
                        onBulkMinPriceApply(
                            pendingMinPrice,
                            applyToProductType,
                        )
                    }
                ) {
                    Text("확인")
                }
            },
            dismissButton = {
                TextButton(onClick = { showMinPriceConfirmDialog = false }) {
                    Text("취소")
                }
            },
        )
    }

    if (showMaxPriceConfirmDialog) {
        AlertDialog(
            onDismissRequest = { showMaxPriceConfirmDialog = false },
            title = { Text("전체 최대 가격 변경") },
            text = {
                Text("$bulkScopeLabel 이상 알림 최대 가격을 ${formatKrwDisplay(pendingMaxPrice)}로 변경할까요?")
            },
            confirmButton = {
                TextButton(
                    onClick = {
                        showMaxPriceConfirmDialog = false
                        onBulkMaxPriceApply(
                            pendingMaxPrice,
                            applyToProductType,
                        )
                    }
                ) {
                    Text("확인")
                }
            },
            dismissButton = {
                TextButton(onClick = { showMaxPriceConfirmDialog = false }) {
                    Text("취소")
                }
            },
        )
    }

    if (showWatchPriorityConfirmDialog) {
        AlertDialog(
            onDismissRequest = { showWatchPriorityConfirmDialog = false },
            title = { Text("알림 속도 변경") },
            text = {
                val priorityLabel = WATCH_PRIORITY_UI_OPTIONS
                    .firstOrNull { it.value == pendingBulkWatchPriority }
                    ?.label
                    ?: "보통"
                Text("$bulkScopeLabel 알림 속도를 $priorityLabel(으)로 모두 변경할까요?")
            },
            confirmButton = {
                TextButton(
                    onClick = {
                        showWatchPriorityConfirmDialog = false
                        onBulkWatchPriorityApply(
                            pendingBulkWatchPriority,
                            applyToProductType,
                        )
                    }
                ) {
                    Text("확인")
                }
            },
            dismissButton = {
                TextButton(onClick = { showWatchPriorityConfirmDialog = false }) {
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

private data class BulkPriceBoundsScopeState(
    val minPrice: Int?,
    val maxPrice: Int?,
    val hasBelowDirection: Boolean,
    val hasAboveDirection: Boolean,
)

private fun resolveBulkPriceBoundsScopeState(
    settings: List<UserFairPriceItem>,
): BulkPriceBoundsScopeState {
    if (settings.isEmpty()) {
        return BulkPriceBoundsScopeState(
            minPrice = null,
            maxPrice = null,
            hasBelowDirection = false,
            hasAboveDirection = false,
        )
    }

    val belowItems = settings.filter { item ->
        normalizeAlertDirection(
            item.user_alert_price_direction
                ?: item.effective_alert_price_direction
                ?: item.system_alert_price_direction
        ) == BELOW_OR_EQUAL_DIRECTION
    }
    val aboveItems = settings.filter { item ->
        normalizeAlertDirection(
            item.user_alert_price_direction
                ?: item.effective_alert_price_direction
                ?: item.system_alert_price_direction
        ) == ABOVE_OR_EQUAL_DIRECTION
    }

    val belowBounds = belowItems.map { it.user_min_price_krw ?: it.effective_min_price_krw }.distinct()
    val aboveBounds = aboveItems.map { it.user_max_price_krw ?: it.effective_max_price_krw }.distinct()

    return BulkPriceBoundsScopeState(
        minPrice = if (belowBounds.size == 1) belowBounds.firstOrNull() else null,
        maxPrice = if (aboveBounds.size == 1) aboveBounds.firstOrNull() else null,
        hasBelowDirection = belowItems.isNotEmpty(),
        hasAboveDirection = aboveItems.isNotEmpty(),
    )
}
