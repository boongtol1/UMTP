package com.boongtol.umtp_android.ui

const val WATCH_PRIORITY_FAST = "FAST"
const val WATCH_PRIORITY_NORMAL = "NORMAL"
const val WATCH_PRIORITY_LOW = "LOW"

data class WatchPriorityUiOption(
    val value: String,
    val label: String,
    val description: String,
)

val WATCH_PRIORITY_UI_OPTIONS = listOf(
    WatchPriorityUiOption(
        value = WATCH_PRIORITY_FAST,
        label = "빠름",
        description = "더 자주 확인해요",
    ),
    WatchPriorityUiOption(
        value = WATCH_PRIORITY_NORMAL,
        label = "보통",
        description = "일반적인 속도",
    ),
    WatchPriorityUiOption(
        value = WATCH_PRIORITY_LOW,
        label = "절전",
        description = "천천히 확인해요",
    ),
)

fun normalizeWatchPriority(value: String?): String {
    return when (value?.trim()?.uppercase()) {
        WATCH_PRIORITY_FAST -> WATCH_PRIORITY_FAST
        WATCH_PRIORITY_LOW -> WATCH_PRIORITY_LOW
        else -> WATCH_PRIORITY_NORMAL
    }
}
