package com.boongtol.umtp_android.ui

import android.util.Log
import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import com.boongtol.umtp_android.network.*
import com.boongtol.umtp_android.user.UserPreferences
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import retrofit2.HttpException
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

class MacBookAirSettingsViewModel(private val userPreferences: UserPreferences) : ViewModel() {
    companion object {
        private const val ALERT_POLL_INTERVAL_MS = 10_000L
    }

    class Factory(private val userPreferences: UserPreferences) : ViewModelProvider.Factory {
        override fun <T : ViewModel> create(modelClass: Class<T>): T {
            @Suppress("UNCHECKED_CAST")
            return MacBookAirSettingsViewModel(userPreferences) as T
        }
    }

    private val _userId = MutableStateFlow(userPreferences.getUserId())
    val userId: StateFlow<String?> = _userId.asStateFlow()

    private val _units = MutableStateFlow<List<MacBookAirUnit>>(emptyList())
    val units: StateFlow<List<MacBookAirUnit>> = _units.asStateFlow()

    private val _userSettings = MutableStateFlow<List<UserFairPriceItem>>(emptyList())
    val userSettings: StateFlow<List<UserFairPriceItem>> = _userSettings.asStateFlow()

    private val _alerts = MutableStateFlow<List<AlertItem>>(emptyList())
    val alerts: StateFlow<List<AlertItem>> = _alerts.asStateFlow()

    private val _readGroupedAlerts = MutableStateFlow<Map<String, Map<String, List<AlertItem>>>>(emptyMap())
    val readGroupedAlerts: StateFlow<Map<String, Map<String, List<AlertItem>>>> = _readGroupedAlerts.asStateFlow()

    private val _isLoading = MutableStateFlow(false)
    val isLoading: StateFlow<Boolean> = _isLoading.asStateFlow()

    private val _errorMessage = MutableStateFlow<String?>(null)
    val errorMessage: StateFlow<String?> = _errorMessage.asStateFlow()

    private val _toastMessage = MutableStateFlow<String?>(null)
    val toastMessage: StateFlow<String?> = _toastMessage.asStateFlow()

    private val _savingItemKey = MutableStateFlow<String?>(null)
    val savingItemKey: StateFlow<String?> = _savingItemKey.asStateFlow()

    private val _isApplyingBulkSettings = MutableStateFlow(false)
    val isApplyingBulkSettings: StateFlow<Boolean> = _isApplyingBulkSettings.asStateFlow()

    private val _isSubmittingResaleTrade = MutableStateFlow(false)
    val isSubmittingResaleTrade: StateFlow<Boolean> = _isSubmittingResaleTrade.asStateFlow()

    private val _isRefreshingAlerts = MutableStateFlow(false)
    val isRefreshingAlerts: StateFlow<Boolean> = _isRefreshingAlerts.asStateFlow()

    private val _isRefreshingReadArchive = MutableStateFlow(false)
    val isRefreshingReadArchive: StateFlow<Boolean> = _isRefreshingReadArchive.asStateFlow()

    private val _isMarkingAllAlertsRead = MutableStateFlow(false)
    val isMarkingAllAlertsRead: StateFlow<Boolean> = _isMarkingAllAlertsRead.asStateFlow()

    private val _isClearingReadArchiveAll = MutableStateFlow(false)
    val isClearingReadArchiveAll: StateFlow<Boolean> = _isClearingReadArchiveAll.asStateFlow()

    private val _isClearingReadArchiveSelected = MutableStateFlow(false)
    val isClearingReadArchiveSelected: StateFlow<Boolean> = _isClearingReadArchiveSelected.asStateFlow()

    private val _alertsRefreshStatusMessage = MutableStateFlow<String?>(null)
    val alertsRefreshStatusMessage: StateFlow<String?> = _alertsRefreshStatusMessage.asStateFlow()

    private val _readArchiveRefreshStatusMessage = MutableStateFlow<String?>(null)
    val readArchiveRefreshStatusMessage: StateFlow<String?> = _readArchiveRefreshStatusMessage.asStateFlow()

    private val _lastAlertsRefreshLabel = MutableStateFlow<String?>(null)
    val lastAlertsRefreshLabel: StateFlow<String?> = _lastAlertsRefreshLabel.asStateFlow()

    private val _isRefreshingSettings = MutableStateFlow(false)
    val isRefreshingSettings: StateFlow<Boolean> = _isRefreshingSettings.asStateFlow()

    private val _settingsRefreshStatusMessage = MutableStateFlow<String?>(null)
    val settingsRefreshStatusMessage: StateFlow<String?> = _settingsRefreshStatusMessage.asStateFlow()

    private val _lastSettingsRefreshLabel = MutableStateFlow<String?>(null)
    val lastSettingsRefreshLabel: StateFlow<String?> = _lastSettingsRefreshLabel.asStateFlow()

    private val _refreshingRuleIds = MutableStateFlow<Set<Long>>(emptySet())
    val refreshingRuleIds: StateFlow<Set<Long>> = _refreshingRuleIds.asStateFlow()

    private val _ruleRefreshStatusMessages = MutableStateFlow<Map<Long, String>>(emptyMap())
    val ruleRefreshStatusMessages: StateFlow<Map<Long, String>> = _ruleRefreshStatusMessages.asStateFlow()

