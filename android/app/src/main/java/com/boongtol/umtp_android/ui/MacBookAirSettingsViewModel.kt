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

    private val _recommendedKeywords = MutableStateFlow<List<String>>(emptyList())
    val recommendedKeywords: StateFlow<List<String>> = _recommendedKeywords.asStateFlow()

    private val _watchRuleSaving = MutableStateFlow(false)
    val watchRuleSaving: StateFlow<Boolean> = _watchRuleSaving.asStateFlow()

    private val _watchRuleRequestingNow = MutableStateFlow(false)
    val watchRuleRequestingNow: StateFlow<Boolean> = _watchRuleRequestingNow.asStateFlow()

    private val _watchRuleLastAlertDropRatePercent = MutableStateFlow<Double?>(null)
    val watchRuleLastAlertDropRatePercent: StateFlow<Double?> = _watchRuleLastAlertDropRatePercent.asStateFlow()

    private val _watchRules = MutableStateFlow<List<WatchRuleItem>>(emptyList())
    val watchRules: StateFlow<List<WatchRuleItem>> = _watchRules.asStateFlow()

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
                loadUserWatchRules(uid)
                fetchAlerts(uid)
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
                // Ignore background refresh errors
            }
        }
    }

    fun fetchAlerts(uid: String) {
        viewModelScope.launch {
            try {
                val response = UmtpApiClient.apiService.getAlerts(uid)
                if (response.ok) {
                    _alerts.value = response.items.sortedByDescending { it.created_at }
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
            }
        }
    }

    fun loadUserWatchRules(uid: String) {
        viewModelScope.launch {
            try {
                val response = UmtpApiClient.apiService.getUserWatchRules(uid)
                if (response.ok) {
                    _watchRules.value = response.items
                } else {
                    _watchRules.value = emptyList()
                }
            } catch (e: Exception) {
                // Keep screen responsive even when network fails.
                _watchRules.value = emptyList()
            }
        }
    }

    private fun startAlertPolling(uid: String) {
        viewModelScope.launch {
            while (true) {
                delay(30000) // 30 seconds
                fetchAlerts(uid)
            }
        }
    }

    fun registerUser(userId: String, deviceId: String?) {
        val trimmedUserId = userId.trim()
        val trimmedDeviceId = deviceId?.trim().orEmpty()
        val normalizedDeviceId = trimmedDeviceId.takeIf { it.isNotEmpty() }
        if (trimmedUserId.length < 2) {
            _toastMessage.value = "User ID는 2자 이상이어야 합니다."
            return
        }

        viewModelScope.launch {
            _isLoading.value = true
            try {
                val response = UmtpApiClient.apiService.registerUser(
                    UserRegisterRequest(
                        user_id = trimmedUserId,
                        device_id = normalizedDeviceId
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
        dropRate: Int,
        enabled: Boolean
    ) {
        val uid = _userId.value ?: return
        val itemKey = "${unit.chip}-${unit.screen_inch}-${unit.ram_gb}-${unit.ssd_gb}"
        
        viewModelScope.launch {
            _savingItemKey.value = itemKey
            try {
                val request = UserFairPriceUpsertRequest(
                    user_id = uid,
                    product_type = unit.product_type,
                    chip = unit.chip,
                    screen_inch = unit.screen_inch,
                    ram_gb = unit.ram_gb,
                    ssd_gb = unit.ssd_gb,
                    fair_price_krw = fairPrice,
                    alert_drop_rate_percent = dropRate.toDouble(),
                    enabled = enabled
                )
                val response = UmtpApiClient.apiService.upsertUserFairPrice(request)
                if (response.ok) {
                    _toastMessage.value = "저장 완료"
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

    fun fetchRecommendedKeywords(
        productType: String,
        chip: String,
        ramGb: Int?,
        ssdGb: Int?
    ) {
        viewModelScope.launch {
            try {
                val response = UmtpApiClient.apiService.getRecommendedKeywords(
                    productType = productType,
                    chip = chip,
                    ramGb = ramGb,
                    ssdGb = ssdGb
                )
                if (response.ok) {
                    _recommendedKeywords.value = response.items
                } else {
                    _recommendedKeywords.value = emptyList()
                    _toastMessage.value = "추천 검색어 조회 실패: ${response.reason ?: "unknown"}"
                }
            } catch (e: Exception) {
                _recommendedKeywords.value = emptyList()
                _toastMessage.value = buildNetworkErrorMessage("추천 검색어 조회 실패", e)
            }
        }
    }

    fun upsertWatchRule(request: WatchRuleUpsertRequest) {
        viewModelScope.launch {
            _watchRuleSaving.value = true
            try {
                val response = UmtpApiClient.apiService.upsertWatchRule(request)
                if (response.ok) {
                    _watchRuleLastAlertDropRatePercent.value = response.alert_drop_rate_percent
                    val immediateRequested = response.immediate_poll_requested == true
                    loadUserWatchRules(request.user_id)
                    _toastMessage.value = if (immediateRequested) {
                        "감시 조건이 저장됐어요. 곧 검색이 시작됩니다. (즉시 검색 요청됨)"
                    } else {
                        "감시 조건이 저장됐어요. 곧 검색이 시작됩니다."
                    }
                } else {
                    _toastMessage.value = "저장 실패: ${response.message ?: response.reason ?: "unknown"}"
                }
            } catch (e: Exception) {
                _toastMessage.value = buildNetworkErrorMessage("감시 조건 저장 실패", e)
            } finally {
                _watchRuleSaving.value = false
            }
        }
    }

    fun requestWatchRulePollNow(userId: String, searchKeyword: String) {
        val normalizedUserId = userId.trim()
        val normalizedSearchKeyword = searchKeyword.trim()
        if (normalizedUserId.isEmpty() || normalizedSearchKeyword.isEmpty()) {
            _toastMessage.value = "user_id와 검색어를 확인하세요."
            return
        }

        viewModelScope.launch {
            _watchRuleRequestingNow.value = true
            try {
                val response = UmtpApiClient.apiService.requestPollNow(
                    RequestPollNowRequest(
                        user_id = normalizedUserId,
                        search_keyword = normalizedSearchKeyword
                    )
                )
                if (response.ok) {
                    loadUserWatchRules(normalizedUserId)
                    _toastMessage.value = "즉시 검색 요청 완료"
                } else {
                    _toastMessage.value = "즉시 검색 요청 실패: ${response.message ?: response.reason ?: "unknown"}"
                }
            } catch (e: Exception) {
                _toastMessage.value = buildNetworkErrorMessage("즉시 검색 요청 실패", e)
            } finally {
                _watchRuleRequestingNow.value = false
            }
        }
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
}
