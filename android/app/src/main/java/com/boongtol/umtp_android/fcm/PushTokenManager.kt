package com.boongtol.umtp_android.fcm

import android.content.Context
import android.util.Log
import com.boongtol.umtp_android.network.PushTokenRequest
import com.boongtol.umtp_android.network.UmtpApiClient
import com.boongtol.umtp_android.user.UserPreferences
import com.google.firebase.messaging.FirebaseMessaging
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.tasks.await

class PushTokenManager(context: Context) {
    private val userPreferences = UserPreferences(context)
    private val apiService = UmtpApiClient.apiService
    private val scope = CoroutineScope(Dispatchers.IO)

    fun checkAndRegisterToken() {
        FirebaseMessaging.getInstance().token.addOnCompleteListener { task ->
            if (!task.isSuccessful) {
                Log.w("PushTokenManager", "Fetching FCM registration token failed", task.exception)
                return@addOnCompleteListener
            }

            val token = task.result
            val maskedToken = if (token.length > 10) {
                "${token.take(6)}...${token.takeLast(6)}"
            } else {
                "***"
            }
            Log.d("PushTokenManager", "FCM Token: $maskedToken")
            
            val savedToken = userPreferences.getFcmToken()
            if (savedToken != token) {
                userPreferences.setFcmToken(token)
                userPreferences.setPushTokenRegistered(false)
            }
            
            registerTokenToServerIfNeeded()
        }
    }

    fun registerTokenToServerIfNeeded() {
        val userId = userPreferences.getUserId()
        val token = userPreferences.getFcmToken()
        val alreadyRegistered = userPreferences.isPushTokenRegistered()

        if (userId != null && token != null && !alreadyRegistered) {
            scope.launch {
                try {
                    val response = apiService.registerPushToken(userId, PushTokenRequest(token = token))
                    Log.d("PushTokenManager", "Push token registered: ${response.message}")
                    userPreferences.setPushTokenRegistered(true)
                } catch (e: Exception) {
                    Log.e("PushTokenManager", "Failed to register push token", e)
                }
            }
        } else {
            if (userId == null) Log.d("PushTokenManager", "Skip registration: userId is null")
            if (token == null) Log.d("PushTokenManager", "Skip registration: token is null")
            if (alreadyRegistered) Log.d("PushTokenManager", "Skip registration: already registered")
        }
    }
    
    suspend fun getFreshToken(): String? {
        return try {
            FirebaseMessaging.getInstance().token.await()
        } catch (e: Exception) {
            Log.e("PushTokenManager", "Error getting fresh token", e)
            null
        }
    }
}