    private val _ruleLastRefreshLabels = MutableStateFlow<Map<Long, String>>(emptyMap())
    val ruleLastRefreshLabels: StateFlow<Map<Long, String>> = _ruleLastRefreshLabels.asStateFlow()

    private var isAlertRefreshInFlight: Boolean = false
    private var isSettingsRefreshInFlight: Boolean = false
    private var alertPollingJob: Job? = null

    init {
        _userId.value?.let {
            loadInitialData(it)
            startAlertPolling(it)
        }
    }

    private fun loadInitialData(uid: String) {
        viewModelScope.launch {
            _isLoading.value = true
            try {
                val unitsRefreshError = refreshUnitsInternal()
                val settingsRefreshError = refreshUserSettingsInternal(uid)

                if (unitsRefreshError != null || settingsRefreshError != null) {
                    val reasons = listOfNotNull(unitsRefreshError, settingsRefreshError)
                    _errorMessage.value = reasons.joinToString(" / ")
                }
                fetchAlerts(uid, showFeedback = false)
                fetchReadGroupedAlerts(uid, showFeedback = false)
            } catch (e: Exception) {
                _errorMessage.value = e.toSafeUserMessage(ErrorContext.NETWORK)
            } finally {
                _isLoading.value = false
            }
        }
    }

    fun loadUserSettings(uid: String) {
        viewModelScope.launch {
            refreshUserSettingsInternal(uid)
        }
    }

    fun refreshSettings(uid: String, showFeedback: Boolean = true) {
        if (isSettingsRefreshInFlight) {
            return
        }
        viewModelScope.launch {
            isSettingsRefreshInFlight = true
            if (showFeedback) {
                _isRefreshingSettings.value = true
                _settingsRefreshStatusMessage.value = "새로고침 중..."
            }
            try {
                val refreshSavedAtError = refreshActiveRulesSavedAtInternal(uid)
                val unitsRefreshError = refreshUnitsInternal()
                val settingsRefreshError = refreshUserSettingsInternal(uid)
                fetchAlerts(uid, showFeedback = false)
                fetchReadGroupedAlerts(uid, showFeedback = false)

                if (showFeedback) {
                    if (refreshSavedAtError == null && unitsRefreshError == null && settingsRefreshError == null) {
                        val nowMillis = System.currentTimeMillis()
                        _settingsRefreshStatusMessage.value = "새로고침됨"
                        _lastSettingsRefreshLabel.value =
                            "마지막 새로고침: ${formatRefreshTimeLabel(nowMillis)}"
                        val refreshedRuleIds = _userSettings.value
                            .asSequence()
                            .filter { it.has_user_override && it.enabled && it.id != null }
                            .mapNotNull { it.id }
                            .toSet()
                        applyRuleRefreshSuccessMarkers(refreshedRuleIds, nowMillis)
                    } else {
                        val reasons = listOfNotNull(refreshSavedAtError, unitsRefreshError, settingsRefreshError)
                        _settingsRefreshStatusMessage.value = "새로고침 실패"
                        _toastMessage.value = reasons.joinToString(" / ")
                    }
                }
            } catch (e: Exception) {
                if (showFeedback) {
                    _settingsRefreshStatusMessage.value = "새로고침 실패"
                    _toastMessage.value = e.toSafeUserMessage(ErrorContext.NETWORK)
                }
            } finally {
                if (showFeedback) {
                    _isRefreshingSettings.value = false
                }
                isSettingsRefreshInFlight = false
            }
        }
    }

    fun refreshSingleRuleSavedAt(uid: String, ruleId: Long) {
        if (ruleId <= 0L) {
            _toastMessage.value = "새로고침 실패: 유효하지 않은 조건입니다."
            return
        }

        if (_refreshingRuleIds.value.contains(ruleId)) {
            return
        }

        viewModelScope.launch {
            _refreshingRuleIds.value = _refreshingRuleIds.value + ruleId
            _ruleRefreshStatusMessages.value = _ruleRefreshStatusMessages.value + (ruleId to "새로고침 중...")
            try {
                val response = UmtpApiClient.apiService.refreshSingleUserRuleSavedAt(uid, ruleId)
                if (response.ok) {
                    val nowMillis = System.currentTimeMillis()
                    applyRuleRefreshSuccessMarkers(setOf(ruleId), nowMillis)
                    refreshUserSettingsInternal(uid)
                } else {
                    _ruleRefreshStatusMessages.value = _ruleRefreshStatusMessages.value + (ruleId to "새로고침 실패")
                    _toastMessage.value = resolveSafeErrorMessage(
                        context = ErrorContext.NETWORK,
                        rawMessage = response.message,
                        rawReason = response.reason,
                    )
                }
            } catch (e: Exception) {
                _ruleRefreshStatusMessages.value = _ruleRefreshStatusMessages.value + (ruleId to "새로고침 실패")
                _toastMessage.value = e.toSafeUserMessage(ErrorContext.NETWORK)
            } finally {
                _refreshingRuleIds.value = _refreshingRuleIds.value - ruleId
            }
        }
    }

