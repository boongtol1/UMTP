package com.boongtol.umtp_android.ui

const val BELOW_OR_EQUAL_DIRECTION = "BELOW_OR_EQUAL"
const val ABOVE_OR_EQUAL_DIRECTION = "ABOVE_OR_EQUAL"

data class AlertBoundsRequest(
    val min_price_krw: Int?,
    val max_price_krw: Int?,
)

fun normalizeAlertDirection(raw: String?): String {
    return when (raw?.trim()?.uppercase()) {
        ABOVE_OR_EQUAL_DIRECTION -> ABOVE_OR_EQUAL_DIRECTION
        else -> BELOW_OR_EQUAL_DIRECTION
    }
}

fun buildAlertBoundsRequest(
    alertPriceDirection: String?,
    boundPriceKrw: Int?,
): AlertBoundsRequest {
    val normalizedDirection = normalizeAlertDirection(alertPriceDirection)
    val normalizedBound = if (boundPriceKrw != null && boundPriceKrw >= 0) boundPriceKrw else null
    if (normalizedDirection == ABOVE_OR_EQUAL_DIRECTION) {
        return AlertBoundsRequest(
            min_price_krw = null,
            max_price_krw = normalizedBound,
        )
    }
    return AlertBoundsRequest(
        min_price_krw = normalizedBound,
        max_price_krw = null,
    )
}
