package com.boongtol.umtp_android.ui

import java.text.NumberFormat
import java.math.BigDecimal
import java.math.RoundingMode
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

fun normalizePriceTextInput(input: String): String {
    if (input.isEmpty()) {
        return ""
    }
    if (!input.all { it.isDigit() }) {
        return ""
    }
    val trimmed = input.trimStart('0')
    return if (trimmed.isEmpty()) "0" else trimmed
}

fun computeAlertDropRatePercent(fairPrice: Int?, desiredPrice: Int?): Double? {
    if (fairPrice == null || desiredPrice == null || fairPrice <= 0) {
        return null
    }
    val fair = BigDecimal(fairPrice)
    val desired = BigDecimal(desiredPrice)
    val ratio = fair.subtract(desired)
        .divide(fair, 8, RoundingMode.HALF_UP)
        .multiply(BigDecimal("100"))
    return ratio.setScale(2, RoundingMode.HALF_UP).toDouble()
}

fun computeMarketPriceGapPercent(fairPrice: Int?, desiredPrice: Int?): Double? {
    if (fairPrice == null || desiredPrice == null || fairPrice <= 0) {
        return null
    }
    val fair = BigDecimal(fairPrice)
    val desired = BigDecimal(desiredPrice)
    val ratio = fair.subtract(desired)
        .divide(fair, 8, RoundingMode.HALF_UP)
        .multiply(BigDecimal("100"))
    return ratio.setScale(2, RoundingMode.HALF_UP).toDouble()
}
