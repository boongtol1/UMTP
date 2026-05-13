package com.boongtol.umtp_android.notification

import android.service.notification.NotificationListenerService
import android.service.notification.StatusBarNotification
import android.util.Log

class UmtpNotificationListenerService : NotificationListenerService() {
    override fun onCreate() {
        super.onCreate()
        Log.d("UMTP_NOTIFICATION", "onCreate")
    }

    override fun onListenerConnected() {
        super.onListenerConnected()
        Log.d("UMTP_NOTIFICATION", "onListenerConnected")
    }

    override fun onListenerDisconnected() {
        super.onListenerDisconnected()
        Log.d("UMTP_NOTIFICATION", "onListenerDisconnected")
    }

    override fun onNotificationPosted(sbn: StatusBarNotification?) {
        super.onNotificationPosted(sbn)
        sbn?.let {
            val packageName = it.packageName
            val extras = it.notification.extras
            val title = extras.getString("android.title") ?: ""
            val text = extras.getCharSequence("android.text")?.toString() ?: ""
            val bigText = extras.getCharSequence("android.bigText")?.toString() ?: ""

            Log.d("UMTP_NOTIFICATION", "onNotificationPosted packageName=$packageName")
            Log.d("UMTP_NOTIFICATION", "  title=$title")
            Log.d("UMTP_NOTIFICATION", "  text=$text")
            if (bigText.isNotEmpty()) {
                Log.d("UMTP_NOTIFICATION", "  bigText=$bigText")
            }

            // Dump all extras for debugging and URL discovery
            try {
                Log.d("UMTP_NOTIFICATION", "========== notification extras dump start ==========")
                Log.d("UMTP_NOTIFICATION", "packageName=$packageName")
                for (key in extras.keySet()) {
                    val value = extras.get(key)
                    Log.d("UMTP_NOTIFICATION", "  extras[$key]=$value")
                }
                Log.d("UMTP_NOTIFICATION", "========== notification extras dump end ==========")
            } catch (e: Exception) {
                Log.e("UMTP_NOTIFICATION", "extras dump error", e)
            }
        }
    }

    override fun onDestroy() {
        super.onDestroy()
        Log.d("UMTP_NOTIFICATION", "onDestroy")
    }
}
