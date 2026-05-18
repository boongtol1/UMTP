package com.boongtol.umtp_android.network

import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.Path
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

    @POST("users/{user_id}/rules/refresh")
    suspend fun refreshUserRulesSavedAt(
        @Path("user_id") userId: String
    ): UserRulesRefreshResponse

    @POST("users/{user_id}/rules/{rule_id}/refresh")
    suspend fun refreshSingleUserRuleSavedAt(
        @Path("user_id") userId: String,
        @Path("rule_id") ruleId: Long,
    ): UserRuleRefreshResponse

    @POST("users/register")
    suspend fun registerUser(
        @Body request: UserRegisterRequest
    ): UserRegisterResponse

    @POST("users/{user_id}/push-token")
    suspend fun registerPushToken(
        @retrofit2.http.Path("user_id") userId: String,
        @Body request: PushTokenRequest
    ): PushTokenResponse

    @GET("alerts")
    suspend fun getAlerts(
        @Query("user_id") userId: String
    ): AlertsResponse

    @GET("user-fair-prices/recommended-keywords")
    suspend fun getRecommendedKeywords(
        @Query("product_type") productType: String,
        @Query("chip") chip: String,
        @Query("ram_gb") ramGb: Int?,
        @Query("ssd_gb") ssdGb: Int?
    ): RecommendedKeywordsResponse
}
