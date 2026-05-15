package com.boongtol.umtp_android.network

import com.google.gson.annotations.SerializedName

data class UserRegisterRequest(
    @SerializedName("user_id") val user_id: String,
    @SerializedName("device_id") val device_id: String? = null,
)

data class UserRegisterResponse(
    @SerializedName("ok") val ok: Boolean,
    @SerializedName("user_id") val user_id: String? = null,
    @SerializedName("message") val message: String? = null,
    @SerializedName("reason") val reason: String? = null
)

data class MacBookAirUnit(
    val product_type: String,
    val chip: String,
    val screen_inch: Int,
    val ram_gb: Int,
    val ssd_gb: Int
)

data class MacBookAirUnitsResponse(
    val ok: Boolean,
    val units: List<MacBookAirUnit> = emptyList()
)

data class UserFairPriceItem(
    val product_type: String,
    val chip: String,
    val screen_inch: Int,
    val ram_gb: Int,
    val ssd_gb: Int,

    val system_fair_price_krw: Int? = null,
    val system_alert_drop_rate_percent: Double? = null,

    val user_fair_price_krw: Int? = null,
    val user_alert_drop_rate_percent: Double? = null,
    val enabled: Boolean = false,

    val effective_fair_price_krw: Int? = null,
    val effective_alert_drop_rate_percent: Double? = null,
    val has_user_override: Boolean = false
)

data class UserFairPricesResponse(
    val ok: Boolean,
    val user_id: String? = null,
    val items: List<UserFairPriceItem> = emptyList(),
    val reason: String? = null,
    val message: String? = null
)

data class UserFairPriceUpsertRequest(
    val user_id: String,
    val product_type: String,
    val chip: String,
    val screen_inch: Int,
    val ram_gb: Int,
    val ssd_gb: Int,
    val fair_price_krw: Int,
    val alert_drop_rate_percent: Double,
    val enabled: Boolean
)

data class UserFairPriceUpsertResponse(
    val ok: Boolean,
    val message: String? = null,
    val reason: String? = null
)
