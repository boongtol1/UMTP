package com.boongtol.umtp_android.ui

import android.util.Log
import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import com.boongtol.umtp_android.network.*
import com.boongtol.umtp_android.user.UserPreferences
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import java.net.ConnectException
import java.net.SocketTimeoutException
import java.net.UnknownHostException
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

class MacBookAirSettingsViewModel(private val userPreferences: UserPreferences) : ViewModel() {

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

    private val _isRefreshingAlerts = MutableStateFlow(false)
    val isRefreshingAlerts: StateFlow<Boolean> = _isRefreshingAlerts.asStateFlow()

    private val _isRefreshingReadArchive = MutableStateFlow(false)
    val isRefreshingReadArchive: StateFlow<Boolean> = _isRefreshingReadArchive.asStateFlow()

    private val _isMarkingAllAlertsRead = MutableStateFlow(false)
    val isMarkingAllAlertsRead: StateFlow<Boolean> = _isMarkingAllAlertsRead.asStateFlow()

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
                    _errorMessage.value = "데이터 로딩 에러: ${reasons.joinToString(" / ")}"
                }
                fetchAlerts(uid, showFeedback = false)
                fetchReadGroupedAlerts(uid, showFeedback = false)
            } catch (e: Exception) {
                _errorMessage.value = "데이터 로딩 에러: ${e.localizedMessage}"
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
                        _toastMessage.value = "새로고침 실패: ${reasons.joinToString(" / ")}"
                    }
                }
            } catch (e: Exception) {
                if (showFeedback) {
                    _settingsRefreshStatusMessage.value = "새로고침 실패"
                    _toastMessage.value = buildNetworkErrorMessage("새로고침 실패", e)
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
                    _toastMessage.value =
                        "새로고침 실패: ${response.reason ?: response.message ?: "서버 응답 오류"}"
                }
            } catch (e: Exception) {
                _ruleRefreshStatusMessages.value = _ruleRefreshStatusMessages.value + (ruleId to "새로고침 실패")
                _toastMessage.value = buildNetworkErrorMessage("새로고침 실패", e)
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
                    _toastMessage.value = "새로고침 실패: ${response.reason ?: response.message ?: "서버 응답 오류"}"
                }
            } catch (e: Exception) {
                if (showFeedback) {
                    _alertsRefreshStatusMessage.value = "새로고침 실패"
                    _toastMessage.value = buildNetworkErrorMessage("새로고침 실패", e)
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
                    _toastMessage.value = "읽음 보관함 새로고침 실패: ${response.reason ?: response.message ?: "서버 응답 오류"}"
                }
            } catch (e: Exception) {
                if (showFeedback) {
                    _readArchiveRefreshStatusMessage.value = "새로고침 실패"
                    _toastMessage.value = buildNetworkErrorMessage("읽음 보관함 새로고침 실패", e)
                }
            } finally {
                if (showFeedback) {
                    _isRefreshingReadArchive.value = false
                }
            }
        }
    }

    fun markAlertAsRead(uid: String, alertEventId: Long, showFeedback: Boolean = false) {
        if (alertEventId <= 0L) {
            return
        }
        viewModelScope.launch {
            try {
                val response = UmtpApiClient.apiService.markAlertEventRead(alertEventId, uid)
                if (!response.ok && showFeedback) {
                    _toastMessage.value =
                        "읽음 처리 실패: ${response.reason ?: response.message ?: "서버 응답 오류"}"
                }
            } catch (e: Exception) {
                if (showFeedback) {
                    _toastMessage.value = buildNetworkErrorMessage("읽음 처리 실패", e)
                }
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
                val response = UmtpApiClient.apiService.markAllAlertEventsRead(uid)
                if (response.ok) {
                    _toastMessage.value = response.message ?: "모두 읽음 처리 완료"
                    fetchAlerts(uid, showFeedback = false)
                    fetchReadGroupedAlerts(uid, showFeedback = false)
                } else {
                    _toastMessage.value =
                        "모두 읽음 처리 실패: ${response.reason ?: response.message ?: "서버 응답 오류"}"
                }
            } catch (e: Exception) {
                _toastMessage.value = buildNetworkErrorMessage("모두 읽음 처리 실패", e)
            } finally {
                _isMarkingAllAlertsRead.value = false
            }
        }
    }

    private fun startAlertPolling(uid: String) {
        viewModelScope.launch {
            while (true) {
                delay(30000) // 30 seconds
                fetchAlerts(uid, showFeedback = false)
            }
        }
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
                    _toastMessage.value = "등록 실패: ${response.message ?: response.reason ?: "서버 응답 오류"}"
                }
            } catch (e: Exception) {
                Log.e("UMTP_NET", "Register Error", e)
                _toastMessage.value = buildNetworkErrorMessage("등록 실패", e)
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
        searchKeyword: String?,
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
                    search_keyword = searchKeyword?.trim()?.ifEmpty { null },
                    poll_interval_seconds = 60
                )
                val response = UmtpApiClient.apiService.upsertUserFairPrice(request)
                if (response.ok) {
                    val missedCandidateCount = response.missed_candidate_count ?: 0
                    _toastMessage.value = if (missedCandidateCount > 0) {
                        response.message ?: "조건 변경 사이에 새 기준에 맞는 매물이 ${missedCandidateCount}개 있었어요."
                    } else if (response.immediate_poll_requested == true) {
                        response.message ?: "저장 완료 (즉시 검색 요청됨)"
                    } else {
                        response.message ?: "저장 완료"
                    }
                    loadUserSettings(uid)
                } else {
                    _toastMessage.value = "저장 실패: ${response.message ?: response.reason}"
                }
            } catch (e: Exception) {
                _toastMessage.value = buildNetworkErrorMessage("저장 실패", e)
            } finally {
                _savingItemKey.value = null
            }
        }
    }

    fun clearToastMessage() {
        _toastMessage.value = null
    }

    private fun buildNetworkErrorMessage(prefix: String, error: Exception): String {
        val reason = when (error) {
            is UnknownHostException -> "서버 주소를 찾지 못했어요."
            is ConnectException -> "서버에 연결할 수 없어요."
            is SocketTimeoutException -> "서버 응답 시간이 초과됐어요."
            else -> error.localizedMessage ?: "알 수 없는 네트워크 오류"
        }
        return "$prefix: $reason 서버 주소(${UmtpApiClient.baseUrl})를 확인해주세요."
    }

    private suspend fun refreshUnitsInternal(): String? {
        return try {
            val unitsResponse = UmtpApiClient.apiService.getMacBookAirUnits()
            if (!unitsResponse.ok) {
                unitsResponse.reason ?: unitsResponse.message ?: "MacBook Air 단위 목록 응답 오류"
            } else {
                _units.value = unitsResponse.units
                null
            }
        } catch (e: Exception) {
            buildNetworkErrorMessage("MacBook Air 단위 목록 로딩 실패", e)
        }
    }

    private suspend fun refreshUserSettingsInternal(uid: String): String? {
        return try {
            val response = UmtpApiClient.apiService.getUserFairPrices(uid)
            if (!response.ok) {
                response.reason ?: response.message ?: "사용자 설정 응답 오류"
            } else {
                _userSettings.value = response.items
                pruneRuleRefreshState(response.items.mapNotNull { it.id }.toSet())
                null
            }
        } catch (e: Exception) {
            buildNetworkErrorMessage("사용자 설정 로딩 실패", e)
        }
    }

    private suspend fun refreshActiveRulesSavedAtInternal(uid: String): String? {
        return try {
            val response = UmtpApiClient.apiService.refreshUserRulesSavedAt(uid)
            if (!response.ok) {
                response.reason ?: response.message ?: "활성 조건 saved_at 새로고침 응답 오류"
            } else {
                null
            }
        } catch (e: Exception) {
            buildNetworkErrorMessage("활성 조건 saved_at 새로고침 실패", e)
        }
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
