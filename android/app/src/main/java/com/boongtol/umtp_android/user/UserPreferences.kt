package com.boongtol.umtp_android.user

import android.content.Context
import android.content.SharedPreferences

class UserPreferences(context: Context) {
    private val prefs: SharedPreferences = context.getSharedPreferences("umtp_prefs", Context.MODE_PRIVATE)

    companion object {
        private const val KEY_USER_ID = "user_id"
        private const val KEY_IS_REGISTERED = "is_user_registered"
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
}