    fun fetchAlerts(uid: String, showFeedback: Boolean = false) {
        if (isAlertRefreshInFlight) {
            return
        }
        viewModelScope.launch {
            isAlertRefreshInFlight = true
            if (showFeedback) {
                _isRefreshingAlerts.value = true
                _alertsRefreshStatusMessage.value = "새로고침 중..."
            }
            try {
                val response = UmtpApiClient.apiService.getAlerts(uid, isRead = "0")
                if (response.ok) {
                    _alerts.value = response.items.sortedByDescending { it.created_at }
                    if (showFeedback) {
                        _alertsRefreshStatusMessage.value = "방금 새로고침됨"
                        _lastAlertsRefreshLabel.value =
                            "마지막 새로고침: ${formatRefreshTimeLabel(System.currentTimeMillis())}"
                    }
                } else if (showFeedback) {
                    _alertsRefreshStatusMessage.value = "새로고침 실패"
                    _toastMessage.value = resolveSafeErrorMessage(
                        context = ErrorContext.NETWORK,
                        rawMessage = response.message,
                        rawReason = response.reason,
                    )
                }
            } catch (e: Exception) {
                if (showFeedback) {
                    _alertsRefreshStatusMessage.value = "새로고침 실패"
                    _toastMessage.value = e.toSafeUserMessage(ErrorContext.NETWORK)
                }
            } finally {
                if (showFeedback) {
                    _isRefreshingAlerts.value = false
                }
                isAlertRefreshInFlight = false
            }
        }
    }

    fun fetchReadGroupedAlerts(uid: String, showFeedback: Boolean = false) {
        viewModelScope.launch {
            if (showFeedback) {
                _isRefreshingReadArchive.value = true
                _readArchiveRefreshStatusMessage.value = "새로고침 중..."
            }
            try {
                val response = UmtpApiClient.apiService.getGroupedReadAlerts(uid)
                if (response.ok) {
                    _readGroupedAlerts.value = response.groups
                    if (showFeedback) {
                        _readArchiveRefreshStatusMessage.value = "방금 새로고침됨"
                    }
                } else if (showFeedback) {
                    _readArchiveRefreshStatusMessage.value = "새로고침 실패"
                    _toastMessage.value = resolveSafeErrorMessage(
                        context = ErrorContext.NETWORK,
                        rawMessage = response.message,
                        rawReason = response.reason,
                    )
                }
            } catch (e: Exception) {
                if (showFeedback) {
                    _readArchiveRefreshStatusMessage.value = "새로고침 실패"
                    _toastMessage.value = e.toSafeUserMessage(ErrorContext.NETWORK)
                }
            } finally {
                if (showFeedback) {
                    _isRefreshingReadArchive.value = false
                }
            }
        }
    }

    fun markAlertAsRead(
        uid: String,
        alertEventId: Long,
        showFeedback: Boolean = false,
        onComplete: ((Boolean) -> Unit)? = null,
    ) {
        if (alertEventId <= 0L) {
            onComplete?.invoke(false)
            return
        }
        viewModelScope.launch {
            try {
                val response = markAlertEventReadWithFallback(alertEventId, uid)
                if (response.ok) {
                    onComplete?.invoke(true)
                } else {
                    if (showFeedback) {
                        _toastMessage.value = resolveSafeErrorMessage(
                            context = ErrorContext.UNKNOWN,
                            rawMessage = response.message,
                            rawReason = response.reason,
                        )
                    }
                    onComplete?.invoke(false)
                }
            } catch (e: Exception) {
                if (showFeedback) {
                    _toastMessage.value = e.toSafeUserMessage(ErrorContext.NETWORK)
                }
                onComplete?.invoke(false)
            }
        }
    }

    fun markAllAlertsAsRead(uid: String) {
        if (_isMarkingAllAlertsRead.value) {
            return
        }
        viewModelScope.launch {
            _isMarkingAllAlertsRead.value = true
            try {
                val response = markAllAlertsReadWithFallback(uid)
                if (response.ok) {
                    _toastMessage.value = response.message ?: "모두 읽음 처리 완료"
                    fetchAlerts(uid, showFeedback = false)
                    fetchReadGroupedAlerts(uid, showFeedback = false)
                } else {
                    _toastMessage.value = resolveSafeErrorMessage(
                        context = ErrorContext.UNKNOWN,
                        rawMessage = response.message,
                        rawReason = response.reason,
                    )
                }
            } catch (e: Exception) {
                _toastMessage.value = e.toSafeUserMessage(ErrorContext.NETWORK)
            } finally {
                _isMarkingAllAlertsRead.value = false
            }
        }
    }

    private suspend fun markAlertEventReadWithFallback(
        alertEventId: Long,
        userId: String,
    ): MarkAlertReadResponse {
        return try {
            UmtpApiClient.apiService.markAlertEventRead(alertEventId, userId)
        } catch (error: Exception) {
            if (!shouldFallbackToPostForReadActions(error)) {
                throw error
            }
            UmtpApiClient.apiService.markAlertEventReadPost(alertEventId, userId)
        }
    }

    private suspend fun markAllAlertsReadWithFallback(userId: String): MarkAllAlertsReadResponse {
        return try {
            UmtpApiClient.apiService.markAllAlertEventsRead(userId)
        } catch (error: Exception) {
            if (!shouldFallbackToPostForReadActions(error)) {
                throw error
            }
            UmtpApiClient.apiService.markAllAlertEventsReadPost(userId)
        }
    }

