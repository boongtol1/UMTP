package com.boongtol.umtp_android.network

data class AlertItem(
    val id: Long = 0L,
    val user_id: String? = null,
    val title: String? = null,
    val source: String? = null,
    val product_url: String? = null,
    val url: String? = null,
    val listing_price_krw: Int? = null,
    val fair_price_krw: Int? = null,
    val user_market_price_krw: Int? = null,
    val alert_target_price_krw: Int? = null,
    val diff_ratio: Double? = null,
    val price_gap_percent: Double? = null,
    val alert_price_direction: String? = null,
    val alert_condition_label: String? = null,
    val product_type: String? = null,
    val chip: String? = null,
    val screen_inch: Int? = null,
    val ram_gb: Int? = null,
    val ssd_gb: Int? = null,
    val risk_level: String? = null,
    val formatted_risk_label: String? = null,
    val risk_score: Int? = null,
    val risk_keywords: List<String>? = null,
    val trade_type_flags: TradeTypeFlags? = null,
    val body_excerpt: String? = null,
    val body_text: String? = null,
    val analyzed_at: String? = null,
    val created_at: String? = null,
    val is_alert_target: Boolean = true,
)

data class TradeTypeFlags(
    val is_exchange: Boolean = false,
    val is_free: Boolean = false,
    val is_suspicious: Boolean = false,
)

data class AlertsResponse(
    val ok: Boolean,
    val items: List<AlertItem> = emptyList(),
    val message: String? = null,
    val reason: String? = null,
)
