package com.boongtol.umtp_android

import com.boongtol.umtp_android.ui.buildMarketPriceLabel
import com.boongtol.umtp_android.ui.ellipsizeUserId
import com.boongtol.umtp_android.ui.formatKrwDisplay
import com.boongtol.umtp_android.ui.formatPercentDisplay
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
}
