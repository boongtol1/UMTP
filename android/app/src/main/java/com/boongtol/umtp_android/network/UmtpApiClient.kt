package com.boongtol.umtp_android.network

import android.util.Log
import com.boongtol.umtp_android.BuildConfig
import okhttp3.Dns
import okhttp3.HttpUrl.Companion.toHttpUrl
import okhttp3.HttpUrl.Companion.toHttpUrlOrNull
import okhttp3.OkHttpClient
import okhttp3.dnsoverhttps.DnsOverHttps
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import java.net.InetAddress
import java.net.UnknownHostException
import java.util.concurrent.TimeUnit

object UmtpApiClient {
    private const val TAG = "UmtpApiClient"
    private const val FALLBACK_BASE_URL = "https://umtp.duckdns.org/"

    private fun normalizeBaseUrl(raw: String?): String {
        val trimmed = raw?.trim().orEmpty()
        if (trimmed.isEmpty()) {
            return FALLBACK_BASE_URL
        }
        return if (trimmed.endsWith("/")) trimmed else "$trimmed/"
    }

    val baseUrl: String = normalizeBaseUrl(BuildConfig.UMTP_BASE_URL)
    private val baseHost: String? = baseUrl.toHttpUrlOrNull()?.host

    private val loggingInterceptor = HttpLoggingInterceptor().apply {
        level = HttpLoggingInterceptor.Level.BODY
    }

    private data class NamedDnsResolver(
        val name: String,
        val dns: Dns,
    )

    private val dnsLookupClient = OkHttpClient.Builder()
        .callTimeout(4, TimeUnit.SECONDS)
        .connectTimeout(4, TimeUnit.SECONDS)
        .readTimeout(4, TimeUnit.SECONDS)
        .build()

    private fun buildDnsOverHttpsResolver(
        name: String,
        url: String,
        vararg bootstrapHosts: String,
    ): NamedDnsResolver {
        return NamedDnsResolver(
            name = name,
            dns = DnsOverHttps.Builder()
                .client(dnsLookupClient)
                .url(url.toHttpUrl())
                .bootstrapDnsHosts(*bootstrapHosts.map { InetAddress.getByName(it) }.toTypedArray())
                .build(),
        )
    }

    private val dnsOverHttpsResolvers = listOf(
        buildDnsOverHttpsResolver(
            "Cloudflare",
            "https://cloudflare-dns.com/dns-query",
            "1.1.1.1",
            "1.0.0.1",
        ),
        buildDnsOverHttpsResolver(
            "Google",
            "https://dns.google/dns-query",
            "8.8.8.8",
            "8.8.4.4",
        ),
    )

    private fun shouldRetryWithDnsOverHttps(hostname: String): Boolean {
        return hostname.equals(baseHost, ignoreCase = true) ||
            hostname.endsWith(".duckdns.org", ignoreCase = true)
    }

    private val duckDnsAwareDns = object : Dns {
        override fun lookup(hostname: String): List<InetAddress> {
            return try {
                Dns.SYSTEM.lookup(hostname)
            } catch (systemException: UnknownHostException) {
                if (!shouldRetryWithDnsOverHttps(hostname)) {
                    throw systemException
                }
                Log.w(TAG, "System DNS failed for $hostname; retrying with DNS-over-HTTPS", systemException)
                var lastDnsOverHttpsException: UnknownHostException? = null
                for (resolver in dnsOverHttpsResolvers) {
                    try {
                        val addresses = resolver.dns.lookup(hostname)
                        Log.i(TAG, "Resolved $hostname with ${resolver.name} DNS-over-HTTPS")
                        return addresses
                    } catch (dnsOverHttpsException: UnknownHostException) {
                        lastDnsOverHttpsException?.let { dnsOverHttpsException.addSuppressed(it) }
                        lastDnsOverHttpsException = dnsOverHttpsException
                        Log.w(TAG, "${resolver.name} DNS-over-HTTPS failed for $hostname", dnsOverHttpsException)
                    }
                }
                val failure = lastDnsOverHttpsException ?: systemException
                if (failure !== systemException) {
                    failure.addSuppressed(systemException)
                }
                throw failure
            }
        }
    }

    private val okHttpClient = OkHttpClient.Builder()
        .dns(duckDnsAwareDns)
        .addInterceptor(loggingInterceptor)
        .build()

    private val retrofit: Retrofit = Retrofit.Builder()
        .baseUrl(baseUrl)
        .client(okHttpClient)
        .addConverterFactory(GsonConverterFactory.create())
        .build()

    val apiService: UmtpApiService = retrofit.create(UmtpApiService::class.java)
}
