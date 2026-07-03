package com.boongtol.umtp_android.network

import com.boongtol.umtp_android.BuildConfig
import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory

object UmtpApiClient {
    private const val FALLBACK_BASE_URL = "https://umtp.duckdns.org/"

    private fun normalizeBaseUrl(raw: String?): String {
        val trimmed = raw?.trim().orEmpty()
        if (trimmed.isEmpty()) {
            return FALLBACK_BASE_URL
        }
        return if (trimmed.endsWith("/")) trimmed else "$trimmed/"
    }

    val baseUrl: String = normalizeBaseUrl(BuildConfig.UMTP_BASE_URL)

    private val loggingInterceptor = HttpLoggingInterceptor().apply {
        level = HttpLoggingInterceptor.Level.BODY
    }

    private val okHttpClient = OkHttpClient.Builder()
        .addInterceptor(loggingInterceptor)
        .build()

    private val retrofit: Retrofit = Retrofit.Builder()
        .baseUrl(baseUrl)
        .client(okHttpClient)
        .addConverterFactory(GsonConverterFactory.create())
        .build()

    val apiService: UmtpApiService = retrofit.create(UmtpApiService::class.java)
}
