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

data class TradeJourneyStartFromUrlRequest(
    val user_id: String,
    val url: String,
)

data class TradeJourneyStartFromAlertRequest(
    val user_id: String,
    val alert_event_id: Long,
)

data class TradeJourneyStartFromReadArchiveRequest(
    val user_id: String,
    val read_archive_event_id: Long,
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

data class TradeJourneyStartResponse(
    val ok: Boolean,
    val existing: Boolean? = null,
    val trade_journey_id: Long? = null,
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
    val seller_location: String? = null,
    val image_urls: Any? = null,
    val body_text: String? = null,
    val fair_price_krw: Int? = null,
    val discount_rate_percent: Double? = null,
    val product_type: String? = null,
    val chip: String? = null,
    val screen_inch: Int? = null,
    val ram_gb: Int? = null,
    val ssd_gb: Int? = null,
    val seller_nickname: String? = null,
    val contacted_at: String? = null,
    val seller_response_at: String? = null,
    val current_stage: String? = null,
    val purchased_at: String? = null,
    val purchase_price_krw: Int? = null,
    val purchase_method: String? = null,
    val purchase_location: String? = null,
    val transport_cost_krw: Int? = null,
    val shipping_cost_krw: Int? = null,
    val total_cost_krw: Int? = null,
    val payment_method: String? = null,
    val serial_number: String? = null,
    val model_number: String? = null,
    val activation_lock_off: Any? = null,
    val mdm_lock_none: Any? = null,
    val battery_health_percent: Int? = null,
    val battery_cycle_count: Int? = null,
    val inspection_notes: String? = null,
    val resale_listing_price_krw: Int? = null,
    val resale_platform: String? = null,
    val resale_url: String? = null,
    val sold_at: String? = null,
    val sale_price_krw: Int? = null,
    val buyer_nickname: String? = null,
    val sale_method: String? = null,
    val sale_location: String? = null,
    val sale_platform: String? = null,
    val created_at: String? = null,
    val updated_at: String? = null,
)

data class ResaleTradeUpsertResponse(
    val ok: Boolean,
    val id: Long? = null,
    val source: String? = null,
    val product_id: String? = null,
    val current_stage: String? = null,
    val row: ResaleTradeJourneyRow? = null,
    val reason: String? = null,
    val message: String? = null,
)
