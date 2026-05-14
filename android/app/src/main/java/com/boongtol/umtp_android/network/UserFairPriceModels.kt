package com.boongtol.umtp_android.network

data class UserRegisterRequest(
    val nickname: String,
    val device_id: String,
    val user_id: String? = null
)

data class UserRegisterResponse(
    val ok: Boolean,
    val user_id: String? = null,
    val nickname: String? = null,
    val message: String? = null,
    val reason: String? = null
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
    val system_alert_drop_rate_percent: Int? = null,

    val user_fair_price_krw: Int? = null,
    val user_alert_drop_rate_percent: Int? = null,
    val enabled: Boolean = false,

    val effective_fair_price_krw: Int? = null,
    val effective_alert_drop_rate_percent: Int? = null,
    val has_user_override: Boolean = false
)

data class UserFairPricesResponse(
    val ok: Boolean,
    val user_id: String,
    val items: List<UserFairPriceItem> = emptyList()
)

data class UserFairPriceUpsertRequest(
    val user_id: String,
    val product_type: String,
    val chip: String,
    val screen_inch: Int,
    val ram_gb: Int,
    val ssd_gb: Int,
    val fair_price_krw: Int,
    val alert_drop_rate_percent: Int,
    val enabled: Boolean
)

data class UserFairPriceUpsertResponse(
    val ok: Boolean,
    val message: String? = null,
    val reason: String? = null
)
