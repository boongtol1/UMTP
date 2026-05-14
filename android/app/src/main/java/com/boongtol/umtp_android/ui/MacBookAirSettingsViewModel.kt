package com.boongtol.umtp_android.ui

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.boongtol.umtp_android.network.UmtpApiClient
import com.boongtol.umtp_android.network.UserFairPriceItem
import com.boongtol.umtp_android.network.UserFairPriceUpsertRequest
import com.boongtol.umtp_android.user.UserPreferences
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

class MacBookAirSettingsViewModel(private val userPreferences: UserPreferences) : ViewModel() {

    private val _items = MutableStateFlow<List<UserFairPriceItem>>(emptyList())
    val items: StateFlow<List<UserFairPriceItem>> = _items.asStateFlow()

    private val _isLoading = MutableStateFlow(false)
    val isLoading: StateFlow<Boolean> = _isLoading.asStateFlow()

    private val _errorMessage = MutableStateFlow<String?>(null)
    val errorMessage: StateFlow<String?> = _errorMessage.asStateFlow()

    private val _toastMessage = MutableStateFlow<String?>(null)
    val toastMessage: StateFlow<String?> = _toastMessage.asStateFlow()

    private val _savingItemKey = MutableStateFlow<String?>(null)
    val savingItemKey: StateFlow<String?> = _savingItemKey.asStateFlow()

    val userId: String = userPreferences.getUserId()

    init {
        loadItems()
    }

    fun loadItems() {
        viewModelScope.launch {
            _isLoading.value = true
            _errorMessage.value = null
            try {
                val response = UmtpApiClient.apiService.getUserFairPrices(userId)
                if (response.ok) {
                    _items.value = response.items
                } else {
                    _errorMessage.value = "Failed to load settings"
                }
            } catch (e: Exception) {
                _errorMessage.value = "Error: ${e.localizedMessage}"
            } finally {
                _isLoading.value = false
            }
        }
    }

    fun upsertItem(
        item: UserFairPriceItem,
        fairPrice: Int,
        dropRate: Int,
        enabled: Boolean
    ) {
        val itemKey = "${item.chip}-${item.screen_inch}-${item.ram_gb}-${item.ssd_gb}"
        viewModelScope.launch {
            _savingItemKey.value = itemKey
            try {
                val request = UserFairPriceUpsertRequest(
                    user_id = userId,
                    product_type = item.product_type,
                    chip = item.chip,
                    screen_inch = item.screen_inch,
                    ram_gb = item.ram_gb,
                    ssd_gb = item.ssd_gb,
                    fair_price_krw = fairPrice,
                    alert_drop_rate_percent = dropRate,
                    enabled = enabled
                )
                val response = UmtpApiClient.apiService.upsertUserFairPrice(request)
                if (response.ok) {
                    _toastMessage.value = "저장 완료"
                    loadItems() // Reload to get effective values
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
