package com.boongtol.umtp_android.network

import retrofit2.http.Body
import retrofit2.http.POST

interface UmtpApiService {
    @POST("analyze-url")
    suspend fun analyzeUrl(
        @Body request: AnalyzeUrlRequest
    ): AnalyzeUrlResponse
}
