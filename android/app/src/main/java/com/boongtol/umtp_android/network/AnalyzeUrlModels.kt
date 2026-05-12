package com.boongtol.umtp_android.network

data class AnalyzeUrlRequest(
    val user_id: String,
    val url: String
)

data class AnalyzeUrlResponse(
    val ok: Boolean,
    val status: String? = null,
    val message: String? = null,
    val reason: String? = null,
    val title: String? = null,
    val listing_price_krw: Int? = null,
    val fair_price_krw: Int? = null,
    val diff_ratio: Double? = null,
    val is_alert_target: Boolean? = null,
    val risk_level: String? = null,
    val trade_type: String? = null
)