    private fun shouldFallbackToPostForReadActions(error: Throwable): Boolean {
        val statusCode = (error as? HttpException)?.code() ?: return false
        return statusCode == 404 || statusCode == 405 || statusCode == 501
    }

    fun clearAllReadArchive(uid: String) {
        if (_isClearingReadArchiveAll.value) {
            return
        }
        viewModelScope.launch {
            _isClearingReadArchiveAll.value = true
            try {
                val response = UmtpApiClient.apiService.clearAllReadArchive(uid)
                if (response.ok) {
                    val clearedCount = response.cleared_count ?: 0
                    _toastMessage.value = response.message ?: "읽음 보관함 전체 비우기 완료 (${clearedCount}건)"
                    fetchReadGroupedAlerts(uid, showFeedback = false)
                } else {
                    _toastMessage.value = resolveSafeErrorMessage(
                        context = ErrorContext.UNKNOWN,
                        rawMessage = response.message,
                        rawReason = response.reason,
                    )
                }
            } catch (e: Exception) {
                _toastMessage.value = e.toSafeUserMessage(ErrorContext.NETWORK)
            } finally {
                _isClearingReadArchiveAll.value = false
            }
        }
    }

    fun clearSelectedReadArchive(uid: String, alertEventIds: List<Long>) {
        if (_isClearingReadArchiveSelected.value) {
            return
        }
        val normalizedIds = alertEventIds
            .filter { it > 0L }
            .distinct()
        if (normalizedIds.isEmpty()) {
            _toastMessage.value = "선택된 읽음 알림이 없습니다."
            return
        }

        viewModelScope.launch {
            _isClearingReadArchiveSelected.value = true
            try {
                val response = UmtpApiClient.apiService.clearSelectedReadArchive(
                    uid,
                    ClearSelectedReadArchiveRequest(alert_event_ids = normalizedIds),
                )
                if (response.ok) {
                    val clearedCount = response.cleared_count ?: 0
                    val skippedCount = response.skipped_count ?: 0
                    _toastMessage.value = if (skippedCount > 0) {
                        "선택 비우기 완료 (${clearedCount}건 비움, ${skippedCount}건 건너뜀)"
                    } else {
                        "선택 비우기 완료 (${clearedCount}건)"
                    }
                    fetchReadGroupedAlerts(uid, showFeedback = false)
                } else {
                    _toastMessage.value = resolveSafeErrorMessage(
                        context = ErrorContext.UNKNOWN,
                        rawMessage = response.message,
                        rawReason = response.reason,
                    )
                }
            } catch (e: Exception) {
                _toastMessage.value = e.toSafeUserMessage(ErrorContext.NETWORK)
            } finally {
                _isClearingReadArchiveSelected.value = false
            }
        }
    }

    private fun startAlertPolling(uid: String) {
        alertPollingJob?.cancel()
        alertPollingJob = viewModelScope.launch {
            while (true) {
                fetchAlerts(uid, showFeedback = false)
                delay(ALERT_POLL_INTERVAL_MS)
            }
        }
    }

    override fun onCleared() {
        alertPollingJob?.cancel()
        alertPollingJob = null
        super.onCleared()
    }

    fun registerUser(userId: String, deviceId: String?) {
        val trimmedUserId = userId.trim()
        val trimmedDeviceId = deviceId?.trim().orEmpty()
        if (trimmedUserId.length < 2) {
            _toastMessage.value = "User ID는 2자 이상이어야 합니다."
            return
        }
        if (trimmedDeviceId.isEmpty()) {
            _toastMessage.value = "기기 식별값(device_id)을 확인할 수 없습니다."
            return
        }

        viewModelScope.launch {
            _isLoading.value = true
            try {
                val response = UmtpApiClient.apiService.registerUser(
                    UserRegisterRequest(
                        user_id = trimmedUserId,
                        device_id = trimmedDeviceId
                    )
                )

                Log.d("UMTP_NET", "Register Response: ok=${response.ok}, user_id=${response.user_id}, message=${response.message}")

                if (response.ok) {
                    val effectiveUserId = response.user_id?.trim()
                        ?.takeIf { it.isNotEmpty() }
                        ?: trimmedUserId
                    userPreferences.setUserId(effectiveUserId)
                    _userId.value = effectiveUserId
                    loadInitialData(effectiveUserId)
                    startAlertPolling(effectiveUserId)
                    _toastMessage.value = response.message ?: "등록 완료"
                } else {
                    _toastMessage.value = resolveSafeErrorMessage(
                        context = ErrorContext.UNKNOWN,
                        rawMessage = response.message,
                        rawReason = response.reason,
                    )
                }
            } catch (e: Exception) {
                Log.e("UMTP_NET", "Register Error", e)
                _toastMessage.value = e.toSafeUserMessage(ErrorContext.NETWORK)
            } finally {
                _isLoading.value = false
            }
        }
    }

