package com.boongtol.umtp_android.fcm

import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.os.Build
import android.util.Log
import androidx.core.app.NotificationCompat
import com.boongtol.umtp_android.MainActivity
import com.boongtol.umtp_android.R
import com.boongtol.umtp_android.user.UserPreferences
import com.google.firebase.messaging.FirebaseMessagingService
import com.google.firebase.messaging.RemoteMessage

class UMTPFirebaseMessagingService : FirebaseMessagingService() {

    companion object {
        private const val TAG = "UMTPFirebaseMsgService"
        private const val CHANNEL_ID = "umtp_alerts_channel"
        private const val CHANNEL_NAME = "UMTP 매물 알림"
    }

    override fun onNewToken(token: String) {
        super.onNewToken(token)
        Log.d(TAG, "Refreshed token: ${token.take(6)}...")
        
        val userPreferences = UserPreferences(applicationContext)
        userPreferences.setFcmToken(token)
        userPreferences.setPushTokenRegistered(false)
        
        // Try to register to server immediately if userId exists
        PushTokenManager(applicationContext).registerTokenToServerIfNeeded()
    }

    override fun onMessageReceived(remoteMessage: RemoteMessage) {
        super.onMessageReceived(remoteMessage)
        Log.d(TAG, "From: ${remoteMessage.from}")

        if (remoteMessage.data.isNotEmpty()) {
            Log.d(TAG, "Message data payload: ${remoteMessage.data}")
            handleNow(remoteMessage.data)
        }

        remoteMessage.notification?.let {
            Log.d(TAG, "Message Notification Body: ${it.body}")
            // If it has a standard notification payload, we might not need to do anything 
            // as OS handles it in background. But in foreground we want to show it.
            showNotification(
                it.title ?: "UMTP 새 매물 알림",
                it.body ?: "",
                remoteMessage.data["alert_id"]
            )
        }
    }

    private fun handleNow(data: Map<String, String>) {
        val alertId = data["alert_id"]
        val title = "UMTP 새 매물 알림"
        val listingTitle = data["listing_title"]
        val price = data["listing_price_krw"]
        val fraudText = resolveFraudProbabilityText(data)

        val body = buildString {
            if (listingTitle != null) append(listingTitle)
            if (price != null) {
                if (isNotEmpty()) append(" · ")
                append(formatPrice(price))
                append("원")
            }
            if (fraudText != null) {
                if (isNotEmpty()) append(" · ")
                append("사기 가능성 $fraudText")
            }
        }.ifEmpty { data["alert_reason_message"] ?: "새로운 매물이 등록되었습니다." }

        showNotification(title, body, alertId)
    }

    private fun resolveFraudProbabilityText(data: Map<String, String>): String? {
        data["fraud_probability_text"]?.trim()?.takeIf { it.isNotEmpty() }?.let {
            return it
        }

        val probability = data["fraud_probability"]?.toDoubleOrNull()
        val label = when (data["fraud_probability_label"]?.uppercase()) {
            "LOW" -> "낮음"
            "MEDIUM" -> "주의"
            "HIGH" -> "높음"
            else -> null
        }

        if (probability == null) {
            return label
        }

        val percentText = "${"%.0f".format(probability * 100)}%"
        return if (label == null) {
            percentText
        } else {
            "$label ($percentText)"
        }
    }

    private fun formatPrice(priceStr: String): String {
        return try {
            val price = priceStr.toLong()
            java.text.NumberFormat.getInstance(java.util.Locale.KOREA).format(price)
        } catch (e: Exception) {
            priceStr
        }
    }

    private fun showNotification(title: String, body: String, alertId: String?) {
        val notificationManager = getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                CHANNEL_ID,
                CHANNEL_NAME,
                NotificationManager.IMPORTANCE_HIGH
            )
            notificationManager.createNotificationChannel(channel)
        }

        val intent = Intent(this, MainActivity::class.java).apply {
            flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP
            if (alertId != null) {
                putExtra("alert_id", alertId)
            }
        }
        
        val pendingIntent = PendingIntent.getActivity(
            this, 
            alertId?.hashCode() ?: 0, 
            intent,
            PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT
        )

        val notificationBuilder = NotificationCompat.Builder(this, CHANNEL_ID)
            .setSmallIcon(R.drawable.ic_launcher_foreground) // Need to check if this exists or use a better one
            .setContentTitle(title)
            .setContentText(body)
            .setAutoCancel(true)
            .setContentIntent(pendingIntent)
            .setPriority(NotificationCompat.PRIORITY_HIGH)

        notificationManager.notify(alertId?.hashCode() ?: System.currentTimeMillis().toInt(), notificationBuilder.build())
    }
}
