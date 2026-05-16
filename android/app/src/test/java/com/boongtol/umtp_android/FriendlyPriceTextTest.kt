package com.boongtol.umtp_android

import com.boongtol.umtp_android.ui.buildMarketPriceLabel
import com.boongtol.umtp_android.ui.computeAlertDropRatePercent
import com.boongtol.umtp_android.ui.ellipsizeUserId
import com.boongtol.umtp_android.ui.formatKrwDisplay
import com.boongtol.umtp_android.ui.formatPercentDisplay
import com.boongtol.umtp_android.ui.normalizePriceTextInput
import org.junit.Assert.assertEquals
import org.junit.Test

class FriendlyPriceTextTest {
    @Test
    fun buildMarketPriceLabel_usesFallbackWhenUserIdMissing() {
        assertEquals("내가 생각한 시장가", buildMarketPriceLabel(null))
        assertEquals("내가 생각한 시장가", buildMarketPriceLabel("   "))
    }

    @Test
    fun buildMarketPriceLabel_usesUserIdWhenPresent() {
        assertEquals("boongtol이 생각한 시장가", buildMarketPriceLabel("boongtol"))
    }

    @Test
    fun ellipsizeUserId_shortensLongUserId() {
        assertEquals("aver…serid", ellipsizeUserId("averylonguserid", 10))
    }

    @Test
    fun formatKrwDisplay_formatsWithComma() {
        assertEquals("795,000원", formatKrwDisplay(795000))
    }

    @Test
    fun formatPercentDisplay_formatsTwoDecimals() {
        assertEquals("20.50%", formatPercentDisplay(20.5))
        assertEquals("-10.00%", formatPercentDisplay(-10.0))
    }

    @Test
    fun normalizePriceTextInput_collapsesLeadingZeros() {
        assertEquals("", normalizePriceTextInput(""))
        assertEquals("0", normalizePriceTextInput("0"))
        assertEquals("0", normalizePriceTextInput("0000"))
        assertEquals("123", normalizePriceTextInput("000123"))
    }

    @Test
    fun computeAlertDropRatePercent_usesConsistentFormula() {
        assertEquals(20.50, computeAlertDropRatePercent(1000000, 795000) ?: 0.0, 0.0001)
        assertEquals(-25.00, computeAlertDropRatePercent(800000, 1000000) ?: 0.0, 0.0001)
    }
}