    fun upsertItem(
        unit: MacBookAirUnit,
        fairPrice: Int,
        desiredPrice: Int,
        alertPriceDirection: String,
        enabled: Boolean,
        conditionChangeCandidateNoticeEnabled: Boolean,
        searchKeyword: String?,
        priority: String,
        boundPrice: Int?
    ) {
        val uid = _userId.value ?: return
        val itemKey = "${unit.chip}-${unit.screen_inch}-${unit.ram_gb}-${unit.ssd_gb}"

        if (fairPrice <= 0 || desiredPrice <= 0) {
            _toastMessage.value = "시장가와 알림 기준 가격은 1원 이상이어야 합니다."
            return
        }

        val dropRatePercent = computeAlertDropRatePercent(fairPrice, desiredPrice)
        if (dropRatePercent == null) {
            _toastMessage.value = "시장가와의 차이(%)를 계산할 수 없습니다."
            return
        }
        if (boundPrice != null && boundPrice < 0) {
            _toastMessage.value = "최소/최대 가격은 0원 이상이어야 합니다."
            return
        }

        viewModelScope.launch {
            _savingItemKey.value = itemKey
            try {
                val normalizedDirection = normalizeAlertDirection(alertPriceDirection)
                val boundsRequest = buildAlertBoundsRequest(
                    alertPriceDirection = normalizedDirection,
                    boundPriceKrw = boundPrice,
                )
                val request = UserFairPriceUpsertRequest(
                    user_id = uid,
                    product_type = unit.product_type,
                    chip = unit.chip,
                    screen_inch = unit.screen_inch,
                    ram_gb = unit.ram_gb,
                    ssd_gb = unit.ssd_gb,
                    fair_price_krw = fairPrice,
                    alert_drop_rate_percent = dropRatePercent,
                    alert_price_direction = normalizedDirection,
                    min_price_krw = boundsRequest.min_price_krw,
                    max_price_krw = boundsRequest.max_price_krw,
                    enabled = enabled,
                    condition_change_candidate_notice_enabled = conditionChangeCandidateNoticeEnabled,
                    search_keyword = searchKeyword?.trim()?.ifEmpty { null },
                    poll_interval_seconds = 60,
                    priority = normalizeWatchPriority(priority),
                )
                val response = UmtpApiClient.apiService.upsertUserFairPrice(request)
                if (response.ok) {
                    _toastMessage.value = if (enabled) {
                        if (response.immediate_poll_requested == true) {
                            "저장 완료. 즉시 검색을 요청했어요."
                        } else {
                            "저장은 완료됐지만, 즉시 검색 요청은 보내지 못했어요. 잠시 후 다시 시도해 주세요."
                        }
                    } else {
                        "저장 완료."
                    }
                    loadUserSettings(uid)
                } else {
                    _toastMessage.value = resolveSafeErrorMessage(
                        context = ErrorContext.SAVE,
                        rawMessage = response.message,
                        rawReason = response.reason,
                    )
                }
            } catch (e: Exception) {
                _toastMessage.value = e.toSafeUserMessage(ErrorContext.SAVE)
            } finally {
                _savingItemKey.value = null
            }
        }
    }

    fun bulkSetAlertsEnabled(
        enabled: Boolean,
        productType: String? = null,
        chip: String? = null,
        screenInch: Int? = null,
    ) {
        val uid = _userId.value ?: return
        if (_isApplyingBulkSettings.value) {
            return
        }
        val normalizedChip = chip?.trim()?.takeIf { it.isNotEmpty() }

        viewModelScope.launch {
            _isApplyingBulkSettings.value = true
            try {
                applyBulkUpsertFallback(
                    uid = uid,
                    productType = productType,
                    chip = normalizedChip,
                    screenInch = screenInch,
                    enabledOverride = enabled,
                )
                _toastMessage.value = if (enabled) {
                    "전체 알림이 켜졌습니다."
                } else {
                    "전체 알림이 꺼졌습니다."
                }
                refreshUserSettingsInternal(uid)
                fetchAlerts(uid, showFeedback = false)
                fetchReadGroupedAlerts(uid, showFeedback = false)
            } catch (e: Exception) {
                _toastMessage.value = e.toSafeUserMessage(ErrorContext.SAVE)
            } finally {
                _isApplyingBulkSettings.value = false
            }
        }
    }

    fun bulkSetDropRatePercent(
        dropRatePercent: Double,
        productType: String? = null,
        chip: String? = null,
        screenInch: Int? = null,
    ) {
        val uid = _userId.value ?: return
        if (_isApplyingBulkSettings.value) {
            return
        }
        val normalizedChip = chip?.trim()?.takeIf { it.isNotEmpty() }

        viewModelScope.launch {
            _isApplyingBulkSettings.value = true
            try {
                applyBulkUpsertFallback(
                    uid = uid,
                    productType = productType,
                    chip = normalizedChip,
                    screenInch = screenInch,
                    dropRatePercentOverride = dropRatePercent,
                )
                _toastMessage.value = "전체 차이 %가 변경되었습니다."
                refreshUserSettingsInternal(uid)
                fetchAlerts(uid, showFeedback = false)
                fetchReadGroupedAlerts(uid, showFeedback = false)
            } catch (e: Exception) {
                _toastMessage.value = e.toSafeUserMessage(ErrorContext.SAVE)
            } finally {
                _isApplyingBulkSettings.value = false
            }
        }
    }

