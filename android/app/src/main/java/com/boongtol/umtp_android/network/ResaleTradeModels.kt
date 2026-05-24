package com.boongtol.umtp_android.network

data class ResaleTradeAfterPurchaseUpsertRequest(
    val user_id: String,
    val source: String = "joongna",
    val product_id: String? = null,
    val url: String? = null,
    val updates: Map<String, Any?> = emptyMap(),
)

data class ResaleTradeAfterResaleUpsertRequest(
    val user_id: String,
    val source: String = "joongna",
    val product_id: String? = null,
    val url: String? = null,
    val updates: Map<String, Any?> = emptyMap(),
)

data class ResaleTradeJourneyFromProductRequest(
    val source: String,
    val product_id: String,
)

data class ResaleTradeJourneyPatchRequest(
    val updates: Map<String, Any?> = emptyMap(),
)

data class ResaleTradeJourneyDeleteSelectedRequest(
    val journey_ids: List<Long> = emptyList(),
)

data class ResaleTradeJourneyDeleteResponse(
    val ok: Boolean,
    val deleted_count: Int? = null,
    val reason: String? = null,
    val message: String? = null,
)

data class ResaleTradeJourneyListResponse(
    val ok: Boolean,
    val items: List<ResaleTradeJourneyRow> = emptyList(),
    val reason: String? = null,
    val message: String? = null,
)

data class ResaleTradeJourneyResponse(
    val ok: Boolean,
    val id: Long? = null,
    val source: String? = null,
    val product_id: String? = null,
    val current_stage: String? = null,
    val row: ResaleTradeJourneyRow? = null,
    val reason: String? = null,
    val message: String? = null,
)

data class ResaleTradeJourneyRow(
    val id: Long? = null,
    val user_id: String? = null,
    val source: String? = null,
    val product_id: String? = null,
    val url: String? = null,
    val title: String? = null,
    val listing_price_krw: Int? = null,
    val fair_price_krw: Int? = null,
    val discount_rate_percent: Double? = null,
    val product_type: String? = null,
    val chip: String? = null,
    val screen_inch: Int? = null,
    val ram_gb: Int? = null,
    val ssd_gb: Int? = null,
    val seller_nickname: String? = null,
    val seller_shop_id: String? = null,
    val current_stage: String? = null,
    val purchased_at: String? = null,
    val sold_at: String? = null,
    val sale_price_krw: Int? = null,
    val purchase_price_krw: Int? = null,
    val net_profit_krw: Int? = null,
    val roi_percent: Double? = null,
)

data class ResaleTradeUpsertResponse(
    val ok: Boolean,
    val id: Long? = null,
    val current_stage: String? = null,
    val reason: String? = null,
    val message: String? = null,
)
