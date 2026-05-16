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

    private val _alertsRefreshStatusMessage = MutableStateFlow<String?>(null)
    val alertsRefreshStatusMessage: StateFlow<String?> = _alertsRefreshStatusMessage.asStateFlow()

    private val _lastAlertsRefreshLabel = MutableStateFlow<String?>(null)
    val lastAlertsRefreshLabel: StateFlow<String?> = _lastAlertsRefreshLabel.asStateFlow()

    private var isAlertRefreshInFlight: Boolean = false

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
                val unitsResponse = UmtpApiClient.apiService.getMacBookAirUnits()
                if (unitsResponse.ok) {
                    _units.value = unitsResponse.units
                }
                
                loadUserSettings(uid)
                fetchAlerts(uid, showFeedback = false)
            } catch (e: Exception) {
                _errorMessage.value = "데이터 로딩 에러: ${e.localizedMessage}"
            } finally {
                _isLoading.value = false
            }
        }
    }

    fun loadUserSettings(uid: String) {
        viewModelScope.launch {
            try {
                val response = UmtpApiClient.apiService.getUserFairPrices(uid)
                if (response.ok) {
                    _userSettings.value = response.items
                }
            } catch (e: Exception) {
                // Ignore background settings refresh errors
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
                val response = UmtpApiClient.apiService.getAlerts(uid)
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
                // Mock fallback if API fails
                if (_alerts.value.isEmpty()) {
                    _alerts.value = listOf(
                        AlertItem(
                            id = 1,
                            title = "Mock: 맥북 에어 M1 8GB 256GB 실버",
                            listing_price_krw = 430000,
                            fair_price_krw = 550000,
                            diff_ratio = -21.8,
                            is_alert_target = true,
                            risk_score = 15,
                            product_url = "https://web.joongna.com/product/228559836",
                            created_at = "2026-05-14T03:22:11"
                        )
                    )
                }
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
        if (dropRatePercent == null || dropRatePercent < -100.0 || dropRatePercent > 100.0) {
            _toastMessage.value = "시장가와의 차이(%)는 -100.00% ~ 100.00% 범위여야 합니다."
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
                    _toastMessage.value = if (response.immediate_poll_requested == true) {
                        "저장 완료 (즉시 검색 요청됨)"
                    } else {
                        "저장 완료"
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

    private fun formatRefreshTimeLabel(epochMillis: Long): String {
        val formatter = SimpleDateFormat("HH:mm", Locale.KOREA)
        return formatter.format(Date(epochMillis))
    }
}
