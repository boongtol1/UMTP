package com.boongtol.umtp_android.network

import com.google.gson.annotations.SerializedName

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
    @SerializedName("ok")
    val ok: Boolean,
    @SerializedName("existing")
    val existing: Boolean? = null,
    @SerializedName("trade_journey_id")
    val trade_journey_id: Long? = null,
    @SerializedName("id")
    val id: Long? = null,
    @SerializedName("source")
    val source: String? = null,
    @SerializedName("product_id")
    val product_id: String? = null,
    @SerializedName("current_stage")
    val current_stage: String? = null,
    @SerializedName("row")
    val row: ResaleTradeJourneyRow? = null,
    @SerializedName("reason")
    val reason: String? = null,
    @SerializedName("message")
    val message: String? = null,
)

data class ResaleTradeJourneyRow(
    @SerializedName("id")
    val id: Long? = null,
    @SerializedName("user_id")
    val user_id: String? = null,
    @SerializedName("source")
    val source: String? = null,
    @SerializedName("product_id")
    val product_id: String? = null,
    @SerializedName("url")
    val url: String? = null,
    @SerializedName("title")
    val title: String? = null,
    @SerializedName("listing_price_krw")
    val listing_price_krw: Int? = null,
    @SerializedName("seller_location")
    val seller_location: String? = null,
    @SerializedName("image_urls")
    val image_urls: Any? = null,
    @SerializedName("body_text")
    val body_text: String? = null,
    @SerializedName("fair_price_krw")
    val fair_price_krw: Int? = null,
    @SerializedName("discount_rate_percent")
    val discount_rate_percent: Double? = null,
    @SerializedName("product_type")
    val product_type: String? = null,
    @SerializedName("chip")
    val chip: String? = null,
    @SerializedName("screen_inch")
    val screen_inch: Int? = null,
    @SerializedName("ram_gb")
    val ram_gb: Int? = null,
    @SerializedName("ssd_gb")
    val ssd_gb: Int? = null,
    @SerializedName("seller_nickname")
    val seller_nickname: String? = null,
    @SerializedName("contacted_at")
    val contacted_at: String? = null,
    @SerializedName("seller_response_at")
    val seller_response_at: String? = null,
    @SerializedName("current_stage")
    val current_stage: String? = null,
    @SerializedName("purchased_at")
    val purchased_at: String? = null,
    @SerializedName("purchase_price_krw")
    val purchase_price_krw: Int? = null,
    @SerializedName("purchase_method")
    val purchase_method: String? = null,
    @SerializedName("purchase_location")
    val purchase_location: String? = null,
    @SerializedName("transport_cost_krw")
    val transport_cost_krw: Int? = null,
    @SerializedName("shipping_cost_krw")
    val shipping_cost_krw: Int? = null,
    @SerializedName("total_cost_krw")
    val total_cost_krw: Int? = null,
    @SerializedName("payment_method")
    val payment_method: String? = null,
    @SerializedName("serial_number")
    val serial_number: String? = null,
    @SerializedName("model_number")
    val model_number: String? = null,
    @SerializedName("activation_lock_off")
    val activation_lock_off: Any? = null,
    @SerializedName("mdm_lock_none")
    val mdm_lock_none: Any? = null,
    @SerializedName("battery_health_percent")
    val battery_health_percent: Int? = null,
    @SerializedName("battery_cycle_count")
    val battery_cycle_count: Int? = null,
    @SerializedName("inspection_notes")
    val inspection_notes: String? = null,
    @SerializedName("resale_listing_price_krw")
    val resale_listing_price_krw: Int? = null,
    @SerializedName("resale_platform")
    val resale_platform: String? = null,
    @SerializedName("resale_url")
    val resale_url: String? = null,
    @SerializedName("sold_at")
    val sold_at: String? = null,
    @SerializedName("sale_price_krw")
    val sale_price_krw: Int? = null,
    @SerializedName("buyer_nickname")
    val buyer_nickname: String? = null,
    @SerializedName("sale_method")
    val sale_method: String? = null,
    @SerializedName("sale_location")
    val sale_location: String? = null,
    @SerializedName("sale_platform")
    val sale_platform: String? = null,
    @SerializedName("created_at")
    val created_at: String? = null,
    @SerializedName("updated_at")
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
