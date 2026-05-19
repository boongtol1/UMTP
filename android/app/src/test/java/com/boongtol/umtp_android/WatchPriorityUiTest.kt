package com.boongtol.umtp_android

import com.boongtol.umtp_android.network.UserFairPriceUpsertRequest
import com.boongtol.umtp_android.ui.WATCH_PRIORITY_FAST
import com.boongtol.umtp_android.ui.WATCH_PRIORITY_NORMAL
import com.boongtol.umtp_android.ui.normalizeWatchPriority
import org.junit.Assert.assertEquals
import org.junit.Test

class WatchPriorityUiTest {

    @Test
    fun normalizeWatchPriorityDefaultsToNormal() {
        assertEquals(WATCH_PRIORITY_NORMAL, normalizeWatchPriority(null))
        assertEquals(WATCH_PRIORITY_NORMAL, normalizeWatchPriority("unknown"))
        assertEquals(WATCH_PRIORITY_FAST, normalizeWatchPriority("fast"))
    }

    @Test
    fun selectedSpeedIsIncludedInUpsertRequest() {
        val selectedPriority = normalizeWatchPriority(WATCH_PRIORITY_FAST)
        val request = UserFairPriceUpsertRequest(
            user_id = "boongtol",
            product_type = "MacBook Air",
            chip = "M2",
            screen_inch = 13,
            ram_gb = 8,
            ssd_gb = 256,
            fair_price_krw = 1000000,
            alert_drop_rate_percent = 20.0,
            enabled = true,
            priority = selectedPriority,
        )

        assertEquals(WATCH_PRIORITY_FAST, request.priority)
    }
}
