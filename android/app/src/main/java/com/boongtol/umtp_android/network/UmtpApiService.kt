package com.boongtol.umtp_android.network

import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.POST
import retrofit2.http.Query

interface UmtpApiService {
    @POST("analyze-url")
    suspend fun analyzeUrl(
        @Body request: AnalyzeUrlRequest
    ): AnalyzeUrlResponse

    @GET("macbook-air-units")
    suspend fun getMacBookAirUnits(): MacBookAirUnitsResponse

    @GET("user-fair-prices")
    suspend fun getUserFairPrices(
        @Query("user_id") userId: String
    ): UserFairPricesResponse

    @POST("user-fair-prices/upsert")
    suspend fun upsertUserFairPrice(
        @Body request: UserFairPriceUpsertRequest
    ): UserFairPriceUpsertResponse
}