    fun bulkSetMinPrice(
        minPrice: Int,
        productType: String? = null,
        chip: String? = null,
        screenInch: Int? = null,
    ) {
        val uid = _userId.value ?: return
        if (_isApplyingBulkSettings.value) {
            return
        }
        if (minPrice < 0) {
            _toastMessage.value = "최소 가격은 0원 이상이어야 합니다."
            return
        }
        val normalizedChip = chip?.trim()?.takeIf { it.isNotEmpty() }

        viewModelScope.launch {
            _isApplyingBulkSettings.value = true
            try {
                applyBulkUpsertFallback(
                    uid = uid,
                    productType = productType,
                    chip = normalizedChip,
                    screenInch = screenInch,
                    minPriceOverride = minPrice,
                    applyMinPriceOverride = true,
                )
                _toastMessage.value = "최소 가격이 변경되었습니다."
                refreshUserSettingsInternal(uid)
            } catch (e: Exception) {
                _toastMessage.value = e.toSafeUserMessage(ErrorContext.SAVE)
            } finally {
                _isApplyingBulkSettings.value = false
            }
        }
    }

    fun bulkSetMaxPrice(
        maxPrice: Int,
        productType: String? = null,
        chip: String? = null,
        screenInch: Int? = null,
    ) {
        val uid = _userId.value ?: return
        if (_isApplyingBulkSettings.value) {
            return
        }
        if (maxPrice < 0) {
            _toastMessage.value = "최대 가격은 0원 이상이어야 합니다."
            return
        }
        val normalizedChip = chip?.trim()?.takeIf { it.isNotEmpty() }

        viewModelScope.launch {
            _isApplyingBulkSettings.value = true
            try {
                applyBulkUpsertFallback(
                    uid = uid,
                    productType = productType,
                    chip = normalizedChip,
                    screenInch = screenInch,
                    maxPriceOverride = maxPrice,
                    applyMaxPriceOverride = true,
                )
                _toastMessage.value = "최대 가격이 변경되었습니다."
                refreshUserSettingsInternal(uid)
            } catch (e: Exception) {
                _toastMessage.value = e.toSafeUserMessage(ErrorContext.SAVE)
            } finally {
                _isApplyingBulkSettings.value = false
            }
        }
    }

    fun bulkSetConditionChangeCandidateNoticeEnabled(
        enabled: Boolean,
        productType: String? = null,
        chip: String? = null,
        screenInch: Int? = null,
    ) {
        val uid = _userId.value ?: return
        if (_isApplyingBulkSettings.value) {
            return
        }
        val normalizedChip = chip?.trim()?.takeIf { it.isNotEmpty() }

        viewModelScope.launch {
            _isApplyingBulkSettings.value = true
            try {
                applyBulkUpsertFallback(
                    uid = uid,
                    productType = productType,
                    chip = normalizedChip,
                    screenInch = screenInch,
                    conditionChangeCandidateNoticeEnabledOverride = enabled,
                )
                _toastMessage.value = if (enabled) {
                    "조건 변경 후보 알림이 켜졌습니다."
                } else {
                    "조건 변경 후보 알림이 꺼졌습니다."
                }
                refreshUserSettingsInternal(uid)
            } catch (e: Exception) {
                _toastMessage.value = e.toSafeUserMessage(ErrorContext.SAVE)
            } finally {
                _isApplyingBulkSettings.value = false
            }
        }
    }

    fun bulkSetWatchPriority(
        priority: String,
        productType: String? = null,
        chip: String? = null,
        screenInch: Int? = null,
    ) {
        val uid = _userId.value ?: return
        if (_isApplyingBulkSettings.value) {
            return
        }
        val normalizedChip = chip?.trim()?.takeIf { it.isNotEmpty() }
        val normalizedPriority = normalizeWatchPriority(priority)

        viewModelScope.launch {
            _isApplyingBulkSettings.value = true
            try {
                applyBulkUpsertFallback(
                    uid = uid,
                    productType = productType,
                    chip = normalizedChip,
                    screenInch = screenInch,
                    priorityOverride = normalizedPriority,
                )
                _toastMessage.value = "알림 속도가 변경되었습니다."
                refreshUserSettingsInternal(uid)
            } catch (e: Exception) {
                _toastMessage.value = e.toSafeUserMessage(ErrorContext.SAVE)
            } finally {
                _isApplyingBulkSettings.value = false
            }
        }
    }

    fun resetFairPricesToSystem(
        productType: String? = null,
        chip: String? = null,
        screenInch: Int? = null,
    ) {
        val uid = _userId.value ?: return
        if (_isApplyingBulkSettings.value) {
            return
        }
        val normalizedChip = chip?.trim()?.takeIf { it.isNotEmpty() }

        viewModelScope.launch {
            _isApplyingBulkSettings.value = true
            try {
                applyBulkUpsertFallback(
                    uid = uid,
                    productType = productType,
                    chip = normalizedChip,
                    screenInch = screenInch,
                    useSystemFairPrice = true,
                )
                _toastMessage.value = "시스템 기준 시장가로 업데이트했습니다."
                refreshUserSettingsInternal(uid)
                fetchAlerts(uid, showFeedback = false)
                fetchReadGroupedAlerts(uid, showFeedback = false)
            } catch (e: Exception) {
                _toastMessage.value = e.toSafeUserMessage(ErrorContext.SAVE)
            } finally {
                _isApplyingBulkSettings.value = false
            }
        }
    }

