package com.boongtol.umtp_android.ui

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

    private fun startAlertPolling(uid: String) {
        viewModelScope.launch {
            while (true) {
                delay(30000) // 30 seconds
                fetchAlerts(uid)
            }
        }
    }

    fun registerUser(id: String) {
        val trimmedId = id.trim()
        if (trimmedId.length < 2) {
            _toastMessage.value = "User ID는 2자 이상이어야 합니다."
            return
        }

        viewModelScope.launch {
            _isLoading.value = true
            try {
                val response = UmtpApiClient.apiService.registerUser(UserRegisterRequest(user_id = trimmedId))
                if (response.ok) {
                    userPreferences.setUserId(trimmedId)
                    _userId.value = trimmedId
                    loadInitialData(trimmedId)
                    startAlertPolling(trimmedId)
                } else {
                    _toastMessage.value = "등록 실패: ${response.message ?: response.reason}"
                }
            } catch (e: Exception) {
                _toastMessage.value = "에러: ${e.localizedMessage}"
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
                    alert_drop_rate_percent = dropRate,
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
                _toastMessage.value = "에러: ${e.localizedMessage}"
            } finally {
                _savingItemKey.value = null
            }
        }
    }

    fun clearToastMessage() {
        _toastMessage.value = null
    }
}
