package com.boongtol.umtp_android.network

data class AlertItem(
    val id: Long,
    val title: String,
    val listing_price_krw: Int,
    val fair_price_krw: Int,
    val diff_ratio: Double,
    val is_alert_target: Boolean,
    val risk_score: Int? = null,
    val product_url: String,
    val created_at: String
)

data class AlertsResponse(
    val ok: Boolean,
    val items: List<AlertItem> = emptyList()
)
