package com.boongtol.umtp_android.notification

import android.service.notification.NotificationListenerService
import android.util.Log

class UmtpNotificationListenerService : NotificationListenerService() {
    override fun onListenerConnected() {
        super.onListenerConnected()
        Log.d("UMTP_NOTIFICATION", "Notification Listener connected")
    }
}
