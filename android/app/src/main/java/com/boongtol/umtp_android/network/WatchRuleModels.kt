package com.boongtol.umtp_android.network

data class WatchRuleUpsertRequest(
    val user_id: String,
    val product_type: String,
    val chip: String,
    val screen_inch: Int,
    val ram_gb: Int,
    val ssd_gb: Int,
    val search_keyword: String?,
    val enabled: Boolean,
    val poll_interval_seconds: Int,
    val target_price_krw: Int?,
    val fair_price_krw: Int?
)

data class WatchRuleUpsertResponse(
    val ok: Boolean,
    val message: String? = null,
    val reason: String? = null,
    val search_keyword: String? = null,
    val immediate_poll_requested: Boolean? = null,
    val alert_drop_rate_percent: Double? = null
)

data class RecommendedKeywordsResponse(
    val ok: Boolean,
    val items: List<String> = emptyList(),
    val reason: String? = null
)

data class RequestPollNowRequest(
    val user_id: String,
    val search_keyword: String
)

data class RequestPollNowResponse(
    val ok: Boolean,
    val message: String? = null,
    val reason: String? = null,
    val immediate_poll_requested: Boolean? = null
)
