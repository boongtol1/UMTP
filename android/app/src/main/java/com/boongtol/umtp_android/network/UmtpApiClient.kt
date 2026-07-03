package com.boongtol.umtp_android.network

import android.util.Log
import com.boongtol.umtp_android.BuildConfig
import okhttp3.Dns
import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import java.net.InetAddress
import java.net.UnknownHostException

object UmtpApiClient {
    private const val TAG = "UmtpApiClient"
    private const val FALLBACK_BASE_URL = "https://umtp.duckdns.org/"
    private const val FALLBACK_API_HOST = "umtp.duckdns.org"
    private val FALLBACK_API_IPS = listOf("183.111.181.122")

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

    private val resilientDns = Dns { hostname ->
        try {
            Dns.SYSTEM.lookup(hostname)
        } catch (e: UnknownHostException) {
            if (!hostname.equals(FALLBACK_API_HOST, ignoreCase = true)) {
                throw e
            }
            Log.w(TAG, "System DNS failed for $hostname; using fallback API address", e)
            FALLBACK_API_IPS.map { InetAddress.getByName(it) }
        }
    }

    private val okHttpClient = OkHttpClient.Builder()
        .dns(resilientDns)
        .addInterceptor(loggingInterceptor)
        .build()

    private val retrofit: Retrofit = Retrofit.Builder()
        .baseUrl(baseUrl)
        .client(okHttpClient)
        .addConverterFactory(GsonConverterFactory.create())
        .build()

    val apiService: UmtpApiService = retrofit.create(UmtpApiService::class.java)
}
