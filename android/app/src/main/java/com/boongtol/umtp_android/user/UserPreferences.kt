package com.boongtol.umtp_android.user

import android.content.Context
import android.content.SharedPreferences

class UserPreferences(context: Context) {
    private val prefs: SharedPreferences = context.getSharedPreferences("umtp_prefs", Context.MODE_PRIVATE)

    companion object {
        private const val KEY_USER_ID = "user_id"
        private const val KEY_IS_REGISTERED = "is_user_registered"
        private const val KEY_FCM_TOKEN = "fcm_token"
        private const val KEY_PUSH_TOKEN_REGISTERED = "push_token_registered"
    }

    fun getUserId(): String? {
        return prefs.getString(KEY_USER_ID, null)
    }

    fun setUserId(userId: String) {
        prefs.edit()
            .putString(KEY_USER_ID, userId)
            .putBoolean(KEY_IS_REGISTERED, true)
            .apply()
    }

    fun isRegistered(): Boolean {
        return prefs.getBoolean(KEY_IS_REGISTERED, false)
    }

    fun getFcmToken(): String? {
        return prefs.getString(KEY_FCM_TOKEN, null)
    }

    fun setFcmToken(token: String?) {
        prefs.edit().putString(KEY_FCM_TOKEN, token).apply()
    }

    fun isPushTokenRegistered(): Boolean {
        return prefs.getBoolean(KEY_PUSH_TOKEN_REGISTERED, false)
    }

    fun setPushTokenRegistered(registered: Boolean) {
        prefs.edit().putBoolean(KEY_PUSH_TOKEN_REGISTERED, registered).apply()
    }
}
