package com.boongtol.umtp_android.network

data class PushTokenRequest(
    val platform: String = "android",
    val token: String
)

data class PushTokenResponse(
    val message: String
)
