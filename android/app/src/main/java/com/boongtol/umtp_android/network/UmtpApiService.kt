package com.boongtol.umtp_android.network

import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.PATCH
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

    @PATCH("user-watch-rules/bulk-enabled")
    suspend fun bulkSetUserWatchRulesEnabled(
        @Body request: UserWatchRulesBulkEnabledRequest
    ): BulkOperationResponse

    @PATCH("user-fair-prices/bulk-drop-rate")
    suspend fun bulkSetUserFairPricesDropRate(
        @Body request: UserFairPricesBulkDropRateRequest
    ): BulkOperationResponse

    @POST("user-fair-prices/reset-to-system-market-prices")
    suspend fun resetUserFairPricesToSystemMarketPrices(
        @Body request: UserFairPricesResetToSystemRequest
    ): BulkOperationResponse

    @POST("resale-trades/after-purchase/upsert")
    suspend fun upsertResaleTradeAfterPurchase(
        @Body request: ResaleTradeAfterPurchaseUpsertRequest
    ): ResaleTradeUpsertResponse

    @POST("resale-trades/after-resale/upsert")
    suspend fun upsertResaleTradeAfterResale(
        @Body request: ResaleTradeAfterResaleUpsertRequest
    ): ResaleTradeUpsertResponse

    @POST("users/{user_id}/resale-trade-journeys/from-product")
    suspend fun createResaleTradeJourneyFromProduct(
        @Path("user_id") userId: String,
        @Body request: ResaleTradeJourneyFromProductRequest,
    ): ResaleTradeJourneyResponse

    @POST("trade-journeys/start-from-url")
    suspend fun startTradeJourneyFromUrl(
        @Body request: TradeJourneyStartFromUrlRequest,
    ): TradeJourneyStartResponse

    @GET("resale/prefill")
    suspend fun getResaleTradePrefill(
        @Query("user_id") userId: String,
        @Query("input") input: String,
    ): TradeJourneyStartResponse

    @POST("trade-journeys/start-from-alert")
    suspend fun startTradeJourneyFromAlert(
        @Body request: TradeJourneyStartFromAlertRequest,
    ): TradeJourneyStartResponse

    @POST("trade-journeys/start-from-read-archive")
    suspend fun startTradeJourneyFromReadArchive(
        @Body request: TradeJourneyStartFromReadArchiveRequest,
    ): TradeJourneyStartResponse

    @PATCH("users/{user_id}/resale-trade-journeys/{journey_id}/purchase")
    suspend fun patchResaleTradeJourneyPurchase(
        @Path("user_id") userId: String,
        @Path("journey_id") journeyId: Long,
        @Body request: ResaleTradeJourneyPatchRequest,
    ): ResaleTradeJourneyResponse

    @PATCH("users/{user_id}/resale-trade-journeys/{journey_id}/resale")
    suspend fun patchResaleTradeJourneyResale(
        @Path("user_id") userId: String,
        @Path("journey_id") journeyId: Long,
        @Body request: ResaleTradeJourneyPatchRequest,
    ): ResaleTradeJourneyResponse

    @PATCH("users/{user_id}/resale-trade-journeys/{journey_id}/sold")
    suspend fun patchResaleTradeJourneySold(
        @Path("user_id") userId: String,
        @Path("journey_id") journeyId: Long,
        @Body request: ResaleTradeJourneyPatchRequest,
    ): ResaleTradeJourneyResponse

    @GET("users/{user_id}/resale-trade-journeys/completed")
    suspend fun getCompletedResaleTradeJourneys(
        @Path("user_id") userId: String,
        @Query("limit") limit: Int = 200,
    ): ResaleTradeJourneyListResponse

    @GET("users/{user_id}/resale-trade-journeys/purchased")
    suspend fun getPurchasedResaleTradeJourneys(
        @Path("user_id") userId: String,
        @Query("limit") limit: Int = 200,
    ): ResaleTradeJourneyListResponse

    @PATCH("users/{user_id}/resale-trade-journeys/completed/delete-selected")
    suspend fun deleteSelectedCompletedResaleTradeJourneys(
        @Path("user_id") userId: String,
        @Body request: ResaleTradeJourneyDeleteSelectedRequest,
    ): ResaleTradeJourneyDeleteResponse

    @PATCH("users/{user_id}/resale-trade-journeys/completed/delete-all")
    suspend fun deleteAllCompletedResaleTradeJourneys(
        @Path("user_id") userId: String,
    ): ResaleTradeJourneyDeleteResponse

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
        @Query("user_id") userId: String,
        @Query("is_read") isRead: String = "0",
    ): AlertsResponse

    @PATCH("alert-events/{alert_event_id}/read")
    suspend fun markAlertEventRead(
        @Path("alert_event_id") alertEventId: Long,
        @Query("user_id") userId: String,
    ): MarkAlertReadResponse

    @POST("alert-events/{alert_event_id}/read")
    suspend fun markAlertEventReadPost(
        @Path("alert_event_id") alertEventId: Long,
        @Query("user_id") userId: String,
    ): MarkAlertReadResponse

    @PATCH("alert-events/read-all")
    suspend fun markAllAlertEventsRead(
        @Query("user_id") userId: String,
    ): MarkAllAlertsReadResponse

    @POST("alert-events/read-all")
    suspend fun markAllAlertEventsReadPost(
        @Query("user_id") userId: String,
    ): MarkAllAlertsReadResponse

    @GET("alert-events/read/grouped")
    suspend fun getGroupedReadAlerts(
        @Query("user_id") userId: String,
    ): GroupedReadAlertsResponse

    @PATCH("alert-events/read/archive/clear-all")
    suspend fun clearAllReadArchive(
        @Query("user_id") userId: String,
    ): ClearReadArchiveResponse

    @PATCH("alert-events/read/archive/clear-selected")
    suspend fun clearSelectedReadArchive(
        @Query("user_id") userId: String,
        @Body request: ClearSelectedReadArchiveRequest,
    ): ClearReadArchiveResponse

    @GET("user-fair-prices/recommended-keywords")
    suspend fun getRecommendedKeywords(
        @Query("product_type") productType: String,
        @Query("chip") chip: String,
        @Query("ram_gb") ramGb: Int?,
        @Query("ssd_gb") ssdGb: Int?
    ): RecommendedKeywordsResponse
}
