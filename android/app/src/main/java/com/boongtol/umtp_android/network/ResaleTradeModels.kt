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

data class ResaleTradeUpsertResponse(
    val ok: Boolean,
    val id: Long? = null,
    val current_stage: String? = null,
    val reason: String? = null,
    val message: String? = null,
)
