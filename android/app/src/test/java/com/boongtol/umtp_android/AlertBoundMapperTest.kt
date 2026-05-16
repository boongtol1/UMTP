package com.boongtol.umtp_android

import com.boongtol.umtp_android.ui.ABOVE_OR_EQUAL_DIRECTION
import com.boongtol.umtp_android.ui.BELOW_OR_EQUAL_DIRECTION
import com.boongtol.umtp_android.ui.buildAlertBoundsRequest
import com.boongtol.umtp_android.ui.normalizeAlertDirection
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

class AlertBoundMapperTest {

    @Test
    fun belowDirectionUsesMinBoundOnly() {
        val result = buildAlertBoundsRequest(
            alertPriceDirection = BELOW_OR_EQUAL_DIRECTION,
            boundPriceKrw = 300000,
        )

        assertEquals(300000, result.min_price_krw)
        assertNull(result.max_price_krw)
    }

    @Test
    fun aboveDirectionUsesMaxBoundOnly() {
        val result = buildAlertBoundsRequest(
            alertPriceDirection = ABOVE_OR_EQUAL_DIRECTION,
            boundPriceKrw = 900000,
        )

        assertNull(result.min_price_krw)
        assertEquals(900000, result.max_price_krw)
    }

    @Test
    fun unknownDirectionDefaultsToBelow() {
        assertEquals(BELOW_OR_EQUAL_DIRECTION, normalizeAlertDirection("unknown"))
    }
}
