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
        }
    }

    override fun onDestroy() {
        super.onDestroy()
        Log.d("UMTP_NOTIFICATION", "onDestroy")
    }
}