    fun upsertResaleTradeAfterPurchase(
        productId: String?,
        url: String?,
        updates: Map<String, Any?>,
    ) {
        val uid = _userId.value ?: return
        if (_isSubmittingResaleTrade.value) {
            return
        }

        val normalizedProductId = productId?.trim()?.ifEmpty { null }
        val normalizedUrl = url?.trim()?.ifEmpty { null }
        if (normalizedProductId == null && normalizedUrl == null) {
            _toastMessage.value = "product_id 또는 url 중 하나는 필요합니다."
            return
        }

        viewModelScope.launch {
            _isSubmittingResaleTrade.value = true
            try {
                val normalizedUpdates = updates.filterValues { value -> value != null }
                val response = UmtpApiClient.apiService.upsertResaleTradeAfterPurchase(
                    ResaleTradeAfterPurchaseUpsertRequest(
                        user_id = uid,
                        source = "joongna",
                        product_id = normalizedProductId,
                        url = normalizedUrl,
                        updates = normalizedUpdates,
                    )
                )
                if (response.ok) {
                    val stage = response.current_stage?.takeIf { it.isNotBlank() } ?: "-"
                    _toastMessage.value = "구매 후 데이터 저장 완료 (stage: $stage)"
                } else {
                    _toastMessage.value = resolveSafeErrorMessage(
                        context = ErrorContext.SAVE,
                        rawMessage = response.message,
                        rawReason = response.reason,
                    )
                }
            } catch (e: Exception) {
                _toastMessage.value = e.toSafeUserMessage(ErrorContext.SAVE)
            } finally {
                _isSubmittingResaleTrade.value = false
            }
        }
    }

    fun upsertResaleTradeAfterResale(
        productId: String?,
        url: String?,
        updates: Map<String, Any?>,
    ) {
        val uid = _userId.value ?: return
        if (_isSubmittingResaleTrade.value) {
            return
        }

        val normalizedProductId = productId?.trim()?.ifEmpty { null }
        val normalizedUrl = url?.trim()?.ifEmpty { null }
        if (normalizedProductId == null && normalizedUrl == null) {
            _toastMessage.value = "product_id 또는 url 중 하나는 필요합니다."
            return
        }

        viewModelScope.launch {
            _isSubmittingResaleTrade.value = true
            try {
                val normalizedUpdates = updates.filterValues { value -> value != null }
                val response = UmtpApiClient.apiService.upsertResaleTradeAfterResale(
                    ResaleTradeAfterResaleUpsertRequest(
                        user_id = uid,
                        source = "joongna",
                        product_id = normalizedProductId,
                        url = normalizedUrl,
                        updates = normalizedUpdates,
                    )
                )
                if (response.ok) {
                    val stage = response.current_stage?.takeIf { it.isNotBlank() } ?: "-"
                    _toastMessage.value = "되팔이 후 데이터 저장 완료 (stage: $stage)"
                } else {
                    _toastMessage.value = resolveSafeErrorMessage(
                        context = ErrorContext.SAVE,
                        rawMessage = response.message,
                        rawReason = response.reason,
                    )
                }
            } catch (e: Exception) {
                _toastMessage.value = e.toSafeUserMessage(ErrorContext.SAVE)
            } finally {
                _isSubmittingResaleTrade.value = false
            }
        }
    }

    fun clearToastMessage() {
        _toastMessage.value = null
    }

    private suspend fun refreshUnitsInternal(): String? {
        return try {
            val unitsResponse = UmtpApiClient.apiService.getMacBookAirUnits()
            if (!unitsResponse.ok) {
                resolveSafeErrorMessage(
                    context = ErrorContext.NETWORK,
                    rawMessage = unitsResponse.message,
                    rawReason = unitsResponse.reason,
                )
            } else {
                _units.value = unitsResponse.units
                null
            }
        } catch (e: Exception) {
            e.toSafeUserMessage(ErrorContext.NETWORK)
        }
    }

    private suspend fun refreshUserSettingsInternal(uid: String): String? {
        return try {
            val response = UmtpApiClient.apiService.getUserFairPrices(uid)
            if (!response.ok) {
                resolveSafeErrorMessage(
                    context = ErrorContext.NETWORK,
                    rawMessage = response.message,
                    rawReason = response.reason,
                )
            } else {
                _userSettings.value = response.items
                pruneRuleRefreshState(response.items.mapNotNull { it.id }.toSet())
                null
            }
        } catch (e: Exception) {
            e.toSafeUserMessage(ErrorContext.NETWORK)
        }
    }

    private suspend fun refreshActiveRulesSavedAtInternal(uid: String): String? {
        return try {
            val response = UmtpApiClient.apiService.refreshUserRulesSavedAt(uid)
            if (!response.ok) {
                resolveSafeErrorMessage(
                    context = ErrorContext.NETWORK,
                    rawMessage = response.message,
                    rawReason = response.reason,
                )
            } else {
                null
            }
        } catch (e: Exception) {
            e.toSafeUserMessage(ErrorContext.NETWORK)
        }
    }

