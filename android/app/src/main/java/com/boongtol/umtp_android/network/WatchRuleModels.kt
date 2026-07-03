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
    val priority: String = "NORMAL",
    val target_price_krw: Int?,
    val fair_price_krw: Int?
)

data class WatchRuleUpsertResponse(
    val ok: Boolean? = null,
    val message: String? = null,
    val reason: String? = null,
    val search_keyword: String? = null,
    val immediate_poll_requested: Boolean? = null,
    val alert_drop_rate_percent: Double? = null
)

data class RecommendedKeywordsResponse(
    val ok: Boolean? = null,
    val items: List<String> = emptyList(),
    val reason: String? = null
)

data class RequestPollNowRequest(
    val user_id: String,
    val search_keyword: String
)

data class RequestPollNowResponse(
    val ok: Boolean? = null,
    val message: String? = null,
    val reason: String? = null,
    val immediate_poll_requested: Boolean? = null
)

data class WatchRuleItem(
    val id: Long? = null,
    val user_id: String? = null,
    val product_type: String? = null,
    val chip: String? = null,
    val screen_inch: Int? = null,
    val ram_gb: Int? = null,
    val ssd_gb: Int? = null,
    val search_keyword: String? = null,
    val enabled: Boolean? = null,
    val force_poll: Boolean? = null,
    val poll_interval_seconds: Int? = null,
    val priority: String? = null,
    val target_price_krw: Int? = null,
    val fair_price_krw: Int? = null,
    val alert_drop_rate_percent: Double? = null,
    val last_polled_at: String? = null,
    val last_poll_requested_at: String? = null
)

data class WatchRuleListResponse(
    val ok: Boolean? = null,
    val user_id: String? = null,
    val items: List<WatchRuleItem> = emptyList(),
    val message: String? = null,
    val reason: String? = null
)
