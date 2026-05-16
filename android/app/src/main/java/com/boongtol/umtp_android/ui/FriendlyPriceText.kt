package com.boongtol.umtp_android.ui

import java.text.NumberFormat
import java.util.Locale

private const val DEFAULT_MARKET_PRICE_LABEL = "내가 생각한 시장가"
private const val MAX_USER_ID_LABEL_LENGTH = 12

fun buildMarketPriceLabel(userId: String?): String {
    val normalized = userId?.trim().orEmpty()
    if (normalized.isEmpty()) {
        return DEFAULT_MARKET_PRICE_LABEL
    }
    val displayUserId = ellipsizeUserId(normalized, MAX_USER_ID_LABEL_LENGTH)
    return "${displayUserId}이 생각한 시장가"
}

fun ellipsizeUserId(userId: String, maxLength: Int = MAX_USER_ID_LABEL_LENGTH): String {
    val normalized = userId.trim()
    if (normalized.length <= maxLength || maxLength < 5) {
        return normalized
    }

    val headLength = (maxLength - 1) / 2
    val tailLength = maxLength - headLength - 1
    return normalized.take(headLength) + "…" + normalized.takeLast(tailLength)
}

fun formatKrwDisplay(value: Int?): String {
    if (value == null) {
        return "정보 없음"
    }
    val formatter = NumberFormat.getNumberInstance(Locale.KOREA)
    return "${formatter.format(value)}원"
}

fun formatPercentDisplay(value: Double?): String {
    if (value == null) {
        return "정보 없음"
    }
    return "${"%.2f".format(value)}%"
}