    private suspend fun applyBulkUpsertFallback(
        uid: String,
        productType: String?,
        chip: String? = null,
        screenInch: Int? = null,
        enabledOverride: Boolean? = null,
        conditionChangeCandidateNoticeEnabledOverride: Boolean? = null,
        priorityOverride: String? = null,
        dropRatePercentOverride: Double? = null,
        minPriceOverride: Int? = null,
        applyMinPriceOverride: Boolean = false,
        maxPriceOverride: Int? = null,
        applyMaxPriceOverride: Boolean = false,
        useSystemFairPrice: Boolean = false,
    ) {
        val scopedSettings = _userSettings.value.filter { item ->
            matchesBulkScope(
                item = item,
                productType = productType,
                chip = chip,
                screenInch = screenInch,
            )
        }

        if (scopedSettings.isEmpty()) {
            return
        }

        scopedSettings.forEach { setting ->
            val fairPrice = resolveFallbackFairPrice(setting, useSystemFairPrice) ?: return@forEach
            val dropRatePercent = dropRatePercentOverride
                ?: setting.user_alert_drop_rate_percent
                ?: setting.effective_alert_drop_rate_percent
                ?: setting.system_alert_drop_rate_percent
                ?: 20.0
            val direction = normalizeAlertDirection(
                setting.user_alert_price_direction
                    ?: setting.effective_alert_price_direction
                    ?: setting.system_alert_price_direction
            )
            var boundPriceForDirection = if (direction == ABOVE_OR_EQUAL_DIRECTION) {
                setting.user_max_price_krw ?: setting.effective_max_price_krw
            } else {
                setting.user_min_price_krw ?: setting.effective_min_price_krw
            }
            if (direction == ABOVE_OR_EQUAL_DIRECTION && applyMaxPriceOverride) {
                boundPriceForDirection = maxPriceOverride
            }
            if (direction == BELOW_OR_EQUAL_DIRECTION && applyMinPriceOverride) {
                boundPriceForDirection = minPriceOverride
            }
            val boundsRequest = buildAlertBoundsRequest(
                alertPriceDirection = direction,
                boundPriceKrw = boundPriceForDirection,
            )
            val request = UserFairPriceUpsertRequest(
                user_id = uid,
                product_type = setting.product_type,
                chip = setting.chip,
                screen_inch = setting.screen_inch,
                ram_gb = setting.ram_gb,
                ssd_gb = setting.ssd_gb,
                fair_price_krw = fairPrice,
                alert_drop_rate_percent = dropRatePercent,
                alert_price_direction = direction,
                min_price_krw = boundsRequest.min_price_krw,
                max_price_krw = boundsRequest.max_price_krw,
                enabled = enabledOverride ?: setting.enabled,
                condition_change_candidate_notice_enabled = conditionChangeCandidateNoticeEnabledOverride
                    ?: setting.condition_change_candidate_notice_enabled,
                search_keyword = setting.custom_search_keyword?.trim()?.ifEmpty { null },
                poll_interval_seconds = setting.poll_interval_seconds ?: 60,
                priority = priorityOverride ?: normalizeWatchPriority(setting.priority),
            )
            val response = UmtpApiClient.apiService.upsertUserFairPrice(request)
            if (!response.ok) {
                throw IllegalStateException("bulk_fallback_upsert_failed")
            }
        }
    }

    private fun resolveFallbackFairPrice(setting: UserFairPriceItem, useSystemFairPrice: Boolean): Int? {
        val preferred = if (useSystemFairPrice) {
            setting.system_fair_price_krw
        } else {
            setting.user_fair_price_krw ?: setting.effective_fair_price_krw ?: setting.system_fair_price_krw
        }
        return preferred?.takeIf { it > 0 }
    }

    private fun matchesBulkScope(
        item: UserFairPriceItem,
        productType: String?,
        chip: String?,
        screenInch: Int?,
    ): Boolean {
        if (!productType.isNullOrBlank() && item.product_type != productType) {
            return false
        }
        if (!chip.isNullOrBlank() && item.chip != chip) {
            return false
        }
        if (screenInch != null && item.screen_inch != screenInch) {
            return false
        }
        return true
    }

    private fun formatRefreshTimeLabel(epochMillis: Long): String {
        val formatter = SimpleDateFormat("HH:mm", Locale.KOREA)
        return formatter.format(Date(epochMillis))
    }

    private fun applyRuleRefreshSuccessMarkers(ruleIds: Set<Long>, epochMillis: Long) {
        if (ruleIds.isEmpty()) {
            return
        }
        val timeLabel = "마지막 새로고침: ${formatRefreshTimeLabel(epochMillis)}"
        val nextStatus = _ruleRefreshStatusMessages.value.toMutableMap()
        val nextLabels = _ruleLastRefreshLabels.value.toMutableMap()
        ruleIds.forEach { ruleId ->
            nextStatus[ruleId] = "새로고침됨"
            nextLabels[ruleId] = timeLabel
        }
        _ruleRefreshStatusMessages.value = nextStatus
        _ruleLastRefreshLabels.value = nextLabels
    }

    private fun pruneRuleRefreshState(validRuleIds: Set<Long>) {
        if (validRuleIds.isEmpty()) {
            _refreshingRuleIds.value = emptySet()
            _ruleRefreshStatusMessages.value = emptyMap()
            _ruleLastRefreshLabels.value = emptyMap()
            return
        }

        _refreshingRuleIds.value = _refreshingRuleIds.value.filterTo(mutableSetOf()) { it in validRuleIds }
        _ruleRefreshStatusMessages.value = _ruleRefreshStatusMessages.value.filterKeys { it in validRuleIds }
        _ruleLastRefreshLabels.value = _ruleLastRefreshLabels.value.filterKeys { it in validRuleIds }
    }
}
